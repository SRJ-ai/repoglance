"""Higher-level analytics computed from a completed scan.

Everything here reuses data already gathered during the scan (complexity, git
churn, per-function flags), except the import graph which re-parses Python files
on demand.
"""
from __future__ import annotations

import ast
from typing import Dict, List, Optional


def file_worst_complexity(res) -> Dict[str, int]:
    """Highest function complexity per file."""
    worst: Dict[str, int] = {}
    for s in res.func_scores:
        if s.complexity > worst.get(s.path, 0):
            worst[s.path] = s.complexity
    return worst


def risk_ranking(res, git, top: int = 15) -> List[dict]:
    """Rank files by churn x complexity — frequently changed *and* complex code.

    This is the classic "where should I actually spend refactoring effort"
    signal (Michael Feathers). Needs git history; returns [] without it.
    """
    if not git:
        return []
    churn = dict(git.hot_files)
    worst = file_worst_complexity(res)
    rows = []
    for path, cx in worst.items():
        c = churn.get(path, 0)
        if c and cx:
            rows.append({"path": path, "complexity": cx, "churn": c, "risk": cx * c})
    rows.sort(key=lambda r: r["risk"], reverse=True)
    return rows[:top]


def longest_functions(res, top: int = 10) -> List[dict]:
    """Functions with the most logical lines of code."""
    ranked = sorted(res.func_scores, key=lambda s: s.nloc, reverse=True)
    return [
        {"name": s.name, "path": s.path, "line": s.line, "nloc": s.nloc, "complexity": s.complexity}
        for s in ranked[:top] if s.nloc > 0
    ]


def python_quality(res) -> Optional[dict]:
    """Docstring and type-hint coverage across analyzed Python functions."""
    py = [s for s in res.func_scores if s.is_python]
    if not py:
        return None
    total = len(py)
    documented = sum(1 for s in py if s.has_doc)
    typed = sum(1 for s in py if s.typed)
    return {
        "functions": total,
        "documented": documented,
        "typed": typed,
        "doc_coverage": round(documented / total, 3),
        "type_coverage": round(typed / total, 3),
    }


def _module_name(rel: str) -> str:
    p = rel[:-3] if rel.endswith(".py") else rel
    parts = [seg for seg in p.split("/") if seg]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def import_graph(res, max_cycles: int = 10) -> Optional[dict]:
    """Build an intra-repo Python import graph and detect circular imports."""
    py_files = [f for f in res.files if f.language == "Python"]
    if not py_files:
        return None
    modules = {_module_name(f.path): f.path for f in py_files}
    edges: Dict[str, set] = {m: set() for m in modules}

    for f in py_files:
        src_mod = _module_name(f.path)
        try:
            tree = ast.parse((res.root / f.path).read_text(encoding="utf-8", errors="ignore"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Import):
                targets = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                targets = _resolve_from(node, src_mod)
            for name in targets:
                # Link to the longest repo module that is a prefix of the import.
                hit = _match_module(name, modules)
                if hit and hit != src_mod:
                    edges[src_mod].add(hit)

    cycles = _find_cycles(edges, max_cycles)
    return {
        "modules": len(modules),
        "edges": sum(len(v) for v in edges.values()),
        "circular": cycles,
    }


def _resolve_from(node, src_mod: str) -> List[str]:
    """Resolve an ImportFrom (absolute or relative) to candidate module names."""
    if node.level == 0:
        return [node.module] if node.module else []
    # Relative import: walk up from the current module's package.
    pkg = src_mod.split(".")[:-1]                 # package containing src_mod
    base = pkg[: len(pkg) - (node.level - 1)] if node.level > 1 else pkg
    prefix = ".".join(base)
    if node.module:
        return [f"{prefix}.{node.module}" if prefix else node.module]
    # `from . import a, b` -> submodules of the package.
    return [f"{prefix}.{a.name}" if prefix else a.name for a in node.names]


def _match_module(name: str, modules) -> Optional[str]:
    if name in modules:
        return name
    parts = name.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in modules:
            return cand
    return None


def _find_cycles(edges: Dict[str, set], limit: int) -> List[List[str]]:
    """Detect elementary cycles with an iterative DFS (bounded output)."""
    cycles: List[List[str]] = []
    color: Dict[str, int] = {}  # 0=unseen,1=on-stack,2=done
    stack: List[str] = []

    def visit(start: str):
        work = [(start, iter(sorted(edges.get(start, ()))))]
        color[start] = 1
        stack.append(start)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if color.get(nxt, 0) == 0:
                    color[nxt] = 1
                    stack.append(nxt)
                    work.append((nxt, iter(sorted(edges.get(nxt, ())))))
                    advanced = True
                    break
                if color.get(nxt) == 1 and len(cycles) < limit:
                    idx = stack.index(nxt)
                    cycles.append(stack[idx:] + [nxt])
            if not advanced:
                color[node] = 2
                stack.pop()
                work.pop()

    for m in edges:
        if color.get(m, 0) == 0 and len(cycles) < limit:
            visit(m)
    return cycles
