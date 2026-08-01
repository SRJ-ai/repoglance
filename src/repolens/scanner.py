"""Repository walker: collects per-file stats while honoring ignore rules."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .languages import lang_for

# Directories never worth scanning.
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
    skipped_binary: int = 0

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


# Comment prefixes by language (single-line only; good enough for stats).
_COMMENT_PREFIX = {
    "Python": ("#",), "Ruby": ("#",), "Shell": ("#",), "YAML": ("#",),
    "PowerShell": ("#",), "R": ("#",), "Makefile": ("#",), "TOML": ("#",),
    "JavaScript": ("//", "/*", "*"), "TypeScript": ("//", "/*", "*"),
    "Go": ("//", "/*", "*"), "Rust": ("//", "/*", "*"), "Java": ("//", "/*", "*"),
    "C": ("//", "/*", "*"), "C++": ("//", "/*", "*"), "C#": ("//", "/*", "*"),
    "PHP": ("//", "#", "/*", "*"), "Swift": ("//", "/*", "*"),
    "CSS": ("/*", "*"), "SCSS": ("//", "/*", "*"),
}


def _count_lines(text: str, language: str):
    prefixes = _COMMENT_PREFIX.get(language, ())
    total = blank = comment = 0
    for raw in text.splitlines():
        total += 1
        stripped = raw.strip()
        if not stripped:
            blank += 1
        elif prefixes and stripped.startswith(prefixes):
            comment += 1
    code = total - blank - comment
    return total, code, blank, comment


def scan(
    root: os.PathLike,
    max_bytes: int = 2_000_000,
    extra_ignores: Optional[set] = None,
) -> ScanResult:
    """Walk ``root`` and gather per-file line/language stats plus TODO markers."""
    root_path = Path(root).resolve()
    result = ScanResult(root=root_path)
    ignore = IGNORE_DIRS | (extra_ignores or set())

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune ignored dirs in place so os.walk skips descending them.
        dirnames[:] = [d for d in dirnames if d not in ignore and not d.startswith(".git")]
        for fn in filenames:
            ext = fn.rsplit(".", 1)[-1] if "." in fn else ""
            if ext.lower() in BINARY_EXT:
                result.skipped_binary += 1
                continue
            language = lang_for(ext, fn)
            if not language:
                continue
            full = Path(dirpath) / fn
            try:
                size = full.stat().st_size
                if size > max_bytes:
                    continue
                text = full.read_text(encoding="utf-8", errors="ignore")
            except (OSError, ValueError):
                continue

            rel = full.relative_to(root_path).as_posix()
            total, code, blank, comment = _count_lines(text, language)
            result.files.append(
                FileStat(rel, language, total, code, blank, comment, size)
            )
            _collect_todos(text, rel, language, result.todos)

    return result


# Line-comment tokens per language, used to confine TODO scanning to comments so
# marker *words* in prose or code (e.g. "TODO tracker", a marker list) aren't
# counted as debt.
_LINE_COMMENT = {
    "Python": ("#",), "Ruby": ("#",), "Shell": ("#",), "YAML": ("#",),
    "PowerShell": ("#",), "R": ("#",), "TOML": ("#",), "Makefile": ("#",),
    "JavaScript": ("//",), "TypeScript": ("//",), "Go": ("//",), "Rust": ("//",),
    "Java": ("//",), "C": ("//",), "C++": ("//",), "C#": ("//",),
    "PHP": ("//", "#"), "Swift": ("//",), "SCSS": ("//",), "Kotlin": ("//",),
    "Scala": ("//",), "Dart": ("//",), "Lua": ("--",), "SQL": ("--",),
}


def _collect_todos(text: str, rel: str, language: str, out: List[Todo]) -> None:
    prefixes = _LINE_COMMENT.get(language)
    if not prefixes:
        # No reliable line-comment syntax (markup/data/prose) — skip to avoid
        # false positives from documentation that merely mentions the markers.
        return
    for i, line in enumerate(text.splitlines(), start=1):
        # Only consider the portion of the line inside a line comment.
        starts = [line.find(p) for p in prefixes if line.find(p) != -1]
        if not starts:
            continue
        comment_part = line[min(starts):]
        upper = comment_part.upper()
        for marker in TODO_MARKERS:
            idx = upper.find(marker)
            if idx == -1:
                continue
            # Require non-alphanumeric boundaries so "DEBUG" != "BUG" etc.
            before = upper[idx - 1] if idx > 0 else " "
            after_idx = idx + len(marker)
            after = upper[after_idx] if after_idx < len(upper) else " "
            if before.isalnum() or after.isalnum():
                continue
            out.append(Todo(rel, i, marker, comment_part[idx:].strip()[:120]))
            break
