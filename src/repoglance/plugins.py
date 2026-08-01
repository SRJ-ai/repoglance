"""Third-party metric plugins via entry points.

A plugin package registers a callable under the ``repoglance.metrics`` entry
point group. Each callable receives the completed ``ScanResult`` and returns a
JSON-serializable value; results appear under ``plugins`` in the JSON output.

Example (in a plugin's pyproject.toml)::

    [project.entry-points."repoglance.metrics"]
    my_metric = "my_pkg:compute"
"""
from __future__ import annotations

from typing import Any, Dict

_GROUP = "repoglance.metrics"


def _iter_entry_points():
    try:
        from importlib.metadata import entry_points
    except Exception:  # pragma: no cover
        return []
    try:
        eps = entry_points()
        # Python 3.10+ returns a SelectableGroups object.
        if hasattr(eps, "select"):
            return list(eps.select(group=_GROUP))
        return list(eps.get(_GROUP, []))  # 3.9
    except Exception:  # pragma: no cover
        return []


def run_plugins(result) -> Dict[str, Any]:
    """Invoke every registered metric plugin, isolating failures."""
    out: Dict[str, Any] = {}
    for ep in _iter_entry_points():
        try:
            func = ep.load()
            out[ep.name] = func(result)
        except Exception as exc:  # a broken plugin must not break the report
            out[ep.name] = {"error": str(exc)}
    return out
