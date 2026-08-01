from click.testing import CliRunner

from repoglance.cli import main


def _make(tmp_path):
    (tmp_path / "a.py").write_text(
        "def f(x):\n    if x:\n        return 1  # TODO later\n    return 0\n",
        encoding="utf-8",
    )
    return tmp_path


def test_cli_default_report(tmp_path):
    r = CliRunner().invoke(main, [str(_make(tmp_path)), "--no-git"])
    assert r.exit_code == 0
    assert "repoglance" in r.output
    assert "Health score" in r.output


def test_cli_json(tmp_path):
    r = CliRunner().invoke(main, [str(_make(tmp_path)), "--no-git", "--json"])
    assert r.exit_code == 0
    assert '"total_code_lines"' in r.output


def test_cli_markdown(tmp_path):
    r = CliRunner().invoke(main, [str(_make(tmp_path)), "--no-git", "--md"])
    assert r.exit_code == 0
    assert r.output.startswith("### ")


def test_cli_ci_gate_fails(tmp_path):
    r = CliRunner().invoke(
        main, [str(_make(tmp_path)), "--no-git", "--ci", "--fail-under", "101"]
    )
    assert r.exit_code == 2


def test_cli_no_source(tmp_path):
    (tmp_path / "photo.png").write_bytes(b"\x89PNG")
    r = CliRunner().invoke(main, [str(tmp_path), "--no-git"])
    assert r.exit_code == 1


def test_cli_artifacts(tmp_path):
    _make(tmp_path)
    badge = tmp_path / "b.svg"
    r = CliRunner().invoke(
        main, [str(tmp_path), "--no-git", "--badge", str(badge)]
    )
    assert r.exit_code == 0
    assert badge.exists()
    assert badge.read_text(encoding="utf-8").lstrip().startswith("<svg")
