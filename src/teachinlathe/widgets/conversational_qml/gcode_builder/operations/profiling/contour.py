"""Contour pass for profile roughing (OD and ID).

The supplied path is already offset by stock-to-leave and clipped to X Start.
"""

from ...config import fmt
from .context import RoughingContext
from .toolpath import emit_toolpath


def emit_roughing_contour_pass(
    lines: list,
    ctx: RoughingContext,
    path: list,
) -> None:
    pfx = ctx.optional_prefix
    if not path:
        return
    entry_x = path[0].x

    lines.append(f"( Contour with StockToLeave[radial={fmt(ctx.stock_x)} axial={fmt(ctx.stock_z)}] )")
    # lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(ctx.z_start)}")
    lines.append(f"{pfx}G0 X{fmt(entry_x)} Z{fmt(ctx.z_start)}")
    emit_toolpath(lines, pfx, path)
    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)}")
    lines.append(f"{pfx}G0 Z{fmt(ctx.z_start)}")
    lines.append("")
