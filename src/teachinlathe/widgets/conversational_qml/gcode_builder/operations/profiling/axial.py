"""Axial roughing passes for profile roughing (OD and ID).

Strategy: step in X one doc at a time, cut axially in Z at each diameter.
Both OD and ID share the same pass-planning logic; only the approach/retract
sequence differs because:

  OD (x_direction=-1): x_safe is outside (large X); the tool approaches
      from x_safe directly to cut_x — no risk of crashing into uncut material.

  ID (x_direction=+1): x_safe is toward bore centre (small X); a careful
      3-move approach (clear Z → approach X from inside → diagonal to z_start)
      is required to avoid colliding with the bore wall.

Profile queries use the roughing path supplied by ProfileRoughing. That path is
already offset by stock-to-leave and clipped to X Start.
"""

import math

from ...config import fmt
from ...helpers.m1 import inspect_position_int
from .geometry import find_deepest_z_at_x_path
from .context import RoughingContext


def _include_m1(m1_params) -> bool:
    if not m1_params:
        return False
    if hasattr(m1_params, "include_m1"):
        return bool(m1_params.include_m1)
    return bool(m1_params.get("include_m1", False))


def emit_axial_roughing(
    lines: list,
    context: RoughingContext,
    path: list,
    m1_params=None,
    spindle_direction: int = 0,
) -> None:
    prefix = context.optional_prefix
    include_m1 = _include_m1(m1_params)

    if not context.has_radial_range():
        lines.append("( ProfileRoughing axial: nothing to cut – check x_start vs profile )")
        return

    pass_count = max(1, math.ceil(abs(context.x_limit - context.x_start) / (context.doc * 2)))
    passes = []
    for n in range(pass_count):
        raw_x = context.x_start + context.x_direction * (n + 1) * context.doc * 2
        cut_x = context.clamp_cut_x(raw_x)
        if abs(cut_x - context.x_limit) < 1e-9:
            continue  # at contour boundary; contour pass handles this
        cut_z = find_deepest_z_at_x_path(path, cut_x)
        if cut_z > context.z_start + 1e-9:
            continue
        passes.append((cut_x, cut_z))

    if not passes:
        lines.append("( ProfileRoughing axial: no valid passes after geometry checks )")
        return

    lines.append(f"{prefix}G0 X{fmt(context.x_safe)} Z{fmt(context.z_start)}")

    for cut_x, cut_z in passes:
        # Lead-in/lead-out move away from the cut in X and toward z_start in Z.
        entry_x = cut_x - context.x_direction * context.retract * 2
        entry_z = context.z_start + context.retract
        exit_x = cut_x - context.x_direction * context.retract * 2
        exit_z = cut_z + context.retract

        if context.x_direction < 0:
            # OD: approach from outside, then lead in diagonally to the cut start.
            lines.append(f"{prefix}G0 Z{fmt(entry_z)}")
            lines.append(f"{prefix}G0 X{fmt(entry_x)}")
            lines.append(f"{prefix}G0 X{fmt(cut_x)} Z{fmt(context.z_start)}")
            lines.append(f"{prefix}G1 Z{fmt(cut_z)}")
            lines.append(f"{prefix}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")
            lines.append(f"{prefix}G0 Z{fmt(entry_z)}")
            lines.append("(End of OD pass)")
            if include_m1:
                lines.append(
                    f"{prefix}o<m1_handling> call "
                    f"[{inspect_position_int(m1_params)}] "
                    f"[{fmt(exit_x)}] "
                    f"[{fmt(entry_z)}] "
                    f"[{spindle_direction}]"
                )
                lines.append("")
        else:
            # ID: 3-move approach to avoid crashing into bore wall.
            lines.append(f"{prefix}G0 Z{fmt(entry_z)}")
            lines.append(f"{prefix}G0 X{fmt(entry_x)}")
            lines.append(f"{prefix}G0 X{fmt(cut_x)} Z{fmt(context.z_start)}")
            lines.append(f"{prefix}G1 Z{fmt(cut_z)}")
            lines.append(f"{prefix}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")
            lines.append(f"{prefix}G0 Z{fmt(entry_z)}")
            lines.append("(End of ID pass)")
            if include_m1:
                lines.append(
                    f"{prefix}o<m1_handling> call "
                    f"[{inspect_position_int(m1_params)}] "
                    f"[{fmt(exit_x)}] "
                    f"[{fmt(entry_z)}] "
                    f"[{spindle_direction}]"
                )
                lines.append("")

    lines.append("")
