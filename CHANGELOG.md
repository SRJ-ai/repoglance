# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2026-08-01

### Added
- **Refactor priority**: files ranked by **churn × complexity** — frequently
  changed *and* complex code, the classic "fix this first" signal. Shown as a
  panel and in JSON (`risk`).
- **Coverage × complexity** (`--coverage <cobertura.xml|lcov>`): surfaces
  complex, poorly-covered files (risk = complexity × (1 − coverage)).
- **Python quality**: docstring and type-hint coverage across functions.
- **Import graph** (`--imports`): intra-repo Python module coupling and
  **circular-import detection**.
- **Longest functions**: biggest functions by logical lines (in JSON).
- **Activity trend**: commits-per-month sparkline in the git panel.
- **GitHub Action inline annotations** (`annotations: true`): a Check Run places
  complexity warnings on the exact lines in a PR.

## [0.4.3] - 2026-08-01

### Added
- **`--fast` mode**: counts only (languages, LOC, sizes), skipping per-function
  complexity parsing — the expensive step. Combined with the process pool this
  scans **20 million lines in ~4.4 s** (~4.5M LOC/s). Use it for size/inventory
  passes on very large monorepos; drop it for full complexity/health analysis.

### Changed
- **Python complexity now uses CPython's C-accelerated `ast`** instead of the
  pure-Python tokenizer, roughly **halving full-analysis time on Python-heavy
  repos** (Django 415k LOC: ~10 s → ~5 s on 8 cores). Other languages still use
  lizard. Adaptive process-pool chunk sizing reduces IPC overhead.

## [0.4.2] - 2026-08-01

### Added
- **Multicore scanning for large repositories**: complexity parsing now runs in
  a process pool when a scan is big enough (CPU-bound work the GIL kept threads
  from parallelizing), roughly halving cold-scan time on large monorepos. Force
  the mode with `--processes` / `--threads`. Django (415k LOC): ~20.5s → ~10.1s.

## [0.4.1] - 2026-08-01

### Added
- `--sarif-threshold` to control the minimum complexity reported in SARIF.
- Ruff linting and coverage reporting in CI; a reproducible `benchmarks/bench.py`.

### Changed
- Internal refactors (`gitinfo.collect`) and lint cleanups; no behavior change.

## [0.4.0] - 2026-08-01

### Added
- **Duplicate-code detection** (`--duplicates`): sliding line-window hashing
  surfaces copy-paste blocks and a duplication percentage.
- **Vendored/generated detection**: minified bundles, `_pb2.py`, lock files,
  `node_modules`, and files marked `@generated` are excluded by default;
  `--include-vendored` keeps them.
- **Ownership** (`--owners`): attributes the top complexity hotspots to authors
  via `git blame`.
- **Incremental cache** (`--cache <file>`): unchanged files are reused across
  runs by mtime + size, speeding up repeated scans.
- **Plugin API**: third-party packages can register metrics under the
  `repoglance.metrics` entry-point group; results appear under `plugins`.
- **Watch mode** (`--watch`): re-render the report whenever files change.
- Homebrew formula template and a minimal VS Code extension (Problems panel).

### Fixed
- Git subprocesses now decode as UTF-8, fixing crashes on non-Latin-1 blame
  output on Windows.

## [0.3.0] - 2026-08-01

### Added
- **Real cyclomatic complexity across 15+ languages** via `lizard` (C/C++, Java,
  C#, JavaScript, TypeScript, Go, Rust, Ruby, PHP, Swift, Kotlin, Python and
  more). Python keeps an AST fallback; a keyword heuristic remains as last
  resort. Complexity for non-Python languages is now trustworthy, not a guess.
- **Maintainability index** (0–100), approximate Microsoft MI from complexity,
  size and token counts.
- **Diff mode** `--since <rev>`: analyze only files changed since a git ref —
  ideal for PRs. The Action exposes it via `diff-base`.
- **Baselines & regression ratchet**: `--baseline` snapshots a report;
  `--compare` shows health/complexity/TODO/LOC deltas; `--fail-on-regression`
  fails only on new or worse complexity.
- **SARIF output** (`--sarif`) for GitHub code scanning; the Action can upload
  it (`sarif: true`) so hotspots appear inline on the Files changed tab.
- **CSV output** (`--csv`) and a **per-directory rollup** (report + JSON).
- **Config file**: `.repoglance.toml` or `[tool.repoglance]` in pyproject.
- **Glob include/exclude** (`--include` / `--exclude`) beyond directory names.
- **Parallel scanning** (`--jobs`) via a thread pool.
- Docker image, GitLab CI template, and mkdocs docs scaffold.

## [0.2.2] - 2026-08-01

### Added
- Respect the repository's `.gitignore`: when scanning a git repo, the file
  list comes from `git ls-files` so ignored files are excluded (matches the
  behavior of `tokei`/`scc`). Non-git directories still use a pruned walk.
- Count C-style `/* ... */` block comments when classifying lines, improving the
  comment ratio (and therefore the health score) for C-family languages.
- Expanded test suite: CLI end-to-end (`click` runner), `.gitignore` handling,
  block comments, and inline complexity scoring.

### Changed
- Every file is now read exactly once. Complexity is computed during the scan
  from the text already in memory instead of re-reading every file in a second
  pass — roughly halving I/O on large repositories.

## [0.2.1] - 2026-08-01

### Changed
- Marketplace listing name set to a globally-unique title.

## [0.2.0] - 2026-08-01

### Changed
- Renamed the PyPI package and CLI to **repoglance** (the GitHub repository is
  unchanged). Only line-comment TODO markers are counted, avoiding false
  positives from prose and marker lists.

## [0.1.0] - 2026-08-01

### Added
- Initial release: rich terminal report (languages, complexity hotspots, TODO
  tracker, biggest files, git activity), health score, JSON/Markdown/SVG/HTML
  output, self-contained and dynamic badges, CI gate, GitHub Action, and
  pre-commit hook.
