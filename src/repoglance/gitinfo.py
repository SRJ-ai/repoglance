"""Optional git-history insights. Degrades gracefully when git is absent."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class GitStats:
    total_commits: int
    contributors: List[tuple]      # (name, commit_count), sorted desc
    hot_files: List[tuple]         # (path, change_count), sorted desc
    first_commit: str
    last_commit: str
    active_days: int               # distinct YYYY-MM-DD with commits


def _run(root: Path, args: List[str]) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def owners(root: Path, paths: List[str]) -> dict:
    """Map each path to its dominant author via ``git blame`` (best-effort)."""
    result: dict = {}
    for rel in paths:
        out = _run(root, ["blame", "--line-porcelain", "HEAD", "--", rel])
        if not out:
            continue
        counts: dict = {}
        for line in out.splitlines():
            if line.startswith("author "):
                name = line[len("author "):].strip()
                counts[name] = counts.get(name, 0) + 1
        if counts:
            top = max(counts.items(), key=lambda kv: kv[1])
            result[rel] = {"author": top[0], "lines": top[1]}
    return result


def collect(root: Path) -> Optional[GitStats]:
    """Return git statistics, or ``None`` if ``root`` is not a git repo."""
    if _run(root, ["rev-parse", "--is-inside-work-tree"]) is None:
        return None

    count_raw = _run(root, ["rev-list", "--count", "HEAD"])
    total_commits = int(count_raw.strip()) if count_raw and count_raw.strip().isdigit() else 0
    if total_commits == 0:
        return None

    authors: dict = {}
    for line in (_run(root, ["log", "--format=%an"]) or "").splitlines():
        name = line.strip()
        if name:
            authors[name] = authors.get(name, 0) + 1
    contributors = sorted(authors.items(), key=lambda kv: kv[1], reverse=True)

    files: dict = {}
    for line in (_run(root, ["log", "--name-only", "--format="]) or "").splitlines():
        p = line.strip()
        if p:
            files[p] = files.get(p, 0) + 1
    hot_files = sorted(files.items(), key=lambda kv: kv[1], reverse=True)

    days = {
        line.strip()
        for line in (_run(root, ["log", "--format=%cd", "--date=short"]) or "").splitlines()
        if line.strip()
    }

    first = (_run(root, ["log", "--reverse", "--format=%cd", "--date=short"]) or "").splitlines()
    last = (_run(root, ["log", "-1", "--format=%cd", "--date=short"]) or "").strip()

    return GitStats(
        total_commits=total_commits,
        contributors=contributors[:10],
        hot_files=hot_files[:10],
        first_commit=first[0].strip() if first else "?",
        last_commit=last or "?",
        active_days=len(days),
    )
