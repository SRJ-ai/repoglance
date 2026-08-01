# repoglance

Instant, gorgeous insight into any code repository — in one command.

```bash
pip install repoglance
repoglance .
```

See the [README](https://github.com/SRJ-ai/repoglance#readme) for the full
feature tour: languages, real cyclomatic complexity (via lizard), TODO tracker,
git activity, health score, maintainability index, diff mode, baselines, SARIF,
and the GitHub Action.

## Common commands

| Command | Purpose |
|---|---|
| `repoglance .` | Terminal report |
| `repoglance --json` / `--md` / `--csv` / `--sarif` | Machine-readable output |
| `repoglance --since main` | Only files changed since a revision |
| `repoglance --baseline base.json` | Snapshot for later comparison |
| `repoglance --compare base.json --fail-on-regression` | Fail on new complexity |
| `repoglance --ci --fail-under 70 --max-complexity 25` | Gate a build |

## Configuration

Add a `[tool.repoglance]` table to `pyproject.toml` or a `.repoglance.toml`:

```toml
[tool.repoglance]
exclude = ["**/*_pb2.py", "vendor/**"]
max_complexity = 25
fail_under = 70
```
