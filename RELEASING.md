# Releasing repolens

Releases publish to [PyPI](https://pypi.org/project/repolens/) automatically
via GitHub Actions using PyPI's **trusted publisher** (OIDC) — there is no API
token stored anywhere.

## One-time PyPI setup

1. Sign in to PyPI → **Account → Publishing → Add a pending publisher**.
2. Fill in:
   - **PyPI project name:** `repolens`
   - **Owner:** `SRJ-ai`
   - **Repository:** `repolens`
   - **Workflow name:** `release.yml`
   - **Environment:** `pypi`
3. Save.
4. In the GitHub repo → **Settings → Secrets and variables → Actions →
   Variables**, add a repository variable `PUBLISH_TO_PYPI` = `true`. This gates
   the publish job, so version tags can be cut (e.g. to publish the Action to
   the Marketplace) without a failing PyPI job before the publisher exists.

## Cutting a release

1. Bump the version in **both** `pyproject.toml` and
   `src/repolens/__init__.py` (keep them in sync).
2. Commit: `git commit -am "release: v0.1.1"`.
3. Tag and push:

   ```bash
   git tag v0.1.1
   git push origin main --tags
   ```

4. The `Release` workflow builds the sdist + wheel, runs `twine check`, and
   publishes to PyPI. Watch it under the repo's **Actions** tab.

## Local build check

```bash
python -m pip install --upgrade build twine
python -m build
twine check dist/*
```
