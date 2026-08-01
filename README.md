<div align="center">

# 🔍 repoglance

### Instant, gorgeous insight into any code repository — in one command.

Point it at any folder. In under a second you get a beautiful terminal report:
language breakdown, complexity hotspots, TODO tracker, biggest files, and git
activity. **Zero config. Zero API keys. Zero telemetry.**

[![PyPI](https://img.shields.io/pypi/v/repoglance.svg)](https://pypi.org/project/repoglance/)
[![CI](https://github.com/SRJ-ai/repoglance/actions/workflows/ci.yml/badge.svg)](https://github.com/SRJ-ai/repoglance/actions/workflows/ci.yml)
[![Python](https://img.shields.io/pypi/pyversions/repoglance.svg)](https://pypi.org/project/repoglance/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![repoglance](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/SRJ-ai/repoglance/main/.repoglance-badge.json)](https://github.com/SRJ-ai/repoglance)

</div>

---

## Why repoglance?

You clone an unfamiliar repo. What *is* this thing? How big? What's the messy
part? Where's the unfinished work? `cloc` gives you a wall of numbers. `tokei`
is fast but bare. `repoglance` answers the human questions in one glance:

```bash
repoglance .
```

<div align="center">

![repoglance demo](assets/demo.svg)

</div>

## Seen in the wild

repoglance run against well-known projects (click to view the full report):

| Project | Files | Lines of code | Health |
|---|--:|--:|:--:|
| [flask](assets/showcase/flask.svg) | 207 | 25,266 | D (67) |
| [httpie](assets/showcase/httpie.svg) | 234 | 20,023 | D (66) |
| [requests](assets/showcase/requests.svg) | 88 | 13,709 | C (70) |

<div align="center">

[![flask report](assets/showcase/flask.svg)](assets/showcase/flask.svg)

</div>

## Install

```bash
pip install repoglance
```

Or run without installing:

```bash
pipx run repoglance .
```

## Usage

```bash
repoglance                       # analyze current directory
repoglance path/to/repo          # analyze another repo
repoglance --json                # machine-readable output for scripts / CI
repoglance --csv                 # per-file CSV
repoglance --sarif               # SARIF for GitHub code scanning
repoglance --svg report.svg      # export a vector report
repoglance --html report.html    # export a browser report
repoglance --badge badge.svg     # export an embeddable badge
repoglance --since origin/main   # only files changed since a revision
repoglance --baseline base.json                         # snapshot now
repoglance --compare base.json --fail-on-regression     # fail on new complexity
repoglance --ci --fail-under 70 --max-complexity 25     # gate a build
repoglance --include "src/**" --exclude "**/*_pb2.py"   # glob filters
repoglance --duplicates          # detect copy-paste blocks
repoglance --owners              # attribute hotspots to authors (git blame)
repoglance --cache .rg.cache     # incremental cache for fast repeat runs
repoglance --watch               # live re-render on file changes
repoglance --no-git --jobs 8
```

### JSON output

Pipe structured data anywhere — dashboards, CI gates, badges:

```bash
repoglance --json | jq '.languages.Python.code'
```

## What it measures

| Section | What you get |
|---|---|
| **Languages** | Lines of code per language, ranked, with % bars |
| **Complexity hotspots** | Real per-function cyclomatic complexity across 15+ languages (C/C++, Java, C#, JS, TS, Go, Rust, Ruby, PHP, Swift, Kotlin, Python…) via [lizard](https://github.com/terryyin/lizard) |
| **Maintainability index** | Approximate MI (0–100) from complexity, size and token counts |
| **Duplicate code** | Copy-paste blocks across files, with a duplication % |
| **TODO tracker** | Every `TODO` / `FIXME` / `HACK` / `XXX` / `BUG` with file:line |
| **Biggest files & directories** | Where the mass and the worst complexity live |
| **Ownership** | Which author owns each hotspot (`--owners`, git blame) |
| **Git activity** | Top authors, most-churned files, active days, project lifespan |

Vendored and generated files (minified bundles, `_pb2.py`, `node_modules`, files
marked `@generated`) are detected and excluded by default — pass
`--include-vendored` to keep them.

Binary files, `node_modules`, `.venv`, build dirs and friends are skipped
automatically.

## More than a counter

`repoglance` isn't just another `cloc`. Tools like `tokei`, `cloc` and `scc`
answer *"how many lines?"*. repoglance answers *"what should I look at?"* — and
gives you artifacts you can put in a PR or a README.

| | repoglance | tokei | scc | cloc |
|---|:---:|:---:|:---:|:---:|
| Lines-of-code by language | ✅ | ✅ | ✅ | ✅ |
| Per-function complexity (15+ langs) | ✅ | ❌ | ⚠️ file-level | ❌ |
| Maintainability index | ✅ | ❌ | ❌ | ❌ |
| TODO / FIXME tracker | ✅ | ❌ | ❌ | ❌ |
| Git activity (authors, churn) | ✅ | ❌ | ❌ | ❌ |
| Respects `.gitignore` | ✅ | ✅ | ✅ | ❌ |
| JSON / CSV / **SARIF** output | ✅ | ⚠️ | ⚠️ | ⚠️ |
| **HTML / SVG report export** | ✅ | ❌ | ❌ | ❌ |
| **Embeddable repo badge** | ✅ | ❌ | ❌ | ❌ |
| **Diff mode (`--since`) + baselines** | ✅ | ❌ | ❌ | ❌ |
| **CI gate + regression ratchet** | ✅ | ❌ | ❌ | ❌ |
| **Config file** (`[tool.repoglance]`) | ✅ | ✅ | ❌ | ❌ |

## Share it: badges & reports

Generate a self-contained SVG badge — no shields.io round-trip, no tracking:

```bash
repoglance --badge assets/badge.svg
```

![repoglance badge](assets/badge.svg)

Export the full report as a standalone file to drop in a PR or wiki:

```bash
repoglance --svg report.svg      # vector, pixel-perfect
repoglance --html report.html    # opens in any browser
```

## Guard your codebase in CI

Fail the build when complexity or TODO debt crosses a line:

```bash
repoglance --ci --max-complexity 25 --max-todos 100
```

```yaml
# .github/workflows/quality.yml
- run: pip install repoglance
- run: repoglance --ci --max-complexity 25
```

Exit code `0` = clean, `2` = a threshold was exceeded.

## Integrations

### GitHub Action — comment on every PR

Drop repoglance into any repo. It posts a sticky report comment on pull requests
and can gate the build:

```yaml
# .github/workflows/repoglance.yml
name: repoglance
on: [pull_request]
permissions:
  contents: read
  pull-requests: write
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: SRJ-ai/repoglance@v0.4.0
        with:
          fail-under: "70"       # optional health gate
          max-complexity: "25"   # optional complexity gate
```

The report also lands in the workflow's **job summary** every run.

### pre-commit hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/SRJ-ai/repoglance
    rev: v0.4.0
    hooks:
      - id: repoglance
        args: ["--ci", "--fail-under", "70"]
```

### Self-updating badge

Commit a shields endpoint file and point a dynamic badge at it — the badge
refreshes itself, no service to run:

```bash
repoglance --badge-json .repoglance-badge.json   # commit this file
```

```markdown
![repoglance](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/SRJ-ai/repoglance/main/.repoglance-badge.json)
```

### Markdown anywhere

```bash
repoglance --md   # paste into a PR, wiki, or Slack
```

### Configuration file

Set defaults once via `.repoglance.toml` or a `[tool.repoglance]` table in
`pyproject.toml` (CLI flags always win):

```toml
[tool.repoglance]
exclude = ["**/*_pb2.py", "vendor/**"]
max_complexity = 25
fail_under = 70
```

### Docker & GitLab

```bash
docker run --rm -v "$PWD:/repo" repoglance /repo
```

A ready-to-copy GitLab CI job lives in
[`integrations/gitlab-ci.yml`](integrations/gitlab-ci.yml).

## Built for large monorepos

repoglance is designed to stay useful at the scale of a big-tech monorepo —
millions of lines, thousands of files — not just small projects:

- **Diff mode** (`--since <rev>`) analyzes only the files a change touches, so a
  PR check on a giant repo stays fast regardless of total size.
- **Incremental cache** (`--cache`) reuses unchanged files by mtime + size —
  repeat runs are near-instant (see below).
- **True multicore scanning**: for large repos it automatically uses a process
  pool (complexity parsing is CPU-bound, so threads alone can't use every core),
  roughly halving cold-scan time. Force it with `--processes` / `--threads`.
- **`.gitignore`-aware** and **vendored/generated exclusion**, so third-party
  and generated code doesn't drown the signal.
- **Path scoping** with `--include` / `--exclude` globs for per-team slices of a
  shared repo.

> Note: repoglance is an independent open-source project. It is not affiliated
> with, endorsed by, or used by any company named for scale comparison.

## Performance

Measured on Django (3,180 files, ~415k lines of code), single machine:

| Run | Repo | Time |
|---|---|--:|
| Cold scan, full analysis (8 cores) | Django, 415k LOC | ~5.0 s |
| Re-run with `--cache` | Django, 415k LOC | ~1.1 s |
| **`--fast` (counts only), process pool** | **20,000,000 LOC** | **~4.4 s** |

`--fast` skips per-function complexity parsing (the expensive step) and reports
languages, line counts and sizes only — that's what makes a 20-million-line
scan finish in seconds (~4.5M LOC/s here). Drop `--fast` when you want the full
complexity/health analysis.

The cold scan is dominated by real per-function complexity parsing. The process
pool spreads that across cores (~2× here); the incremental cache (`--cache
<file>`) reuses unchanged files by mtime + size, so repeat runs — the common
case in editors and CI — are roughly **20× faster** than a cold thread scan.

## Design goals

- **Fast** — a single pass, no external services.
- **Honest** — no network, no telemetry, no surprise writes.
- **Pretty** — powered by [rich](https://github.com/Textualize/rich).
- **Scriptable** — everything the report shows is available as `--json`.

## Contributing

Adding a language is a one-line change in `languages.py`. PRs welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © repoglance contributors
