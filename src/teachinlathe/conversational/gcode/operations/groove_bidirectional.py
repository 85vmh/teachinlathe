"""BiDirectional Grooving: an OD groove roughed in passes along Z, one way
and back - an S - each a Depth of Cut deeper than the one before, to the
groove's profile with its stock to leave.

From the clearance over the groove's Z+ end it goes in to the mouth, down
the right flank a Depth of Cut, along Z toward Z- to the left flank, down it
a Depth of Cut, back toward Z+ to the right flank, and so on; the last pass
goes down the flank it is at, along the bottom and up the other flank as far
as the pass before went, so all that is left is the stock to leave. Each
plunge down a flank ends with the dwell.

Where the tool may go is worked out as for the Groove Roughing: the part
with its stock to leave grown by the tool turned round - a blade's end and
body, or an insert with its edges carried on for the holder - so the passes
end where the tool touches the stock, and the plunges go along it. A tool
that cannot go all the way down - a blade, a round insert wider than the
groove is down there - goes as deep as it fits.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

from shapely.geometry import LineString, Point as ShapelyPoint

from teachinlathe.conversational.model.data_types import ProfilingType
from teachinlathe.tooling.model.data_types import BladeTool, TurningTool

from ..toolpath import Arrows, DrawnLine, GcodeEmitter, OperationPreview, Point
from .groove_common import (
    CONTOUR_ARC_TOLERANCE,
    begin_gcode,
    blade_start_x,
    drawn_groove,
    groove_path,
    operation_error,
    part_with_stock,
    path_bounds,
    start_diameter_of,
    stock_to_leave,
)
from .profiling.operation_input import GrooveCut
from .profiling.plan_gcode import fit_arcs
from .profiling.shapes import Pt, edge_between, obstacle_of
from .profiling.tool_shape import blade_shape, insert_tool_shape

TITLE = "BiDirectional Grooving"

#: mm under the outside with its stock to leave the groove's mouth is taken
#: at: where the tool goes in.
MOUTH_DEPTH = 0.01

#: mm: a pass along Z this close over the bottom is left to the last pass,
#: which goes along the bottom.
MIN_LEVEL = 0.01

#: mm past the groove's ends a pass along Z is looked for in: outside it,
#: under the outside, is the part.
ACROSS_REACH = 1.0


@dataclass(frozen=True)
class Leg:
    """A stretch of the S, cut at the feed: ``points`` (z, r) of the point
    the tool was touched off on, from where the one before ended; ``plunge``
    when it goes down a flank to the next pass - the dwell after it."""
    points: Tuple[Pt, ...]
    plunge: bool


@dataclass(frozen=True)
class Plan:
    """What a BiDirectional Grooving cuts: in from ``safe_x`` (a diameter,
    the clearance out from the start diameter ``start_x``) over ``entry`` -
    the groove's mouth, (z, r) - then its legs, one after the other; ``part``
    the part with its stock to leave (a shapely Polygon, in (z, r)) and
    ``outline`` the tool's round the point it was touched off on, all along
    which the tool touches it."""
    start_x: float
    safe_x: float
    entry: Pt
    legs: Tuple[Leg, ...]
    part: Any = None
    outline: Tuple[Pt, ...] = ()


def _tool_envelope(tool) -> Optional[Tuple[Tuple[Pt, ...], Tuple[Pt, ...], float]]:
    """(envelope, outline, width) of ``tool`` (a MountedTool or None) round
    the point it was touched off on: a blade's end and body, an insert with
    its edges carried on for the holder - not swung, so it goes down a flank
    leaning more than its edge - what of it cuts, and how wide it is; None
    for any other tool."""
    cutting = tool.tool if tool is not None else None
    if isinstance(cutting, BladeTool):
        width = float(cutting.blade_width)
        if width <= 0:
            return None
        shape = blade_shape(width, float(cutting.left_radius), float(cutting.right_radius), tool.z_control)
        return shape.envelope, shape.outline, width
    if isinstance(cutting, TurningTool):
        shape = insert_tool_shape(cutting, clearance_degrees=0.0)
        if shape is None:
            return None
        zs = [z for z, _r in shape.outline]
        return shape.envelope, shape.outline, max(zs) - min(zs)
    return None


def _across(obstacle, r, z_min, z_max) -> Optional[Tuple[float, float]]:
    """(right, left): the Z the tool goes from and to along Z at ``r``
    inside the groove - between ``z_min`` and ``z_max`` - where it touches
    the part with its stock, or None where it does not fit there."""
    line = LineString([(z_min - ACROSS_REACH, r), (z_max + ACROSS_REACH, r)])
    free = line.difference(obstacle)
    pieces = [g for g in getattr(free, "geoms", [free]) if isinstance(g, LineString) and g.length > MIN_LEVEL]
    if not pieces:
        return None
    zs = [z for z, _r in max(pieces, key=lambda g: g.length).coords]
    return max(zs), min(zs)


def bidirectional_plan(cut: GrooveCut):
    """(Plan, "") of what ``cut`` cuts, or (None, why not)."""
    op = cut.op
    path, profile_type, error = groove_path(cut)
    if path is None:
        return None, error
    if profile_type is ProfilingType.ID:
        return None, "only OD grooves are cut bidirectionally"
    tool = _tool_envelope(cut.tool)
    if tool is None:
        return None, "the tool must be a grooving blade or a turning tool held neutral"
    envelope, outline, width = tool
    doc = abs(op.cuttingParameters.doc)
    if doc <= 0:
        return None, "the Depth of Cut must be more than 0"

    radial, axial = stock_to_leave(op)
    part, _points = part_with_stock(path, profile_type, radial, axial, reach=width)
    obstacle = obstacle_of(part, envelope)
    _x_min, _x_max, z_min, z_max = path_bounds(path)

    # the outside with its stock: the start diameter
    start_x = start_diameter_of(path, profile_type, radial)
    safe_x = blade_start_x(start_x, profile_type, abs(op.cuttingParameters.retract))
    r_top = start_x / 2.0
    mouth = _across(obstacle, r_top - MOUTH_DEPTH, z_min, z_max)
    if mouth is None:
        return None, "the tool does not fit in the groove's mouth"
    mouth_right = (mouth[0], r_top - MOUTH_DEPTH)
    mouth_left = (mouth[1], r_top - MOUTH_DEPTH)
    bottom = edge_between(obstacle, mouth_right, mouth_left)
    r_floor = min(r for _z, r in bottom)

    # the passes along Z, a Depth of Cut apart, down to over the bottom
    levels = []
    k = 1
    while r_top - k * doc > r_floor + MIN_LEVEL:
        r = r_top - k * doc
        across = _across(obstacle, r, z_min, z_max)
        if across is None:
            break
        levels.append((r, across))
        k += 1

    legs: List[Leg] = []
    current, on_right, last_reached = mouth_right, True, None
    for r, (right, left) in levels:
        reached = (right, r) if on_right else (left, r)
        other = (left, r) if on_right else (right, r)
        legs.append(Leg(tuple(edge_between(obstacle, current, reached)), True))
        legs.append(Leg((reached, other), False))
        current, on_right, last_reached = other, not on_right, reached
    # the last: down the flank it is at, along the bottom, up the other as
    # far as the pass before went
    last = edge_between(obstacle, current, last_reached) if last_reached is not None else bottom
    legs.append(Leg(tuple(last), False))
    return Plan(start_x, safe_x, mouth_right, tuple(legs), part, tuple(outline)), ""


def groove_bidirectional_toolpath(cut: GrooveCut, gcode: GcodeEmitter):
    """The G-code of a BiDirectional Grooving, as it is cut (``cut``), onto
    ``gcode``."""
    op = cut.op
    begin_gcode(gcode, op)

    plan, error = bidirectional_plan(cut)
    if plan is None:
        gcode.error(f"{TITLE} -- {error}")
        return
    dwell_time = op.cuttingParameters.dwellTime

    gcode.code(f"(---{TITLE} P{op.radial_profile_id}---)")
    gcode.rapid(x=plan.safe_x)
    gcode.rapid(z=plan.entry[0])
    gcode.start_pass()
    gcode.feed(x=2.0 * plan.entry[1])
    for n, leg in enumerate(plan.legs):
        if n > 0:
            gcode.start_pass()
        for segment in fit_arcs(list(leg.points), CONTOUR_ARC_TOLERANCE):
            segment.write(gcode)
        if leg.plunge and dwell_time > 0:
            gcode.dwell(dwell_time)
    gcode.rapid(x=plan.safe_x)


def generate_groove_bidirectional_gcode(cut: GrooveCut):
    """A BiDirectional Grooving's G-code on its own."""
    gcode = GcodeEmitter(cut.op.is_optional_block)
    groove_bidirectional_toolpath(cut, gcode)
    return gcode.lines


# ── what the editor draws ───────────────────────────────────────────────────
# The S where the tool touches the part with its stock - not the point it
# was touched off on, which for a blade touched off on one corner is its
# width off the stock on the other flank - each stretch its arrows along it,
# the way it goes.

#: mm: two of the tool's points this much apart from the part touch it
#: alike - a blade flat on the bottom - and the one ahead is taken.
SAME_TOUCH = 0.001

@dataclass(frozen=True)
class GrooveBidirectionalPreview(OperationPreview):
    """A BiDirectional Grooving as the editor draws it: its legs, each a pass
    with its arrows along it; ``start`` where the tool starts - over the
    mouth, the clearance out from the start diameter - and the start
    diameter."""
    start: Optional[Point] = None
    start_diameter: Optional[float] = None


def _touching(plan: Plan, point: Pt, toward: float) -> int:
    """Which point of the tool's outline, its touch-off point at ``point``,
    touches the part with its stock: the one nearest it - of two touching
    alike, the one farther ``toward`` along Z (+1 or -1, the way it goes)."""
    z, r = point
    gaps = [plan.part.distance(ShapelyPoint(z + dz, r + dr)) for dz, dr in plan.outline]
    nearest = min(gaps)
    return max((n for n, gap in enumerate(gaps) if gap <= nearest + SAME_TOUCH),
               key=lambda n: toward * plan.outline[n][0])


def _lowest(plan: Plan, toward: float) -> int:
    """Which point of the tool's outline is its lowest - the depth it cuts
    at going along Z - of two alike, the one farther ``toward`` along Z."""
    bottom = min(r for _z, r in plan.outline)
    return max((n for n, (_z, r) in enumerate(plan.outline) if r <= bottom + SAME_TOUCH),
               key=lambda n: toward * plan.outline[n][0])


def _round_the_tool(outline, a: int, b: int) -> List[int]:
    """The outline's points from ``a`` to ``b``, the shorter way round it."""
    count = len(outline)

    def way(step):
        out = [a]
        while out[-1] != b:
            out.append((out[-1] + step) % count)
        return out

    def length(indices):
        return sum(LineString([outline[i], outline[j]]).length for i, j in zip(indices, indices[1:]))

    return min(way(1), way(-1), key=length)


def _touching_legs(plan: Plan) -> List[List[Pt]]:
    """The legs where the tool touches the part with its stock (_touching),
    each point by the way it goes there; a pass along Z its lowest point,
    the depth it cuts at - from its back to its front, for a blade flat
    along it - between the flanks. Where what touches changes -
    off a flank onto the bottom, a blade's one corner to the other - round
    the tool from the one to the other: the shape it leaves there."""
    out, last = [], None
    for leg in plan.legs:
        points, drawn = leg.points, []
        across = not leg.plunge and all(abs(r - points[0][1]) < SAME_TOUCH for _z, r in points)
        for n, point in enumerate(points):
            a, b = (points[n - 1], point) if n > 0 else (point, points[min(1, len(points) - 1)])
            toward = 1.0 if b[0] > a[0] + SAME_TOUCH else -1.0 if b[0] < a[0] - SAME_TOUCH else 0.0
            # along Z, from the point of it behind - where the plunge left
            # it - to the one ahead: the whole width it cuts
            index = (_lowest(plan, toward if n > 0 else -toward) if across
                     else _touching(plan, point, toward))
            z, r = point
            # along Z, straight from its back to its front: what is between
            # them is cut, not left
            rounds = last is not None and not (across and n > 0)
            for i in _round_the_tool(plan.outline, last, index) if rounds else [index]:
                at = (z + plan.outline[i][0], r + plan.outline[i][1])
                if not drawn or abs(at[0] - drawn[-1][0]) + abs(at[1] - drawn[-1][1]) > SAME_TOUCH:
                    drawn.append(at)
            last = index
        out.append(drawn)
    return out


def groove_bidirectional_preview(cut: GrooveCut) -> GrooveBidirectionalPreview:
    """What a BiDirectional Grooving - as it is cut, ``cut`` - will cut, as
    the editor draws it (GrooveBidirectionalPreview)."""
    op = cut.op
    path, profile_type, error = groove_path(cut)
    if path is None:
        return GrooveBidirectionalPreview(error=error)

    drawn = drawn_groove(path, profile_type, *stock_to_leave(op))

    plan, error = bidirectional_plan(cut)
    if plan is None:
        # the G-code's own words for it
        gcode = GcodeEmitter(op.is_optional_block)
        groove_bidirectional_toolpath(cut, gcode)
        return GrooveBidirectionalPreview(error=operation_error(gcode) or error, **drawn)

    z_entry, r_entry = plan.entry
    legs = _touching_legs(plan)
    # in from the start diameter, over where the tool touches the mouth:
    # above it is the clearance, drawn as a rapid
    z_in = legs[0][0][0]
    legs[0] = [(z_in, plan.start_x / 2.0)] + legs[0]
    feeds = []
    for n, points in enumerate(legs):
        for (z0, r0), (z1, r1) in zip(points, points[1:]):
            feeds.append(DrawnLine(2.0 * r0, z0, 2.0 * r1, z1, n, False, Arrows.ALONG))
    rapids = [DrawnLine(plan.safe_x, z_in, plan.start_x, z_in)] if plan.safe_x != plan.start_x else []
    return GrooveBidirectionalPreview(
        feeds=tuple(feeds), rapids=tuple(rapids), **drawn,
        start=Point(plan.safe_x, z_entry), start_diameter=plan.start_x)
