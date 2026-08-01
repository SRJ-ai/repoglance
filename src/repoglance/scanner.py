"""Repository walker: collects per-file stats while honoring ignore rules.

When the target is a git repository, the file list comes from ``git ls-files``
so the user's ``.gitignore`` is respected for free. Otherwise we fall back to a
pruned ``os.walk``. Complexity is computed inline from the text we already read,
so every file is read exactly once.
"""
from __future__ import annotations

import fnmatch
import functools
import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .complexity import FuncScore, analyze_complexity
from .languages import lang_for
from .vendored import is_vendored

# Above this many files we default to process-based parallelism: complexity
# parsing is CPU-bound and the GIL prevents threads from using multiple cores.
_PROCESS_THRESHOLD = 400

# Directories never worth scanning (used only on the non-git fallback path).
IGNORE_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "env",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "dist", "build", "target", ".next", ".nuxt", "out", "coverage",
    ".idea", ".vscode", ".gradle", "vendor", "bower_components", ".cache",
    "site-packages", ".eggs",
}

# File suffixes that are binary / not source.
BINARY_EXT = {
    "png", "jpg", "jpeg", "gif", "bmp", "ico", "webp", "svg", "pdf",
    "zip", "gz", "tar", "tgz", "rar", "7z", "jar", "war", "class",
    "exe", "dll", "so", "dylib", "o", "a", "bin", "wasm",
    "mp3", "mp4", "mov", "avi", "wav", "flac", "webm",
    "ttf", "otf", "woff", "woff2", "eot",
    "pyc", "pyo", "lock", "db", "sqlite", "sqlite3",
}

TODO_MARKERS = ("TODO", "FIXME", "HACK", "XXX", "BUG", "OPTIMIZE")


@dataclass
class FileStat:
    path: str            # repo-relative, forward-slash
    language: str
    lines: int
    code_lines: int
    blank_lines: int
    comment_lines: int
    size_bytes: int


@dataclass
class Todo:
    path: str
    line: int
    marker: str
    text: str


@dataclass
class ScanResult:
    root: Path
    files: List[FileStat] = field(default_factory=list)
    todos: List[Todo] = field(default_factory=list)
    func_scores: List[FuncScore] = field(default_factory=list)
    skipped_binary: int = 0
    vendored_files: int = 0
    used_gitignore: bool = False
    contents: Dict[str, str] = field(default_factory=dict)  # rel -> text, for dedup
    cache_entries: Dict[str, dict] = field(default_factory=dict)  # updated cache
    ownership: Dict[str, dict] = field(default_factory=dict)  # rel -> {author, lines}

    @property
    def total_lines(self) -> int:
        return sum(f.lines for f in self.files)

    @property
    def total_code(self) -> int:
        return sum(f.code_lines for f in self.files)

    def by_language(self) -> Dict[str, Dict[str, int]]:
        """Aggregate code lines, file count and bytes per language."""
        agg: Dict[str, Dict[str, int]] = {}
        for f in self.files:
            d = agg.setdefault(f.language, {"code": 0, "files": 0, "bytes": 0})
            d["code"] += f.code_lines
            d["files"] += 1
            d["bytes"] += f.size_bytes
        return agg


# Line-comment prefixes by language (for blank/comment/code classification).
_COMMENT_PREFIX = {
    "Python": ("#",), "Ruby": ("#",), "Shell": ("#",), "YAML": ("#",),
    "PowerShell": ("#",), "R": ("#",), "Makefile": ("#",), "TOML": ("#",),
    "JavaScript": ("//",), "TypeScript": ("//",),
    "Go": ("//",), "Rust": ("//",), "Java": ("//",),
    "C": ("//",), "C++": ("//",), "C#": ("//",),
    "PHP": ("//", "#"), "Swift": ("//",),
    "SCSS": ("//",),
}

# Languages that use C-style /* ... */ block comments.
_BLOCK_COMMENT_LANGS = {
    "JavaScript", "TypeScript", "Go", "Rust", "Java", "C", "C++", "C#",
    "PHP", "Swift", "CSS", "SCSS", "Kotlin", "Scala", "Dart",
}

# Line-comment tokens used to confine TODO scanning to comments.
_LINE_COMMENT = {
    "Python": ("#",), "Ruby": ("#",), "Shell": ("#",), "YAML": ("#",),
    "PowerShell": ("#",), "R": ("#",), "TOML": ("#",), "Makefile": ("#",),
    "JavaScript": ("//",), "TypeScript": ("//",), "Go": ("//",), "Rust": ("//",),
    "Java": ("//",), "C": ("//",), "C++": ("//",), "C#": ("//",),
    "PHP": ("//", "#"), "Swift": ("//",), "SCSS": ("//",), "Kotlin": ("//",),
    "Scala": ("//",), "Dart": ("//",), "Lua": ("--",), "SQL": ("--",),
}


def _count_lines(text: str, language: str):
    """Classify lines into total/code/blank/comment, handling /* */ blocks."""
    prefixes = _COMMENT_PREFIX.get(language, ())
    has_block = language in _BLOCK_COMMENT_LANGS
    total = blank = comment = 0
    in_block = False
    for raw in text.splitlines():
        total += 1
        stripped = raw.strip()
        if not stripped:
            blank += 1
            continue
        if in_block:
            comment += 1
            if "*/" in stripped:
                in_block = False
            continue
        if has_block and stripped.startswith("/*"):
            comment += 1
            if "*/" not in stripped[2:]:
                in_block = True
            continue
        if prefixes and stripped.startswith(prefixes):
            comment += 1
            continue
    code = total - blank - comment
    return total, code, blank, comment


def changed_files(root: os.PathLike, since_rev: str) -> Optional[set]:
    """Repo-relative paths changed since ``since_rev`` (for --since / diff mode)."""
    root_path = Path(root).resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(root_path), "diff", "--name-only", since_rev, "--"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def _git_tracked(root: Path) -> Optional[List[str]]:
    """Return repo-relative paths git considers part of the tree (honoring
    .gitignore), or ``None`` when ``root`` is not a git repository."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others",
             "--exclude-standard"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return [line for line in out.stdout.splitlines() if line]


def _glob_ok(rel: str, include, exclude) -> bool:
    """Apply include/exclude glob patterns (fnmatch) to a repo-relative path."""
    if exclude and any(fnmatch.fnmatch(rel, p) for p in exclude):
        return False
    return not (include and not any(fnmatch.fnmatch(rel, p) for p in include))


def scan(
    root: os.PathLike,
    max_bytes: int = 2_000_000,
    extra_ignores: Optional[set] = None,
    include: Optional[Iterable[str]] = None,
    exclude: Optional[Iterable[str]] = None,
    changed_only: Optional[set] = None,
    jobs: Optional[int] = None,
    include_vendored: bool = False,
    keep_contents: bool = False,
    cache_data: Optional[dict] = None,
    processes: Optional[bool] = None,
) -> ScanResult:
    """Walk ``root`` and gather per-file line/language/complexity stats.

    Files are processed in a thread pool (I/O-bound), so ordering is restored by
    sorting the results afterwards for stable output.
    """
    root_path = Path(root).resolve()
    result = ScanResult(root=root_path)
    ignore = IGNORE_DIRS | (extra_ignores or set())
    include = list(include) if include else None
    exclude = list(exclude) if exclude else None

    tracked = _git_tracked(root_path)
    if tracked is not None:
        result.used_gitignore = True
        candidates = [
            root_path / rel for rel in tracked
            if not (extra_ignores and any(p in extra_ignores for p in rel.split("/")))
        ]
    else:
        candidates = _walk(root_path, ignore)

    todo = _select_files(candidates, root_path, changed_only, include, exclude, result)

    # Incremental cache: reuse unchanged files (skipped when contents are needed
    # for dedup, since the cache does not store file text).
    use_cache = cache_data is not None and not keep_contents
    to_parse: List[Path] = []
    if use_cache:
        from . import cache as _cache
        for full in todo:
            rel = full.relative_to(root_path).as_posix()
            try:
                st = full.stat()
            except OSError:
                continue
            entry = cache_data.get(rel)
            if entry and entry.get("mtime") == st.st_mtime and entry.get("size") == st.st_size:
                stat, todos, scores, vendored = _cache.rebuild(rel, entry)
                result.cache_entries[rel] = entry
                _absorb(result, stat, todos, scores, vendored, include_vendored, None, keep_contents)
            else:
                to_parse.append(full)
    else:
        to_parse = todo

    processed = _parallel_process(to_parse, root_path, max_bytes, keep_contents, jobs, processes)

    for full, item in zip(to_parse, processed):
        if item is None:
            continue
        stat, todos, scores, text, vendored = item
        if cache_data is not None:
            from . import cache as _cache
            try:
                mtime = full.stat().st_mtime
            except OSError:
                mtime = 0
            result.cache_entries[stat.path] = _cache.entry_from(stat, todos, scores, vendored, mtime)
        _absorb(result, stat, todos, scores, vendored, include_vendored, text if keep_contents else None, keep_contents)

    # Deterministic output regardless of thread completion order.
    result.files.sort(key=lambda f: f.path)
    result.todos.sort(key=lambda t: (t.path, t.line))
    return result


def _select_files(candidates, root_path, changed_only, include, exclude, result) -> List[Path]:
    """Filter candidate paths to the source files we will actually parse."""
    todo: List[Path] = []
    for full in candidates:
        fn = full.name
        ext = fn.rsplit(".", 1)[-1] if "." in fn else ""
        if ext.lower() in BINARY_EXT:
            result.skipped_binary += 1
            continue
        if not lang_for(ext, fn):
            continue
        rel = full.relative_to(root_path).as_posix()
        if changed_only is not None and rel not in changed_only:
            continue
        if not _glob_ok(rel, include, exclude):
            continue
        todo.append(full)
    return todo


def _absorb(result, stat, todos, scores, vendored, include_vendored, text, keep_contents) -> None:
    """Add one processed/cached file's results into the ScanResult."""
    if vendored and not include_vendored:
        result.vendored_files += 1
        return
    result.files.append(stat)
    result.todos.extend(todos)
    result.func_scores.extend(scores)
    if keep_contents and text is not None:
        result.contents[stat.path] = text


def _parallel_process(to_parse, root_path, max_bytes, keep_contents, jobs, processes):
    """Analyze files in parallel. Uses processes for large, CPU-bound scans so
    complexity parsing actually spreads across cores (threads can't, due to the
    GIL); falls back to threads for small scans or when contents must be kept."""
    if not to_parse:
        return []
    worker = functools.partial(
        _process_file, root_path=root_path, max_bytes=max_bytes, keep_contents=keep_contents,
    )
    use_proc = processes if processes is not None else (
        not keep_contents and len(to_parse) >= _PROCESS_THRESHOLD and (os.cpu_count() or 1) > 1
    )
    if use_proc:
        try:
            workers = jobs or min(8, os.cpu_count() or 2)
            with ProcessPoolExecutor(max_workers=workers) as pool:
                return list(pool.map(worker, to_parse, chunksize=16))
        except Exception:
            pass  # fall back to threads if the process pool cannot start
    workers = jobs or min(32, (os.cpu_count() or 4) * 4)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(worker, to_parse))


def _process_file(full: Path, root_path: Path, max_bytes: int, keep_contents: bool = False):
    """Read and analyze one file. Returns (FileStat, todos, scores, text, vendored)
    or None. Top-level and picklable so it works with a process pool."""
    fn = full.name
    ext = fn.rsplit(".", 1)[-1] if "." in fn else ""
    language = lang_for(ext, fn)
    try:
        size = full.stat().st_size
        if size > max_bytes:
            return None
        text = full.read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        return None

    rel = full.relative_to(root_path).as_posix()
    total, code, blank, comment = _count_lines(text, language)
    stat = FileStat(rel, language, total, code, blank, comment, size)
    vendored = is_vendored(rel, text)
    todos: List[Todo] = []
    scores: List[FuncScore] = []
    if not vendored:
        _collect_todos(text, rel, language, todos)
        _score_complexity(text, rel, language, scores)
    # Avoid shipping file text back across a process boundary unless needed.
    return stat, todos, scores, (text if keep_contents else None), vendored


def _walk(root_path: Path, ignore: set):
    """Return file paths under ``root_path``, pruning ignored directories."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        dirnames[:] = [d for d in dirnames if d not in ignore and not d.startswith(".git")]
        for fn in filenames:
            out.append(Path(dirpath) / fn)
    return out


def _score_complexity(text: str, rel: str, language: str, out: List[FuncScore]) -> None:
    """Compute complexity from already-read text (no second file read)."""
    out.extend(analyze_complexity(text, rel, language))


def _collect_todos(text: str, rel: str, language: str, out: List[Todo]) -> None:
    prefixes = _LINE_COMMENT.get(language)
    if not prefixes:
        # No reliable line-comment syntax (markup/data/prose) — skip to avoid
        # false positives from documentation that merely mentions the markers.
        return
    for i, line in enumerate(text.splitlines(), start=1):
        starts = [line.find(p) for p in prefixes if line.find(p) != -1]
        if not starts:
            continue
        comment_part = line[min(starts):]
        upper = comment_part.upper()
        for marker in TODO_MARKERS:
            idx = upper.find(marker)
            if idx == -1:
                continue
            before = upper[idx - 1] if idx > 0 else " "
            after_idx = idx + len(marker)
            after = upper[after_idx] if after_idx < len(upper) else " "
            if before.isalnum() or after.isalnum():
                continue
            out.append(Todo(rel, i, marker, comment_part[idx:].strip()[:120]))
            break
