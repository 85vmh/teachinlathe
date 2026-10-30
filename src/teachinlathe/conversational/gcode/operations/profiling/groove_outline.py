"""A groove of a radial profile as a profile: its four points, its top
corners cut by their blends, and the profile primitives it is drawn and cut
along - the one place they are worked out, for the G-code and the canvas.

The outline goes from the top of the right flank (Z+) down it, across the
bottom and up the left flank. A top corner is between its flank and the
outside, along Z, and is cut here - a chamfer as a line, a fillet as an
arc; the bottom's corners are cut by the blends of the lines they end.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from teachinlathe.conversational.model.data_types import (
    ArcTo, BlendType, Groove, LineTo, ProfileBlend, ProfilePrimitive, StartPoint,
)

from .geometry import SAME_MM

#: mm the outside is drawn on along Z from a groove's top corner, for the
#: corner's blend: past any groove.
OUTSIDE_LEG = 10000.0

#: Radians: a corner turning less than this is straight - no blend is cut.
MIN_CORNER_ANGLE = 0.001

#: The cosine a corner's angle is kept within, short of a straight line
#: either way, so its half-angle's tangent and sine are never zero.
CORNER_DOT_LIMIT = 0.9999

#: What a primitive of the outline draws (GrooveOutline.parts).
START = "start"               # the start point, at the top of the right flank's blend
RIGHT_BLEND = "p1Blend"       # the right flank's top corner, cut by its blend
RIGHT_FLANK = "rightFlank"    # the right flank, down to P2
BOTTOM = "bottom"             # the bottom, P2 to P3
LEFT_FLANK = "leftFlank"      # the left flank, up from P3
LEFT_BLEND = "p4Blend"        # the left flank's top corner, cut by its blend

_NO_BLEND = ProfileBlend(blend_type=BlendType.NONE)


@dataclass(frozen=True)
class At:
    """A point of a groove's outline: its Z, and its X on the radius."""
    z: float
    xh: float

    @property
    def x(self) -> float:
        """Its X, a diameter."""
        return self.xh * 2.0

    @staticmethod
    def on_diameter(x, z) -> "At":
        return At(z, x / 2.0)


@dataclass(frozen=True)
class CornerCut:
    """A corner as its blend cuts it: from ``start`` to ``end``, along the
    arc about ``center`` for a fillet - clockwise or not as the model's
    ArcTo has it - and straight for a chamfer; at the corner, both ends,
    with no blend."""
    start: At
    end: At
    center: Optional[At] = None
    radius: float = 0.0
    clockwise: bool = False

    @property
    def middle(self) -> At:
        """The middle of the cut: of its arc, or of its line."""
        if self.center is None:
            return At((self.start.z + self.end.z) / 2.0, (self.start.xh + self.end.xh) / 2.0)
        dz = (self.start.z - self.center.z) + (self.end.z - self.center.z)
        dx = (self.start.xh - self.center.xh) + (self.end.xh - self.center.xh)
        length = math.hypot(dz, dx)
        if length < 1e-9:
            return self.start
        return At(self.center.z + dz / length * self.radius, self.center.xh + dx / length * self.radius)


@dataclass(frozen=True)
class GrooveOutline:
    """A groove's outline: ``points`` P1-P4 - the right flank's top and
    bottom, the left flank's bottom and top - its top corners as their
    blends cut them, and the primitives it is drawn and cut along, each with
    what it draws (``parts``: START, RIGHT_BLEND, ...)."""
    points: Tuple[At, At, At, At]
    right_corner: CornerCut
    left_corner: CornerCut
    primitives: Tuple[ProfilePrimitive, ...]
    parts: Tuple[str, ...]


def groove_points(groove: Groove) -> Tuple[At, At, At, At]:
    """P1-P4 of ``groove``: where its right flank starts, that flank's
    bottom, the left flank's bottom and where the left flank starts - each
    flank's bottom along Z as far in as its angle leans it."""
    right, bottom, left = groove.right_flank, groove.bottom, groove.left_flank
    right_dz = abs((right.x_start - bottom.x_end_right) / 2.0 * math.tan(math.radians(abs(right.angle))))
    left_dz = abs((left.x_start - bottom.x_end_left) / 2.0 * math.tan(math.radians(abs(left.angle))))
    return (At.on_diameter(right.x_start, right.z_start),
            At.on_diameter(bottom.x_end_right, right.z_start - right_dz),
            At.on_diameter(bottom.x_end_left, left.z_start + left_dz),
            At.on_diameter(left.x_start, left.z_start))


def _unit_from(corner: At, point: At):
    """(z, xh, length): the way from ``corner`` to ``point``, or None when
    they are the same."""
    dz = point.z - corner.z
    dx = point.xh - corner.xh
    length = math.hypot(dz, dx)
    if length < SAME_MM:
        return None
    return dz / length, dx / length, length


def corner_cut(corner: At, leg_a_end: At, leg_b_end: At, blend: ProfileBlend) -> CornerCut:
    """The corner between the legs from ``corner`` to ``leg_a_end`` and to
    ``leg_b_end``, cut by ``blend``: from leg a to leg b."""
    ua = _unit_from(corner, leg_a_end)
    ub = _unit_from(corner, leg_b_end)
    if not ua or not ub or blend.blend_type is BlendType.NONE:
        return CornerCut(corner, corner)

    fillet = blend.blend_type is BlendType.FILLET
    amount = blend.fillet_radius if fillet else blend.chamfer_width
    if amount <= SAME_MM:
        return CornerCut(corner, corner)

    (ua_z, ua_x, ua_len), (ub_z, ub_x, ub_len) = ua, ub
    dot = max(-CORNER_DOT_LIMIT, min(CORNER_DOT_LIMIT, ua_z * ub_z + ua_x * ub_x))
    theta = math.acos(dot)
    if theta < MIN_CORNER_ANGLE:
        return CornerCut(corner, corner)

    tangent_distance = amount / math.tan(theta / 2.0) if fillet else amount
    tangent_distance = min(tangent_distance, ua_len, ub_len)
    t1 = At(corner.z + ua_z * tangent_distance, corner.xh + ua_x * tangent_distance)
    t2 = At(corner.z + ub_z * tangent_distance, corner.xh + ub_x * tangent_distance)
    if not fillet:
        return CornerCut(t1, t2)

    bis_z = ua_z + ub_z
    bis_x = ua_x + ub_x
    bis_len = math.hypot(bis_z, bis_x)
    if bis_len < SAME_MM:
        return CornerCut(t1, t2)

    center_distance = amount / math.sin(theta / 2.0)
    center = At(corner.z + bis_z / bis_len * center_distance, corner.xh + bis_x / bis_len * center_distance)
    start_angle = math.atan2(t1.xh - center.xh, t1.z - center.z)
    end_angle = math.atan2(t2.xh - center.xh, t2.z - center.z)
    delta = end_angle - start_angle
    while delta > math.pi:
        delta -= math.pi * 2.0
    while delta < -math.pi:
        delta += math.pi * 2.0
    # its angle growing, about the centre in (Z, X), is clockwise to the model
    return CornerCut(t1, t2, center, amount, clockwise=delta > 0)


def _end_of(primitive: ProfilePrimitive) -> At:
    if isinstance(primitive, StartPoint):
        return At.on_diameter(primitive.x_start, primitive.z_start)
    return At.on_diameter(primitive.x_end, primitive.z_end)


def _same(a: At, b: At) -> bool:
    return abs(a.z - b.z) < SAME_MM and abs(a.x - b.x) < SAME_MM


class _Outline:
    """The outline as it is put together: its primitives, and what each draws."""

    def __init__(self, start: At):
        self.primitives: List[ProfilePrimitive] = [
            StartPoint(primitive_id=1, primitive_type="startPoint", x_start=start.x, z_start=start.z,
                       blend=_NO_BLEND)]
        self.parts: List[str] = [START]

    def line(self, part: str, point: At, blend: ProfileBlend = _NO_BLEND):
        """A line on to ``point`` - none when it is there already and has
        no blend to make."""
        if _same(point, _end_of(self.primitives[-1])) and blend.blend_type is BlendType.NONE:
            return
        self.primitives.append(LineTo(primitive_id=len(self.primitives) + 1, primitive_type="lineTo",
                                      x_end=point.x, z_end=point.z, blend=blend, input="xz"))
        self.parts.append(part)

    def corner(self, part: str, cut: CornerCut):
        """On along ``cut`` to its end: its arc, or a line."""
        if cut.center is None:
            self.line(part, cut.end)
            return
        self.primitives.append(ArcTo(
            primitive_id=len(self.primitives) + 1, primitive_type="arcTo",
            direction="cw" if cut.clockwise else "ccw", x_end=cut.end.x, z_end=cut.end.z,
            x_center=cut.center.x, z_center=cut.center.z, arc_radius=cut.radius, blend=_NO_BLEND))
        self.parts.append(part)


def groove_outline(groove: Groove) -> GrooveOutline:
    """``groove``'s outline (see the module)."""
    points = groove_points(groove)
    right_top, right_bottom, left_bottom, left_top = points
    right_corner = corner_cut(right_top, At(right_top.z + OUTSIDE_LEG, right_top.xh), right_bottom,
                              groove.right_flank.start_blend)
    left_corner = corner_cut(left_top, left_bottom, At(left_top.z - OUTSIDE_LEG, left_top.xh),
                             groove.left_flank.start_blend)

    outline = _Outline(right_corner.start)
    outline.corner(RIGHT_BLEND, right_corner)
    outline.line(RIGHT_FLANK, right_bottom, groove.bottom.blend_right)
    outline.line(BOTTOM, left_bottom, groove.bottom.blend_left)
    outline.line(LEFT_FLANK, left_corner.start)
    outline.corner(LEFT_BLEND, left_corner)
    return GrooveOutline(points, right_corner, left_corner, tuple(outline.primitives), tuple(outline.parts))
