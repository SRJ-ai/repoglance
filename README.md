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
[![repolens](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/SRJ-ai/repolens/main/.repolens-badge.json)](https://github.com/SRJ-ai/repolens)

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

![repolens demo](assets/demo.svg)

</div>

## Seen in the wild

repolens run against well-known projects (click to view the full report):

| Project | Files | Lines of code | Health |
|---|--:|--:|:--:|
| [flask](assets/showcase/flask.svg) | 200 | 25,030 | D (64) |
| [httpie](assets/showcase/httpie.svg) | 217 | 19,604 | D (62) |
| [requests](assets/showcase/requests.svg) | 71 | 13,215 | D (69) |

<div align="center">

[![flask report](assets/showcase/flask.svg)](assets/showcase/flask.svg)

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
repolens                       # analyze current directory
repolens path/to/repo          # analyze another repo
repolens --json                # machine-readable output for scripts / CI
repolens --svg report.svg      # export a vector report
repolens --html report.html    # export a browser report
repolens --badge badge.svg     # export an embeddable badge
repolens --ci --max-complexity 25   # fail CI on hotspots
repolens --no-git              # skip git history
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

## More than a counter

`repolens` isn't just another `cloc`. Tools like `tokei`, `cloc` and `scc`
answer *"how many lines?"*. repolens answers *"what should I look at?"* — and
gives you artifacts you can put in a PR or a README.

| | repolens | tokei | scc | cloc |
|---|:---:|:---:|:---:|:---:|
| Lines-of-code by language | ✅ | ✅ | ✅ | ✅ |
| Complexity hotspots (per function) | ✅ | ❌ | ⚠️ file-level | ❌ |
| TODO / FIXME tracker | ✅ | ❌ | ❌ | ❌ |
| Git activity (authors, churn) | ✅ | ❌ | ❌ | ❌ |
| JSON output | ✅ | ✅ | ✅ | ✅ |
| **HTML / SVG report export** | ✅ | ❌ | ❌ | ❌ |
| **Embeddable repo badge** | ✅ | ❌ | ❌ | ❌ |
| **CI gate (`--max-complexity`)** | ✅ | ❌ | ❌ | ❌ |
| Zero install deps beyond one `pip` | ✅ | (binary) | (binary) | (perl) |

## Share it: badges & reports

Generate a self-contained SVG badge — no shields.io round-trip, no tracking:

```bash
repolens --badge assets/badge.svg
```

![repolens badge](assets/badge.svg)

Export the full report as a standalone file to drop in a PR or wiki:

```bash
repolens --svg report.svg      # vector, pixel-perfect
repolens --html report.html    # opens in any browser
```

## Guard your codebase in CI

Fail the build when complexity or TODO debt crosses a line:

```bash
repolens --ci --max-complexity 25 --max-todos 100
```

```yaml
# .github/workflows/quality.yml
- run: pip install repolens
- run: repolens --ci --max-complexity 25
```

Exit code `0` = clean, `2` = a threshold was exceeded.

## Integrations

### GitHub Action — comment on every PR

Drop repolens into any repo. It posts a sticky report comment on pull requests
and can gate the build:

```yaml
# .github/workflows/repolens.yml
name: repolens
on: [pull_request]
permissions:
  contents: read
  pull-requests: write
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: SRJ-ai/repolens@main
        with:
          fail-under: "70"       # optional health gate
          max-complexity: "25"   # optional complexity gate
```

The report also lands in the workflow's **job summary** every run.

### pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/SRJ-ai/repolens
    rev: v0.1.1
    hooks:
      - id: repolens
        args: ["--ci", "--fail-under", "70"]
```

### Self-updating badge

Commit a shields endpoint file and point a dynamic badge at it — the badge
refreshes itself, no service to run:

```bash
repolens --badge-json .repolens-badge.json   # commit this file
```

```markdown
![repolens](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/SRJ-ai/repolens/main/.repolens-badge.json)
```

### Markdown anywhere

```bash
repolens --md   # paste into a PR, wiki, or Slack
```

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
