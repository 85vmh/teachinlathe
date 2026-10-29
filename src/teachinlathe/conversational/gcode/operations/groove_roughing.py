import dataclasses
import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from shapely.geometry import LineString, Polygon, box
from shapely.ops import linemerge

from teachinlathe.conversational.model.data_types import (
    BlendType, GrooveRoughingStrategy, LineTo, ProfileBlend, ProfilingType,
)
from teachinlathe.conversational.model.data_types import StartPoint as ProfileStart

from ..helpers.spindle import build_feed_gcode, build_spindle_gcode
from ..helpers.utils import get_float
from .profiling.geometry import (
    ROUNDING,
    SAME_MM,
    StartPoint,
    ToolpathArc,
    ToolpathLine,
    arc_x_at_z,
    build_path,
)
from .profiling.plan_drawing import flatten_path
from .profiling.plan_gcode import fit_arcs
from .profiling.shapes import FAR, drop_onto, edge_between, minkowski, obstacle_of, path_points
from .profiling.tool_shape import blade_shape
from ..toolpath import Arrows, DrawnLine, GcodeEmitter, OperationPreview
from ..toolpath import Point as CanvasPoint
from .profiling.operation_input import GrooveCut

# ── Geometry ─────────────────────────────────────────────────────────────────

#: Chords a fillet on a groove's corner is drawn with in its profile.
FILLET_CHORDS = 10

#: mm the outside is drawn on along Z from a groove's top corner, for the
#: corner's blend: past any groove.
OUTSIDE_LEG = 10000.0

#: Radians: a corner turning less than this is straight - no blend is cut.
MIN_CORNER_ANGLE = 0.001

#: The cosine a corner's angle is kept within, short of a straight line
#: either way, so its half-angle's tangent and sine are never zero.
CORNER_DOT_LIMIT = 0.9999

#: mm the bar is carried on past the groove's ends, either side, for the
#: part's outline - more for more stock, so it still reaches past it.
BAR_PAST_GROOVE = 10.0

#: mm above the pulley's outside, with its stock, the stock-to-leave line is
#: taken up to: past the top of it, so the line keeps its ends.
OVER_THE_OUTSIDE = 1.0

#: mm the contour's chords may be off the arc they are written as
#: (plan_gcode.fit_arcs): under the bump a blade's corner makes rolling over
#: a corner of the profile's chords, which a looser arc would cut into.
CONTOUR_ARC_TOLERANCE = 0.0005

#: mm past the blade's width beyond the groove's ends the contour's edge is
#: taken from (_contour_edge): on the outside, where the blade sits on it.
RIM_REACH = 1.0


class Corner(Enum):
    """One of the blade's corners - its right, on the Z+ side, or its left -
    as the G-code's comment over a contour cut with it says (corner_comment)."""
    RIGHT = "right"
    LEFT = "left"

    @property
    def along_z(self) -> float:
        """Which way along Z it is from the blade's middle: +1 or -1."""
        return 1.0 if self is Corner.RIGHT else -1.0


def _on_diameter(radial):
    """A distance along X, such as the clearance - given on the radius, as
    the canvas dimensions it - on the diameter the G-code's X is."""
    return 2.0 * abs(radial)


def _outward(profile_type):
    """Which way out of the groove is along X: +1 for an OD one, -1 for ID."""
    return -1.0 if profile_type is ProfilingType.ID else 1.0


def _top_x(path, profile_type):
    """The pulley's outside, the groove's mouth: the largest diameter of its
    profile ``path``, the smallest for ID."""
    x_min, x_max, _z_min, _z_max = _profile_bounds_from_path(path)
    return x_min if profile_type is ProfilingType.ID else x_max


def _start_x(path, profile_type, stock_radial):
    """The start diameter: the pulley's outside with ``stock_radial`` - the
    radial stock to leave, or the one left - on it."""
    return _top_x(path, profile_type) + _outward(profile_type) * _on_diameter(stock_radial)


def _blade_start_x(start_x, profile_type, clearance):
    """Where the blade starts, and backs off to: ``clearance`` out from the
    start diameter ``start_x``."""
    return start_x + _outward(profile_type) * _on_diameter(clearance)


def _groove_path(profile):
    """The profile of the first groove of the radial ``profile``, as the
    G-code goes along it - from its Z+ end to its Z- one - or None."""
    groove = _first_groove(profile)
    if not groove:
        return None
    path = build_path(_radial_profile_primitives(groove), _profiling_type(profile.get("profile_type")))
    if not path or not isinstance(path[0], StartPoint):
        return None
    return path


def _profiling_type(value) -> ProfilingType:
    return ProfilingType.ID if str(value or "od").lower() == "id" else ProfilingType.OD


def _fmt(value):
    return f"{float(value):.3f}"


def _first_groove(profile):
    for primitive in (profile.get("profile_primitives", []) or []):
        if isinstance(primitive, dict) and primitive.get("type") == "groove":
            return primitive
    return None


#: A radial profile's blend types - the editor's, and "radius" as it once
#: called a fillet - as the model's.
_BLEND_TYPES = {"chamfer": BlendType.CHAMFER, "fillet": BlendType.FILLET, "radius": BlendType.FILLET}


def _blend(blend) -> ProfileBlend:
    """A blend of the radial profile (its dict) as the model's ProfileBlend."""
    blend = blend or {}
    return ProfileBlend(
        blend_type=_BLEND_TYPES.get(str(blend.get("type", "none") or "none").lower(), BlendType.NONE),
        chamfer_width=get_float(blend, "chamfer_width", 0.0),
        fillet_radius=get_float(blend, "fillet_radius", 0.0),
    )


_NO_BLEND = ProfileBlend(blend_type=BlendType.NONE)


@dataclass(frozen=True)
class _At:
    """A point of a groove's outline: its Z, and its X on the radius."""
    z: float
    xh: float

    @property
    def x(self) -> float:
        return self.xh * 2.0

    @staticmethod
    def on_diameter(x, z) -> "_At":
        return _At(z, x / 2.0)


@dataclass(frozen=True)
class _Corner:
    """A top corner of a groove as its blend cuts it: from ``start`` to
    ``end``, through ``arc`` for a fillet (its chords' ends, ``end`` last)."""
    start: _At
    end: _At
    arc: Tuple[_At, ...] = ()


def _unit_from(corner: _At, point: _At):
    """(z, xh, length): the way from ``corner`` to ``point``, or None when
    they are the same."""
    dz = point.z - corner.z
    dx = point.xh - corner.xh
    length = math.hypot(dz, dx)
    if length < SAME_MM:
        return None
    return dz / length, dx / length, length


def _corner_blend(corner: _At, leg_a_end: _At, leg_b_end: _At, blend: ProfileBlend) -> _Corner:
    """The corner between the legs from ``corner`` to ``leg_a_end`` and to
    ``leg_b_end``, cut by ``blend``."""
    ua = _unit_from(corner, leg_a_end)
    ub = _unit_from(corner, leg_b_end)
    if not ua or not ub or blend.blend_type is BlendType.NONE:
        return _Corner(corner, corner)

    fillet = blend.blend_type is BlendType.FILLET
    amount = blend.fillet_radius if fillet else blend.chamfer_width
    if amount <= SAME_MM:
        return _Corner(corner, corner)

    (ua_z, ua_x, ua_len), (ub_z, ub_x, ub_len) = ua, ub
    dot = max(-CORNER_DOT_LIMIT, min(CORNER_DOT_LIMIT, ua_z * ub_z + ua_x * ub_x))
    theta = math.acos(dot)
    if theta < MIN_CORNER_ANGLE:
        return _Corner(corner, corner)

    tangent_distance = amount / math.tan(theta / 2.0) if fillet else amount
    tangent_distance = min(tangent_distance, ua_len, ub_len)
    t1 = _At(corner.z + ua_z * tangent_distance, corner.xh + ua_x * tangent_distance)
    t2 = _At(corner.z + ub_z * tangent_distance, corner.xh + ub_x * tangent_distance)

    if not fillet:
        return _Corner(t1, t2)

    bis_z = ua_z + ub_z
    bis_x = ua_x + ub_x
    bis_len = math.hypot(bis_z, bis_x)
    if bis_len < SAME_MM:
        return _Corner(t1, t2)

    center_distance = amount / math.sin(theta / 2.0)
    center = _At(corner.z + bis_z / bis_len * center_distance, corner.xh + bis_x / bis_len * center_distance)
    start_angle = math.atan2(t1.xh - center.xh, t1.z - center.z)
    end_angle = math.atan2(t2.xh - center.xh, t2.z - center.z)
    delta = end_angle - start_angle
    while delta > math.pi:
        delta -= math.pi * 2.0
    while delta < -math.pi:
        delta += math.pi * 2.0

    arc = []
    for index in range(1, FILLET_CHORDS + 1):
        angle = start_angle + delta * index / float(FILLET_CHORDS)
        arc.append(_At(center.z + math.cos(angle) * amount, center.xh + math.sin(angle) * amount))
    return _Corner(t1, t2, tuple(arc))


def _same_point(a: _At, b_x, b_z) -> bool:
    return abs(a.z - b_z) < SAME_MM and abs(a.x - b_x) < SAME_MM


def _append_line(out, point: _At, blend: ProfileBlend = _NO_BLEND):
    """A line on to ``point`` after ``out``'s last primitive - none when it
    is there already and has no blend to make."""
    last = out[-1]
    last_x, last_z = (last.x_start, last.z_start) if isinstance(last, ProfileStart) else (last.x_end, last.z_end)
    if _same_point(point, last_x, last_z) and blend.blend_type is BlendType.NONE:
        return
    out.append(LineTo(primitive_id=len(out) + 1, primitive_type="lineTo",
                      x_end=point.x, z_end=point.z, blend=blend, input="xz"))


def _groove_corner_points(groove):
    """(right top, right bottom, left bottom, left top) of the groove."""
    right = groove.get("right_flank", {}) or {}
    bottom = groove.get("bottom", {}) or {}
    left = groove.get("left_flank", {}) or {}

    rx0 = get_float(right, "x_start", 0.0)
    rz0 = get_float(right, "z_start", 0.0)
    lx0 = get_float(left, "x_start", 0.0)
    lz0 = get_float(left, "z_start", 0.0)
    rxe = get_float(bottom, "x_end_right", 0.0)
    lxe = get_float(bottom, "x_end_left", 0.0)
    ra = abs(get_float(right, "angle", 0.0)) * math.pi / 180.0
    la = abs(get_float(left, "angle", 0.0)) * math.pi / 180.0
    rdz = abs((rx0 - rxe) / 2.0 * math.tan(ra))
    ldz = abs((lx0 - lxe) / 2.0 * math.tan(la))

    return (_At.on_diameter(rx0, rz0), _At.on_diameter(rxe, rz0 - rdz),
            _At.on_diameter(lxe, lz0 + ldz), _At.on_diameter(lx0, lz0))


def _radial_profile_primitives(groove):
    """The groove's outline as profile primitives - the model's StartPoint
    and LineTos - from the right flank's top to the left's: its top corners
    cut by their blends here, its bottom corners by the lines' blends."""
    right_top, right_bottom, left_bottom, left_top = _groove_corner_points(groove)
    right = groove.get("right_flank", {}) or {}
    left = groove.get("left_flank", {}) or {}
    bottom = groove.get("bottom", {}) or {}

    # each top corner is between its flank and the outside, along Z
    right_corner = _corner_blend(right_top, _At(right_top.z + OUTSIDE_LEG, right_top.xh), right_bottom,
                                 _blend(right.get("start_blend")))
    left_corner = _corner_blend(left_top, left_bottom, _At(left_top.z - OUTSIDE_LEG, left_top.xh),
                                _blend(left.get("start_blend")))

    out = [ProfileStart(primitive_id=1, primitive_type="startPoint",
                        x_start=right_corner.start.x, z_start=right_corner.start.z, blend=_NO_BLEND)]
    for point in right_corner.arc or (right_corner.end,):
        _append_line(out, point)
    _append_line(out, right_bottom, _blend(bottom.get("blend_right")))
    _append_line(out, left_bottom, _blend(bottom.get("blend_left")))
    _append_line(out, left_corner.start)
    for point in left_corner.arc or (left_corner.end,):
        _append_line(out, point)
    return out


def _profile_bounds_from_path(path):
    xs = []
    zs = []
    for element in path:
        if isinstance(element, StartPoint):
            xs.append(element.x)
            zs.append(element.z)
        else:
            xs.append(element.end_x)
            zs.append(element.end_z)
    return min(xs), max(xs), min(zs), max(zs)


_CONTROL_NAMES = {-1: "left corner", 0: "middle", 1: "right corner"}


def _blade_control(tool):
    """Which point of the blade - ``tool``, a MountedTool or None - it was
    touched off on, so the G-code is written for: -1 its left corner, 0 the
    middle of its end, 1 its right corner."""
    return tool.z_control if tool is not None else 0


def _path_end_point(path):
    if not path:
        return None
    last = path[-1]
    if isinstance(last, StartPoint):
        return last.x, last.z
    return last.end_x, last.end_z


def _reverse_path(path):
    if not path:
        return []

    end_point = _path_end_point(path)
    if end_point is None:
        return []

    reversed_path = [StartPoint(end_point[0], end_point[1])]
    current_x = path[0].x
    current_z = path[0].z
    segments = []
    for element in path[1:]:
        segments.append((current_x, current_z, element))
        current_x = element.end_x
        current_z = element.end_z

    for start_x, start_z, element in reversed(segments):
        if isinstance(element, ToolpathLine):
            reversed_path.append(ToolpathLine(start_x, start_z))
        elif isinstance(element, ToolpathArc):
            reversed_path.append(ToolpathArc(
                start_x,
                start_z,
                element.center_x,
                element.center_z,
                not element.anticlockwise,
            ))
    return reversed_path


def _line_point_at_z(start_x, start_z, end_x, end_z, target_z):
    if abs(end_z - start_z) <= ROUNDING:
        return end_x, target_z
    ratio = (target_z - start_z) / (end_z - start_z)
    return start_x + ratio * (end_x - start_x), target_z


def _arc_point_at_z(start_x, start_z, element, target_z):
    xs = arc_x_at_z(
        start_x,
        start_z,
        element.end_x,
        element.end_z,
        element.center_x,
        element.center_z,
        element.anticlockwise,
        target_z,
    )
    if not xs:
        return None
    x = min(xs, key=lambda candidate: abs(candidate - start_x))
    return x, target_z


def _split_path_at_z(path, target_z):
    if not path or not isinstance(path[0], StartPoint):
        return [], []

    first = [StartPoint(path[0].x, path[0].z)]
    current_x = path[0].x
    current_z = path[0].z

    for index, element in enumerate(path[1:], start=1):
        end_x = element.end_x
        end_z = element.end_z
        crosses = min(current_z, end_z) - ROUNDING <= target_z <= max(current_z, end_z) + ROUNDING

        if crosses:
            if isinstance(element, ToolpathLine):
                split_x, split_z = _line_point_at_z(current_x, current_z, end_x, end_z, target_z)
                first.append(ToolpathLine(split_x, split_z))
            elif isinstance(element, ToolpathArc):
                hit = _arc_point_at_z(current_x, current_z, element, target_z)
                if not hit:
                    first.append(element)
                    current_x = end_x
                    current_z = end_z
                    continue
                split_x, split_z = hit
                first.append(ToolpathArc(
                    split_x,
                    split_z,
                    element.center_x,
                    element.center_z,
                    element.anticlockwise,
                ))
            else:
                first.append(element)
                split_x, split_z = end_x, end_z

            second = [StartPoint(split_x, split_z)]
            if isinstance(element, ToolpathLine):
                if abs(split_x - end_x) > SAME_MM or abs(split_z - end_z) > SAME_MM:
                    second.append(ToolpathLine(end_x, end_z))
            elif isinstance(element, ToolpathArc):
                if abs(split_x - end_x) > SAME_MM or abs(split_z - end_z) > SAME_MM:
                    second.append(ToolpathArc(
                        end_x,
                        end_z,
                        element.center_x,
                        element.center_z,
                        element.anticlockwise,
                    ))
            second.extend(path[index + 1:])
            return first, second

        first.append(element)
        current_x = end_x
        current_z = end_z

    return first, []


def _tool_is_blade(tool):
    """Whether ``tool`` (a MountedTool or None) is a blade."""
    return tool is not None and tool.blade is not None


def _blade_width(tool):
    """The width of blade ``tool`` (a MountedTool or None); 0 for no blade."""
    return float(tool.blade.blade_width) if _tool_is_blade(tool) else 0.0


def _blade_radii(tool):
    """(left, right): the corner radii of blade ``tool`` (a MountedTool)."""
    return float(tool.blade.left_radius), float(tool.blade.right_radius)


def _append_peck(gcode, z_pos, safe_x, final_x, peck_depth, clearance, dwell_time):
    if peck_depth <= 0:
        peck_depth = abs(safe_x - final_x)
    direction = -1 if final_x < safe_x else 1
    outside = -direction
    current_x = safe_x

    gcode.rapid(x=safe_x)
    gcode.rapid(z=z_pos)
    while True:
        remaining = abs(final_x - current_x)
        if remaining <= SAME_MM:
            break
        next_x = current_x + direction * min(abs(peck_depth), remaining)
        # The operation sets G95 F once before its first cut. Keep the feed
        # modal across pecks instead of repeating F on every G1.
        gcode.feed(x=next_x)
        if dwell_time > 0:
            gcode.dwell(dwell_time)
        current_x = next_x
        if abs(final_x - current_x) <= SAME_MM:
            break
        retract_x = current_x + outside * _on_diameter(clearance)
        gcode.rapid(x=retract_x)
        gcode.rapid(x=current_x)
    gcode.rapid(x=safe_x)


def _next_depth(current_x, final_x, peck_depth):
    if peck_depth <= 0:
        return final_x
    direction = -1 if final_x < current_x else 1
    next_x = current_x + direction * abs(peck_depth)
    if direction < 0:
        return max(next_x, final_x)
    return min(next_x, final_x)


def _next_center_depth(current_x, final_x, peck_depth):
    return _next_depth(current_x, final_x, abs(peck_depth) * 2.0)


def _is_at_depth(current_x, final_x):
    if final_x < current_x:
        return current_x <= final_x + SAME_MM
    return current_x >= final_x - SAME_MM


def _append_incremental_cut(
    gcode,
    z_pos,
    current_x,
    target_x,
    clearance,
    dwell_time,
    retract_reference_x=None,
):
    if abs(target_x - current_x) <= SAME_MM:
        return
    # out of the cut is back the way it came in, from wherever it goes to
    outward = 1.0 if current_x > target_x else -1.0
    approach_x = current_x + outward * _on_diameter(clearance)
    gcode.rapid(x=approach_x)
    gcode.rapid(z=z_pos)
    # G95 F was set once at the start of this operation.
    gcode.feed(x=target_x)
    if dwell_time > 0:
        gcode.dwell(dwell_time)
    # backed off to clear the other plunge too, so the move over to it is
    # in the air: out past the shallower of the two - never deeper than
    # this cut, whatever depth the other is at
    if retract_reference_x is None:
        retract_reference_x = target_x
    shallower = max(retract_reference_x, target_x) if outward > 0 else min(retract_reference_x, target_x)
    retract_x = shallower + outward * _on_diameter(clearance)
    gcode.rapid(x=retract_x)


def _append_center_pair_roughing(
    gcode,
    first_z,
    first_final_x,
    second_z,
    second_final_x,
    top_x,
    peck_depth,
    clearance,
    dwell_time,
):
    first_depth = top_x
    second_depth = top_x

    first_target = _next_depth(first_depth, first_final_x, peck_depth)
    _append_incremental_cut(
        gcode,
        first_z,
        first_depth,
        first_target,
        clearance,
        dwell_time,
        retract_reference_x=second_depth,
    )
    first_depth = first_target

    while not (_is_at_depth(first_depth, first_final_x) and _is_at_depth(second_depth, second_final_x)):
        if not _is_at_depth(second_depth, second_final_x):
            next_depth = _next_center_depth(second_depth, second_final_x, peck_depth)
            _append_incremental_cut(
                gcode,
                second_z,
                second_depth,
                next_depth,
                clearance,
                dwell_time,
                retract_reference_x=first_depth,
            )
            second_depth = next_depth

        if not _is_at_depth(first_depth, first_final_x):
            next_depth = _next_center_depth(first_depth, first_final_x, peck_depth)
            _append_incremental_cut(
                gcode,
                first_z,
                first_depth,
                next_depth,
                clearance,
                dwell_time,
                retract_reference_x=second_depth,
            )
            first_depth = next_depth


def _append_unique_position(positions, value, z_min, z_max):
    if value < z_min - SAME_MM or value > z_max + SAME_MM:
        return
    if not any(abs(existing - value) < SAME_MM for existing in positions):
        positions.append(value)


def _center_positions(center, left_limit, right_limit, initial_offset, afterwards_offset):
    positions = []
    if initial_offset > 0:
        right_seed = center + initial_offset / 2.0
        left_seed = center - initial_offset / 2.0
        _append_unique_position(positions, right_seed, left_limit, right_limit)
        _append_unique_position(positions, left_seed, left_limit, right_limit)
    else:
        right_seed = center
        left_seed = center
        _append_unique_position(positions, center, left_limit, right_limit)

    if afterwards_offset <= 0:
        afterwards_offset = initial_offset if initial_offset > 0 else 1.0

    z = right_seed + afterwards_offset
    while z <= right_limit + SAME_MM:
        _append_unique_position(positions, z, left_limit, right_limit)
        z += afterwards_offset

    z = left_seed - afterwards_offset
    while z >= left_limit - SAME_MM:
        _append_unique_position(positions, z, left_limit, right_limit)
        z -= afterwards_offset

    return positions


#: The comment put over a contour cut with one of the blade's corners, which
#: the backplot reads to draw it along that corner (backplot.blade_middle).
CORNER_COMMENT = "( blade {} corner on the contour )"


def corner_comment(corner: Corner):
    """The comment over a contour cut with the blade's ``corner``."""
    return CORNER_COMMENT.format(corner.value)


def _emit_contour_section(gcode, safe_x, section, profile_type, corner=None):
    """``section`` - (z, r) of the touch-off point, in the part's frame - at
    the feed: in from ``safe_x`` over its start, along it - its runs of
    chords on one circle as arcs (plan_gcode.fit_arcs) - and back out; the
    blade's ``corner`` cutting it said over it."""
    if len(section) < 2:
        return
    if corner:
        gcode.code(corner_comment(corner))
    sign = _outward(profile_type)
    points = [(z, sign * r) for z, r in section]
    gcode.rapid(x=safe_x)
    gcode.rapid(z=points[0][0])
    gcode.feed(2.0 * points[0][1], points[0][0])
    for segment in fit_arcs(points, CONTOUR_ARC_TOLERANCE):
        segment.write(gcode)
    gcode.rapid(x=safe_x)


def _safe_x_for_contour(sections, safe_x, clearance, profile_type):
    """Where the blade goes in from and back out to for ``sections``: the
    start's clearance out, or the clearance out from the sections' highest."""
    sign = _outward(profile_type)
    xs = [2.0 * sign * r for section in sections for _z, r in section]
    if not xs:
        return safe_x
    if profile_type is ProfilingType.ID:
        return min(safe_x, min(xs) - _on_diameter(clearance))
    return max(safe_x, max(xs) + _on_diameter(clearance))


def _part_with_stock(path, profile_type, radial, axial, reach=0.0):
    """The part under the groove's profile ``path``, the bar carried on past
    it either side - ``reach`` farther still - grown by the stock to leave -
    ``radial`` off the bottom, ``axial`` off the flanks - as a shapely
    Polygon in (z, r), r turned over for ID so the part is under it either
    way; with ``points``, the profile's (z, r) from its right end to its
    left, in the same frame."""
    sign = _outward(profile_type)
    points = [(z, sign * r) for z, r in path_points(path)]
    if points[0][0] < points[-1][0]:
        points.reverse()                        # from the right end to the left
    (z_right, r_right), (z_left, r_left) = points[0], points[-1]
    far = BAR_PAST_GROOVE + 2 * (radial + axial) + reach
    floor = min(r for _z, r in points) - far
    part = Polygon([(z_right + far, r_right)] + points + [(z_left - far, r_left), (z_left - far, floor),
                                                          (z_right + far, floor)]).buffer(0)
    if radial > 0 or axial > 0:
        part = minkowski(part, [(-axial, -radial), (axial, -radial), (axial, radial), (-axial, radial)])
    return part, points


def _stock_allowance(path, profile_type, radial, axial):
    """The groove's profile ``path`` offset by the stock to leave - ``radial``
    off its bottom, ``axial`` off its flanks, as the stock it is left with is
    the part grown by both - as [(z, x)] (X a diameter) from its right end
    to its left, between the profile's ends, out to the pulley's outside
    with its stock; [] with none to leave."""
    if radial <= 0 and axial <= 0:
        return []
    sign = _outward(profile_type)
    allowance, points = _part_with_stock(path, profile_type, radial, axial)
    (z_right, r_right), (z_left, r_left) = points[0], points[-1]
    floor = min(r for _z, r in points) - BAR_PAST_GROOVE - 2 * (radial + axial)
    # its edge between the profile's ends, up to the outside with its stock
    outside = max(r_right, r_left) + radial + OVER_THE_OUTSIDE
    inside = allowance.exterior.intersection(box(z_left, floor, z_right, outside))
    pieces = [g for g in getattr(inside, "geoms", [inside]) if isinstance(g, LineString) and not g.is_empty]
    if not pieces:
        return []
    line = linemerge(pieces) if len(pieces) > 1 else pieces[0]
    if not isinstance(line, LineString):
        line = max(line.geoms, key=lambda g: g.length)
    coords = list(line.coords)
    if coords[0][0] < coords[-1][0]:
        coords.reverse()
    return [(z, 2 * sign * r) for z, r in coords]


def _blade_obstacle(tool, path, profile_type, radial, axial):
    """Where the point blade ``tool`` (a MountedTool) was touched off on may
    not go without the blade going into the part or the stock it is to be
    left with (``radial``, ``axial``; _part_with_stock) - the bar carried on
    past the groove as far as the blade sits on its outside either side -
    the part grown by the blade (tool_shape.blade_shape) turned round, in
    the part's frame."""
    width = _blade_width(tool)
    part, _points = _part_with_stock(path, profile_type, radial, axial, reach=width)
    left_radius, right_radius = _blade_radii(tool)
    return obstacle_of(part, blade_shape(width, left_radius, right_radius, _blade_control(tool)).envelope)


def _plunge_x(inside, z, start_x, profile_type):
    """How deep the touch-off point plunged at ``z`` from the start diameter
    ``start_x`` goes before the blade meets the part or its stock -
    ``inside``, the blade's obstacle (_blade_obstacle) shrunk by SAME_MM, so
    a blade's side flush with a flank goes on down it: the X it stops at."""
    sign = _outward(profile_type)
    r_start = sign * start_x / 2.0
    return 2.0 * sign * drop_onto(inside, z, r_start + OVER_THE_OUTSIDE, r_start - FAR, SAME_MM)


def _contour_edge(obstacle, path, width):
    """The touch-off point's way across the groove with the blade on the part
    (``obstacle``, _blade_obstacle): its top, from over the outside past
    the groove's Z+ end - the blade sitting on it - to past its Z- end, as
    (z, r) in the part's frame."""
    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    top = obstacle.bounds[3] + OVER_THE_OUTSIDE
    ends = [(z, drop_onto(obstacle, z, top, top - FAR, 0.0))
            for z in (z_max + width + RIM_REACH, z_min - width - RIM_REACH)]
    return edge_between(obstacle, *ends)


def _to_middle(edge, stop_z):
    """``edge`` (_contour_edge, or it the other way round) from where it
    leaves the outside - the groove's rim - as far as ``stop_z`` along Z, or
    to where it goes back up, whichever comes first: the far flank, met by
    a blade wider than what is left of the groove."""
    if len(edge) < 2:
        return []
    toward = 1.0 if stop_z > edge[0][0] else -1.0
    outside = edge[0][1]
    start = 0
    while start + 1 < len(edge) and edge[start + 1][1] >= outside - SAME_MM:
        start += 1
    section = [edge[start]]
    lowest = edge[start][1]
    for z, r in edge[start + 1:]:
        last_z, last_r = section[-1]
        if (z - stop_z) * toward >= 0.0:
            if abs(z - last_z) > ROUNDING and (stop_z - last_z) * toward > SAME_MM:
                t = (stop_z - last_z) / (z - last_z)
                section.append((stop_z, last_r + t * (r - last_r)))
            break
        if r > lowest + SAME_MM:
            break
        section.append((z, r))
        lowest = min(lowest, r)
    return section


def _cut_path(path, profile_type, radial, axial):
    """What the blade cuts to: ``path``, the groove's profile, offset by the
    stock to leave (_stock_allowance) - as lines - or itself with none."""
    allowance = _stock_allowance(path, profile_type, radial, axial)
    if len(allowance) < 2:
        return path
    z, x = allowance[0]
    return [StartPoint(x, z)] + [ToolpathLine(x, z) for z, x in allowance[1:]]


def _append_contour(gcode, safe_x, obstacle, path, center_z, clearance, profile_type,
                    left_radius, right_radius, half_width, control):
    """The finish contour: the blade on the part with its stock (``obstacle``)
    from the Z+ rim, its right corner cutting, to the groove's middle - its
    middle past it by the rest of its end - then from the Z- rim, its left
    corner cutting, the same."""
    edge = _contour_edge(obstacle, path, 2.0 * half_width)
    z_control = control * half_width
    z_plus = _to_middle(edge, center_z - max(half_width - right_radius, 0.0) + z_control)
    z_minus = _to_middle(edge[::-1], center_z + max(half_width - left_radius, 0.0) + z_control)
    contour_safe_x = _safe_x_for_contour([z_plus, z_minus], safe_x, clearance, profile_type)

    gcode.begin_contour()
    gcode.code("(----------Groove Roughing Finish Contour Z+ to Center----------)")
    _emit_contour_section(gcode, contour_safe_x, z_plus, profile_type, Corner.RIGHT)

    gcode.code("(----------Groove Roughing Finish Contour Z- to Center----------)")
    _emit_contour_section(gcode, contour_safe_x, z_minus, profile_type, Corner.LEFT)


def groove_roughing_toolpath(cut: GrooveCut, gcode: GcodeEmitter):
    """The G-code of a Groove Roughing, as it is cut (``cut``), onto ``gcode``."""
    op = cut.op
    cutting = op.cuttingParameters
    roughing = op.roughingParameters
    # the radial profile's own primitives are dicts: the groove geometry reads them so
    profile = cut.radial_profile.to_dict() if cut.radial_profile is not None else {}
    tool = cut.tool

    gcode.codes(build_spindle_gcode(op.speedsAndFeeds, ""))
    feed_rate = op.speedsAndFeeds.feed
    gcode.code(build_feed_gcode(feed_rate))
    peck_depth = abs(cutting.peckDepth)
    clearance = abs(cutting.retract)
    dwell_time = cutting.dwellTime
    initial_offset = abs(roughing.initial_offset)
    afterwards_offset = abs(roughing.afterwards_offset)
    strategy = roughing.strategy
    stock_radial = op.stockToLeave.stockToLeaveX if op.stockToLeaveEnabled else 0.0
    stock_axial = op.stockToLeave.stockToLeaveZ if op.stockToLeaveEnabled else 0.0

    gcode.blank()

    if strategy is not GrooveRoughingStrategy.START_CENTER:
        gcode.error("Groove Roughing -- only start_center strategy is implemented")
        return
    if not profile:
        gcode.error("Groove Roughing -- no Define Radial Profile found above this operation")
        return
    if not _tool_is_blade(tool):
        gcode.error("Groove Roughing -- current tool must be a parting or grooving blade")
        return

    width = _blade_width(tool)
    if width <= 0:
        gcode.error("Groove Roughing -- blade width is not defined in tool extras")
        return

    groove = _first_groove(profile)
    if not groove:
        gcode.error("Groove Roughing -- radial profile has no groove primitive")
        return

    path = _groove_path(profile)
    if path is None:
        gcode.error("Groove Roughing -- radial profile did not produce a valid toolpath")
        return

    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    center_z = (z_min + z_max) / 2.0
    half_width = width / 2.0

    profile_type = _profiling_type(profile.get("profile_type"))
    # the pulley's outside; the start diameter, the plunges' start: that with
    # its radial stock to leave on; where the blade starts and backs off to:
    # the clearance out from the start diameter
    top_x = _top_x(path, profile_type)
    start_x = _start_x(path, profile_type, stock_radial)
    safe_x = _blade_start_x(start_x, profile_type, clearance)
    # where the blade may not go: into the part, or the stock it is to be
    # left with - radial off the bottom, axial off the flanks - nor, past the
    # groove's ends, below the outside with its stock
    obstacle = _blade_obstacle(tool, path, profile_type, stock_radial, stock_axial)
    inside = obstacle.buffer(-SAME_MM)

    def _plunges_into(target_x):
        """Whether a plunge to ``target_x`` goes into the groove at all."""
        if target_x is None:
            return False
        return target_x > top_x + SAME_MM if profile_type is ProfilingType.ID else target_x < top_x - SAME_MM

    right_limit = z_max - stock_axial - half_width
    left_limit = z_min + stock_axial + half_width
    if left_limit > right_limit:
        gcode.error("Groove Roughing -- blade is wider than available groove after axial stock")
        return

    positions = _center_positions(center_z, left_limit, right_limit, initial_offset, afterwards_offset)
    # the plunges are planned for the blade's middle; the G-code is written
    # for the point it was touched off on
    control = _blade_control(tool)
    z_control = control * half_width
    left_radius, right_radius = _blade_radii(tool)

    gcode.code(
        f"(----------Groove Roughing: Start Center P{int(roughing.profile_id or 0)}----------)"
    )
    gcode.code(
        f"( blade width={_fmt(width)} left radius={_fmt(left_radius)} right radius={_fmt(right_radius)} touched off at {_CONTROL_NAMES[control]} )"
    )

    start_index = 0
    if len(positions) >= 2 and initial_offset > 0:
        first_z = positions[0]
        second_z = positions[1]
        first_target_x = _plunge_x(inside, first_z + z_control, start_x, profile_type)
        second_target_x = _plunge_x(inside, second_z + z_control, start_x, profile_type)
        if _plunges_into(first_target_x) and _plunges_into(second_target_x):
            gcode.code("(----------Groove Roughing Initial Center Pair----------)")
            _append_center_pair_roughing(
                gcode,
                first_z + z_control,
                first_target_x,
                second_z + z_control,
                second_target_x,
                start_x,
                peck_depth,
                clearance,
                dwell_time,
            )
            start_index = 2

    for z_pos in positions[start_index:]:
        target_x = _plunge_x(inside, z_pos + z_control, start_x, profile_type)
        if not _plunges_into(target_x):
            continue
        _append_peck(gcode, z_pos + z_control, safe_x, target_x, peck_depth, clearance, dwell_time)

    _append_contour(gcode, safe_x, obstacle, path, center_z, clearance, profile_type,
                    left_radius, right_radius, half_width, control)



def generate_groove_roughing_gcode(cut: GrooveCut):
    """A Groove Roughing's G-code on its own."""
    gcode = GcodeEmitter(cut.op.is_optional_block)
    groove_roughing_toolpath(cut, gcode)
    return gcode.lines


# ── what the editor draws ───────────────────────────────────────────────────
# The pecks the G-code makes (groove_roughing_toolpath's moves), along the
# blade's middle - so the drawing is the program, peck for peck - its finish
# contour on the contour itself, not where the blade's corners are
# compensated to, and the groove's profile offset by the stock to leave.

#: How far from its own plunge toward the other a peck's number in the pair
#: in the middle is put: near enough to say whose it is, far enough from the
#: other's number at the same depth.
ORDER_BY_ITS_PLUNGE = 0.25


@dataclass(frozen=True)
class PeckDimension:
    """One whole peck, to point at Peck Depth from: on the plunge at ``z``,
    from ``from_x`` to ``to_x``."""
    z: float
    from_x: float
    to_x: float


@dataclass(frozen=True)
class PeckNumber:
    """A peck of the two plunges in the middle, made a peck at a time each in
    turn: ``n`` its place in that order, drawn at ``z`` - between them, by its
    own plunge - going from ``x0`` to the depth ``x``."""
    n: int
    z: float
    x: float
    x0: float


@dataclass(frozen=True)
class GrooveRoughingPreview(OperationPreview):
    """A Groove Roughing as the editor draws it: its pecks, each its arrow
    where it ends and a line across there as wide as the blade, and the
    finish contour, its arrows along it; ``plunges`` the Z of each plunge in
    the order they are made, ``peck`` one whole peck for its dimension,
    ``order`` the pecks of the pair in the middle numbered; the plunges'
    start - the pulley's outside with its radial stock on it - and where the
    blade starts, the clearance out from it."""
    plunges: Tuple[float, ...] = ()
    peck: Optional[PeckDimension] = None
    order: Tuple[PeckNumber, ...] = ()
    start_diameter: Optional[float] = None
    blade_x: Optional[float] = None


def groove_path(cut: GrooveCut):
    """(path, profile_type, error) of the groove ``cut`` cuts: its radial
    profile, from its Z+ end, and "" - or None and why not."""
    profile = cut.radial_profile.to_dict() if cut.radial_profile is not None else {}
    profile_type = cut.radial_profile.profile_type if cut.radial_profile is not None else ProfilingType.OD
    if not _first_groove(profile):
        return None, profile_type, "no radial profile with a groove above this operation"
    path = _groove_path(profile)
    if path is None:
        return None, profile_type, "the radial profile does not make a groove"
    return path, profile_type, ""


def operation_error(gcode: GcodeEmitter) -> str:
    """Why a groove operation written on ``gcode`` cuts nothing - its first
    error, the reason after the "--" - or ""."""
    return gcode.errors[0].split(" -- ", 1)[-1] if gcode.errors else ""


def _cut_feeds(moves):
    """The feeds of ``moves`` (Moves) that are not the finish contour's, as
    DrawnLines, a pass counting the cuts from 0 - a cut being the feeds
    between two rapids."""
    feeds, pass_no, last_feed = [], -1, False
    for move in moves:
        if not move.feed:
            last_feed = False
            continue
        if not last_feed:
            pass_no += 1
        last_feed = True
        if not move.contour:
            feeds.append(DrawnLine(2 * move.r0, move.z0, 2 * move.r1, move.z1, pass_no))
    return feeds


def _from_start(feed: DrawnLine, start_x, profile_type):
    """``feed`` from the start diameter ``start_x`` on - the part of it in the
    air above it cut off - or None when it is all in the air."""
    outside = ((lambda x: x < start_x - ROUNDING) if profile_type is ProfilingType.ID
               else (lambda x: x > start_x + ROUNDING))
    if outside(feed.x0) and outside(feed.x1):
        return None
    if outside(feed.x0) and abs(feed.x1 - feed.x0) > ROUNDING:
        t = (start_x - feed.x0) / (feed.x1 - feed.x0)
        return dataclasses.replace(feed, z0=feed.z0 + t * (feed.z1 - feed.z0), x0=start_x)
    return feed


def _peck(feeds, peck_depth, plunges):
    """One whole peck, to point at Peck Depth from - on the first plunge
    after the two in the middle, toward Z+, or failing it the next that has
    two pecks one after the other a Peck Depth apart, from the end of the one
    to the end of the next - or None."""
    if peck_depth <= 0:
        return None
    by_z = {}
    for f in feeds:
        if abs(f.z1 - f.z0) < SAME_MM:
            by_z.setdefault(round(f.z0, 6), []).append(f.x1)
    for z in [round(p, 6) for p in plunges[2:] + plunges[:2]]:
        ends = by_z.get(z, [])
        for a, b in zip(ends, ends[1:]):
            if abs(abs(b - a) - peck_depth) < SAME_MM:
                return PeckDimension(z, a, b)
    return None


def _contour_feeds(path, cut_path, first_pass):
    """The finish contour as the G-code cuts it, on the contour - the profile
    with the stock to leave (``cut_path``) - not compensated: from the right
    flank's start to the groove's middle, then from the left one's. Each a
    pass of its own, from ``first_pass``, its arrows along it."""
    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    z_plus, z_minus = _split_path_at_z(cut_path, (z_min + z_max) / 2.0)
    feeds = []
    for n, section in enumerate((z_plus, _reverse_path(z_minus))):
        if not section or not isinstance(section[0], StartPoint):
            continue
        points = flatten_path(section)
        for a, b in zip(points, points[1:]):
            feeds.append(DrawnLine(a.x, a.z, b.x, b.z, first_pass + n, True, Arrows.ALONG))
    return feeds


def groove_roughing_preview(cut: GrooveCut) -> GrooveRoughingPreview:
    """What a Groove Roughing - as it is cut, ``cut`` - will cut, as the
    editor draws it (GrooveRoughingPreview)."""
    op = cut.op
    path, profile_type, error = groove_path(cut)
    if path is None:
        return GrooveRoughingPreview(error=error)

    radial = abs(op.stockToLeave.stockToLeaveX) if op.stockToLeaveEnabled else 0.0
    axial = abs(op.stockToLeave.stockToLeaveZ) if op.stockToLeaveEnabled else 0.0

    gcode = GcodeEmitter(op.is_optional_block)
    groove_roughing_toolpath(cut, gcode)
    error = operation_error(gcode)
    feeds = [] if error else _cut_feeds(gcode.moves)
    # the G-code is written for the point the blade was touched off on; the
    # pecks are drawn down its middle
    half_width = _blade_width(cut.tool) / 2.0
    z_control = _blade_control(cut.tool) * half_width
    feeds = [dataclasses.replace(f, z0=f.z0 - z_control, z1=f.z1 - z_control) for f in feeds]
    # the pecks, each with its arrow where it ends - the depth it goes to -
    # from the start diameter on, the pulley's largest with its radial stock
    # to leave: what the G-code feeds through above it is air; the contour
    # drawn on the contour
    start_x = _start_x(path, profile_type, radial)
    feeds = [f for f in (_from_start(dataclasses.replace(f, arrows=Arrows.END), start_x, profile_type)
                         for f in feeds) if f]
    plunges = []
    for f in feeds:
        if not any(abs(f.z0 - z) < SAME_MM for z in plunges):
            plunges.append(f.z0)
    peck = _peck(feeds, abs(op.cuttingParameters.peckDepth), plunges)
    # the two plunges in the middle are made a peck at a time each in turn:
    # each peck's place in that order, between them by its own plunge -
    # ORDER_BY_ITS_PLUNGE of the way to the other, so two at the same depth
    # stay apart - at the depth it goes to
    order = []
    if len(plunges) > 1:
        for f in feeds:
            for own, other in ((plunges[0], plunges[1]), (plunges[1], plunges[0])):
                if abs(f.z1 - own) < SAME_MM:
                    order.append(PeckNumber(len(order) + 1, own + (other - own) * ORDER_BY_ITS_PLUNGE, f.x1, f.x0))
    # where each peck ends, a line across as wide as the blade
    feeds = [dataclasses.replace(f, end_tick=half_width) for f in feeds]
    if not error:
        feeds += _contour_feeds(path, _cut_path(path, profile_type, radial, axial),
                                max([f.pass_no for f in feeds] + [-1]) + 1)
    # from where the blade starts - the clearance out from the start
    # diameter - down its middle to the start diameter, for the first two
    # plunges, the blade's and its outline's on the canvas; not the G-code's
    # rapids: the backing off and in of the pecks, and the moves between them
    # inside the groove, are not drawn
    clearance = abs(op.cuttingParameters.retract)
    blade_x = _blade_start_x(start_x, profile_type, clearance)
    rapids = [DrawnLine(blade_x, z, start_x, z) for z in plunges[:2]] if clearance > 0 else []
    return GrooveRoughingPreview(
        feeds=tuple(feeds), rapids=tuple(rapids),
        profile=flatten_path(path),
        offset=tuple(CanvasPoint(x, z) for z, x in _stock_allowance(path, profile_type, radial, axial)),
        error=error,
        plunges=tuple(plunges), peck=peck, order=tuple(order),
        start_diameter=start_x, blade_x=blade_x)
