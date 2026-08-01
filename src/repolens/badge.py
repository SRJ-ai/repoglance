"""Generate a self-contained shields-style SVG badge from scan results.

No network, no external service — the SVG is fully static and embeddable in a
README. Character-width estimation mirrors shields.io closely enough for a
clean, non-overlapping badge with Verdana/DejaVu.
"""
from __future__ import annotations

from .languages import color_for
from .scanner import ScanResult

# Approximate per-character advance width at 11px, keyed by character.
# Falls back to _AVG for anything unlisted. Good enough for tidy padding.
_AVG = 7.0
_WIDTHS = {
    " ": 3.5, "i": 3.0, "l": 3.0, "j": 3.0, "t": 4.0, "f": 4.0, "r": 4.5,
    "I": 3.5, ".": 3.5, ",": 3.5, ":": 3.5, "1": 6.0, "m": 10.0, "w": 9.0,
    "M": 10.0, "W": 11.0, "%": 10.0,
}


def _text_width(s: str) -> float:
    return sum(_WIDTHS.get(c, _AVG) for c in s)


def _human_loc(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_badge(label: str, message: str, color: str) -> str:
    """Return an SVG string for a two-part badge: ``label`` | ``message``."""
    pad = 10.0
    lw = _text_width(label) + pad * 2
    mw = _text_width(message) + pad * 2
    total = lw + mw
    height = 20
    # Text anchors sit at the horizontal center of each half (x10 for crispness).
    lx = lw / 2 * 10
    mx = (lw + mw / 2) * 10
    label_e, message_e = _escape(label), _escape(message)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total:.0f}" height="{height}" role="img" aria-label="{label_e}: {message_e}">
  <title>{label_e}: {message_e}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r"><rect width="{total:.0f}" height="{height}" rx="3" fill="#fff"/></clipPath>
  <g clip-path="url(#r)">
    <rect width="{lw:.0f}" height="{height}" fill="#555"/>
    <rect x="{lw:.0f}" width="{mw:.0f}" height="{height}" fill="{color}"/>
    <rect width="{total:.0f}" height="{height}" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="110" text-rendering="geometricPrecision">
    <text aria-hidden="true" x="{lx:.0f}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{_text_width(label) * 10:.0f}">{label_e}</text>
    <text x="{lx:.0f}" y="140" transform="scale(.1)" textLength="{_text_width(label) * 10:.0f}">{label_e}</text>
    <text aria-hidden="true" x="{mx:.0f}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{_text_width(message) * 10:.0f}">{message_e}</text>
    <text x="{mx:.0f}" y="140" transform="scale(.1)" textLength="{_text_width(message) * 10:.0f}">{message_e}</text>
  </g>
</svg>
"""


def badge_for_scan(res: ScanResult) -> str:
    """Build a repolens badge summarizing lines of code and top language."""
    agg = res.by_language()
    top_lang = max(agg.items(), key=lambda kv: kv[1]["code"])[0] if agg else "code"
    message = f"{_human_loc(res.total_code)} loc • {top_lang}"
    return render_badge("repolens", message, color_for(top_lang))
