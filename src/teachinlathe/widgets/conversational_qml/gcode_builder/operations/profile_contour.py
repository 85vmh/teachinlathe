from teachinlathe.conversational.data_types import ProfileContourConfig, ProfilingType

from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float
from .profiling.geometry import (
    StartPoint,
    build_shifted_path_clipped_to_x_boundary,
    build_profile_segments,
    build_render_path,
)
from .profiling.contour import emit_roughing_contour_pass
from .profiling.context import make_id_context, make_od_context


def parse_profile_contour_config(op) -> ProfileContourConfig:
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    strategy = op.get("profile_contour_strategy", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}

    resolved = op.get("_resolved_profile") or {}
    if resolved:
        try:
            profiling_type = ProfilingType(str(resolved.get("profile_type", "od")).lower())
        except ValueError:
            profiling_type = ProfilingType.OD
    else:
        try:
            profiling_type = ProfilingType(str(strategy.get("profiling_type", "od")).lower())
        except ValueError:
            profiling_type = ProfilingType.OD

    stock_enabled = bool(op.get("stock_to_leave_enabled", False))

    return ProfileContourConfig(
        x_start=get_float(params, "x_start", 0.0),
        z_start=get_float(params, "z_start", 0.0),
        doc=get_float(cutting, "doc", 0.5),
        retract=get_float(cutting, "retract", 1.0),
        feed_rate=get_float(cutting, "feed_rate", 0.1),
        stock_x=get_float(stock, "radial", 0.0) if stock_enabled else 0.0,
        stock_z=get_float(stock, "axial", 0.0) if stock_enabled else 0.0,
        stock_enabled=stock_enabled,
        profiling_type=profiling_type,
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


def _resolve_profile(op):
    resolved = op.get("_resolved_profile") or {}
    primitives = resolved.get("profile_primitives", []) or []
    profile_type = str(resolved.get("profile_type", "od")).lower()
    segments = build_profile_segments(primitives)
    path = build_render_path(segments, profile_type)
    return segments, path


def _profile_extents(segments):
    x_vals = []
    for seg in segments:
        if isinstance(seg, StartPoint):
            x_vals.append(seg.x)
        else:
            x_vals.append(seg.end_x)
    x_min = min(x_vals) if x_vals else 0.0
    x_max = max(x_vals) if x_vals else 0.0
    return x_min, x_max


def generate_profile_contour_gcode(op):
    if hasattr(op, "to_dict"):
        op = op.to_dict()

    config = parse_profile_contour_config(op)
    spindle = op.get("spindle_parameters", {}) or {}
    segments, path = _resolve_profile(op)

    lines = []
    lines.extend(build_spindle_gcode(spindle, config.optional_prefix))
    lines.append(f"{config.optional_prefix}G95 F{config.feed_rate}")

    if not segments or not isinstance(segments[0], StartPoint):
        lines.append("( ERROR: Profile Contour -- no valid profile found )")
        return lines

    x_min, x_max = _profile_extents(segments)

    if config.profiling_type == ProfilingType.OD:
        ctx = make_od_context(config, x_min)
        keep_side = "lte"
    else:
        ctx = make_id_context(config, x_max)
        keep_side = "gte"

    contour_path = build_shifted_path_clipped_to_x_boundary(
        path,
        ctx.geo_x_shift,
        ctx.geo_z_shift,
        ctx.x_start,
        keep_side,
    )

    if not contour_path or not isinstance(contour_path[0], StartPoint):
        lines.append("( ERROR: Profile Contour -- no valid contour profile after stock/clipping )")
        return lines

    emit_roughing_contour_pass(lines, ctx, contour_path)
    return lines
