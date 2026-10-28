"""The tool as the planners see it, an outline around the point it was
touched off on: the insert at its real size and nose radius, turned the way
the backplot turns it, its edges carried on to stand for the holder (see
planner.py); a parting or grooving blade, its corners rounded, its body
going on up."""

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

#: mm the square_tool reaches up and toward the tailstock.
SQUARE_TOOL_SIZE = 50.0

#: mm a blade's body is carried up from its end: past any groove, so a body
#: that would rub a flank on its way in is caught as well.
BLADE_BODY = 100.0

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
    size = SQUARE_TOOL_SIZE
    outline = ((0.0, 0.0), (size, 0.0), (size, size), (0.0, size))
    return ToolShape(outline, outline, 0.0, "unknown tool", known=False)

def blade_shape(width: float, left_radius: float, right_radius: float, control: int,
                body: float = BLADE_BODY) -> ToolShape:
    """A parting or grooving blade, ``width`` wide, its end's corners
    rounded by their own radii (each at most half the width), its body going
    on up ``body``: drawn in the planning frame - r away from the part, as
    the square_tool is - around the point it was touched off on, ``control``
    -1 its left corner, 0 the middle of its end, 1 its right corner."""
    half = width / 2.0
    left = min(max(left_radius, 0.0), half)
    right = min(max(right_radius, 0.0), half)
    shift = -control * half

    def corner(centre_z, radius, from_degrees):
        # a quarter round, NOSE_SEGMENTS chords; a sharp corner its point
        if radius <= 0.0:
            return [(centre_z + shift, 0.0)]
        return [(centre_z + shift + radius * math.cos(math.radians(from_degrees + 90.0 * k / NOSE_SEGMENTS)),
                 radius + radius * math.sin(math.radians(from_degrees + 90.0 * k / NOSE_SEGMENTS)))
                for k in range(NOSE_SEGMENTS + 1)]

    # anticlockwise: down its left side, round its end, up its right
    outline = ([(-half + shift, body)] + corner(-half + left, left, 180.0)
               + corner(half - right, right, 270.0) + [(half + shift, body)])
    return ToolShape(tuple(outline), tuple(outline), max(left, right), f"blade {width:g} mm")


def drill_shape(diameter: float, tip_angle: float) -> ToolShape:
    """A drill - or a reamer, ``tip_angle`` 180 - on the axis, as the machine
    has it: its tip, the point it was touched off on, at the control point,
    its point and body going on toward Z+ for BLADE_BODY."""
    radius = diameter / 2.0
    point = radius / math.tan(math.radians(min(max(tip_angle, 1.0), 180.0) / 2.0)) if tip_angle < 180.0 else 0.0
    outline = ((0.0, 0.0), (point, -radius), (BLADE_BODY, -radius), (BLADE_BODY, radius), (point, radius))
    return ToolShape(outline, outline, 0.0, f"drill {diameter:g} mm")


def cutting_shape(mounted) -> Optional[ToolShape]:
    """What of ``mounted`` (a MountedTool) cuts, as the machine has it - an
    outline round its control point, in (z, r): a turning or boring tool's
    insert, a blade held for an OD or ID groove, a drill, a reamer - None
    for a tool whose shape is not known here: a blade held any other way,
    a threading tool, a tap, which cut a thread, not all round."""
    from teachinlathe.conversational.logic.tool_fit import NEUTRAL_ORIENTATION
    from teachinlathe.conversational.model.data_types import ProfilingType
    from teachinlathe.tooling.model.data_types import BladeTool, DrillingTool, ReamingTool, TurningTool

    od, id_ = NEUTRAL_ORIENTATION[ProfilingType.OD], NEUTRAL_ORIENTATION[ProfilingType.ID]

    tool = mounted.tool if mounted is not None else None
    if isinstance(tool, TurningTool):
        shape = insert_tool_shape(tool)
        return ToolShape(shape.outline, shape.outline, shape.nose_radius, shape.label) if shape else None
    if isinstance(tool, BladeTool) and tool.orientation in (od, id_):
        # its end, and as much of its body as it is wide: its end swept down
        # a groove is the groove; a body as long as a groove check takes it
        # (BLADE_BODY) would, turned about the axis, cut the other side too
        blade = blade_shape(tool.blade_width, tool.left_radius, tool.right_radius, mounted.z_control,
                            body=tool.blade_width)
        if tool.orientation == od:
            return blade
        # held for ID: its body toward the axis
        outline = tuple((z, -r) for z, r in reversed(blade.outline))
        return ToolShape(outline, outline, blade.nose_radius, blade.label)
    if isinstance(tool, DrillingTool):
        return drill_shape(tool.diameter, tool.tip_angle)
    if isinstance(tool, ReamingTool):
        return drill_shape(tool.diameter, 180.0)
    return None


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
