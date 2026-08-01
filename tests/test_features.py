import xml.dom.minidom as minidom

from repoglance import badge, report
from repoglance.scanner import scan


def _repo(tmp_path):
    (tmp_path / "a.py").write_text(
        "def big(x):\n"
        "    if x:\n"
        "        for i in range(x):\n"
        "            if i and x or i:\n"
        "                return i\n"
        "    return 0  # TODO cleanup\n",
        encoding="utf-8",
    )
    (tmp_path / "b.py").write_text("y = 1\n", encoding="utf-8")
    return scan(tmp_path)


def test_badge_is_well_formed_svg(tmp_path):
    res = _repo(tmp_path)
    svg = badge.badge_for_scan(res)
    # Must parse as XML and be an <svg> root.
    doc = minidom.parseString(svg)
    assert doc.documentElement.tagName == "svg"
    assert "repoglance" in svg
    assert "loc" in svg


def test_badge_escapes_and_humanizes():
    assert badge._human_loc(1500) == "1.5k"
    assert badge._human_loc(2_000_000) == "2.0M"
    assert "&lt;" in badge.render_badge("x", "a<b", "#000")


def test_export_svg_and_html(tmp_path):
    res = _repo(tmp_path)
    svg_path = tmp_path / "r.svg"
    html_path = tmp_path / "r.html"
    report.export(res, None, str(svg_path), "svg")
    report.export(res, None, str(html_path), "html")
    assert svg_path.read_text(encoding="utf-8").lstrip().startswith("<svg")
    assert "<html" in html_path.read_text(encoding="utf-8").lower()


def test_gate_fails_on_high_complexity(tmp_path):
    res = _repo(tmp_path)
    ok, messages = report.evaluate_gate(res, max_complexity=2, max_todos=None)
    assert ok is False
    assert any("complexity" in m for m in messages)


def test_gate_passes_when_within_limits(tmp_path):
    res = _repo(tmp_path)
    ok, _ = report.evaluate_gate(res, max_complexity=100, max_todos=100)
    assert ok is True


def test_gate_counts_todos(tmp_path):
    res = _repo(tmp_path)
    ok, messages = report.evaluate_gate(res, max_complexity=None, max_todos=0)
    assert ok is False
    assert any("TODO" in m for m in messages)


def test_markdown_report(tmp_path):
    res = _repo(tmp_path)
    md = report.to_markdown(res, None)
    assert md.startswith("### ")
    assert "repoglance report" in md
    assert "| Language |" in md
    assert "health" in md


def test_endpoint_json_is_shields_schema(tmp_path):
    import json

    res = _repo(tmp_path)
    data = json.loads(badge.endpoint_json(res))
    assert data["schemaVersion"] == 1
    assert data["label"] == "repoglance"
    assert "loc" in data["message"]


def test_health_score_bounds_and_grade(tmp_path):
    from repoglance import metrics

    res = _repo(tmp_path)
    h = metrics.compute(res)
    assert 0 <= h.score <= 100
    assert h.grade in {"A", "B", "C", "D", "F"}
    # Four factors, each capped at 25 -> 100 total possible.
    assert sum(m for _, _, m, _ in h.factors) == 100


def test_health_gate(tmp_path):
    res = _repo(tmp_path)
    ok, messages = report.evaluate_gate(res, None, None, fail_under=101)
    assert ok is False
    assert any("health" in m for m in messages)
