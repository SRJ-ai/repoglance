"""Repository walker: collects per-file stats while honoring ignore rules.

When the target is a git repository, the file list comes from ``git ls-files``
so the user's ``.gitignore`` is respected for free. Otherwise we fall back to a
pruned ``os.walk``. Complexity is computed inline from the text we already read,
so every file is read exactly once.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .complexity import FuncScore, heuristic_complexity, python_complexity, NON_CODE_LANGS
from .languages import lang_for

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
    used_gitignore: bool = False

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


def _git_tracked(root: Path) -> Optional[List[str]]:
    """Return repo-relative paths git considers part of the tree (honoring
    .gitignore), or ``None`` when ``root`` is not a git repository."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others",
             "--exclude-standard"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return [line for line in out.stdout.splitlines() if line]


def scan(
    root: os.PathLike,
    max_bytes: int = 2_000_000,
    extra_ignores: Optional[set] = None,
) -> ScanResult:
    """Walk ``root`` and gather per-file line/language/complexity stats."""
    root_path = Path(root).resolve()
    result = ScanResult(root=root_path)
    ignore = IGNORE_DIRS | (extra_ignores or set())

    tracked = _git_tracked(root_path)
    if tracked is not None:
        result.used_gitignore = True
        paths = []
        for rel in tracked:
            # Still honor explicit extra ignores on the git path.
            if extra_ignores and any(part in extra_ignores for part in rel.split("/")):
                continue
            paths.append(root_path / rel)
    else:
        paths = _walk(root_path, ignore)

    for full in paths:
        fn = full.name
        ext = fn.rsplit(".", 1)[-1] if "." in fn else ""
        if ext.lower() in BINARY_EXT:
            result.skipped_binary += 1
            continue
        language = lang_for(ext, fn)
        if not language:
            continue
        try:
            size = full.stat().st_size
            if size > max_bytes:
                continue
            text = full.read_text(encoding="utf-8", errors="ignore")
        except (OSError, ValueError):
            continue

        rel = full.relative_to(root_path).as_posix()
        total, code, blank, comment = _count_lines(text, language)
        result.files.append(FileStat(rel, language, total, code, blank, comment, size))
        _collect_todos(text, rel, language, result.todos)
        _score_complexity(text, rel, language, result.func_scores)

    return result


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
    if language == "Python":
        out.extend(python_complexity(text, rel))
    elif language not in NON_CODE_LANGS:
        score = heuristic_complexity(text, rel)
        if score > 1:
            out.append(FuncScore(rel, "(file)", 1, score))


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
