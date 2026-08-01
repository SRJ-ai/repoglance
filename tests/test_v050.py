from repoglance import analytics, covreport
from repoglance.scanner import scan


class _Git:
    def __init__(self, hot):
        self.hot_files = hot


def _repo(tmp_path):
    (tmp_path / "a.py").write_text(
        '"""mod."""\n'
        "def f(x: int) -> int:\n"
        '    """doc."""\n'
        "    if x:\n        return x\n    return 0\n",
        encoding="utf-8",
    )
    (tmp_path / "b.py").write_text(
        "def g(y):\n" + "".join(f"    v{i} = {i}\n" for i in range(30)) + "    return y\n",
        encoding="utf-8",
    )
    return scan(tmp_path)


def test_risk_ranking_uses_churn_times_complexity(tmp_path):
    res = _repo(tmp_path)
    git = _Git([("b.py", 10), ("a.py", 1)])
    rows = analytics.risk_ranking(res, git)
    assert rows
    top = rows[0]
    assert top["risk"] == top["complexity"] * top["churn"]
    assert analytics.risk_ranking(res, None) == []


def test_longest_functions(tmp_path):
    res = _repo(tmp_path)
    longest = analytics.longest_functions(res, top=1)
    assert longest and longest[0]["name"] == "g"      # b.py's g is the biggest


def test_python_quality(tmp_path):
    res = _repo(tmp_path)
    pq = analytics.python_quality(res)
    assert pq["functions"] == 2
    assert pq["documented"] == 1                       # only f has a docstring
    assert 0 <= pq["type_coverage"] <= 1


def test_import_graph_and_cycles(tmp_path):
    (tmp_path / "x.py").write_text("from y import a\n", encoding="utf-8")
    (tmp_path / "y.py").write_text("from x import b\n", encoding="utf-8")
    res = scan(tmp_path)
    g = analytics.import_graph(res)
    assert g["modules"] == 2
    assert g["edges"] == 2
    assert g["circular"]                               # x <-> y detected


def test_coverage_cobertura_and_lcov(tmp_path):
    xml = tmp_path / "cov.xml"
    xml.write_text(
        '<?xml version="1.0"?><coverage><packages><package><classes>'
        '<class filename="a.py" line-rate="0.5"/>'
        '</classes></package></packages></coverage>',
        encoding="utf-8",
    )
    parsed = covreport.parse_coverage(xml)
    assert parsed["a.py"] == 0.5

    lcov = tmp_path / "cov.info"
    lcov.write_text("SF:b.py\nDA:1,1\nDA:2,0\nend_of_record\n", encoding="utf-8")
    parsed2 = covreport.parse_coverage(lcov)
    assert parsed2["b.py"] == 0.5


def test_coverage_risk_ranks_uncovered_complexity(tmp_path):
    res = _repo(tmp_path)
    rows = covreport.risk_by_coverage(res, {"b.py": 0.1, "a.py": 0.9})
    assert rows
    # b.py is complex and poorly covered -> should outrank a.py.
    assert rows[0]["path"] == "b.py"
