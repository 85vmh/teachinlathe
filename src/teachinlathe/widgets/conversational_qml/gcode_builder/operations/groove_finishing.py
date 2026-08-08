from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float
from .profiling.geometry import StartPoint, build_profile_segments, build_render_path
from .profiling.toolpath import emit_toolpath
from .groove_roughing import (
    _code,
    _emit_contour_section,
    _first_groove,
    _fmt,
    _offset_path_for_tool_radius,
    _path_end_point,
    _profile_bounds_from_path,
    _radial_profile_primitives,
    _reverse_path,
    _safe_x_for_contour,
    _shift_path_x,
    _split_path_at_z,
    _tool_is_blade,
)


def _right_to_center_side(profile_type):
    return "right" if str(profile_type).lower() == "id" else "left"


def _left_to_center_side(profile_type):
    return "left" if str(profile_type).lower() == "id" else "right"


def _right_from_center_side(profile_type):
    return "left" if str(profile_type).lower() == "id" else "right"


def _left_from_center_side(profile_type):
    return "right" if str(profile_type).lower() == "id" else "left"


def _emit_continuous_sections(lines, prefix, safe_x, sections):
    sections = [section for section in sections if section and isinstance(section[0], StartPoint)]
    if not sections:
        return

    start = sections[0][0]
    lines.append(_code(prefix, f"G0 X{_fmt(safe_x)}"))
    lines.append(_code(prefix, f"G0 Z{_fmt(start.z)}"))
    lines.append(_code(prefix, f"G1 X{_fmt(start.x)} Z{_fmt(start.z)}"))

    current_end = (start.x, start.z)
    for index, section in enumerate(sections):
        if index > 0:
            section_start = section[0]
            if abs(current_end[0] - section_start.x) > 0.0001 or abs(current_end[1] - section_start.z) > 0.0001:
                lines.append(_code(prefix, f"G1 X{_fmt(section_start.x)} Z{_fmt(section_start.z)}"))
        emit_toolpath(lines, prefix, section)
        end_point = _path_end_point(section)
        if end_point is not None:
            current_end = end_point

    lines.append(_code(prefix, f"G0 X{_fmt(safe_x)}"))


def _build_profile_path(profile):
    groove = _first_groove(profile)
    if not groove:
        return None
    primitives = _radial_profile_primitives(groove)
    segments = build_profile_segments(primitives)
    profile_type = str(profile.get("profile_type", "od")).lower()
    path = build_render_path(segments, profile_type=profile_type)
    if not path or not isinstance(path[0], StartPoint):
        return None
    return path


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
):
    contour_path = _shift_path_x(path, 0.0)
    z_plus_path, z_minus_path = _split_path_at_z(contour_path, center_z)

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

    safe_path = z_plus_to_center + z_minus_to_center + z_plus_from_center + z_minus_from_center
    contour_safe_x = _safe_x_for_contour(safe_path, safe_x, clearance, profile_type)

    if strategy == "towards_left":
        lines.append(_code(prefix, "(----------Groove Finishing Contour Towards Left----------)"))
        _emit_continuous_sections(lines, prefix, contour_safe_x, [z_plus_to_center, z_minus_from_center])
        return

    if strategy == "towards_right":
        lines.append(_code(prefix, "(----------Groove Finishing Contour Towards Right----------)"))
        _emit_continuous_sections(lines, prefix, contour_safe_x, [z_minus_to_center, z_plus_from_center])
        return

    lines.append(_code(prefix, "(----------Groove Finishing Contour Z+ to Center----------)"))
    _emit_contour_section(lines, prefix, contour_safe_x, z_plus_to_center)

    lines.append(_code(prefix, "(----------Groove Finishing Contour Z- to Center----------)"))
    _emit_contour_section(lines, prefix, contour_safe_x, z_minus_to_center)


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

    path = _build_profile_path(profile)
    if path is None:
        lines.append("( ERROR: Groove Finishing -- radial profile did not produce a valid toolpath )")
        return lines

    x_min, x_max, z_min, z_max = _profile_bounds_from_path(path)
    center_z = (z_min + z_max) / 2.0
    profile_type = str(profile.get("profile_type", "od")).lower()
    if profile_type == "id":
        safe_x = x_min - clearance * 2.0
    else:
        safe_x = x_max + clearance * 2.0

    lines.append(
        _code(
            prefix,
            f"(----------Groove Finishing: {strategy.replace('_', ' ').title()} P{int(finishing.get('profile_id', 0) or 0)}----------)",
        )
    )
    lines.append(
        _code(
            prefix,
            f"( blade left radius={_fmt(get_float(tool, 'left_radius', 0.0))} right radius={_fmt(get_float(tool, 'right_radius', 0.0))} )",
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
        get_float(tool, "left_radius", 0.0),
        get_float(tool, "right_radius", 0.0),
    )
    return lines
