"""Cyclomatic-complexity estimation for Python via AST.

For non-Python files we fall back to a cheap branch-keyword heuristic so the
report still surfaces likely hotspots without language-specific parsers.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import List

# AST nodes that each add a decision point (McCabe-style).
_BRANCH_NODES = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
    ast.With, ast.AsyncWith, ast.Assert, ast.comprehension,
)

_BOOLOP_EXTRA = ast.BoolOp  # each extra operand adds a path

# Keyword heuristic for non-Python source.
_BRANCH_RE = re.compile(
    r"\b(if|else if|elif|for|while|case|catch|except|&&|\|\||\?)\b|\?\s*[^:]+:"
)

# Markup / data / prose languages have no control flow — never treat as hotspots.
NON_CODE_LANGS = {
    "Markdown", "reStructuredText", "TeX", "JSON", "YAML", "TOML", "XML",
    "HTML", "CSS", "SCSS", "Sass", "Less", "SQL", "GraphQL", "Protobuf",
}


@dataclass
class FuncScore:
    path: str
    name: str
    line: int
    complexity: int


def python_complexity(source: str, rel_path: str) -> List[FuncScore]:
    """Return per-function complexity for a Python source string."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    scores: List[FuncScore] = []

    class Visitor(ast.NodeVisitor):
        def _score(self, node) -> int:
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, _BRANCH_NODES):
                    complexity += 1
                elif isinstance(child, _BOOLOP_EXTRA):
                    complexity += len(child.values) - 1
            return complexity

        def visit_FunctionDef(self, node):
            scores.append(
                FuncScore(rel_path, node.name, node.lineno, self._score(node))
            )
            # Do not recurse into nested funcs separately; walk() already covered
            # them for the parent's score. Still visit to catch module-level peers.
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

    Visitor().visit(tree)
    return scores


def heuristic_complexity(source: str, rel_path: str) -> int:
    """Whole-file branch-keyword count for non-Python languages."""
    return 1 + len(_BRANCH_RE.findall(source))


def rank_hotspots(result, top: int = 10) -> List[FuncScore]:
    """Return the worst complexity offenders from a completed scan.

    Scores were computed inline during the scan (single file read), so this is
    just a sort — no filesystem access.
    """
    return sorted(result.func_scores, key=lambda s: s.complexity, reverse=True)[:top]
