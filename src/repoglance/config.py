"""Load configuration from ``.repoglance.toml`` or ``[tool.repoglance]``.

CLI options always win; config only supplies defaults. Recognized keys::

    ignore = ["fixtures", "migrations"]   # directory names
    include = ["src/**"]                  # fnmatch globs (repo-relative)
    exclude = ["**/*_pb2.py"]             # fnmatch globs
    max_bytes = 2000000
    max_complexity = 25
    max_todos = 200
    fail_under = 70
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

try:  # Python 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover - <3.11 uses tomli
    try:
        import tomli as _toml  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        _toml = None

_KEYS = {"ignore", "include", "exclude", "max_bytes", "max_complexity",
         "max_todos", "fail_under"}


def _read_toml(path: Path) -> Dict[str, Any]:
    if _toml is None or not path.is_file():
        return {}
    try:
        with open(path, "rb") as fh:
            return _toml.load(fh)
    except Exception:
        return {}


def load_config(root: Path) -> Dict[str, Any]:
    """Merge ``.repoglance.toml`` and ``[tool.repoglance]`` from pyproject.

    A dedicated ``.repoglance.toml`` takes precedence over the pyproject table.
    """
    cfg: Dict[str, Any] = {}

    pyproject = _read_toml(root / "pyproject.toml")
    tool = pyproject.get("tool", {}).get("repoglance", {})
    if isinstance(tool, dict):
        cfg.update({k: v for k, v in tool.items() if k in _KEYS})

    dedicated = _read_toml(root / ".repoglance.toml")
    cfg.update({k: v for k, v in dedicated.items() if k in _KEYS})

    return cfg
