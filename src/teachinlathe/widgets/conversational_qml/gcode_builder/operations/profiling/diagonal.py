"""Diagonal (45°) roughing passes for profile roughing (OD and ID).

Strategy: sweep a family of parallel 45° lines across the material region.
At step n the nth diagonal line covers both a radial distance and an axial
distance of n*doc from the x_start / z_start corner.

Corner definitions (same for OD and ID)
----------------------------------------
corner_A  — the x_start side at depth:   (x_start,                  z_start - step)
corner_B  — the profile side at face:    (x_start + x_direction*step, z_start      )

x_direction = -1 (OD) means corner_B moves toward smaller X (inward).
x_direction = +1 (ID) means corner_B moves toward larger  X (bore wall).

Profile clipping
----------------
The supplied path is already offset by stock-to-leave and clipped to X Start.
When corner_B would pass x_limit:
    ray direction = (-x_direction, -1)   → from corner_B toward the roughing profile
When corner_A would pass z_cut_deepest:
    ray direction = ( x_direction, +1)   → from corner_A toward the roughing profile

Cut direction
-------------
DIAGONAL_EXTERIOR cuts from X- to X+.
DIAGONAL_INTERIOR cuts from X+ to X-.
The retract path is emitted on a parallel diagonal line offset from the cutting
line by retract.
"""

import math

from teachinlathe.conversational.data_types import PassType

from ...config import fmt
from .geometry import find_45deg_profile_intersection
from .context import RoughingContext


def emit_diagonal_roughing(
    lines: list,
    ctx: RoughingContext,
    path: list,
    x_cut_limit: float,
    z_cut_deepest: float,
    pass_type: PassType,
) -> None:
    pfx = ctx.optional_prefix

    max_span_x = abs(x_cut_limit - ctx.x_start)
    max_span_z = abs(ctx.z_start - z_cut_deepest)
    max_span = max(max_span_x, max_span_z)
    if max_span <= 1e-9:
        lines.append("( ProfileRoughing diagonal: nothing to cut – check x_start/profile/depth )")
        return

    pass_count = max(1, math.ceil(max_span / ctx.doc))
    start_z_clear = ctx.z_start + ctx.retract
    last_points = None

    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(start_z_clear)}")

    for n in range(pass_count):
        step = min((n + 1) * ctx.doc, max_span)

        # ---- corner B: profile side at z_start ----
        corner_b_x = ctx.x_start + ctx.x_direction * step
        corner_b_z = ctx.z_start

        if ctx.x_direction * (corner_b_x - x_cut_limit) <= 0:
            # within radial limit — use geometric corner
            start_x, start_z = corner_b_x, corner_b_z
        else:
            # clipped by profile: ray from corner_B in direction (-x_dir, -1)
            hit = find_45deg_profile_intersection(
                path, corner_b_x, corner_b_z,
                float(-ctx.x_direction), -1.0,
            )
            if hit is None:
                continue
            start_x, start_z = hit

        # ---- corner A: x_start side at depth ----
        corner_a_x = ctx.x_start
        corner_a_z = ctx.z_start - step

        if corner_a_z >= z_cut_deepest - 1e-9:
            # within axial limit — use geometric corner
            end_x, end_z = corner_a_x, corner_a_z
        else:
            # clipped by profile: ray from corner_A in direction (x_dir, +1)
            hit = find_45deg_profile_intersection(
                path, corner_a_x, corner_a_z,
                float(ctx.x_direction), 1.0,
            )
            if hit is None:
                continue
            end_x, end_z = hit

        # sanity checks
        if start_z > ctx.z_start + 1e-9 or end_z > ctx.z_start + 1e-9:
            continue

        points = (round(start_x, 9), round(start_z, 9), round(end_x, 9), round(end_z, 9))
        if points == last_points:
            continue
        last_points = points

        if pass_type == PassType.DIAGONAL_EXTERIOR:
            cut_start_x, cut_start_z = (end_x, end_z) if end_x <= start_x else (start_x, start_z)
            cut_end_x, cut_end_z = (start_x, start_z) if end_x <= start_x else (end_x, end_z)
        else:
            cut_start_x, cut_start_z = (end_x, end_z) if end_x >= start_x else (start_x, start_z)
            cut_end_x, cut_end_z = (start_x, start_z) if end_x >= start_x else (end_x, end_z)

        dx = cut_end_x - cut_start_x
        dz = cut_end_z - cut_start_z
        length = math.hypot(dx, dz)
        if length <= 1e-9:
            continue

        normal_x = -dz / length
        normal_z = dx / length
        safe_mid_x = ctx.x_safe
        safe_mid_z = start_z_clear
        mid_x = (cut_start_x + cut_end_x) * 0.5
        mid_z = (cut_start_z + cut_end_z) * 0.5

        if (safe_mid_x - mid_x) * normal_x + (safe_mid_z - mid_z) * normal_z < 0:
            normal_x = -normal_x
            normal_z = -normal_z

        offset_x = normal_x * ctx.retract
        offset_z = normal_z * ctx.retract
        entry_x = cut_start_x + offset_x
        entry_z = cut_start_z + offset_z
        exit_x = cut_end_x + offset_x
        exit_z = cut_end_z + offset_z

        lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
        lines.append(f"{pfx}G0 X{fmt(entry_x)}")
        lines.append(f"{pfx}G0 X{fmt(cut_start_x)} Z{fmt(cut_start_z)}")
        lines.append(f"{pfx}G1 X{fmt(cut_end_x)} Z{fmt(cut_end_z)}")
        lines.append(f"{pfx}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")
        lines.append(f"{pfx}G0 X{fmt(entry_x)} Z{fmt(entry_z)}")
        lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(start_z_clear)}")

    lines.append(f"{pfx}G0 X{fmt(ctx.x_safe)} Z{fmt(start_z_clear)}")
    lines.append("")
