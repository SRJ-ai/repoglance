"""Render a ScanResult into a rich terminal report (or JSON)."""
from __future__ import annotations

import json
from typing import Optional

from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .complexity import rank_hotspots
from .gitinfo import GitStats
from .languages import color_for
from .metrics import compute as compute_health
from .metrics import maintainability_index
from .scanner import ScanResult

_BAR = "█"


def _human_bytes(n: int) -> str:
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB"):
        if n < step:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= step
    return f"{n:.1f}TB"


def _bar(fraction: float, width: int = 24) -> str:
    filled = int(round(fraction * width))
    return _BAR * filled + " " * (width - filled)


def _header(res: ScanResult, git: Optional[GitStats]) -> Panel:
    name = res.root.name or str(res.root)
    lines = [
        Text.assemble(("📁 ", "bold"), (name, "bold cyan")),
        Text.assemble(
            (f"{len(res.files):,}", "bold white"), (" files scanned   ", "dim"),
            (f"{res.total_code:,}", "bold white"), (" lines of code", "dim"),
        ),
    ]
    if git:
        lines.append(
            Text.assemble(
                (f"{git.total_commits:,}", "bold white"), (" commits   ", "dim"),
                (f"{len(git.contributors)}", "bold white"), (" contributors   ", "dim"),
                (f"{git.first_commit} → {git.last_commit}", "dim"),
            )
        )
    if res.vendored_files:
        lines.append(Text(f"{res.vendored_files} vendored/generated files excluded", style="dim"))
    return Panel(Group(*lines), border_style="cyan", title="[bold]repoglance[/]", title_align="left")


def _language_table(res: ScanResult) -> Panel:
    agg = res.by_language()
    total = res.total_code or 1
    rows = sorted(agg.items(), key=lambda kv: kv[1]["code"], reverse=True)

    table = Table.grid(padding=(0, 1))
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="left")
    table.add_column(justify="right")
    table.add_column(justify="right")

    for lang, d in rows[:12]:
        frac = d["code"] / total
        color = color_for(lang)
        table.add_row(
            Text(lang, style="bold"),
            Text(_bar(frac), style=color),
            Text(f"{frac * 100:4.1f}%", style="white"),
            Text(f"{d['code']:>7,} loc  {d['files']:>4} files", style="dim"),
        )
    return Panel(table, title="[bold]Languages[/]", border_style="blue", title_align="left")


def _hotspots_panel(res: ScanResult) -> Panel:
    hotspots = rank_hotspots(res, top=8)
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", no_wrap=True)
    table.add_column(justify="left")
    table.add_column(justify="left")
    if not hotspots:
        body = Text("No hotspots found.", style="dim")
    else:
        for s in hotspots:
            sev = "red" if s.complexity >= 20 else "yellow" if s.complexity >= 10 else "green"
            table.add_row(
                Text(str(s.complexity), style=f"bold {sev}"),
                Text(f"{s.name}", style="white"),
                Text(f"{s.path}:{s.line}", style="dim"),
            )
        body = table
    return Panel(body, title="[bold]Complexity hotspots[/]", border_style="magenta", title_align="left")


def _todos_panel(res: ScanResult) -> Panel:
    by_marker: dict = {}
    for t in res.todos:
        by_marker[t.marker] = by_marker.get(t.marker, 0) + 1
    summary = "  ".join(f"[bold]{m}[/] {c}" for m, c in sorted(by_marker.items()))

    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="left")
    for t in res.todos[:8]:
        table.add_row(
            Text(t.marker, style="bold yellow"),
            Text.assemble((t.text, "white"), ("  " + f"{t.path}:{t.line}", "dim")),
        )
    header = Text.from_markup(summary or "[dim]No TODOs — clean![/]")
    body = Group(header, Text(""), table) if res.todos else header
    return Panel(body, title="[bold]TODO tracker[/]", border_style="yellow", title_align="left")


def _biggest_panel(res: ScanResult) -> Panel:
    biggest = sorted(res.files, key=lambda f: f.code_lines, reverse=True)[:8]
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", no_wrap=True)
    table.add_column(justify="left")
    for f in biggest:
        table.add_row(
            Text(f"{f.code_lines:,}", style="bold white"),
            Text.assemble((f.path, "cyan"), ("  " + _human_bytes(f.size_bytes), "dim")),
        )
    return Panel(table, title="[bold]Biggest files[/]", border_style="green", title_align="left")


def _git_panel(git: GitStats) -> Panel:
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left")
    table.add_column(justify="left")
    table.add_row(Text("Top authors", style="bold"), Text("Most-churned files", style="bold"))
    top_authors = git.contributors[:5]
    top_files = git.hot_files[:5]
    for i in range(max(len(top_authors), len(top_files))):
        a = f"{top_authors[i][0]} ({top_authors[i][1]})" if i < len(top_authors) else ""
        h = f"{top_files[i][0]} ×{top_files[i][1]}" if i < len(top_files) else ""
        table.add_row(Text(a, style="white"), Text(h, style="dim"))
    footer = Text(f"\n{git.active_days} active days", style="dim")
    return Panel(Group(table, footer), title="[bold]Git activity[/]", border_style="red", title_align="left")


def _health_panel(res: ScanResult) -> Panel:
    h = compute_health(res)
    grade_color = {"A": "green", "B": "green", "C": "yellow", "D": "yellow", "F": "red"}[h.grade]
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="left")
    table.add_column(justify="right")
    for name, pts, mx, detail in h.factors:
        frac = pts / mx if mx else 0
        bar_color = "green" if frac >= 0.8 else "yellow" if frac >= 0.5 else "red"
        table.add_row(
            Text(name, style="bold"),
            Text(_bar(frac, 16), style=bar_color),
            Text.assemble((f"{pts}/{mx}", "white"), ("  " + detail, "dim")),
        )
    headline = Text.assemble(
        (f"{h.score}", f"bold {grade_color}"), ("/100   grade ", "dim"),
        (h.grade, f"bold {grade_color}"),
    )
    return Panel(Group(headline, Text(""), table), title="[bold]Health score[/]", border_style=grade_color, title_align="left")


def _directories_panel(res: ScanResult) -> Panel:
    rows = directory_rollup(res)[:8]
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="left", no_wrap=True)
    table.add_column(justify="right")
    table.add_column(justify="right")
    table.add_row(Text("directory", style="bold"), Text("loc", style="bold"), Text("worst cx", style="bold"))
    for r in rows:
        cx = r["worst_complexity"]
        cx_color = "red" if cx >= 20 else "yellow" if cx >= 10 else "green"
        table.add_row(
            Text(r["dir"], style="cyan"),
            Text(f"{r['code']:,}", style="white"),
            Text(str(cx), style=cx_color),
        )
    return Panel(table, title="[bold]Directories[/]", border_style="blue", title_align="left")


def render(console: Console, res: ScanResult, git: Optional[GitStats]) -> None:
    console.print(_header(res, git))
    console.print(_health_panel(res))
    console.print(_language_table(res))
    console.print(Columns([_hotspots_panel(res), _biggest_panel(res)], expand=True))
    console.print(_directories_panel(res))
    if res.contents:
        console.print(_duplicates_panel(res))
    console.print(_todos_panel(res))
    if git:
        console.print(_git_panel(git))


def _duplicates_panel(res: ScanResult) -> Panel:
    from .dedup import detect_duplicates

    dd = detect_duplicates(res.contents)
    table = Table.grid(padding=(0, 2))
    table.add_column(justify="right", no_wrap=True)
    table.add_column(justify="left")
    if not dd.blocks:
        body = Text("No significant duplication found.", style="dim")
    else:
        for b in dd.blocks[:6]:
            locs = ", ".join(f"{p}:{ln}" for p, ln in b.occurrences[:3])
            more = f" +{len(b.occurrences) - 3}" if len(b.occurrences) > 3 else ""
            table.add_row(Text(f"x{len(b.occurrences)}", style="bold red"),
                          Text(f"{locs}{more}", style="dim"))
        header = Text(f"{dd.ratio * 100:.1f}% duplicated ({dd.duplicated_lines:,} lines)", style="yellow")
        body = Group(header, Text(""), table)
    return Panel(body, title="[bold]Duplication[/]", border_style="red", title_align="left")


def export(res: ScanResult, git: Optional[GitStats], path: str, fmt: str) -> None:
    """Render the report into a recording console and write it as HTML or SVG."""
    import io

    # Record into an off-screen buffer so nothing hits the real terminal and we
    # avoid Windows legacy-console encoding paths.
    console = Console(record=True, file=io.StringIO(), width=100)
    render(console, res, git)
    if fmt == "svg":
        data = console.export_svg(title=f"repoglance · {res.root.name}")
    else:
        data = console.export_html()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(data)


def evaluate_gate(res: ScanResult, max_complexity: Optional[int], max_todos: Optional[int],
                  fail_under: Optional[int] = None):
    """Return (ok, messages) for CI threshold checks. Empty thresholds are skipped."""
    from .complexity import rank_hotspots

    messages = []
    ok = True
    if fail_under is not None:
        h = compute_health(res)
        if h.score < fail_under:
            ok = False
            messages.append(f"health {h.score} (grade {h.grade}) below min {fail_under}")
        else:
            messages.append(f"health ok ({h.score} >= {fail_under}, grade {h.grade})")
    if max_complexity is not None:
        worst = rank_hotspots(res, top=1)
        top = worst[0].complexity if worst else 0
        if top > max_complexity:
            ok = False
            offender = f"{worst[0].name} ({worst[0].path}:{worst[0].line})" if worst else "?"
            messages.append(f"complexity {top} exceeds max {max_complexity} - {offender}")
        else:
            messages.append(f"complexity ok (worst {top} <= {max_complexity})")
    if max_todos is not None:
        n = len(res.todos)
        if n > max_todos:
            ok = False
            messages.append(f"{n} TODO markers exceed max {max_todos}")
        else:
            messages.append(f"todos ok ({n} <= {max_todos})")
    return ok, messages


def to_markdown(res: ScanResult, git: Optional[GitStats]) -> str:
    """A compact Markdown report, ideal for PR comments and job summaries."""
    h = compute_health(res)
    agg = res.by_language()
    total = res.total_code or 1
    out = []
    out.append("### 🔍 repoglance report")
    out.append("")
    out.append(f"**{len(res.files):,} files** · **{res.total_code:,} lines of code** · "
               f"health **{h.score}/100 ({h.grade})**")
    if git:
        out.append(f"_{git.total_commits:,} commits · {len(git.contributors)} contributors · "
                   f"{git.first_commit} → {git.last_commit}_")
    out.append("")

    out.append("| Language | Code | Share | Files |")
    out.append("|---|--:|--:|--:|")
    for lang, d in sorted(agg.items(), key=lambda kv: kv[1]["code"], reverse=True)[:8]:
        out.append(f"| {lang} | {d['code']:,} | {d['code'] / total * 100:.1f}% | {d['files']} |")
    out.append("")

    hotspots = rank_hotspots(res, top=5)
    if hotspots:
        out.append("<details><summary>🔥 Complexity hotspots</summary>")
        out.append("")
        out.append("| Complexity | Function | Location |")
        out.append("|--:|---|---|")
        for s in hotspots:
            out.append(f"| {s.complexity} | `{s.name}` | `{s.path}:{s.line}` |")
        out.append("")
        out.append("</details>")
        out.append("")

    todo_n = len(res.todos)
    out.append(f"**TODO markers:** {todo_n}")
    out.append("")
    out.append("<sub>Generated by [repoglance](https://github.com/SRJ-ai/repoglance)</sub>")
    return "\n".join(out)


def directory_rollup(res: ScanResult, depth: int = 1):
    """Aggregate code lines and worst complexity per top-level directory."""
    dirs: dict = {}
    worst: dict = {}
    for f in res.files:
        parts = f.path.split("/")
        key = "/".join(parts[:depth]) if len(parts) > depth else (parts[0] if len(parts) > 1 else ".")
        d = dirs.setdefault(key, {"code": 0, "files": 0})
        d["code"] += f.code_lines
        d["files"] += 1
    for s in res.func_scores:
        parts = s.path.split("/")
        key = "/".join(parts[:depth]) if len(parts) > depth else (parts[0] if len(parts) > 1 else ".")
        worst[key] = max(worst.get(key, 0), s.complexity)
    rows = [
        {"dir": k, "code": v["code"], "files": v["files"], "worst_complexity": worst.get(k, 0)}
        for k, v in dirs.items()
    ]
    rows.sort(key=lambda r: r["code"], reverse=True)
    return rows


def build_payload(res: ScanResult, git: Optional[GitStats]) -> dict:
    """The structured report used by --json and as a baseline snapshot."""
    agg = res.by_language()
    h = compute_health(res)
    payload = {
        "root": str(res.root),
        "total_files": len(res.files),
        "total_code_lines": res.total_code,
        "total_lines": res.total_lines,
        "health": {
            "score": h.score,
            "grade": h.grade,
            "factors": [
                {"name": n, "points": p, "max": m, "detail": d}
                for n, p, m, d in h.factors
            ],
        },
        "languages": {
            lang: {"code": d["code"], "files": d["files"], "bytes": d["bytes"]}
            for lang, d in sorted(agg.items(), key=lambda kv: kv[1]["code"], reverse=True)
        },
        "hotspots": [
            {"name": s.name, "path": s.path, "line": s.line, "complexity": s.complexity}
            for s in rank_hotspots(res, top=25)
        ],
        "todos": [
            {"marker": t.marker, "path": t.path, "line": t.line, "text": t.text}
            for t in res.todos
        ],
        "biggest_files": [
            {"path": f.path, "code_lines": f.code_lines, "bytes": f.size_bytes}
            for f in sorted(res.files, key=lambda f: f.code_lines, reverse=True)[:15]
        ],
        "directories": directory_rollup(res),
        "maintainability_index": maintainability_index(res),
        "vendored_files": res.vendored_files,
    }
    from .plugins import run_plugins
    plugin_out = run_plugins(res)
    if plugin_out:
        payload["plugins"] = plugin_out
    if res.contents:
        from .dedup import detect_duplicates
        dd = detect_duplicates(res.contents)
        payload["duplication"] = {
            "ratio": round(dd.ratio, 4),
            "duplicated_lines": dd.duplicated_lines,
            "blocks": [
                {"lines": b.lines, "occurrences": [{"path": p, "line": ln} for p, ln in b.occurrences]}
                for b in dd.blocks
            ],
        }
    if getattr(res, "ownership", None):
        payload["ownership"] = res.ownership
    if git:
        payload["git"] = {
            "total_commits": git.total_commits,
            "contributors": [{"name": n, "commits": c} for n, c in git.contributors],
            "hot_files": [{"path": p, "changes": c} for p, c in git.hot_files],
            "first_commit": git.first_commit,
            "last_commit": git.last_commit,
            "active_days": git.active_days,
        }
    return payload


def to_json(res: ScanResult, git: Optional[GitStats]) -> str:
    return json.dumps(build_payload(res, git), indent=2)


def to_csv(res: ScanResult) -> str:
    """Per-file CSV: path, language, code, comment, blank, bytes."""
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["path", "language", "code_lines", "comment_lines", "blank_lines", "bytes"])
    for f in sorted(res.files, key=lambda f: f.path):
        w.writerow([f.path, f.language, f.code_lines, f.comment_lines, f.blank_lines, f.size_bytes])
    return buf.getvalue()


def to_sarif(res: ScanResult, min_complexity: int = 10) -> str:
    """SARIF 2.1.0 so complexity hotspots appear inline in GitHub code scanning."""
    results = []
    for s in res.func_scores:
        if s.complexity < min_complexity:
            continue
        level = "error" if s.complexity >= 25 else "warning"
        results.append({
            "ruleId": "high-complexity",
            "level": level,
            "message": {"text": f"Function '{s.name}' has cyclomatic complexity {s.complexity}."},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": s.path},
                    "region": {"startLine": max(1, s.line)},
                }
            }],
        })
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "repoglance",
                "informationUri": "https://github.com/SRJ-ai/repoglance",
                "rules": [{
                    "id": "high-complexity",
                    "name": "HighCyclomaticComplexity",
                    "shortDescription": {"text": "Function exceeds the cyclomatic complexity threshold."},
                }],
            }},
            "results": results,
        }],
    }
    return json.dumps(sarif, indent=2)


def compare_snapshots(current: dict, base: dict) -> dict:
    """Diff two report payloads: metric deltas and per-function regressions."""
    def worst(payload):
        hs = payload.get("hotspots", [])
        return hs[0]["complexity"] if hs else 0

    cur_h = current.get("health", {}).get("score", 0)
    base_h = base.get("health", {}).get("score", 0)

    base_map = {(h["path"], h["name"]): h["complexity"] for h in base.get("hotspots", [])}
    regressions = []
    for h in current.get("hotspots", []):
        key = (h["path"], h["name"])
        prev = base_map.get(key)
        if prev is None or h["complexity"] > prev:
            regressions.append({
                "path": h["path"], "name": h["name"],
                "complexity": h["complexity"], "was": prev,
            })

    return {
        "health_delta": cur_h - base_h,
        "worst_complexity_delta": worst(current) - worst(base),
        "todo_delta": len(current.get("todos", [])) - len(base.get("todos", [])),
        "loc_delta": current.get("total_code_lines", 0) - base.get("total_code_lines", 0),
        "regressions": regressions,
    }
