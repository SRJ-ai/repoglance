"""Command-line entry point for repolens."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from . import badge as badgemod
from . import gitinfo, report
from .scanner import scan


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON instead of the terminal report.")
@click.option("--md", "--markdown", "as_md", is_flag=True, help="Emit a Markdown report (great for PR comments / job summaries).")
@click.option("--html", "html_path", type=click.Path(dir_okay=False, path_type=Path), help="Write the report to a standalone HTML file.")
@click.option("--svg", "svg_path", type=click.Path(dir_okay=False, path_type=Path), help="Write the report to a standalone SVG file.")
@click.option("--badge", "badge_path", type=click.Path(dir_okay=False, path_type=Path), help="Write a shields-style SVG badge (loc + top language).")
@click.option("--badge-json", "badge_json_path", type=click.Path(dir_okay=False, path_type=Path), help="Write a shields.io endpoint JSON for a self-updating dynamic badge.")
@click.option("--ci", is_flag=True, help="CI gate mode: exit nonzero if a threshold is exceeded.")
@click.option("--max-complexity", type=int, default=None, help="Fail (with --ci) if any function exceeds this complexity.")
@click.option("--max-todos", type=int, default=None, help="Fail (with --ci) if TODO markers exceed this count.")
@click.option("--fail-under", type=int, default=None, help="Fail (with --ci) if the health score is below this (0-100).")
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
@click.option("--max-bytes", default=2_000_000, show_default=True, help="Skip files larger than this many bytes.")
@click.option("--ignore", multiple=True, help="Extra directory name to ignore (repeatable).")
@click.version_option(__version__, "-V", "--version", prog_name="repolens")
def main(path, as_json, as_md, html_path, svg_path, badge_path, badge_json_path, ci, max_complexity, max_todos, fail_under, no_git, max_bytes, ignore):
    """Instant, gorgeous insight into any code repository.

    PATH defaults to the current directory.
    """
    result = scan(path, max_bytes=max_bytes, extra_ignores=set(ignore))
    if not result.files:
        click.echo("No source files found.", err=True)
        sys.exit(1)

    git_stats = None if no_git else gitinfo.collect(result.root)

    # Windows legacy consoles / redirected pipes default to cp1252 and choke on
    # the report's box-drawing, emoji and bar glyphs. Prefer real UTF-8 output.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

    # Side artifacts: write on request, report where they landed.
    if badge_path:
        badge_path.write_text(badgemod.badge_for_scan(result), encoding="utf-8")
        click.echo(f"Wrote badge to {badge_path}", err=True)
    if badge_json_path:
        badge_json_path.write_text(badgemod.endpoint_json(result), encoding="utf-8")
        click.echo(f"Wrote shields endpoint JSON to {badge_json_path}", err=True)
    if html_path:
        report.export(result, git_stats, str(html_path), "html")
        click.echo(f"Wrote HTML report to {html_path}", err=True)
    if svg_path:
        report.export(result, git_stats, str(svg_path), "svg")
        click.echo(f"Wrote SVG report to {svg_path}", err=True)

    # CI gate: evaluate thresholds and exit with a clear status.
    if ci:
        ok, messages = report.evaluate_gate(result, max_complexity, max_todos, fail_under)
        prefix = "OK  " if ok else "FAIL"
        for m in messages:
            click.echo(f"[{prefix}] {m}", err=not ok)
        sys.exit(0 if ok else 2)

    if as_json:
        click.echo(report.to_json(result, git_stats))
        return

    if as_md:
        click.echo(report.to_markdown(result, git_stats))
        return

    # Only-artifact runs (badge/html/svg without a console report) finish here.
    if (badge_path or badge_json_path or html_path or svg_path) and not sys.stdout.isatty():
        return

    console = Console()
    report.render(console, result, git_stats)


if __name__ == "__main__":
    main()
