"""Token-light duplicate-code detection via sliding line-window hashing.

Normalizes each line (strips whitespace, drops trivial lines) and hashes windows
of consecutive lines. Windows that hash-collide across different locations are
reported as duplicated blocks. Cheap, language-agnostic, good enough to surface
copy-paste without a full clone-detection engine.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

_MIN_LINE_LEN = 3  # ignore lines like "}", ")" that create noise


@dataclass
class DuplicateBlock:
    lines: int
    occurrences: List[Tuple[str, int]] = field(default_factory=list)  # (path, start_line)


@dataclass
class DedupResult:
    blocks: List[DuplicateBlock]
    duplicated_lines: int
    total_lines: int

    @property
    def ratio(self) -> float:
        if not self.total_lines:
            return 0.0
        return min(1.0, self.duplicated_lines / self.total_lines)


def _normalize(line: str) -> str:
    return " ".join(line.split())


def detect_duplicates(contents: Dict[str, str], window: int = 6, top: int = 10) -> DedupResult:
    """Find duplicated ``window``-line blocks across ``contents`` (path -> text)."""
    seen: Dict[str, List[Tuple[str, int]]] = {}
    total_lines = 0

    for path, text in contents.items():
        norm = []
        for i, raw in enumerate(text.splitlines(), start=1):
            n = _normalize(raw)
            norm.append((i, n if len(n) >= _MIN_LINE_LEN else ""))
        total_lines += len(norm)
        for start in range(0, len(norm) - window + 1):
            chunk = norm[start:start + window]
            if any(c == "" for _, c in chunk):
                continue  # skip windows containing trivial/blank lines
            digest = hashlib.blake2b(
                "\n".join(c for _, c in chunk).encode("utf-8"), digest_size=16
            ).hexdigest()
            seen.setdefault(digest, []).append((path, chunk[0][0]))

    blocks: List[DuplicateBlock] = []
    duplicated_lines = 0
    for occurrences in seen.values():
        if len(occurrences) < 2:
            continue
        blocks.append(DuplicateBlock(lines=window, occurrences=occurrences))
        duplicated_lines += window * (len(occurrences) - 1)

    blocks.sort(key=lambda b: len(b.occurrences), reverse=True)
    return DedupResult(blocks=blocks[:top], duplicated_lines=duplicated_lines,
                       total_lines=total_lines)
