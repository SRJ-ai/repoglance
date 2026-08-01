# Contributing to repoglance

Thanks for helping! repoglance aims to stay **small, fast, and dependency-light**.

## Dev setup

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Adding a language

Most language support is a one-line change. Add the extension to `EXT_LANG` in
[`src/repoglance/languages.py`](src/repoglance/languages.py):

```python
"kt": "Kotlin",
```

Optionally give it a color in `LANG_COLOR` and a comment prefix in
`_COMMENT_PREFIX` (in `scanner.py`) so blank/comment/code counts are accurate.

## Guidelines

- Keep the runtime dependencies to `rich` + `click`. Anything heavier needs a
  strong justification.
- Every behavior the report shows must also be reachable via `--json`.
- Add or update a test in `tests/` for any logic change.
- Run `python -m pytest -q` before opening a PR.

## Ideas / good first issues

- SVG or PNG report export.
- Per-directory rollups.
- `--since <rev>` to scope git activity to a range.
- More accurate multi-line comment handling.

PRs and issues welcome. Be kind. 🌱
