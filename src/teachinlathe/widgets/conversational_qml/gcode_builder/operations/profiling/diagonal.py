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
DIAGONAL_INTERIOR uses Z lead-in and X lead-out. DIAGONAL_EXTERIOR uses X
lead-in and Z lead-out.
"""

import math
import os

from teachinlathe.conversational.data_types import PassType

from ...config import fmt
from .geometry import find_45deg_profile_intersection
from .context import RoughingContext


def _debug_enabled() -> bool:
    return os.environ.get("TEACHINLATHE_DIAGONAL_DEBUG", "").lower() in {"1", "true", "yes", "on"}


def _debug(message: str) -> None:
    if _debug_enabled():
        print(f"[profile-diagonal] {message}")


def _path_point(element):
    if hasattr(element, "x"):
        return {"type": type(element).__name__, "x": element.x, "z": element.z}
    return {
        "type": type(element).__name__,
        "end_x": element.end_x,
        "end_z": element.end_z,
        "center_x": getattr(element, "center_x", None),
        "center_z": getattr(element, "center_z", None),
        "anticlockwise": getattr(element, "anticlockwise", None),
    }


def emit_diagonal_roughing(
    lines: list,
    context: RoughingContext,
    path: list,
    x_cut_limit: float,
    z_cut_deepest: float,
    pass_type: PassType,
) -> None:
    prefix = context.optional_prefix
    _debug(
        "emit_diagonal_roughing "
        f"pass_type={pass_type!r} x_cut_limit={x_cut_limit!r} z_cut_deepest={z_cut_deepest!r} "
        f"context={context!r} path_len={len(path or [])} path={[_path_point(item) for item in (path or [])]}"
    )

    max_span_x = abs(x_cut_limit - context.x_start)
    max_span_z = abs(context.z_start - z_cut_deepest)
    max_span = max(max_span_x, max_span_z)
    _debug(f"spans max_span_x={max_span_x!r} max_span_z={max_span_z!r} max_span={max_span!r}")
    if max_span <= 1e-9:
        _debug("skip all: max_span <= 1e-9")
        lines.append("( ProfileRoughing diagonal: nothing to cut – check x_start/profile/depth )")
        return

    pass_count = max(1, math.ceil(max_span / context.doc))
    start_z_clear = context.z_start + context.retract
    last_points = None
    _debug(f"planning pass_count={pass_count!r} start_z_clear={start_z_clear!r}")

    lines.append(f"{prefix}G0 X{fmt(context.x_safe)} Z{fmt(start_z_clear)}")

    for n in range(pass_count):
        step = min((n + 1) * context.doc, max_span)
        _debug(f"pass n={n} step={step!r}")

        # ---- corner B: profile side at z_start ----
        corner_b_x = context.x_start + context.x_direction * step
        corner_b_z = context.z_start
        _debug(f"corner_b x={corner_b_x!r} z={corner_b_z!r}")

        if context.x_direction * (corner_b_x - x_cut_limit) <= 0:
            # within radial limit — use geometric corner
            start_x, start_z = corner_b_x, corner_b_z
            _debug(f"corner_b within radial limit -> start=({start_x!r}, {start_z!r})")
        else:
            # clipped by profile: ray from corner_B in direction (-x_dir, -1)
            hit = find_45deg_profile_intersection(
                path, corner_b_x, corner_b_z,
                float(-context.x_direction), -1.0,
            )
            if hit is None:
                _debug(
                    "skip pass: no corner_b/profile intersection "
                    f"ray_start=({corner_b_x!r}, {corner_b_z!r}) "
                    f"dir=({float(-context.x_direction)!r}, {-1.0!r})"
                )
                continue
            start_x, start_z = hit
            _debug(f"corner_b clipped -> start=({start_x!r}, {start_z!r})")

        # ---- corner A: x_start side at depth ----
        corner_a_x = context.x_start
        corner_a_z = context.z_start - step
        _debug(f"corner_a x={corner_a_x!r} z={corner_a_z!r}")

        if corner_a_z >= z_cut_deepest - 1e-9:
            # within axial limit — use geometric corner
            end_x, end_z = corner_a_x, corner_a_z
            _debug(f"corner_a within axial limit -> end=({end_x!r}, {end_z!r})")
        else:
            # clipped by profile: ray from corner_A in direction (x_dir, +1)
            hit = find_45deg_profile_intersection(
                path, corner_a_x, corner_a_z,
                float(context.x_direction), 1.0,
            )
            if hit is None:
                _debug(
                    "skip pass: no corner_a/profile intersection "
                    f"ray_start=({corner_a_x!r}, {corner_a_z!r}) "
                    f"dir=({float(context.x_direction)!r}, {1.0!r})"
                )
                continue
            end_x, end_z = hit
            _debug(f"corner_a clipped -> end=({end_x!r}, {end_z!r})")

        # sanity checks
        if start_z > context.z_start + 1e-9 or end_z > context.z_start + 1e-9:
            _debug(
                "skip pass: sanity z check failed "
                f"start=({start_x!r}, {start_z!r}) end=({end_x!r}, {end_z!r}) "
                f"z_start={context.z_start!r}"
            )
            continue

        points = (round(start_x, 9), round(start_z, 9), round(end_x, 9), round(end_z, 9))
        if points == last_points:
            _debug(f"skip pass: duplicate points={points!r}")
            continue
        last_points = points
        _debug(f"rough points start=({start_x!r}, {start_z!r}) end=({end_x!r}, {end_z!r})")

        if pass_type == PassType.DIAGONAL_EXTERIOR:
            cut_start_x, cut_start_z = (end_x, end_z) if end_x <= start_x else (start_x, start_z)
            cut_end_x, cut_end_z = (start_x, start_z) if end_x <= start_x else (end_x, end_z)
        else:
            cut_start_x, cut_start_z = (end_x, end_z) if end_x >= start_x else (start_x, start_z)
            cut_end_x, cut_end_z = (start_x, start_z) if end_x >= start_x else (end_x, end_z)

        dx = cut_end_x - cut_start_x
        dz = cut_end_z - cut_start_z
        if math.hypot(dx, dz) <= 1e-9:
            _debug(
                "skip pass: cut length <= 1e-9 "
                f"cut_start=({cut_start_x!r}, {cut_start_z!r}) cut_end=({cut_end_x!r}, {cut_end_z!r})"
            )
            continue

        if pass_type == PassType.DIAGONAL_INTERIOR:
            entry_x = cut_start_x
            entry_z = cut_start_z + context.retract
            exit_x = cut_end_x - context.x_direction * context.retract
            exit_z = cut_end_z
        else:
            entry_x = cut_start_x - context.x_direction * context.retract
            entry_z = cut_start_z
            exit_x = cut_end_x
            exit_z = cut_end_z + context.retract
        _debug(
            "emit pass "
            f"cut_start=({cut_start_x!r}, {cut_start_z!r}) "
            f"cut_end=({cut_end_x!r}, {cut_end_z!r}) "
            f"dx={dx!r} dz={dz!r} "
            f"entry=({entry_x!r}, {entry_z!r}) exit=({exit_x!r}, {exit_z!r})"
        )

        if pass_type == PassType.DIAGONAL_INTERIOR:
            lines.append(f"{prefix}G0 X{fmt(entry_x)} Z{fmt(entry_z)}")
            lines.append(f"{prefix}G1 Z{fmt(cut_start_z)}")
        else:
            lines.append(f"{prefix}G0 X{fmt(entry_x)} Z{fmt(entry_z)}")
            lines.append(f"{prefix}G1 X{fmt(cut_start_x)}")

        lines.append(f"{prefix}G1 X{fmt(cut_end_x)} Z{fmt(cut_end_z)}")
        if pass_type == PassType.DIAGONAL_INTERIOR:
            lines.append(f"{prefix}G1 X{fmt(exit_x)}")
        else:
            lines.append(f"{prefix}G1 Z{fmt(exit_z)}")
        lines.append(f"{prefix}G0 X{fmt(entry_x)} Z{fmt(entry_z)}")

    lines.append(f"{prefix}G0 X{fmt(context.x_safe)} Z{fmt(start_z_clear)}")
    lines.append("")
