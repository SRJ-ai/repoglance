# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
