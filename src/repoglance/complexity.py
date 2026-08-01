"""Cyclomatic-complexity analysis.

Uses `lizard <https://github.com/terryyin/lizard>`_ for real, function-level
cyclomatic complexity across many languages (C/C++, Java, C#, JavaScript,
TypeScript, Go, Rust, Ruby, PHP, Swift, Scala, Kotlin, Objective-C, Lua and
Python). If lizard is unavailable or has no reader for a language, we fall back
to a Python AST analyzer and finally to a cheap branch-keyword heuristic.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import List, Optional

try:  # lizard is a runtime dependency, but degrade gracefully if missing.
    import lizard as _lizard
except Exception:  # pragma: no cover - only when dependency absent
    _lizard = None

# AST nodes that each add a decision point (McCabe-style).
_BRANCH_NODES = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
    ast.With, ast.AsyncWith, ast.Assert, ast.comprehension,
)

_BOOLOP_EXTRA = ast.BoolOp  # each extra operand adds a path

# Keyword heuristic for languages lizard cannot read.
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
    nloc: int = 0          # logical lines of code (from lizard)
    tokens: int = 0        # token count (from lizard; used for Halstead-ish MI)
    params: int = 0
    is_python: bool = False
    has_doc: bool = False   # Python: function has a docstring
    typed: bool = False     # Python: has a return or parameter annotation


def _lizard_scores(source: str, rel_path: str) -> Optional[List[FuncScore]]:
    """Real per-function complexity via lizard, or ``None`` if unsupported."""
    if _lizard is None:
        return None
    try:
        analysis = _lizard.analyze_file.analyze_source_code(rel_path, source)
    except Exception:
        return None
    funcs = analysis.function_list
    if not funcs:
        return None
    return [
        FuncScore(
            rel_path, f.name, f.start_line, f.cyclomatic_complexity,
            f.nloc, f.token_count, len(f.parameters),
        )
        for f in funcs
    ]


def python_complexity(source: str, rel_path: str) -> List[FuncScore]:
    """Fast AST-based complexity for Python (CPython's C parser)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    scores: List[FuncScore] = []

    class Visitor(ast.NodeVisitor):
        def _measure(self, node):
            complexity = 1
            nodes = 0
            for child in ast.walk(node):
                nodes += 1
                if isinstance(child, _BRANCH_NODES):
                    complexity += 1
                elif isinstance(child, _BOOLOP_EXTRA):
                    complexity += len(child.values) - 1
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            nloc = max(1, end - node.lineno + 1)
            args = node.args
            params = len(args.args) + len(getattr(args, "posonlyargs", [])) + len(args.kwonlyargs)
            return complexity, nloc, nodes, params

        def visit_FunctionDef(self, node):
            cx, nloc, tokens, params = self._measure(node)
            has_doc = ast.get_docstring(node) is not None
            a = node.args
            typed = node.returns is not None or any(
                arg.annotation is not None
                for arg in (*a.args, *getattr(a, "posonlyargs", []), *a.kwonlyargs)
            )
            scores.append(FuncScore(
                rel_path, node.name, node.lineno, cx, nloc, tokens, params,
                is_python=True, has_doc=has_doc, typed=typed,
            ))
            self.generic_visit(node)

        visit_AsyncFunctionDef = visit_FunctionDef

    Visitor().visit(tree)
    return scores


def heuristic_complexity(source: str, rel_path: str) -> int:
    """Whole-file branch-keyword count — last-resort for unreadable languages."""
    return 1 + len(_BRANCH_RE.findall(source))


def analyze_complexity(source: str, rel_path: str, language: str) -> List[FuncScore]:
    """Return per-function complexity.

    Python is analyzed with CPython's C-accelerated ``ast`` (much faster than a
    pure-Python tokenizer), which matters a lot on Python-heavy monorepos. Other
    languages use lizard; anything lizard cannot read falls back to a heuristic.
    """
    if language in NON_CODE_LANGS:
        return []
    if language == "Python":
        scores = python_complexity(source, rel_path)
        if scores:
            return scores
        # Empty may mean a syntax error (e.g. Python 2); let lizard try.
    scores = _lizard_scores(source, rel_path)
    if scores is not None:
        return scores
    score = heuristic_complexity(source, rel_path)
    return [FuncScore(rel_path, "(file)", 1, score)] if score > 1 else []


def rank_hotspots(result, top: int = 10) -> List[FuncScore]:
    """Return the worst complexity offenders from a completed scan.

    Scores were computed inline during the scan (single file read), so this is
    just a sort — no filesystem access.
    """
    return sorted(result.func_scores, key=lambda s: s.complexity, reverse=True)[:top]


def lizard_available() -> bool:
    return _lizard is not None
