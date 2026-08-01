# repoglance for VS Code

Runs [repoglance](https://github.com/SRJ-ai/repoglance) on your workspace and
shows complexity hotspots in the **Problems** panel.

## Use it

1. `pip install repoglance` (or set `repoglance.path` to the executable).
2. Command Palette → **repoglance: Analyze workspace**.

Functions with cyclomatic complexity ≥ 10 appear as warnings; ≥ 25 as errors.

This is a minimal reference extension (not yet published to the Marketplace).
Package it with [`vsce`](https://github.com/microsoft/vscode-vsce):

```bash
npm install -g @vscode/vsce
vsce package
```
