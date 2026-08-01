import json

from click.testing import CliRunner

from repoglance import report
from repoglance.cli import main
from repoglance.complexity import analyze_complexity, lizard_available
from repoglance.metrics import maintainability_index
from repoglance.scanner import scan


def _py_repo(tmp_path):
    (tmp_path / "a.py").write_text(
        "def f(x):\n    if x:\n        for i in range(x):\n            if i:\n                return i\n    return 0\n",
        encoding="utf-8",
    )
    return tmp_path


def test_lizard_multilang_complexity():
    if not lizard_available():
        return
    js = "function g(x){ if(x){ for(;;){} } return x && 1; }"
    scores = analyze_complexity(js, "g.js", "JavaScript")
    assert scores and scores[0].complexity >= 3
    assert scores[0].name == "g"


def test_include_exclude_globs(tmp_path):
    (tmp_path / "keep.py").write_text("a = 1\n", encoding="utf-8")
    sub = tmp_path / "gen"
    sub.mkdir()
    (sub / "x.py").write_text("b = 2\n", encoding="utf-8")
    res = scan(tmp_path, exclude=["gen/*"])
    assert all(not p.path.startswith("gen/") for p in res.files)
    res2 = scan(tmp_path, include=["keep.py"])
    assert {f.path for f in res2.files} == {"keep.py"}


def test_changed_only_restrict(tmp_path):
    _py_repo(tmp_path)
    (tmp_path / "b.py").write_text("z = 1\n", encoding="utf-8")
    res = scan(tmp_path, changed_only={"a.py"})
    assert {f.path for f in res.files} == {"a.py"}


def test_sarif_output(tmp_path):
    res = scan(_py_repo(tmp_path))
    data = json.loads(report.to_sarif(res, min_complexity=1))
    assert data["version"] == "2.1.0"
    assert data["runs"][0]["tool"]["driver"]["name"] == "repoglance"
    assert len(data["runs"][0]["results"]) >= 1


def test_csv_output(tmp_path):
    res = scan(_py_repo(tmp_path))
    csv_text = report.to_csv(res)
    assert csv_text.splitlines()[0].startswith("path,language,code_lines")
    assert "a.py" in csv_text


def test_directory_rollup(tmp_path):
    _py_repo(tmp_path)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text("c = 1\n", encoding="utf-8")
    res = scan(tmp_path)
    rows = report.directory_rollup(res)
    dirs = {r["dir"] for r in rows}
    assert "pkg" in dirs


def test_maintainability_index_bounds(tmp_path):
    res = scan(_py_repo(tmp_path))
    mi = maintainability_index(res)
    assert 0 <= mi <= 100


def test_compare_detects_regression():
    base = {"health": {"score": 90}, "hotspots": [{"path": "a.py", "name": "f", "complexity": 5}],
            "todos": [], "total_code_lines": 100}
    current = {"health": {"score": 80}, "hotspots": [{"path": "a.py", "name": "f", "complexity": 12}],
               "todos": [], "total_code_lines": 120}
    diff = report.compare_snapshots(current, base)
    assert diff["health_delta"] == -10
    assert diff["loc_delta"] == 20
    assert diff["regressions"] and diff["regressions"][0]["was"] == 5


def test_cli_config_exclude(tmp_path):
    (tmp_path / "keep.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "drop.py").write_text("b = 2\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[tool.repoglance]\nexclude = [\"drop.py\"]\n", encoding="utf-8"
    )
    r = CliRunner().invoke(main, [str(tmp_path), "--no-git", "--json"])
    assert r.exit_code == 0
    data = json.loads(r.output)
    paths = {f["path"] for f in data["biggest_files"]}
    assert "drop.py" not in paths
    assert "keep.py" in paths


def test_cli_sarif_and_csv(tmp_path):
    _py_repo(tmp_path)
    r1 = CliRunner().invoke(main, [str(tmp_path), "--no-git", "--sarif"])
    assert r1.exit_code == 0 and '"version": "2.1.0"' in r1.output
    r2 = CliRunner().invoke(main, [str(tmp_path), "--no-git", "--csv"])
    assert r2.exit_code == 0 and "code_lines" in r2.output
