"""Shapes for the roughing planner (radius space: z, and r = X / 2): the
tolerances it works to, growing and sweeping outlines, a profile as points,
and the differences and intersections GEOS is asked for - kept on a grid,
tried again on the shapes mended when it cannot work one out, and said so."""

from __future__ import annotations

import logging
import math

from typing import List, Sequence, Tuple
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union

from .geometry import ToolpathArc

log = logging.getLogger(__name__)


Pt = Tuple[float, float]

#: Far enough to stand for "everything that way", in mm.
FAR = 1000.0

#: How far a chord of a discretised arc may stray from it, in mm.
ARC_TOLERANCE = 0.002

#: Material thinner than this is not worth a move, and overlaps smaller than
#: this are rounding, not collisions; in mm and mm².
TOLERANCE = 0.005

MIN_AREA = 1e-3

#: A cut taking off less than this, on average along it, is not worth making;
#: in mm.
MIN_CUT = 0.01

def minkowski(shape, convex: Sequence[Pt]):
    """``shape`` (a Polygon or MultiPolygon) grown by the convex outline
    ``convex``: every point of the one plus every point of the other."""
    pieces = []
    polygons = getattr(shape, "geoms", [shape])
    for polygon in polygons:
        if polygon.is_empty:
            continue
        pieces.append(Polygon([(x + convex[0][0], y + convex[0][1])
                               for x, y in polygon.exterior.coords]))
        for ring in [polygon.exterior, *polygon.interiors]:
            coords = list(ring.coords)
            for (ax, ay), (bx, by) in zip(coords, coords[1:]):
                pieces.append(MultiPoint(
                    [(ax + x, ay + y) for x, y in convex]
                    + [(bx + x, by + y) for x, y in convex]).convex_hull)
    return unary_union(pieces)

def sweep(shape: Sequence[Pt], a: Pt, b: Pt):
    """What the convex ``shape`` covers moving from ``a`` to ``b``."""
    return MultiPoint([(a[0] + x, a[1] + y) for x, y in shape]
                      + [(b[0] + x, b[1] + y) for x, y in shape]).convex_hull

def path_points(path) -> List[Pt]:
    """A render path (X as diameter) as (z, r) points, arcs as chords no more
    than ARC_TOLERANCE off, their extremes in Z and X among the points."""
    points = [(path[0].z, path[0].x / 2.0)]
    for element in path[1:]:
        if isinstance(element, ToolpathArc):
            points.extend(_arc_points(points[-1], element)[1:])
        else:
            points.append((element.end_z, element.end_x / 2.0))
    return points

def _arc_points(start: Pt, arc) -> List[Pt]:
    cz, cr = arc.center_z, arc.center_x / 2.0
    radius = math.hypot(start[0] - cz, start[1] - cr)
    a0 = math.atan2(start[1] - cr, start[0] - cz)
    a1 = math.atan2(arc.end_x / 2.0 - cr, arc.end_z - cz)
    sweep_angle = a1 - a0
    if arc.anticlockwise:           # as the preview reads it: angle falling
        while sweep_angle > 0:
            sweep_angle -= 2 * math.pi
    else:
        while sweep_angle < 0:
            sweep_angle += 2 * math.pi
    if radius < 1e-9:
        return [start, (arc.end_z, arc.end_x / 2.0)]
    step = 2 * math.acos(max(-1.0, 1 - ARC_TOLERANCE / radius))
    count = max(1, int(math.ceil(abs(sweep_angle) / step)))
    fractions = {k / count for k in range(count + 1)}
    # the quadrant points - where the arc is furthest in Z or in X
    for k in range(-8, 9):
        q = k * math.pi / 2
        t = (q - a0) / sweep_angle if sweep_angle else 0.0
        if 0.0 < t < 1.0:
            fractions.add(t)
    points = [(cz + radius * math.cos(a0 + sweep_angle * t),
               cr + radius * math.sin(a0 + sweep_angle * t)) for t in sorted(fractions)]
    points[-1] = (arc.end_z, arc.end_x / 2.0)
    return points

#: The grid what is left is kept on, in mm: cut along the same lines again
#: and again - a contour, then passes ending on it - a shape picks up edges a
#: hair apart that GEOS cannot tell crossing or not ("non-noded
#: intersection"); on the grid they either meet or do not.
GRID = 1e-6

def _on_grid(shape):
    from shapely.ops import transform
    if shape.is_empty:
        return shape
    snapped = transform(lambda x, y, z=None: (_round(x), _round(y)), shape)
    return snapped if snapped.is_valid else snapped.buffer(0)

def _round(values):
    if hasattr(values, "__iter__"):
        return type(values)(round(v / GRID) * GRID for v in values)
    return round(values / GRID) * GRID

def _difference(a, b):
    """``a`` less ``b``, on the grid. Cut by many moves, a shape picks up
    slivers GEOS cannot always work with; mended and tried again, they go
    away."""
    from shapely.errors import TopologicalError
    try:
        result = a.difference(b)
    except (TopologicalError, ValueError) as error:
        log.warning("roughing plan: a difference GEOS could not work out (%s); "
                    "tried again on the shapes mended", error)
        result = a.buffer(0).difference(b.buffer(0))
    return _on_grid(result if result.is_valid else result.buffer(0))

def _intersection(a, b):
    """What ``a`` and ``b`` share; mended and tried again as _difference is."""
    from shapely.errors import TopologicalError
    try:
        return a.intersection(b)
    except (TopologicalError, ValueError) as error:
        log.warning("roughing plan: an intersection GEOS could not work out (%s); "
                    "tried again on the shapes mended", error)
        return a.buffer(0).intersection(b.buffer(0))

def _mirror(shape):
    from shapely import affinity
    return affinity.scale(shape, xfact=1.0, yfact=-1.0, origin=(0, 0))

def _simplify(points: List[Pt]) -> List[Pt]:
    """Points in a straight line dropped, the rest kept."""
    if len(points) < 3:
        return points
    out = [points[0]]
    for i in range(1, len(points) - 1):
        a, b, c = out[-1], points[i], points[i + 1]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cross) > 1e-9 * max(1.0, math.hypot(c[0] - a[0], c[1] - a[1])):
            out.append(b)
    out.append(points[-1])
    return out
