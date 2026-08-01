from repoglance.complexity import heuristic_complexity, python_complexity


def test_straight_line_is_one():
    src = "def f():\n    x = 1\n    y = 2\n    return x + y\n"
    scores = python_complexity(src, "f.py")
    assert len(scores) == 1
    assert scores[0].complexity == 1


def test_branches_add_complexity():
    src = (
        "def f(a, b):\n"
        "    if a:\n"
        "        for i in range(b):\n"
        "            if i and a:\n"
        "                return i\n"
        "    return 0\n"
    )
    scores = python_complexity(src, "f.py")
    top = max(s.complexity for s in scores)
    # 1 base + if + for + if + one extra boolop operand = 5
    assert top >= 5


def test_syntax_error_yields_no_scores():
    assert python_complexity("def (:\n", "bad.py") == []


def test_heuristic_counts_branches():
    js = "function f(x){ if(x) return 1; for(;;){} return x && 2; }"
    assert heuristic_complexity(js, "f.js") > 1
