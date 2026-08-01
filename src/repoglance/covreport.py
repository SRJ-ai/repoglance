"""Parse coverage reports (Cobertura XML or lcov) into per-file percentages,
then cross them with complexity to surface high-risk, low-coverage code.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional


def parse_coverage(path: Path) -> Dict[str, float]:
    """Return {relative_path: coverage_fraction} from a coverage.xml or .lcov."""
    text = _read(path)
    if not text:
        return {}
    if text.lstrip().startswith("<"):
        return _parse_cobertura(text)
    return _parse_lcov(text)


def _read(path: Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _norm(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def _parse_cobertura(text: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return out
    for cls in root.iter("class"):
        filename = cls.get("filename")
        rate = cls.get("line-rate")
        if filename and rate is not None:
            try:
                out[_norm(filename)] = float(rate)
            except ValueError:
                pass
    return out


_LCOV_SF = re.compile(r"^SF:(.+)$")
_LCOV_DA = re.compile(r"^DA:\d+,(\d+)")


def _parse_lcov(text: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    cur = None
    total = hit = 0
    for line in text.splitlines():
        m = _LCOV_SF.match(line)
        if m:
            cur, total, hit = _norm(m.group(1)), 0, 0
            continue
        d = _LCOV_DA.match(line)
        if d and cur is not None:
            total += 1
            if int(d.group(1)) > 0:
                hit += 1
        elif line.strip() == "end_of_record" and cur is not None:
            if total:
                out[cur] = hit / total
            cur = None
    return out


def risk_by_coverage(res, coverage: Dict[str, float], top: int = 15) -> List[dict]:
    """Files ranked by complexity while poorly covered (complexity x (1-cov))."""
    from .analytics import file_worst_complexity

    worst = file_worst_complexity(res)
    # Match coverage paths to scanned paths by suffix (coverage tools vary).
    cov_index = dict(coverage)
    rows = []
    for path, cx in worst.items():
        cov = _lookup(path, cov_index)
        if cov is None:
            continue
        rows.append({
            "path": path, "complexity": cx,
            "coverage": round(cov, 3), "risk": round(cx * (1 - cov), 2),
        })
    rows.sort(key=lambda r: r["risk"], reverse=True)
    return rows[:top]


def _lookup(path: str, cov_index: Dict[str, float]) -> Optional[float]:
    if path in cov_index:
        return cov_index[path]
    for k, v in cov_index.items():
        if k.endswith(path) or path.endswith(k):
            return v
    return None
