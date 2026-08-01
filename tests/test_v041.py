import json

from click.testing import CliRunner

from repoglance import gitinfo, plugins
from repoglance.cli import main
from repoglance.config import load_config


def test_process_and_thread_modes_agree(tmp_path):
    from repoglance.scanner import scan

    for i in range(5):
        (tmp_path / f"m{i}.py").write_text(
            f"def f{i}(x):\n    if x:\n        return {i}\n    return 0\n", encoding="utf-8"
        )
    threaded = scan(tmp_path, processes=False)
    forked = scan(tmp_path, processes=True)
    assert [f.path for f in threaded.files] == [f.path for f in forked.files]
    assert threaded.total_code == forked.total_code
    assert {s.name for s in threaded.func_scores} == {s.name for s in forked.func_scores}


def test_tally_counts_and_orders():
    pairs = gitinfo._tally("alice\nbob\nalice\n\nalice\n")
    assert pairs[0] == ("alice", 3)
    assert ("bob", 1) in pairs


def test_config_dedicated_overrides_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.repoglance]\nfail_under = 50\nmax_complexity = 10\n", encoding="utf-8"
    )
    (tmp_path / ".repoglance.toml").write_text("fail_under = 90\n", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg["fail_under"] == 90          # dedicated file wins
    assert cfg["max_complexity"] == 10      # pyproject value retained


def test_sarif_threshold_filters(tmp_path):
    (tmp_path / "a.py").write_text(
        "def f(x):\n"
        + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(8))
        + "    return 0\n",
        encoding="utf-8",
    )
    low = CliRunner().invoke(main, [str(tmp_path), "--no-git", "--sarif", "--sarif-threshold", "1"])
    high = CliRunner().invoke(main, [str(tmp_path), "--no-git", "--sarif", "--sarif-threshold", "100"])
    n_low = len(json.loads(low.output)["runs"][0]["results"])
    n_high = len(json.loads(high.output)["runs"][0]["results"])
    assert n_low >= 1
    assert n_high == 0


def test_broken_plugin_is_isolated(monkeypatch):
    class FakeEP:
        name = "boom"

        def load(self):
            def _f(_result):
                raise RuntimeError("kaboom")
            return _f

    monkeypatch.setattr(plugins, "_iter_entry_points", lambda: [FakeEP()])
    out = plugins.run_plugins(object())
    assert "boom" in out
    assert "error" in out["boom"]


def test_working_plugin_value(monkeypatch):
    class FakeEP:
        name = "answer"

        def load(self):
            return lambda _result: 42

    monkeypatch.setattr(plugins, "_iter_entry_points", lambda: [FakeEP()])
    assert plugins.run_plugins(object()) == {"answer": 42}
