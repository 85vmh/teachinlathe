from dataclasses import dataclass
from typing import Optional

from teachinlathe.conversational.model.data_types import GrooveFinishingStrategy

from ..helpers.spindle import build_feed_gcode, build_spindle_gcode
from .profiling.geometry import StartPoint
from ..toolpath import Arrows, DrawnLine, GcodeEmitter, OperationPreview, Point
from .profiling.plan_drawing import flatten_path
from .profiling.plan_gcode import fit_arcs
from .profiling.operation_input import GrooveCut
from .groove_roughing import (
    CONTOUR_ARC_TOLERANCE,
    _CONTROL_NAMES,
    Corner,
    _blade_control,
    _blade_obstacle,
    _blade_radii,
    _blade_start_x,
    _blade_width,
    _contour_edge,
    _emit_contour_section,
    _fmt,
    _groove_path,
    _outward,
    _profile_bounds_from_path,
    _profiling_type,
    _reverse_path,
    _safe_x_for_contour,
    _split_path_at_z,
    _start_x,
    _stock_allowance,
    _tool_is_blade,
    _to_middle,
    corner_comment,
    groove_path,
    operation_error,
)


def roughing_stock(cut: GrooveCut):
    """(radial, axial) the Groove Roughing above left (``cut.roughing_stock``):
    what this takes off."""
    stock = cut.roughing_stock
    if stock is None:
        return 0.0, 0.0
    return abs(stock.stockToLeaveX), abs(stock.stockToLeaveZ)


def _emit_continuous_sections(gcode, safe_x, sections, corners, profile_type):
    """``sections`` - (z, r) of the touch-off point, in the part's frame -
    one after the other at the feed, each cut with the blade's corner of
    ``corners`` (Corners), said over it."""
    kept = [(section, corner) for section, corner in zip(sections, corners) if len(section) > 1]
    if not kept:
        return
    sign = _outward(profile_type)
    start_z, start_r = kept[0][0][0]
    gcode.code(corner_comment(kept[0][1]))
    gcode.rapid(x=safe_x)
    gcode.rapid(z=start_z)
    gcode.feed(2.0 * sign * start_r, start_z)
    for index, (section, corner) in enumerate(kept):
        if index > 0:
            gcode.code(corner_comment(corner))
        for segment in fit_arcs([(z, sign * r) for z, r in section], CONTOUR_ARC_TOLERANCE):
            segment.write(gcode)
    gcode.rapid(x=safe_x)


def _append_finishing_contour(gcode, safe_x, obstacle, path, center_z, clearance, profile_type,
                              strategy, half_width, control):
    """The contour the strategy goes along, the blade on the part
    (``obstacle``): the Z+ side cut with its right corner, the Z- side with
    its left. Toward the centre, each side takes the blade's middle half its
    width past the groove's middle - the two overlapping by a blade's width;
    a pass going on from one side to the other changes corner there."""
    overlap = half_width if strategy is GrooveFinishingStrategy.TOWARDS_CENTER else 0.0
    edge = _contour_edge(obstacle, path, 2.0 * half_width)
    z_control = control * half_width
    z_plus_to_center = _to_middle(edge, center_z - overlap + z_control)
    z_minus_to_center = _to_middle(edge[::-1], center_z + overlap + z_control)
    z_plus_from_center = z_plus_to_center[::-1]
    z_minus_from_center = z_minus_to_center[::-1]
    contour_safe_x = _safe_x_for_contour([z_plus_to_center, z_minus_to_center], safe_x, clearance,
                                         profile_type)

    if strategy is GrooveFinishingStrategy.TOWARDS_LEFT:
        gcode.code("(----------Groove Finishing Contour Towards Left----------)")
        _emit_continuous_sections(gcode, contour_safe_x, [z_plus_to_center, z_minus_from_center],
                                  [Corner.RIGHT, Corner.LEFT], profile_type)
        return

    if strategy is GrooveFinishingStrategy.TOWARDS_RIGHT:
        gcode.code("(----------Groove Finishing Contour Towards Right----------)")
        _emit_continuous_sections(gcode, contour_safe_x, [z_minus_to_center, z_plus_from_center],
                                  [Corner.LEFT, Corner.RIGHT], profile_type)
        return

    gcode.code("(----------Groove Finishing Contour Z+ to Center----------)")
    _emit_contour_section(gcode, contour_safe_x, z_plus_to_center, profile_type, Corner.RIGHT)

    gcode.code("(----------Groove Finishing Contour Z- to Center----------)")
    _emit_contour_section(gcode, contour_safe_x, z_minus_to_center, profile_type, Corner.LEFT)


def groove_finishing_toolpath(cut: GrooveCut, gcode: GcodeEmitter):
    """The G-code of a Groove Finishing, as it is cut (``cut``), onto ``gcode``."""
    op = cut.op
    finishing = op.finishingParameters
    # the radial profile's own primitives are dicts: the groove geometry reads them so
    profile = cut.radial_profile.to_dict() if cut.radial_profile is not None else {}
    tool = cut.tool

    feed_rate = op.speedsAndFeeds.feed
    clearance = abs(op.cuttingParameters.retract)
    strategy = finishing.strategy

    gcode.codes(build_spindle_gcode(op.speedsAndFeeds, ""))
    gcode.code(build_feed_gcode(feed_rate))
    gcode.blank()

    if not isinstance(strategy, GrooveFinishingStrategy):
        gcode.error("Groove Finishing -- invalid strategy")
        return
    if not profile:
        gcode.error("Groove Finishing -- no Define Radial Profile found above this operation")
        return
    if not _tool_is_blade(tool):
        gcode.error("Groove Finishing -- current tool must be a parting or grooving blade")
        return

    path = _groove_path(profile)
    if path is None:
        gcode.error("Groove Finishing -- radial profile did not produce a valid toolpath")
        return

    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    center_z = (z_min + z_max) / 2.0
    profile_type = _profiling_type(profile.get("profile_type"))
    # what the Groove Roughing above left: the start diameter is the
    # pulley's outside with that radial stock on it, and the blade starts
    # the clearance out from it, as the roughing's did
    stock_radial = roughing_stock(cut)[0]
    safe_x = _blade_start_x(_start_x(path, profile_type, stock_radial), profile_type, clearance)
    width = _blade_width(tool)
    if width <= 0:
        gcode.error("Groove Finishing -- blade width is not defined in tool extras")
        return
    half_width = width / 2.0
    control = _blade_control(tool)
    left_radius, right_radius = _blade_radii(tool)

    gcode.code(
        f"(----------Groove Finishing: {strategy.value.replace('_', ' ').title()} P{int(finishing.profile_id or 0)}----------)"
    )
    gcode.code(
        f"( blade width={_fmt(width)} left radius={_fmt(left_radius)} right radius={_fmt(right_radius)} touched off at {_CONTROL_NAMES[control]} )"
    )

    _append_finishing_contour(gcode, safe_x, _blade_obstacle(tool, path, profile_type, 0.0, 0.0), path,
                              center_z, clearance, profile_type, strategy, half_width, control)


def generate_groove_finishing_gcode(cut: GrooveCut):
    """A Groove Finishing's G-code on its own."""
    gcode = GcodeEmitter(cut.op.is_optional_block)
    groove_finishing_toolpath(cut, gcode)
    return gcode.lines


# ── what the editor draws ───────────────────────────────────────────────────
# What Groove Finishing will cut: the groove's profile, it offset by the
# stock the roughing above left - what the finishing takes off - and the
# contour its strategy goes along, on the profile itself.

@dataclass(frozen=True)
class GrooveFinishingPreview(OperationPreview):
    """A Groove Finishing as the editor draws it: the contour, its arrows
    along it, and the rapids from where the blade starts over to above each
    pass's start and down to it; ``start`` where the blade starts - over the
    groove's middle, the clearance out from the start diameter - and the
    start diameter, the pulley's outside with the stock the roughing left on
    it."""
    start: Optional[Point] = None
    start_diameter: Optional[float] = None


def _passes(path, center_z, strategy, overlap):
    """The profile as the strategy goes along it, a list of passes, each
    Points: toward the centre, each side ``overlap`` past the middle, as
    the blade's middle goes; toward the left, the Z+ side down and on along
    the bottom and up the Z- side; toward the right, the other way round."""
    z_plus, _rest = _split_path_at_z(path, center_z - overlap)
    _rest, z_minus = _split_path_at_z(path, center_z + overlap)
    if strategy is GrooveFinishingStrategy.TOWARDS_LEFT:
        sections = [path]
    elif strategy is GrooveFinishingStrategy.TOWARDS_RIGHT:
        sections = [_reverse_path(path)]
    else:
        sections = [z_plus, _reverse_path(z_minus)]
    return [flatten_path(section) for section in sections if section and isinstance(section[0], StartPoint)]


def groove_finishing_preview(cut: GrooveCut) -> GrooveFinishingPreview:
    """What a Groove Finishing - as it is cut, ``cut``, the stock the
    Groove Roughing of its profile above left included - will cut, as the
    editor draws it (GrooveFinishingPreview)."""
    op = cut.op
    path, profile_type, error = groove_path(cut)
    if path is None:
        return GrooveFinishingPreview(error=error)

    radial, axial = roughing_stock(cut)
    offset = tuple(Point(x, z) for z, x in _stock_allowance(path, profile_type, radial, axial))

    gcode = GcodeEmitter(op.is_optional_block)
    groove_finishing_toolpath(cut, gcode)
    error = operation_error(gcode)

    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    center_z = (z_min + z_max) / 2.0
    clearance = abs(op.cuttingParameters.retract)
    start_x = _start_x(path, profile_type, radial)
    blade_x = _blade_start_x(start_x, profile_type, clearance)
    drawn = dict(profile=flatten_path(path), offset=offset, start=Point(blade_x, center_z),
                 start_diameter=start_x)
    if error:
        return GrooveFinishingPreview(error=error, **drawn)

    feeds, rapids = [], []
    # toward the centre, each side half the blade's width past the middle
    half_width = _blade_width(cut.tool) / 2.0
    for n, points in enumerate(_passes(path, center_z, op.finishingParameters.strategy, half_width)):
        first = points[0]
        rapids.append(DrawnLine(blade_x, center_z, blade_x, first.z))
        rapids.append(DrawnLine(blade_x, first.z, first.x, first.z))
        for a, b in zip(points, points[1:]):
            feeds.append(DrawnLine(a.x, a.z, b.x, b.z, n, True, Arrows.ALONG))
    return GrooveFinishingPreview(feeds=tuple(feeds), rapids=tuple(rapids), **drawn)
