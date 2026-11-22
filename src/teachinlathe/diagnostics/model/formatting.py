"""Numbers as the diagnostics panel shows them."""

from __future__ import annotations

import math


def short(value) -> str:
    """A number in a few characters: 16.5k, 1.2M, 123, 12.3, 1.23."""
    value = float(value)
    if math.isnan(value):
        return "–"
    if abs(value) >= 1e6:
        return "%.1fM" % (value / 1e6)
    if abs(value) >= 1e4:
        return "%.1fk" % (value / 1e3)
    if abs(value) >= 1000:
        return "%.0f" % value
    if abs(value) >= 10:
        return "%.1f" % value
    return "%.2f" % value


def fixed(value, digits: int = 1, unit: str = "") -> str:
    """``value`` with ``digits`` decimals and its unit; "–" with none."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    text = ("%%.%df" % digits) % value
    return text + (" " + unit if unit else "")
