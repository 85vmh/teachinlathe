"""What the groove operations - Groove Roughing, BiDirectional Grooving and
Groove Finishing - share: the groove's profile as a path, the start diameter
and the clearance over it, the part with its stock to leave, where a blade may
go on it and its contour along it, and the G-code's start and the editors'
drawing of the groove that every one of them has.

X is a diameter in the paths and the G-code, as the G-code has it; the
shapes are in (z, r), r turned over for ID so the part is under the profile
either way."""

from enum import Enum

from shapely.geometry import LineString, Polygon, box
from shapely.ops import linemerge

from teachinlathe.conversational.model.data_types import ProfilingType

from ..helpers.spindle import build_feed_gcode, build_spindle_gcode
from ..toolpath import GcodeEmitter, Point
from .profiling.geometry import ROUNDING, SAME_MM, StartPoint, ToolpathArc, ToolpathLine, arc_x_at_z, build_path
from .profiling.groove_outline import groove_outline
from .profiling.operation_input import GrooveCut
from .profiling.plan_drawing import flatten_path
from .profiling.plan_gcode import fit_arcs
from .profiling.shapes import FAR, drop_onto, edge_between, minkowski, obstacle_of, path_points
from .profiling.tool_shape import blade_shape


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
#: taken from (contour_edge): on the outside, where the blade sits on it.
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


def on_diameter(radial):
    """A distance along X, such as the clearance - given on the radius, as
    the canvas dimensions it - on the diameter the G-code's X is."""
    return 2.0 * abs(radial)


def outward_sign(profile_type):
    """Which way out of the groove is along X: +1 for an OD one, -1 for ID."""
    return -1.0 if profile_type is ProfilingType.ID else 1.0


def outside_x(path, profile_type):
    """The pulley's outside, the groove's mouth: the largest diameter of its
    profile ``path``, the smallest for ID."""
    x_min, x_max, _z_min, _z_max = path_bounds(path)
    return x_min if profile_type is ProfilingType.ID else x_max


def start_diameter_of(path, profile_type, stock_radial):
    """The start diameter: the pulley's outside with ``stock_radial`` - the
    radial stock to leave, or the one left - on it."""
    return outside_x(path, profile_type) + outward_sign(profile_type) * on_diameter(stock_radial)


def blade_start_x(start_x, profile_type, clearance):
    """Where the blade starts, and backs off to: ``clearance`` out from the
    start diameter ``start_x``."""
    return start_x + outward_sign(profile_type) * on_diameter(clearance)


# ── in and out of the groove through air ───────────────────────────────────
# A groove is behind the part's face, and between the face and it the part may
# be bigger than the groove's mouth: the blade goes along Z only where nothing
# is in its way. M1 is remapped (subroutines/m1_remap.ngc) to go to G28 / G30
# and back in straight lines: a pause is made only where both are in the air.

def over_x(cut: GrooveCut, safe_x, clearance, profile_type):
    """Where an OD blade goes along Z on its way in and pauses: the clearance
    out from all the material ``cut`` finds - never in from ``safe_x``. For
    ID, ``safe_x``: inside the bore."""
    if profile_type is ProfilingType.ID:
        return safe_x
    material = cut.stock.material if cut.stock is not None else None
    if material is None or material.is_empty:
        return safe_x
    return max(safe_x, 2.0 * material.bounds[3] + on_diameter(clearance))


def front_z(cut: GrooveCut, clearance):
    """In front of the part: the clearance past the material's Z+ end (Z0
    with none known), where an ID blade comes out of the bore to pause."""
    material = cut.stock.material if cut.stock is not None else None
    face = material.bounds[2] if material is not None and not material.is_empty else 0.0
    return face + abs(clearance)


def enter(gcode: GcodeEmitter, safe_x, z, profile_type, over):
    """From wherever the blade is to ``safe_x`` over ``z``, through air.

    An OD blade along Z first, then in to ``safe_x``: from the tool change
    position, or from where it is when that is out at ``over`` (over_x) or
    farther; from anywhere else - lower, or not known - out to ``over`` first,
    outward being always clear. An ID blade in to ``safe_x`` first, in front
    of the bore, then along it."""
    if profile_type is ProfilingType.ID:
        gcode.rapid(x=safe_x)
        gcode.rapid(z=z)
        return
    clear = gcode.at_tool_change or (gcode.x is not None and gcode.x >= over - SAME_MM)
    if not clear:
        gcode.rapid(x=over)
    gcode.rapid(z=z)
    gcode.rapid(x=safe_x)


def pause_to_inspect(gcode: GcodeEmitter, m1_params, safe_x, profile_type, over, front):
    """M1, where the blade can go to G28 / G30 and come back in a straight
    line (m1_remap.ngc): out of the groove to ``safe_x``, then an OD blade out
    to ``over``, an ID one out of the bore to ``front``. The next move in
    takes it back from there."""
    gcode.rapid(x=safe_x)
    if profile_type is ProfilingType.ID:
        gcode.rapid(z=front)
    else:
        gcode.rapid(x=over)
    gcode.inspect_stop(m1_params)


def groove_profile_path(radial_profile):
    """The profile of the first groove of ``radial_profile`` (a Define
    Radial Profile, or None), as the G-code goes along it - from its Z+ end
    to its Z- one - or None."""
    groove = radial_profile.first_groove() if radial_profile is not None else None
    if groove is None:
        return None
    path = build_path(list(groove_outline(groove).primitives), radial_profile.profile_type)
    if not path or not isinstance(path[0], StartPoint):
        return None
    return path


def path_bounds(path):
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


def blade_control(tool):
    """Which point of the blade - ``tool``, a MountedTool or None - it was
    touched off on, so the G-code is written for: -1 its left corner, 0 the
    middle of its end, 1 its right corner."""
    return tool.z_control if tool is not None else 0


def blade_problem(tool) -> str:
    """Why ``tool`` (a MountedTool or None) cannot cut a groove that takes a
    blade - not a blade, or one with no width - or ""."""
    if not is_blade(tool):
        return "current tool must be a parting or grooving blade"
    if blade_width(tool) <= 0:
        return "blade width is not defined in tool extras"
    return ""


def blade_touch_point_comment(tool):
    """The setup note emitted once, when the grooving blade is loaded."""
    return f"( blade touch point: {_CONTROL_NAMES[blade_control(tool)]} )"


def _path_end_point(path):
    if not path:
        return None
    last = path[-1]
    if isinstance(last, StartPoint):
        return last.x, last.z
    return last.end_x, last.end_z


def reverse_path(path):
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


def split_path_at_z(path, target_z):
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


def is_blade(tool):
    """Whether ``tool`` (a MountedTool or None) is a blade."""
    return tool is not None and tool.blade is not None


def blade_width(tool):
    """The width of blade ``tool`` (a MountedTool or None); 0 for no blade."""
    return float(tool.blade.blade_width) if is_blade(tool) else 0.0


def blade_radii(tool):
    """(left, right): the corner radii of blade ``tool`` (a MountedTool)."""
    return float(tool.blade.left_radius), float(tool.blade.right_radius)


#: The comment put over a contour cut with one of the blade's corners, which
#: the backplot reads to draw it along that corner (backplot.blade_middle).
CORNER_COMMENT = "( blade {} corner on the contour )"


def corner_comment(corner: Corner):
    """The comment over a contour cut with the blade's ``corner``."""
    return CORNER_COMMENT.format(corner.value)


def emit_contour_section(gcode, safe_x, section, profile_type, corner=None):
    """``section`` - (z, r) of the touch-off point, in the part's frame - at
    the feed: in from ``safe_x`` over its start, along it - its runs of
    chords on one circle as arcs (plan_gcode.fit_arcs) - and back out; the
    blade's ``corner`` cutting it said over it."""
    if len(section) < 2:
        return
    if corner:
        gcode.code(corner_comment(corner))
    sign = outward_sign(profile_type)
    points = [(z, sign * r) for z, r in section]
    gcode.rapid(x=safe_x)
    gcode.rapid(z=points[0][0])
    gcode.feed(2.0 * points[0][1], points[0][0])
    for segment in fit_arcs(points, CONTOUR_ARC_TOLERANCE):
        segment.write(gcode)
    gcode.rapid(x=safe_x)


def safe_x_for_contour(sections, safe_x, clearance, profile_type):
    """Where the blade goes in from and back out to for ``sections``: the
    start's clearance out, or the clearance out from the sections' highest."""
    sign = outward_sign(profile_type)
    xs = [2.0 * sign * r for section in sections for _z, r in section]
    if not xs:
        return safe_x
    if profile_type is ProfilingType.ID:
        return min(safe_x, min(xs) - on_diameter(clearance))
    return max(safe_x, max(xs) + on_diameter(clearance))


def part_with_stock(path, profile_type, radial, axial, reach=0.0):
    """The part under the groove's profile ``path``, the bar carried on past
    it either side - ``reach`` farther still - grown by the stock to leave -
    ``radial`` off the bottom, ``axial`` off the flanks - as a shapely
    Polygon in (z, r), r turned over for ID so the part is under it either
    way; with ``points``, the profile's (z, r) from its right end to its
    left, in the same frame."""
    sign = outward_sign(profile_type)
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


def stock_allowance(path, profile_type, radial, axial):
    """The groove's profile ``path`` offset by the stock to leave - ``radial``
    off its bottom, ``axial`` off its flanks, as the stock it is left with is
    the part grown by both - as [(z, x)] (X a diameter) from its right end
    to its left, between the profile's ends, out to the pulley's outside
    with its stock; [] with none to leave."""
    if radial <= 0 and axial <= 0:
        return []
    sign = outward_sign(profile_type)
    allowance, points = part_with_stock(path, profile_type, radial, axial)
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


def blade_obstacle(tool, path, profile_type, radial, axial):
    """Where the point blade ``tool`` (a MountedTool) was touched off on may
    not go without the blade going into the part or the stock it is to be
    left with (``radial``, ``axial``; part_with_stock) - the bar carried on
    past the groove as far as the blade sits on its outside either side -
    the part grown by the blade (tool_shape.blade_shape) turned round, in
    the part's frame."""
    width = blade_width(tool)
    part, _points = part_with_stock(path, profile_type, radial, axial, reach=width)
    left_radius, right_radius = blade_radii(tool)
    return obstacle_of(part, blade_shape(width, left_radius, right_radius, blade_control(tool)).envelope)


def contour_edge(obstacle, path, width):
    """The touch-off point's way across the groove with the blade on the part
    (``obstacle``, blade_obstacle): its top, from over the outside past
    the groove's Z+ end - the blade sitting on it - to past its Z- end, as
    (z, r) in the part's frame."""
    _x_min, _x_max, z_min, z_max = path_bounds(path)
    top = obstacle.bounds[3] + OVER_THE_OUTSIDE
    ends = [(z, drop_onto(obstacle, z, top, top - FAR, 0.0))
            for z in (z_max + width + RIM_REACH, z_min - width - RIM_REACH)]
    return edge_between(obstacle, *ends)


def to_middle(edge, stop_z):
    """``edge`` (contour_edge, or it the other way round) from where it
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


def groove_path(cut: GrooveCut):
    """(path, profile_type, error) of the groove ``cut`` cuts: its radial
    profile, from its Z+ end, and "" - or None and why not."""
    profile = cut.radial_profile
    profile_type = profile.profile_type if profile is not None else ProfilingType.OD
    if profile is None or profile.first_groove() is None:
        return None, profile_type, "no radial profile with a groove above this operation"
    path = groove_profile_path(profile)
    if path is None:
        return None, profile_type, "the radial profile does not make a groove"
    return path, profile_type, ""


def operation_error(gcode: GcodeEmitter) -> str:
    """Why a groove operation written on ``gcode`` cuts nothing - its first
    error, the reason after the "--" - or ""."""
    return gcode.errors[0].split(" -- ", 1)[-1] if gcode.errors else ""


# ── what every groove operation does ───────────────────────────────────────

def stock_to_leave(op):
    """(radial, axial): the stock to leave ``op`` - a Groove Roughing or a
    BiDirectional Grooving - is to leave on the groove; none when it is off."""
    if not op.stockToLeaveEnabled:
        return 0.0, 0.0
    return abs(op.stockToLeave.stockToLeaveX), abs(op.stockToLeave.stockToLeaveZ)


def begin_gcode(gcode: GcodeEmitter, op):
    """What a groove operation's G-code starts with: its spindle and its feed."""
    gcode.codes(build_spindle_gcode(op.speedsAndFeeds, ""))
    gcode.code(build_feed_gcode(op.speedsAndFeeds.feed))
    gcode.blank()


def drawn_groove(path, profile_type, radial, axial) -> dict:
    """The groove as an editor draws it under what the operation cuts: its
    profile ``path`` and that offset by the stock left on it - ``radial``,
    ``axial`` - as an OperationPreview's ``profile`` and ``offset``."""
    return dict(profile=flatten_path(path),
                offset=tuple(Point(x, z) for z, x in stock_allowance(path, profile_type, radial, axial)))
