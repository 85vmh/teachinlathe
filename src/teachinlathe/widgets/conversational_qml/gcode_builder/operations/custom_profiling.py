"""CAM-style explicit G-code generator for Custom Profiling.

The generator is intentionally split into:
- operation parsing
- profile geometry expansion
- pass planning
- G-code emission

This keeps the orchestration here short while preserving the existing output.
"""

from .custom_cam.custom_profiling_geometry import build_profile_segments, build_render_path, find_deepest_z_at_x_path, profile_extents
from .custom_cam.custom_profiling_planner import (
    build_spindle_lines,
    emit_contour_pass_gcode,
    emit_finish_gcode,
    emit_roughing_gcode,
    plan_finish_passes,
    plan_roughing_passes,
)
from .custom_cam.custom_profiling_types import ProfilingConfig, StartPoint


def _get_float(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def _parse_config(op):
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    options = op.get("profiling_options", {}) or {}

    return ProfilingConfig(
        x_start=_get_float(params, "x_start", 0.0),
        z_start=_get_float(params, "z_start", 0.0),
        doc=_get_float(cutting, "doc", 0.5),
        retract=_get_float(cutting, "retract", 1.0),
        feed_rate=_get_float(cutting, "feed_rate", 0.1),
        stock_x=_get_float(options, "stock_to_leave_x", 0.0),
        stock_z=_get_float(options, "stock_to_leave_z", 0.0),
        finish_passes=max(1, int(options.get("finish_passes", 1) or 1)),
        spring_passes=max(0, int(options.get("finish_spring_passes", 0) or 0)),
        strategy=str(options.get("strategy", "rough")).lower(),
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


def _resolve_profile(op):
    resolved = op.get("_resolved_profile") or {}
    primitives = resolved.get("profile_primitives", []) or []
    segments = build_profile_segments(primitives)
    path = build_render_path(segments)
    return segments, path


def generate_custom_profiling_gcode(op):
    config = _parse_config(op)
    spindle = op.get("spindle_parameters", {}) or {}
    segments, render_path = _resolve_profile(op)

    lines = []
    lines.extend(build_spindle_lines(spindle, config.optional_prefix, _get_float))
    lines.append(f"{config.optional_prefix}G95 F{config.feed_rate}")

    if not segments or not isinstance(segments[0], StartPoint):
        lines.append("( ERROR: Custom Profiling -- no valid profile found )")
        return lines

    profile_start = segments[0]
    x_profile_start = profile_start.x
    x_min, _ = profile_extents(segments)
    x_safe = config.x_start + config.retract

    if config.strategy == "rough":
        rough_passes = plan_roughing_passes(
            config=config,
            x_min=x_min,
            x_profile_start=x_profile_start,
            find_deepest_z_at_x=lambda x_target, x_shift, z_shift: find_deepest_z_at_x_path(
                render_path, x_target, x_shift, z_shift
            ),
        )
        _, _, passes, contour_pass, contour_entry_x = rough_passes
        emit_roughing_gcode(lines, config.optional_prefix, config, x_safe, passes)
        emit_contour_pass_gcode(lines, config.optional_prefix, config, x_safe, render_path, contour_pass, contour_entry_x)
        return lines

    finish_passes = plan_finish_passes(config)
    emit_finish_gcode(lines, config.optional_prefix, config, x_safe, x_profile_start, render_path, finish_passes)
    return lines
