#!/usr/bin/env python
"""Reproducible timing for repoglance.

Usage:
    python benchmarks/bench.py <path> [--cache]

Prints files, lines of code, and wall-clock time for a scan. Pass --cache to
measure a warm run through the incremental cache.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run(target: str, use_cache: bool) -> None:
    args = [sys.executable, "-m", "repoglance", target, "--no-git", "--json"]
    cache_file = None
    if use_cache:
        cache_file = str(Path(tempfile.gettempdir()) / "repoglance-bench.cache")
        args += ["--cache", cache_file]
        subprocess.run(args, capture_output=True)  # warm the cache first

    start = time.time()
    proc = subprocess.run(args, capture_output=True, text=True)
    elapsed = time.time() - start

    data = json.loads(proc.stdout)
    loc = data["total_code_lines"]
    files = data["total_files"]
    rate = loc / elapsed if elapsed else 0
    label = "cached" if use_cache else "cold"
    print(f"{target}: {files} files, {loc:,} loc — {elapsed:.2f}s ({label}, {rate:,.0f} loc/s)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    path = sys.argv[1]
    run(path, use_cache="--cache" in sys.argv[2:])
