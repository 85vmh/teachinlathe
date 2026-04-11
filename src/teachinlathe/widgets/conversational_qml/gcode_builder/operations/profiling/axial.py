"""Axial roughing passes for profile roughing (OD and ID).

Strategy: step in X one doc at a time, cut axially in Z at each diameter.
Both OD and ID share the same pass-planning logic; only the approach/retract
sequence differs because:

  OD (x_direction=-1): x_safe is outside (large X); the tool approaches
      from x_safe directly to cut_x — no risk of crashing into uncut material.

  ID (x_direction=+1): x_safe is toward bore centre (small X); a careful
      3-move approach (clear Z → approach X from inside → diagonal to z_start)
      is required to avoid colliding with the bore wall.

Profile queries always use (ctx.geo_x_shift, ctx.geo_z_shift) so every pass
targets the offset profile (original + stock translation) consistently.
"""

import math

from ...config import fmt
from ..custom_cam.custom_profiling_geometry import find_deepest_z_at_x_path
from .context import RoughingContext


def emit_axial_roughing(lines: list, ctx: RoughingContext, path: list) -> None:
    pfx = ctx.optional_prefix

    if not ctx.has_radial_range():
        lines.append("( ProfileRoughing axial: nothing to cut – check x_start vs profile )")
        return

    pass_count = max(1, math.ceil(abs(ctx.x_limit - ctx.x_start) / ctx.doc))
    passes = []
    for n in range(pass_count):
        raw_x = ctx.x_start + ctx.x_direction * (n + 1) * ctx.doc
        cut_x = ctx.clamp_cut_x(raw_x)
        cut_z = find_deepest_z_at_x_path(path, cut_x, ctx.geo_x_shift, ctx.geo_z_shift)
        if cut_z > ctx.z_start + 1e-9:
            continue
        passes.append((cut_x, cut_z))

    if not passes:
        lines.append("( ProfileRoughing axial: no valid passes after geometry checks )")
        return

    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(ctx.z_start)}")

    for cut_x, cut_z in passes:
        # Lead-in/lead-out move away from the cut in X and toward z_start in Z.
        entry_x = cut_x - ctx.x_direction * ctx.retract
        entry_z = ctx.z_start + ctx.retract
        exit_x = cut_x - ctx.x_direction * ctx.retract
        exit_z = cut_z + ctx.retract

        if ctx.x_direction < 0:
            # OD: approach from outside, then lead in diagonally to the cut start.
            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
            lines.append(f"{pfx}G0 X{fmt(entry_x)}")
            lines.append(f"{pfx}G0 X{fmt(cut_x)} Z{fmt(ctx.z_start)}")
            lines.append(f"{pfx}G1 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")
        else:
            # ID: 3-move approach to avoid crashing into bore wall.
            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
            lines.append(f"{pfx}G0 X{fmt(entry_x)}")
            lines.append(f"{pfx}G0 X{fmt(cut_x)} Z{fmt(ctx.z_start)}")
            lines.append(f"{pfx}G1 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")

    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(ctx.z_start)}")
    lines.append("")
