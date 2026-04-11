"""Contour pass for profile roughing (OD and ID).

The contour pass follows the offset profile (original profile translated by
geo_x_shift / geo_z_shift) as the final step of roughing, leaving a uniform
stock layer ready for finishing passes.

Entry point
-----------
  OD: entry_x = x_profile_start + stock_x  (offset outward)
  ID: entry_x = x_profile_start - stock_x  (offset inward toward bore centre)

Both collapse to:  entry_x = x_profile_start + geo_x_shift
"""

from ...config import fmt
from ..custom_cam.custom_profiling_planner import emit_toolpath
from .context import RoughingContext


def emit_roughing_contour_pass(
    lines: list,
    ctx: RoughingContext,
    path: list,
    x_profile_start: float,
) -> None:
    pfx = ctx.optional_prefix
    entry_x = x_profile_start + ctx.geo_x_shift

    lines.append(f"( contour pass: stock_x={fmt(ctx.stock_x)} stock_z={fmt(ctx.stock_z)} )")
    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(ctx.z_start)}")
    lines.append(f"{pfx}G0 X{fmt(entry_x)}")
    emit_toolpath(lines, pfx, path, ctx.geo_x_shift, ctx.geo_z_shift)
    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)}")
    lines.append(f"{pfx}G0 Z{fmt(ctx.z_start)}")
    lines.append("")
