"""G-code generator for Profile Roughing (OD and ID).

Dispatches to the shared profiling/ strategies based on ProfilingType (OD/ID)
and PassType (AXIAL / RADIAL / DIAGONAL_*).
"""

from teachinlathe.conversational.data_types import PassType, ProfileRoughingConfig, ProfilingType

from ..helpers.m1 import emit_m1_block
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float
from .profiling.geometry import (
    StartPoint,
    build_shifted_path_clipped_to_x_boundary,
    build_profile_segments,
    build_render_path,
)
from .profiling.axial import emit_axial_roughing
from .profiling.contour import emit_roughing_contour_pass
from .profiling.context import make_id_context, make_od_context
from .profiling.diagonal import emit_diagonal_roughing
from .profiling.radial import emit_radial_roughing


def parse_profile_roughing_config(op) -> ProfileRoughingConfig:
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    strategy = op.get("profile_roughing_strategy", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}

    try:
        profiling_type = ProfilingType(str(strategy.get("profiling_type", "od")).lower())
    except ValueError:
        profiling_type = ProfilingType.OD

    try:
        pass_type = PassType(str(strategy.get("pass_type", "axial")).lower())
    except ValueError:
        pass_type = PassType.AXIAL

    return ProfileRoughingConfig(
        x_start=get_float(params, "x_start", 0.0),
        z_start=get_float(params, "z_start", 0.0),
        doc=get_float(cutting, "doc", 0.5),
        retract=get_float(cutting, "retract", 1.0),
        feed_rate=get_float(cutting, "feed_rate", 0.1),
        stock_x=get_float(stock, "radial", 0.0),
        stock_z=get_float(stock, "axial", 0.0),
        profiling_type=profiling_type,
        pass_type=pass_type,
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


def _resolve_profile(op):
    resolved = op.get("_resolved_profile") or {}
    primitives = resolved.get("profile_primitives", []) or []
    segments = build_profile_segments(primitives)
    path = build_render_path(segments)
    return segments, path


def _profile_extents(segments):
    """Return (x_min, x_max, z_min) across all segment endpoints."""
    x_vals, z_vals = [], []
    for seg in segments:
        if isinstance(seg, StartPoint):
            x_vals.append(seg.x)
            z_vals.append(seg.z)
        else:
            x_vals.append(seg.end_x)
            z_vals.append(seg.end_z)
    x_min = min(x_vals) if x_vals else 0.0
    x_max = max(x_vals) if x_vals else 0.0
    z_min = min(z_vals) if z_vals else 0.0
    return x_min, x_max, z_min


def _path_z_min(path):
    z_vals = []
    for element in path:
        if isinstance(element, StartPoint):
            z_vals.append(element.z)
        else:
            z_vals.append(element.end_z)
    return min(z_vals) if z_vals else 0.0


def generate_profile_roughing_gcode(op):
    if hasattr(op, "to_dict"):
        op = op.to_dict()

    config = parse_profile_roughing_config(op)
    spindle = op.get("spindle_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}
    segments, path = _resolve_profile(op)

    lines = []
    lines.extend(build_spindle_gcode(spindle, config.optional_prefix))
    lines.append(f"{config.optional_prefix}G95 F{config.feed_rate}")

    if not segments or not isinstance(segments[0], StartPoint):
        lines.append("( ERROR: Profile Roughing -- no valid profile found )")
        return lines

    x_min, x_max, _ = _profile_extents(segments)

    if config.profiling_type == ProfilingType.OD:
        ctx = make_od_context(config, x_min)
        keep_side = "lte"
    else:
        ctx = make_id_context(config, x_max)
        keep_side = "gte"

    roughing_path = build_shifted_path_clipped_to_x_boundary(
        path,
        ctx.geo_x_shift,
        ctx.geo_z_shift,
        ctx.x_start,
        keep_side,
    )

    if not roughing_path or not isinstance(roughing_path[0], StartPoint):
        lines.append("( ERROR: Profile Roughing -- no valid roughing profile after stock/clipping )")
        return lines

    # z_cut_deepest is used by radial and diagonal strategies.
    z_cut_deepest = _path_z_min(roughing_path)

    if config.pass_type == PassType.AXIAL:
        emit_axial_roughing(lines, ctx, roughing_path)

    elif config.pass_type == PassType.RADIAL:
        emit_radial_roughing(lines, ctx, roughing_path, z_cut_deepest)

    elif config.pass_type in (PassType.DIAGONAL_INTERIOR, PassType.DIAGONAL_EXTERIOR):
        emit_diagonal_roughing(lines, ctx, roughing_path, ctx.x_limit, z_cut_deepest, config.pass_type)

    emit_roughing_contour_pass(lines, ctx, roughing_path)

    lines.extend(emit_m1_block(m1_params, config.optional_prefix))
    return lines
