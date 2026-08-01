"""Repository health scoring — a transparent 0-100 composite grade.

Every sub-score is a simple, explainable function of numbers already gathered
during the scan, so the grade is auditable rather than a black box.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .complexity import rank_hotspots
from .scanner import ScanResult


@dataclass
class Health:
    score: int             # 0-100
    grade: str             # A-F
    factors: List[tuple]   # (name, points, max_points, detail)


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def compute(res: ScanResult) -> Health:
    """Compute a weighted health score from four cheap, honest signals."""
    factors: List[tuple] = []

    # 1. Documentation: comment lines as a share of code (capped, 25 pts).
    code = res.total_code or 1
    comments = sum(f.comment_lines for f in res.files)
    ratio = comments / code
    doc_pts = min(25, round(ratio / 0.15 * 25))  # 15%+ comments = full marks
    factors.append(("Documentation", doc_pts, 25, f"{ratio * 100:.1f}% comment ratio"))

    # 2. Complexity: penalize the worst hotspot (25 pts).
    worst = rank_hotspots(res, top=1)
    top_cx = worst[0].complexity if worst else 0
    # 10 or below = full; 40+ = zero. Linear in between.
    cx_pts = max(0, min(25, round((40 - top_cx) / 30 * 25)))
    factors.append(("Complexity", cx_pts, 25, f"worst function = {top_cx}"))

    # 3. TODO debt: markers per 1k lines of code (25 pts).
    density = len(res.todos) / (code / 1000)
    # 0 = full; 20+ per kloc = zero.
    todo_pts = max(0, min(25, round((20 - density) / 20 * 25)))
    factors.append(("TODO debt", todo_pts, 25, f"{density:.1f} markers / kloc"))

    # 4. File size discipline: share of files under 400 code lines (25 pts).
    if res.files:
        small = sum(1 for f in res.files if f.code_lines <= 400)
        share = small / len(res.files)
    else:
        share = 1.0
    size_pts = round(share * 25)
    factors.append(("File size", size_pts, 25, f"{share * 100:.0f}% files <= 400 loc"))

    score = sum(p for _, p, _, _ in factors)
    return Health(score=score, grade=_grade(score), factors=factors)


def maintainability_index(res) -> int:
    """Approximate Microsoft Maintainability Index (0-100), averaged over
    functions and weighted by size. Uses lizard's token/nloc counts as a
    Halstead-volume proxy. Returns 100 when there is nothing to measure.
    """
    import math

    total_w = 0.0
    acc = 0.0
    for s in res.func_scores:
        nloc = max(s.nloc, 1)
        tokens = max(s.tokens, 1)
        volume = tokens * math.log2(tokens + 1)
        mi = 171 - 5.2 * math.log(volume) - 0.23 * s.complexity - 16.2 * math.log(nloc)
        mi = max(0.0, min(100.0, mi * 100.0 / 171.0))
        acc += mi * nloc
        total_w += nloc
    if total_w == 0:
        return 100
    return round(acc / total_w)
