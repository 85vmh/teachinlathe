"""The plot's view as glnav keeps it, worked out directly: what the pinch, and
the zoom out and back in of a trip away (excursion_view), set it to.

A view is (distance, modelview): glnav's ortho distance - the half width
shown is ``abs(distance) ** ORTHO_EXPONENT`` eye units across the window's
width (GlNavBase.get_projection_matrix), the height in proportion - and its
4x4 modelview, model (machine, internal units) to eye. Two views that turn
the same way differ by a shift of the eye.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence, Tuple

import numpy as np

#: The exponent in GlNavBase.get_projection_matrix's ortho half width.
ORTHO_EXPONENT = 0.55555
#: The bounds glnav's zoomin/zoomout keep the distance within.
MIN_DISTANCE, MAX_DISTANCE = 0.1, 6000.0
#: Round what a fit takes in, a fraction of its size on each side.
MARGIN = 0.08

View = Tuple[float, np.ndarray]


def half_width(distance: float) -> float:
    """The half width shown at ``distance``, eye units."""
    return abs(distance) ** ORTHO_EXPONENT


def distance_for(half: float) -> float:
    """The distance that shows ``half`` eye units each side, within glnav's bounds."""
    return min(MAX_DISTANCE, max(MIN_DISTANCE, max(half, 1e-9) ** (1.0 / ORTHO_EXPONENT)))


def shift(x: float, y: float) -> np.ndarray:
    """The eye moved by ``x``, ``y``: to go before a modelview."""
    matrix = np.identity(4)
    matrix[0, 3], matrix[1, 3] = x, y
    return matrix


def fit(view: View, points: Iterable[Sequence[float]], width: float, height: float) -> View:
    """``view`` zoomed out and moved to take in ``points`` (model) as well as
    what it shows, with a margin; never zoomed in."""
    distance, modelview = view
    aspect = max(1.0, float(height)) / max(1.0, float(width))
    half = half_width(distance)
    low = np.array([-half, -half * aspect])
    high = -low
    for point in points:
        eye = modelview @ np.array([point[0], point[1], point[2], 1.0])
        low = np.minimum(low, eye[:2])
        high = np.maximum(high, eye[:2])
    centre = (low + high) / 2.0
    size = (high - low) / 2.0 * (1.0 + 2.0 * MARGIN)
    half = max(size[0], size[1] / aspect)
    return math.copysign(distance_for(half), distance or 1.0), shift(-centre[0], -centre[1]) @ modelview


def between(start: View, end: View, fraction: float) -> View:
    """The view ``fraction`` (0..1) of the way from ``start`` to ``end``: the
    half width shown goes geometrically, the eye's shift in a line."""
    fraction = min(1.0, max(0.0, fraction))
    (d0, m0), (d1, m1) = start, end
    k0, k1 = half_width(d0), half_width(d1)
    half = k0 * (k1 / k0) ** fraction if k0 > 0 and k1 > 0 else k1
    # m0 = shift(t) @ m1: the same turn, the eye shifted by t
    origin = np.array([0.0, 0.0, 0.0, 1.0])
    t = (m0 @ origin - m1 @ origin)[:2]
    moved = (1.0 - fraction) * t
    return math.copysign(distance_for(half), d1 or 1.0), shift(moved[0], moved[1]) @ m1


def copy(view: View) -> View:
    return view[0], np.array(view[1], dtype=np.float64, copy=True)
