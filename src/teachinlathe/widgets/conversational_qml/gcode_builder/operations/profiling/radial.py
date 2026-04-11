"""Radial roughing passes for profile roughing (OD and ID).

Strategy: step in Z one doc at a time, cut radially in X at each depth.

Both OD and ID share the same pass-planning logic.  The profile X query uses
BOTH geo_x_shift and geo_z_shift so the radial cut target is consistent with
the offset profile used by axial passes and the contour pass.

  OD (x_direction=-1): tool sits at x_safe (large X / outside).  At each
      depth the tool feeds INWARD (decreasing X) to the offset-profile
      boundary, retracts outward by retract, then returns to x_safe.

  ID (x_direction=+1): tool sits at x_safe (small X / bore centre).  At each
      depth the tool moves to x_start (bore entry), feeds OUTWARD (increasing
      X) to the offset-profile boundary, retracts inward by retract, then
      returns to x_safe.
"""

import math

from ...config import fmt
from ..custom_cam.custom_profiling_geometry import find_profile_x_at_z
from .context import RoughingContext


def emit_radial_roughing(lines: list, ctx: RoughingContext, path: list, z_cut_deepest: float) -> None:
    pfx = ctx.optional_prefix

    if z_cut_deepest >= ctx.z_start - 1e-9:
        lines.append("( ProfileRoughing radial: nothing to cut – check z_start vs profile )")
        return

    pass_count = max(1, math.ceil((ctx.z_start - z_cut_deepest) / ctx.doc))

    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(ctx.z_start)}")

    for n in range(pass_count):
        cut_z = ctx.z_start - (n + 1) * ctx.doc
        if cut_z < z_cut_deepest:
            cut_z = z_cut_deepest

        # Query the offset profile at this depth.
        # geo_z_shift is applied here (fix vs. old boring radial which used z_shift=0).
        cut_x = find_profile_x_at_z(path, cut_z, ctx.geo_x_shift, ctx.geo_z_shift)

        if ctx.x_direction < 0:
            # OD: tool approaches from x_safe (large X), cuts inward to cut_x.
            # cut_x is the offset-profile boundary (profile_x + stock_x).
            if cut_x >= ctx.x_start - 1e-9:
                continue  # offset profile flush with x_start, nothing to remove
            entry_x = ctx.x_start - ctx.x_direction * ctx.retract
            entry_z = cut_z + ctx.retract
            exit_x = cut_x - ctx.x_direction * ctx.retract
            exit_z = cut_z + ctx.retract
            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
            lines.append(f"{pfx}G0 X{fmt(entry_x)}")
            lines.append(f"{pfx}G0 X{fmt(ctx.x_start)} Z{fmt(cut_z)}")
            lines.append(f"{pfx}G1 X{fmt(cut_x)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")
            lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)}")
        else:
            # ID: tool moves to x_start (bore entry), cuts outward to cut_x.
            # cut_x is the offset-profile boundary (profile_x - stock_x).
            if cut_x <= ctx.x_start + 1e-9:
                continue  # offset profile flush with x_start at this depth
            entry_x = ctx.x_start - ctx.x_direction * ctx.retract
            entry_z = cut_z + ctx.retract
            exit_x = cut_x - ctx.x_direction * ctx.retract
            exit_z = cut_z + ctx.retract
            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
            lines.append(f"{pfx}G0 X{fmt(entry_x)}")
            lines.append(f"{pfx}G0 X{fmt(ctx.x_start)} Z{fmt(cut_z)}")
            lines.append(f"{pfx}G1 X{fmt(cut_x)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")
            lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)}")

    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(ctx.z_start)}")
    lines.append("")
