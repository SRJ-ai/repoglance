"""Incremental analysis cache keyed by path + mtime + size.

Unchanged files are reused from a JSON cache instead of being re-read and
re-parsed, which makes repeated runs on large repositories much faster.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from .complexity import FuncScore
from .scanner import FileStat, Todo

CACHE_VERSION = 1


def load(path: Optional[Path]) -> Dict[str, dict]:
    if not path or not Path(path).is_file():
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}
    if data.get("version") != CACHE_VERSION:
        return {}
    return data.get("entries", {})


def save(path: Optional[Path], entries: Dict[str, dict]) -> None:
    if not path:
        return
    try:
        Path(path).write_text(
            json.dumps({"version": CACHE_VERSION, "entries": entries}),
            encoding="utf-8",
        )
    except OSError:
        pass


def entry_from(stat: FileStat, todos, scores, vendored: bool, mtime: float) -> dict:
    return {
        "mtime": mtime,
        "size": stat.size_bytes,
        "stat": [stat.language, stat.lines, stat.code_lines, stat.blank_lines, stat.comment_lines],
        "vendored": vendored,
        "todos": [[t.line, t.marker, t.text] for t in todos],
        "scores": [[s.name, s.line, s.complexity, s.nloc, s.tokens, s.params] for s in scores],
    }


def rebuild(rel: str, entry: dict):
    """Reconstruct (FileStat, todos, scores, vendored) from a cache entry."""
    lang, lines, code, blank, comment = entry["stat"]
    stat = FileStat(rel, lang, lines, code, blank, comment, entry["size"])
    todos = [Todo(rel, l, m, t) for l, m, t in entry["todos"]]
    scores = [FuncScore(rel, n, ln, cx, nloc, tok, pr) for n, ln, cx, nloc, tok, pr in entry["scores"]]
    return stat, todos, scores, entry.get("vendored", False)
