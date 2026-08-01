"""Render a ScanResult into a rich terminal report (or JSON)."""
from __future__ import annotations

import json
from pathlib import Path
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


def render(console: Console, res: ScanResult, git: Optional[GitStats]) -> None:
    console.print(_header(res, git))
    console.print(_health_panel(res))
    console.print(_language_table(res))
    console.print(Columns([_hotspots_panel(res), _biggest_panel(res)], expand=True))
    console.print(_todos_panel(res))
    if git:
        console.print(_git_panel(git))


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


def to_json(res: ScanResult, git: Optional[GitStats]) -> str:
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
            for s in rank_hotspots(res, top=15)
        ],
        "todos": [
            {"marker": t.marker, "path": t.path, "line": t.line, "text": t.text}
            for t in res.todos
        ],
        "biggest_files": [
            {"path": f.path, "code_lines": f.code_lines, "bytes": f.size_bytes}
            for f in sorted(res.files, key=lambda f: f.code_lines, reverse=True)[:15]
        ],
    }
    if git:
        payload["git"] = {
            "total_commits": git.total_commits,
            "contributors": [{"name": n, "commits": c} for n, c in git.contributors],
            "hot_files": [{"path": p, "changes": c} for p, c in git.hot_files],
            "first_commit": git.first_commit,
            "last_commit": git.last_commit,
            "active_days": git.active_days,
        }
    return json.dumps(payload, indent=2)
