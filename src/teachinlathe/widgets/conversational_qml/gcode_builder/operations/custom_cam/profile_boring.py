"""CAM-style explicit G-code generator for Profile Boring.

Profile Boring is like Custom Profiling but operates on the bore interior.
Passes go from XStart (current bore diameter) outward toward the profile,
and retract is toward X- (bore centre).

Roughing strategies
-------------------
axial            – step in X, cut axial in Z at each diameter
radial           – step in Z, cut radial in X at each depth
diagonal           – step in Z, cut at 45° (ΔX = ΔZ)
offset             – translate profile by (-n*doc, +n*doc) per pass
equidistant_offset – geometrically offset profile by perpendicular n*doc per pass
"""

from teachinlathe.conversational.data_types import (
    BoringConfig,
    CutToward,
    RoughingMovement,
    Strategy,
)

from ...config import fmt
from ...helpers.m1 import emit_m1_block
from ...helpers.spindle import build_spindle_gcode
from ...helpers.utils import get_float
from .boring_strategies.axial import emit_axial_roughing
from .boring_strategies.diagonal import emit_diagonal_roughing
from .boring_strategies.equidistant_offset import emit_equidistant_offset_roughing
from .boring_strategies.offset import emit_offset_roughing
from .boring_strategies.radial import emit_radial_roughing
from .custom_profiling_geometry import StartPoint, build_profile_segments, build_render_path
from .custom_profiling_planner import emit_toolpath


def _parse_config(op) -> BoringConfig:
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    options = op.get("profiling_options", {}) or {}
    strat = op.get("roughing_strategy", {}) or {}

    try:
        strategy = Strategy(str(options.get("strategy", "rough")).lower())
    except ValueError:
        strategy = Strategy.ROUGH

    try:
        movement = RoughingMovement(str(strat.get("movement", "axial")).lower())
    except ValueError:
        movement = RoughingMovement.AXIALLY

    try:
        cut_toward = CutToward(str(strat.get("cut_toward", "interior")).lower())
    except ValueError:
        cut_toward = CutToward.INTERIOR

    return BoringConfig(
        x_start=get_float(params, "x_start", 0.0),
        z_start=get_float(params, "z_start", 0.0),
        doc=get_float(cutting, "doc", 0.5),
        retract=abs(get_float(cutting, "retract", 1.0)),
        feed_rate=get_float(cutting, "feed_rate", 0.1),
        stock_x=get_float(options, "radial", 0.0),
        stock_z=get_float(options, "axial", 0.0),
        finish_passes=max(1, int(options.get("finish_passes", 1) or 1)),
        spring_passes=max(0, int(options.get("finish_spring_passes", 0) or 0)),
        strategy=strategy,
        movement=movement,
        cut_toward=cut_toward,
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


def _resolve_profile(op):
    resolved = op.get("_resolved_profile") or {}
    primitives = resolved.get("profile_primitives", []) or []
    segments = build_profile_segments(primitives)
    path = build_render_path(segments)
    return segments, path


def _boring_extents(segments):
    """Return (x_max, z_min) of the profile for boring pass planning."""
    x_vals, z_vals = [], []
    for seg in segments:
        if isinstance(seg, StartPoint):
            x_vals.append(seg.x)
            z_vals.append(seg.z)
        else:
            x_vals.append(seg.end_x)
            z_vals.append(seg.end_z)
    return (max(x_vals) if x_vals else 0.0), (min(z_vals) if z_vals else 0.0)


def _emit_boring_contour_pass(lines, config: BoringConfig, path, x_safe, x_profile_start):
    pfx = config.optional_prefix
    entry_x = x_profile_start - config.stock_x
    lines.append(f"( boring contour pass: stock_x={fmt(config.stock_x)} stock_z={fmt(config.stock_z)} )")
    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(config.z_start)}")
    lines.append(f"{pfx}G0 X{fmt(entry_x)}")
    emit_toolpath(lines, pfx, path, -config.stock_x, config.stock_z)
    lines.append(f"{pfx}G0 X{fmt(x_safe)}")
    lines.append(f"{pfx}G0 Z{fmt(config.z_start)}")
    lines.append("")


def _emit_boring_finish_gcode(lines, config: BoringConfig, path, x_safe, x_profile_start):
    pfx = config.optional_prefix
    passes = []
    for i in range(1, config.finish_passes + 1):
        factor = (config.finish_passes - i) / config.finish_passes
        passes.append((-config.stock_x * factor, config.stock_z * factor))
    for _ in range(config.spring_passes):
        passes.append((0.0, 0.0))

    for offset_x, offset_z in passes:
        entry_x = x_profile_start + offset_x
        lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(config.z_start)}")
        lines.append(f"{pfx}G0 X{fmt(entry_x)}")
        emit_toolpath(lines, pfx, path, offset_x, offset_z)
    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(config.z_start)}")


_ROUGHING_STRATEGY = {
    RoughingMovement.AXIALLY: lambda lines, config, path, x_safe, x_cut_max, z_cut_deepest:
        emit_axial_roughing(lines, config, path, x_safe, x_cut_max),
    RoughingMovement.RADIALLY: lambda lines, config, path, x_safe, x_cut_max, z_cut_deepest:
        emit_radial_roughing(lines, config, path, x_safe, z_cut_deepest),
    RoughingMovement.DIAGONAL: emit_diagonal_roughing,
    RoughingMovement.OFFSET: emit_offset_roughing,
    RoughingMovement.EQUIDISTANT_OFFSET: emit_equidistant_offset_roughing,
}


def generate_profile_boring_gcode(op):
    config = _parse_config(op)
    spindle = op.get("spindle_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}
    segments, render_path = _resolve_profile(op)

    lines = []
    lines.extend(build_spindle_gcode(spindle, config.optional_prefix))
    lines.append(f"{config.optional_prefix}G95 F{config.feed_rate}")

    if not segments or not isinstance(segments[0], StartPoint):
        lines.append("( ERROR: Profile Boring -- no valid profile found )")
        return lines

    x_profile_start = segments[0].x
    x_max, z_min = _boring_extents(segments)
    x_safe = config.x_start - config.retract
    x_cut_max = x_max - config.stock_x
    z_cut_deepest = z_min + config.stock_z

    if config.strategy == Strategy.ROUGH:
        roughing_fn = _ROUGHING_STRATEGY.get(config.movement, emit_diagonal_roughing)
        roughing_fn(lines, config, render_path, x_safe, x_cut_max, z_cut_deepest)
        _emit_boring_contour_pass(lines, config, render_path, x_safe, x_profile_start)
        lines.extend(emit_m1_block(m1_params, config.optional_prefix))
        return lines

    lines.extend(emit_m1_block(m1_params, config.optional_prefix))
    _emit_boring_finish_gcode(lines, config, render_path, x_safe, x_profile_start)
    return lines
