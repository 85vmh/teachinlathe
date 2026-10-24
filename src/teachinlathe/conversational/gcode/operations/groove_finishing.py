from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float
from .profiling.geometry import StartPoint
from .profiling.toolpath import emit_toolpath
from .groove_roughing import (
    CONTACT_MARGIN,
    SAME_MM,
    _CONTROL_NAMES,
    _Blade,
    _blade_control,
    _blade_start_x,
    _blade_width,
    _clear_part_of,
    _code,
    _corner_to_control,
    _emit_contour_section,
    _fmt,
    _groove_path,
    _offset_path_for_tool_radius,
    _part_with_stock,
    _path_end_point,
    _profile_bounds_from_path,
    _reverse_path,
    _safe_x_for_contour,
    _split_path_at_z,
    _start_x,
    _tool_is_blade,
    corner_comment,
)


def roughing_stock(op):
    """(radial, axial) the Groove Roughing above left, as the op carries it
    in ``_resolved_roughing_stock``: what this takes off."""
    stock = op.get("_resolved_roughing_stock") or {}
    return abs(get_float(stock, "radial", 0.0)), abs(get_float(stock, "axial", 0.0))


def _right_to_center_side(profile_type):
    return "right" if str(profile_type).lower() == "id" else "left"


def _left_to_center_side(profile_type):
    return "left" if str(profile_type).lower() == "id" else "right"


def _right_from_center_side(profile_type):
    return "left" if str(profile_type).lower() == "id" else "right"


def _left_from_center_side(profile_type):
    return "right" if str(profile_type).lower() == "id" else "left"


def _emit_continuous_sections(lines, prefix, safe_x, sections, corners):
    """``sections`` one after the other at the feed, each cut with the
    blade's corner of ``corners`` ("right" / "left"), said over it."""
    kept = [(section, corner) for section, corner in zip(sections, corners)
            if section and isinstance(section[0], StartPoint)]
    if not kept:
        return
    sections = [section for section, _corner in kept]
    lines.append(_code(prefix, corner_comment(kept[0][1])))

    start = sections[0][0]
    lines.append(_code(prefix, f"G0 X{_fmt(safe_x)}"))
    lines.append(_code(prefix, f"G0 Z{_fmt(start.z)}"))
    lines.append(_code(prefix, f"G1 X{_fmt(start.x)} Z{_fmt(start.z)}"))

    current_end = (start.x, start.z)
    for index, section in enumerate(sections):
        if index > 0:
            lines.append(_code(prefix, corner_comment(kept[index][1])))
            section_start = section[0]
            if abs(current_end[0] - section_start.x) > SAME_MM or abs(current_end[1] - section_start.z) > SAME_MM:
                lines.append(_code(prefix, f"G1 X{_fmt(section_start.x)} Z{_fmt(section_start.z)}"))
        emit_toolpath(lines, prefix, section)
        end_point = _path_end_point(section)
        if end_point is not None:
            current_end = end_point

    lines.append(_code(prefix, f"G0 X{_fmt(safe_x)}"))


def _finishing_sections(path, center_z, half_width, left_radius, right_radius, overlap=0.0):
    """The groove's profile ``path`` - from its Z+ end to its Z- one - as the
    two sides the blade's corners finish: the Z+ side, cut with its right
    corner, as far along the bottom as puts the blade's middle ``overlap``
    past the groove's middle, and the Z- side, cut with its left, from as
    far the other way. The blade's end - flat between its corners -
    finishes the bottom between them; with no overlap, a pass going on from
    the one to the other goes straight on."""
    right_end = center_z + max(half_width - right_radius, 0.0) - overlap
    left_start = center_z - max(half_width - left_radius, 0.0) + overlap
    z_plus, _rest = _split_path_at_z(path, right_end)
    _rest, z_minus = _split_path_at_z(path, left_start)
    return z_plus, z_minus


def _append_finishing_contour(
    lines,
    prefix,
    safe_x,
    path,
    center_z,
    clearance,
    profile_type,
    strategy,
    left_radius,
    right_radius,
    half_width=0.0,
    control=0,
    blade=None,
    part=None,
):
    # toward the centre, each side takes the blade's middle half its width
    # past the groove's middle - the two overlapping by a blade's width; a
    # pass going on from one side to the other cuts across it anyway
    overlap = half_width if strategy == "towards_center" else 0.0
    z_plus_path, z_minus_path = _finishing_sections(path, center_z, half_width, left_radius, right_radius,
                                                    overlap)

    z_plus_to_center = _offset_path_for_tool_radius(
        z_plus_path,
        right_radius,
        _right_to_center_side(profile_type),
    )
    z_minus_to_center = _offset_path_for_tool_radius(
        _reverse_path(z_minus_path),
        left_radius,
        _left_to_center_side(profile_type),
    )
    z_plus_from_center = _offset_path_for_tool_radius(
        _reverse_path(z_plus_path),
        right_radius,
        _right_from_center_side(profile_type),
    )
    z_minus_from_center = _offset_path_for_tool_radius(
        z_minus_path,
        left_radius,
        _left_from_center_side(profile_type),
    )

    # the Z+ side cut with the blade's right corner, the Z- side with its
    # left: each written for the point it was touched off on, and as far as
    # the blade stays out of the part
    def _placed(section, corner, radius):
        section = _corner_to_control(section, corner, radius, half_width, control, profile_type)
        return _clear_part_of(section, blade, part)

    z_plus_to_center = _placed(z_plus_to_center, "right", right_radius)
    z_plus_from_center = _placed(z_plus_from_center, "right", right_radius)
    z_minus_to_center = _placed(z_minus_to_center, "left", left_radius)
    z_minus_from_center = _placed(z_minus_from_center, "left", left_radius)

    safe_path = z_plus_to_center + z_minus_to_center + z_plus_from_center + z_minus_from_center
    contour_safe_x = _safe_x_for_contour(safe_path, safe_x, clearance, profile_type)

    if strategy == "towards_left":
        lines.append(_code(prefix, "(----------Groove Finishing Contour Towards Left----------)"))
        _emit_continuous_sections(lines, prefix, contour_safe_x, [z_plus_to_center, z_minus_from_center],
                                  ["right", "left"])
        return

    if strategy == "towards_right":
        lines.append(_code(prefix, "(----------Groove Finishing Contour Towards Right----------)"))
        _emit_continuous_sections(lines, prefix, contour_safe_x, [z_minus_to_center, z_plus_from_center],
                                  ["left", "right"])
        return

    lines.append(_code(prefix, "(----------Groove Finishing Contour Z+ to Center----------)"))
    _emit_contour_section(lines, prefix, contour_safe_x, z_plus_to_center, "right")

    lines.append(_code(prefix, "(----------Groove Finishing Contour Z- to Center----------)"))
    _emit_contour_section(lines, prefix, contour_safe_x, z_minus_to_center, "left")


def generate_groove_finishing_gcode(op):
    if hasattr(op, "to_dict"):
        op = op.to_dict()

    prefix = "/" if bool(op.get("is_optional_block", False)) else ""
    spindle = op.get("spindle_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    finishing = op.get("finishing_parameters", {}) or {}
    profile = op.get("_resolved_radial_profile", {}) or {}
    tool = op.get("_resolved_tool", {}) or {}

    feed_rate = get_float(cutting, "feed_rate", 0.1)
    clearance = abs(get_float(cutting, "retract", 1.0))
    strategy = str(finishing.get("strategy", "towards_center")).lower()

    lines = []
    lines.extend(build_spindle_gcode(spindle, prefix))
    lines.append(_code(prefix, f"G95 F{_fmt(feed_rate)}"))
    lines.append("")

    if strategy not in {"towards_left", "towards_right", "towards_center"}:
        lines.append("( ERROR: Groove Finishing -- invalid strategy )")
        return lines
    if not profile:
        lines.append("( ERROR: Groove Finishing -- no Define Radial Profile found above this operation )")
        return lines
    if not _tool_is_blade(tool):
        lines.append("( ERROR: Groove Finishing -- current tool must be a parting or grooving blade )")
        return lines

    path = _groove_path(profile)
    if path is None:
        lines.append("( ERROR: Groove Finishing -- radial profile did not produce a valid toolpath )")
        return lines

    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    center_z = (z_min + z_max) / 2.0
    profile_type = str(profile.get("profile_type", "od")).lower()
    # what the Groove Roughing above left: the start diameter is the
    # pulley's outside with that radial stock on it, and the blade starts
    # the clearance out from it, as the roughing's did
    stock_radial = roughing_stock(op)[0]
    safe_x = _blade_start_x(_start_x(path, profile_type, stock_radial), profile_type, clearance)
    width = _blade_width(tool)
    if width <= 0:
        lines.append("( ERROR: Groove Finishing -- blade width is not defined in tool extras )")
        return lines
    half_width = width / 2.0
    control = _blade_control(tool)
    left_radius = get_float(tool, "left_radius", 0.0)
    right_radius = get_float(tool, "right_radius", 0.0)

    lines.append(
        _code(
            prefix,
            f"(----------Groove Finishing: {strategy.replace('_', ' ').title()} P{int(finishing.get('profile_id', 0) or 0)}----------)",
        )
    )
    lines.append(
        _code(
            prefix,
            f"( blade width={_fmt(width)} left radius={_fmt(left_radius)} right radius={_fmt(right_radius)} touched off at {_CONTROL_NAMES[control]} )",
        )
    )

    _append_finishing_contour(
        lines,
        prefix,
        safe_x,
        path,
        center_z,
        clearance,
        profile_type,
        strategy,
        left_radius,
        right_radius,
        half_width,
        control,
        _Blade(half_width, left_radius, right_radius, control, profile_type),
        _part_with_stock(path, profile_type, 0.0, 0.0)[0].buffer(-CONTACT_MARGIN),
    )
    return lines
