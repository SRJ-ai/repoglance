<div align="center">

# 🔍 repolens

### Instant, gorgeous insight into any code repository — in one command.

Point it at any folder. In under a second you get a beautiful terminal report:
language breakdown, complexity hotspots, TODO tracker, biggest files, and git
activity. **Zero config. Zero API keys. Zero telemetry.**

[![CI](https://github.com/SRJ-ai/repolens/actions/workflows/ci.yml/badge.svg)](https://github.com/SRJ-ai/repolens/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## Why repolens?

You clone an unfamiliar repo. What *is* this thing? How big? What's the messy
part? Where's the unfinished work? `cloc` gives you a wall of numbers. `tokei`
is fast but bare. `repolens` answers the human questions in one glance:

```bash
repolens .
```

<div align="center">

```
╭─ repolens ───────────────────────────────────────────────╮
│ 📁 my-project                                            │
│ 128 files scanned   14,203 lines of code                 │
│ 342 commits   6 contributors   2023-04-01 → 2026-07-30   │
╰──────────────────────────────────────────────────────────╯
╭─ Languages ──────────────────────────────────────────────╮
│ Python      ████████████████████   71.4%   10,142 loc    │
│ TypeScript  ██████                  18.9%    2,681 loc    │
│ CSS         ██                       6.1%      867 loc    │
╰──────────────────────────────────────────────────────────╯
╭─ Complexity hotspots ──────╮ ╭─ Biggest files ───────────╮
│ 27  handle_request  app... │ │ 1,204  src/engine.py      │
│ 19  parse_config    conf.. │ │   932  src/api/routes.py  │
╰────────────────────────────╯ ╰───────────────────────────╯
```

</div>

## Install

```bash
pip install repolens
```

Or run without installing:

```bash
pipx run repolens .
```

## Usage

```bash
repolens                 # analyze current directory
repolens path/to/repo    # analyze another repo
repolens --json          # machine-readable output for scripts / CI
repolens --no-git        # skip git history
repolens --ignore dist --ignore fixtures
```

### JSON output

Pipe structured data anywhere — dashboards, CI gates, badges:

```bash
repolens --json | jq '.languages.Python.code'
```

## What it measures

| Section | What you get |
|---|---|
| **Languages** | Lines of code per language, ranked, with % bars |
| **Complexity hotspots** | Per-function cyclomatic complexity (Python via AST; heuristic for other langs) |
| **TODO tracker** | Every `TODO` / `FIXME` / `HACK` / `XXX` / `BUG` with file:line |
| **Biggest files** | The files most likely to need splitting |
| **Git activity** | Top authors, most-churned files, active days, project lifespan |

Binary files, `node_modules`, `.venv`, build dirs and friends are skipped
automatically.

## Design goals

- **Fast** — a single `os.walk`, no external services.
- **Honest** — no network, no telemetry, no surprise writes.
- **Pretty** — powered by [rich](https://github.com/Textualize/rich).
- **Scriptable** — everything the report shows is available as `--json`.

## Contributing

Adding a language is a one-line change in `languages.py`. PRs welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © repolens contributors
