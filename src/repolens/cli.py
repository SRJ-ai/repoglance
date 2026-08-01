"""Command-line entry point for repolens."""
from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from . import __version__
from . import gitinfo, report
from .scanner import scan


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("path", type=click.Path(exists=True, file_okay=False, path_type=Path), default=".")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON instead of the terminal report.")
@click.option("--no-git", is_flag=True, help="Skip git history analysis.")
@click.option("--max-bytes", default=2_000_000, show_default=True, help="Skip files larger than this many bytes.")
@click.option("--ignore", multiple=True, help="Extra directory name to ignore (repeatable).")
@click.version_option(__version__, "-V", "--version", prog_name="repolens")
def main(path: Path, as_json: bool, no_git: bool, max_bytes: int, ignore) -> None:
    """Instant, gorgeous insight into any code repository.

    PATH defaults to the current directory.
    """
    result = scan(path, max_bytes=max_bytes, extra_ignores=set(ignore))
    if not result.files:
        click.echo("No source files found.", err=True)
        sys.exit(1)

    git_stats = None if no_git else gitinfo.collect(result.root)

    if as_json:
        click.echo(report.to_json(result, git_stats))
        return

    # Windows legacy consoles / redirected pipes default to cp1252 and choke on
    # the report's box-drawing and emoji glyphs. Prefer real UTF-8 output.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass

    console = Console()
    report.render(console, result, git_stats)


if __name__ == "__main__":
    main()
