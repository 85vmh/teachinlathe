"""Radial roughing passes for profile roughing (OD and ID).

Strategy: step in Z one doc at a time, cut radially in X at each depth.

Both OD and ID share the same pass-planning logic. The supplied path is already
offset by stock-to-leave and clipped to X Start, so all strategies use the same
working profile.

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
from ...helpers.m1 import inspect_position_int
from .geometry import find_profile_x_at_z
from .context import RoughingContext


def _include_m1(m1_params) -> bool:
    if not m1_params:
        return False
    if hasattr(m1_params, "include_m1"):
        return bool(m1_params.include_m1)
    return bool(m1_params.get("include_m1", False))


def _emit_m1_handling_at_safe_diameter(
    lines: list,
    prefix: str,
    m1_params,
    x_return: float,
    z_return: float,
    spindle_direction: int,
) -> None:
    lines.append(
        f"{prefix}o<m1_handling> call "
        f"[{inspect_position_int(m1_params)}] "
        f"[{fmt(x_return)}] "
        f"[{fmt(z_return)}] "
        f"[{spindle_direction}]"
    )


def emit_radial_roughing(
    lines: list,
    context: RoughingContext,
    path: list,
    z_cut_deepest: float,
    m1_params=None,
    spindle_direction: int = 0,
) -> None:
    prefix = context.optional_prefix
    include_m1 = _include_m1(m1_params)

    if z_cut_deepest >= context.z_start - 1e-9:
        lines.append("( ProfileRoughing radial: nothing to cut – check z_start vs profile )")
        return

    pass_count = max(1, math.ceil((context.z_start - z_cut_deepest) / context.doc))

    lines.append(f"{prefix}G0 X{fmt(context.x_safe)} Z{fmt(context.z_start)}")

    for n in range(pass_count):
        cut_z = context.z_start - (n + 1) * context.doc
        if cut_z < z_cut_deepest:
            cut_z = z_cut_deepest
        if abs(cut_z - z_cut_deepest) < 1e-9:
            continue  # at contour depth; contour pass handles this

        cut_x = find_profile_x_at_z(path, cut_z)

        if context.x_direction < 0:
            # OD: tool approaches from x_safe (large X), cuts inward to cut_x.
            # cut_x is the offset-profile boundary (profile_x + stock_x).
            if cut_x >= context.x_start - 1e-9:
                continue  # offset profile flush with x_start, nothing to remove
            entry_x = context.x_start - context.x_direction * context.retract * 2
            entry_z = cut_z + context.retract
            exit_x = cut_x - context.x_direction * context.retract * 2
            exit_z = cut_z + context.retract
            lines.append(f"{prefix}G0 Z{fmt(entry_z)}")
            lines.append(f"{prefix}G0 X{fmt(entry_x)}")
            lines.append(f"{prefix}G0 X{fmt(context.x_start)} Z{fmt(cut_z)}")
            lines.append(f"{prefix}G1 X{fmt(cut_x)}")
            lines.append(f"{prefix}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")
            lines.append(f"{prefix}G0 X{fmt(context.x_safe)}")
            lines.append("(End of OD pass)")
            if include_m1:
                _emit_m1_handling_at_safe_diameter(
                    lines, prefix, m1_params, context.x_safe, exit_z, spindle_direction
                )
                lines.append("")
        else:
            # ID: tool moves to x_start (bore entry), cuts outward to cut_x.
            # cut_x is the offset-profile boundary (profile_x - stock_x).
            if cut_x <= context.x_start + 1e-9:
                continue  # offset profile flush with x_start at this depth
            entry_x = context.x_start - context.x_direction * context.retract * 2
            entry_z = cut_z + context.retract
            exit_x = cut_x - context.x_direction * context.retract * 2
            exit_z = cut_z + context.retract
            lines.append(f"{prefix}G0 Z{fmt(entry_z)}")
            lines.append(f"{prefix}G0 X{fmt(entry_x)}")
            lines.append(f"{prefix}G0 X{fmt(context.x_start)} Z{fmt(cut_z)}")
            lines.append(f"{prefix}G1 X{fmt(cut_x)}")
            lines.append(f"{prefix}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")
            lines.append(f"{prefix}G0 X{fmt(context.x_safe)}")
            lines.append("(End of ID pass)")
            if include_m1:
                _emit_m1_handling_at_safe_diameter(
                    lines, prefix, m1_params, context.x_safe, exit_z, spindle_direction
                )
                lines.append("")

    lines.append(f"{prefix}G0 X{fmt(context.x_safe)} Z{fmt(context.z_start)}")
    lines.append("")
