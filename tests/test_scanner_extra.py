import subprocess

import pytest

from repoglance.scanner import scan


def test_block_comments_counted(tmp_path):
    (tmp_path / "a.js").write_text(
        "/* a\n"        # block start
        " * b\n"        # block middle
        " */\n"         # block end
        "const x = 1;\n"
        "// line comment\n",
        encoding="utf-8",
    )
    res = scan(tmp_path, extra_ignores=None)
    f = next(f for f in res.files if f.path == "a.js")
    assert f.comment_lines == 4          # 3 block + 1 line
    assert f.code_lines == 1


def _git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)


def test_gitignore_is_respected(tmp_path):
    if subprocess.run(["git", "--version"], capture_output=True).returncode != 0:
        pytest.skip("git not available")
    _git(tmp_path, "init")
    (tmp_path / ".gitignore").write_text("build/\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    build = tmp_path / "build"
    build.mkdir()
    (build / "generated.py").write_text("y = 2\n", encoding="utf-8")

    res = scan(tmp_path)
    assert res.used_gitignore is True
    paths = {f.path for f in res.files}
    assert "main.py" in paths
    assert all(not p.startswith("build/") for p in paths)  # ignored dir excluded


def test_extra_ignores_on_git_path(tmp_path):
    if subprocess.run(["git", "--version"], capture_output=True).returncode != 0:
        pytest.skip("git not available")
    _git(tmp_path, "init")
    (tmp_path / "keep.py").write_text("a = 1\n", encoding="utf-8")
    vendor = tmp_path / "vendored"
    vendor.mkdir()
    (vendor / "lib.py").write_text("b = 2\n", encoding="utf-8")

    res = scan(tmp_path, extra_ignores={"vendored"})
    paths = {f.path for f in res.files}
    assert "keep.py" in paths
    assert all("vendored" not in p for p in paths)


def test_complexity_scored_during_scan(tmp_path):
    (tmp_path / "m.py").write_text(
        "def f(a):\n    if a:\n        return 1\n    return 0\n", encoding="utf-8"
    )
    res = scan(tmp_path, extra_ignores=None)
    # func_scores are populated inline; rank uses them without re-reading.
    assert any(s.name == "f" and s.complexity >= 2 for s in res.func_scores)
