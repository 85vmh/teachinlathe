"""The tool as the roughing planner sees it: the insert at its real size and
nose radius, turned the way the backplot turns it, hung from its control
point, its edges carried on to stand for the holder (see machining.py)."""

from __future__ import annotations

import math

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
from shapely.geometry import MultiPoint

from .shapes import Pt


#: How far round the insert is swung either way to keep clear of what it
#: passes, in degrees.
CLEARANCE_DEGREES = 2.0

#: The insert's nose rounded with this many chords per corner.
NOSE_SEGMENTS = 24

#: How far the insert's cutting edges are carried on past their ends, to
#: stand for the holder behind them; in mm.
EDGE_REACH = 200.0

@dataclass(frozen=True)
class ToolShape:
    """The insert as an outline around its control point, in (z, r), as the
    real tool sits - not mirrored for ID."""
    outline: Tuple[Pt, ...]          # the insert itself, for drawing
    envelope: Tuple[Pt, ...]         # outline with its edges carried on, swung by the clearance, convex
    nose_radius: float
    label: str
    known: bool = True               # False: no insert to go by (see square_tool)
    #: the nose's centre, from the control point
    centre: Pt = (0.0, 0.0)

def insert_tool_shape(tool, clearance_degrees: float = CLEARANCE_DEGREES) -> Optional[ToolShape]:
    """The shape of a Tool Library TurningTool (boring bars too); None for
    any other kind of tool."""
    from teachinlathe.tooling.model import insert_catalog, tool_angles
    from teachinlathe.tooling.model.data_types import TurningTool
    from teachinlathe.ui.tabs.programs.backplot.actors.geometry import circle_loop, rounded_polygon

    if not isinstance(tool, TurningTool):
        return None
    insert = insert_catalog.insert_for(tool.insert)
    tip = insert.active_tip()
    rotation = math.radians(tool_angles.insert_rotation(
        tool.orientation, tool.front_angle, tool.back_angle,
        tool_angles.direction_degrees(tip)))
    edges = []                          # the cutting corner's two neighbours
    if insert.is_round:
        loop = circle_loop(insert.ic / 2.0, 8 * NOSE_SEGMENTS)
    else:
        verts, _cutting = insert.outline()
        loop = rounded_polygon(verts, insert.nose_radius, NOSE_SEGMENTS)
        index = verts.index(tip)
        edges = [verts[(index - 1) % len(verts)], verts[(index + 1) % len(verts)]]
    nose = insert.nose_centre()
    radius = insert.ic / 2.0 if insert.is_round else insert.nose_radius

    def place(point):
        # backplot.actors.insert_tool: hung from the sharp tip, turned, then
        # the drawing's y is minus X
        x, y = point[0] - tip[0], point[1] - tip[1]
        c, s = math.cos(rotation), math.sin(rotation)
        x, y = x * c - y * s, x * s + y * c
        return x, -y                                  # (z, r)

    outline = [place(p) for p in loop]
    centre = place(nose)
    tip_dir = (-centre[0], -centre[1])               # nose centre -> sharp tip
    control = _control_point(centre, radius, tip_dir)
    outline = [(z - control[0], r - control[1]) for z, r in outline]
    centre = (centre[0] - control[0], centre[1] - control[1])
    reach = list(outline)
    corner = place(tip)
    for neighbour in map(place, edges):
        dz, dr = neighbour[0] - corner[0], neighbour[1] - corner[1]
        length = math.hypot(dz, dr)
        reach += [(z + EDGE_REACH * dz / length, r + EDGE_REACH * dr / length) for z, r in outline]
    envelope = _swung(reach, centre, clearance_degrees)
    return ToolShape(tuple(outline), tuple(envelope), radius, insert.iso_code, centre=centre)

def square_tool() -> ToolShape:
    """Stands in for a tool there is nothing known about: a square corner
    reaching far up and toward the tailstock. Cutting with it is roughing
    along the profile's monotonic hull - no pocket, no undercut is entered,
    since nothing proves the real tool would fit."""
    size = 50.0
    outline = ((0.0, 0.0), (size, 0.0), (size, size), (0.0, size))
    return ToolShape(outline, outline, 0.0, "unknown tool", known=False)

def _control_point(centre: Pt, radius: float, tip_dir: Pt) -> Pt:
    """The point the tool is programmed to: where touching off in X and in Z
    measures it - the nose's tangent in each direction the tip points. A tip
    pointing straight along X has its Z on the centre."""
    sz = 0.0 if abs(tip_dir[0]) < 1e-3 * math.hypot(*tip_dir) else math.copysign(1.0, tip_dir[0])
    sr = 0.0 if abs(tip_dir[1]) < 1e-3 * math.hypot(*tip_dir) else math.copysign(1.0, tip_dir[1])
    return centre[0] + sz * radius, centre[1] + sr * radius

def _swung(points: Sequence[Pt], centre: Pt, degrees: float) -> List[Pt]:
    """``points`` and the same turned ``degrees`` either way about ``centre``,
    as one convex outline: the insert with its clearance."""
    swept = list(points)
    for angle in (-degrees, degrees):
        a = math.radians(angle)
        c, s = math.cos(a), math.sin(a)
        for z, r in points:
            dz, dr = z - centre[0], r - centre[1]
            swept.append((centre[0] + dz * c - dr * s, centre[1] + dz * s + dr * c))
    hull = MultiPoint(swept).convex_hull
    return list(hull.exterior.coords)[:-1]
