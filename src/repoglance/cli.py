"""Command-line entry point for repoglance."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from . import badge as badgemod
from . import gitinfo, report
from .config import load_config
from .scanner import changed_files, scan


def _resolve(cli_val, cfg, key, default):
    return cli_val if cli_val is not None else cfg.get(key, default)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
# stdout formats
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option("--md", "--markdown", "as_md", is_flag=True, help="Emit a Markdown report (PR comments / summaries).")
@click.option("--csv", "as_csv", is_flag=True, help="Emit a per-file CSV.")
@click.option("--sarif", "as_sarif", is_flag=True, help="Emit SARIF 2.1.0 (GitHub code scanning).")
# file artifacts
@click.option("--html", "html_path", type=click.Path(dir_okay=False, path_type=Path), help="Write a standalone HTML report.")
@click.option("--svg", "svg_path", type=click.Path(dir_okay=False, path_type=Path), help="Write a standalone SVG report.")
@click.option("--badge", "badge_path", type=click.Path(dir_okay=False, path_type=Path), help="Write a shields-style SVG badge.")
@click.option("--badge-json", "badge_json_path", type=click.Path(dir_okay=False, path_type=Path), help="Write a shields.io endpoint JSON (dynamic badge).")
@click.option("--baseline", "baseline_out", type=click.Path(dir_okay=False, path_type=Path), help="Write the current report as a baseline snapshot.")
# scoping
@click.option("--since", "since_rev", default=None, help="Only analyze files changed since this git revision (diff mode).")
@click.option("--include", multiple=True, help="Glob of paths to include (repeatable).")
@click.option("--exclude", multiple=True, help="Glob of paths to exclude (repeatable).")
@click.option("--ignore", multiple=True, help="Extra directory name to ignore (repeatable).")
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
@click.option("--max-bytes", type=int, default=None, help="Skip files larger than this many bytes.")
@click.option("--jobs", type=int, default=None, help="Worker threads for scanning.")
# comparison
@click.option("--compare", "compare_to", type=click.Path(dir_okay=False, exists=True, path_type=Path), help="Compare against a baseline snapshot and show deltas.")
@click.option("--fail-on-regression", is_flag=True, help="Exit nonzero if --compare finds new/worse complexity.")
# gates
@click.option("--ci", is_flag=True, help="CI gate mode: exit nonzero if a threshold is exceeded.")
@click.option("--max-complexity", type=int, default=None, help="Fail (with --ci) if any function exceeds this complexity.")
@click.option("--max-todos", type=int, default=None, help="Fail (with --ci) if TODO markers exceed this count.")
@click.option("--fail-under", type=int, default=None, help="Fail (with --ci) if the health score is below this (0-100).")
@click.version_option(__version__, "-V", "--version", prog_name="repoglance")
def main(path, as_json, as_md, as_csv, as_sarif, html_path, svg_path, badge_path,
         badge_json_path, baseline_out, since_rev, include, exclude, ignore, no_git,
         max_bytes, jobs, compare_to, fail_on_regression, ci, max_complexity,
         max_todos, fail_under):
    """Instant, gorgeous insight into any code repository.

    PATH defaults to the current directory. Configuration may be supplied via
    ``.repoglance.toml`` or a ``[tool.repoglance]`` table in ``pyproject.toml``.
    """
    root = Path(path).resolve()
    cfg = load_config(root)

    ignores = set(ignore) | set(cfg.get("ignore", []))
    include = list(include) or cfg.get("include") or None
    exclude = list(exclude) or cfg.get("exclude") or None
    max_bytes = _resolve(max_bytes, cfg, "max_bytes", 2_000_000)

    changed = changed_files(root, since_rev) if since_rev else None
    if since_rev and not changed:
        click.echo(f"No changed files since {since_rev} (or not a git repo).", err=True)
        return

    result = scan(
        root, max_bytes=max_bytes, extra_ignores=ignores,
        include=include, exclude=exclude, changed_only=changed, jobs=jobs,
    )
    if not result.files:
        click.echo("No source files found.", err=True)
        sys.exit(1)

    git_stats = None if no_git else gitinfo.collect(result.root)

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

    # File artifacts.
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
    if baseline_out:
        baseline_out.write_text(report.to_json(result, git_stats), encoding="utf-8")
        click.echo(f"Wrote baseline snapshot to {baseline_out}", err=True)

    # Comparison against a baseline.
    regression_fail = False
    if compare_to:
        base = json.loads(compare_to.read_text(encoding="utf-8"))
        diff = report.compare_snapshots(report.build_payload(result, git_stats), base)
        _print_comparison(diff)
        if fail_on_regression and diff["regressions"]:
            regression_fail = True

    # CI gate.
    gate_fail = False
    if ci:
        max_complexity = _resolve(max_complexity, cfg, "max_complexity", None)
        max_todos = _resolve(max_todos, cfg, "max_todos", None)
        fail_under = _resolve(fail_under, cfg, "fail_under", None)
        ok, messages = report.evaluate_gate(result, max_complexity, max_todos, fail_under)
        prefix = "OK  " if ok else "FAIL"
        for m in messages:
            click.echo(f"[{prefix}] {m}", err=not ok)
        gate_fail = not ok

    if regression_fail or gate_fail:
        sys.exit(2)

    # stdout report formats.
    if as_json:
        click.echo(report.to_json(result, git_stats))
        return
    if as_md:
        click.echo(report.to_markdown(result, git_stats))
        return
    if as_csv:
        click.echo(report.to_csv(result), nl=False)
        return
    if as_sarif:
        click.echo(report.to_sarif(result))
        return

    # If only artifacts/gates were requested (non-interactive), stop here.
    only_side = (badge_path or badge_json_path or html_path or svg_path
                 or baseline_out or compare_to or ci)
    if only_side and not sys.stdout.isatty():
        return

    console = Console()
    report.render(console, result, git_stats)


def _print_comparison(diff: dict) -> None:
    def sign(n):
        return f"+{n}" if n > 0 else str(n)

    click.echo("Comparison vs baseline:")
    click.echo(f"  health:           {sign(diff['health_delta'])}")
    click.echo(f"  worst complexity: {sign(diff['worst_complexity_delta'])}")
    click.echo(f"  TODO markers:     {sign(diff['todo_delta'])}")
    click.echo(f"  lines of code:    {sign(diff['loc_delta'])}")
    if diff["regressions"]:
        click.echo(f"  regressions ({len(diff['regressions'])}):")
        for r in diff["regressions"][:15]:
            was = "new" if r["was"] is None else f"{r['was']}->{r['complexity']}"
            click.echo(f"    {r['complexity']:>3}  {r['name']}  {r['path']}  ({was})")
    else:
        click.echo("  no complexity regressions")


if __name__ == "__main__":
    main()
