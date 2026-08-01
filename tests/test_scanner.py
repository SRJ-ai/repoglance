from pathlib import Path

from repoglance.scanner import scan


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "a.py").write_text(
        "# comment\n\nimport os\n\n\ndef f():\n    return 1  # TODO: refine\n",
        encoding="utf-8",
    )
    (tmp_path / "b.js").write_text(
        "// header\nconst x = 1;\nfunction g() { return x; } // FIXME hurry\n",
        encoding="utf-8",
    )
    node = tmp_path / "node_modules"
    node.mkdir()
    (node / "junk.js").write_text("should be ignored\n", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n binary")
    return tmp_path


def test_scan_counts_languages(tmp_path):
    res = scan(_make_repo(tmp_path))
    langs = res.by_language()
    assert "Python" in langs
    assert "JavaScript" in langs
    # node_modules content must be excluded.
    assert all("node_modules" not in f.path for f in res.files)


def test_binary_skipped(tmp_path):
    res = scan(_make_repo(tmp_path))
    assert res.skipped_binary >= 1
    assert all(not f.path.endswith(".png") for f in res.files)


def test_line_classification(tmp_path):
    _make_repo(tmp_path)
    res = scan(tmp_path)
    py = next(f for f in res.files if f.path == "a.py")
    assert py.blank_lines == 3
    assert py.comment_lines == 1
    assert py.code_lines == py.lines - py.blank_lines - py.comment_lines


def test_todos_detected(tmp_path):
    res = scan(_make_repo(tmp_path))
    markers = {t.marker for t in res.todos}
    assert "TODO" in markers
    assert "FIXME" in markers


def test_todo_word_boundary(tmp_path):
    (tmp_path / "c.py").write_text("debugger = 1  # not a real hack marker word\n", encoding="utf-8")
    # 'hack' lowercase inside a word still needs boundary; 'HACK' as a token here is fine.
    res = scan(tmp_path)
    # "hack" here is a standalone word -> should match HACK marker.
    assert any(t.marker == "HACK" for t in res.todos)
