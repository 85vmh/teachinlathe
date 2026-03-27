import math

from teachinlathe.conversational.data_types import BoringConfig, CutToward

from ....config import fmt
from ..custom_profiling_geometry import find_45deg_profile_intersection


def emit_diagonal_roughing(lines: list, config: BoringConfig, path: list, x_safe: float, x_cut_max: float, z_cut_deepest: float):
    """Emit diagonal boring passes while preserving a parallel 45-degree line family."""
    pfx = config.optional_prefix
    x_start = config.x_start
    z_start = config.z_start
    doc = config.doc if config.doc > 0 else 0.5
    retract = config.retract
    stock_x = config.stock_x
    stock_z = config.stock_z

    max_span_x = max(0.0, x_cut_max - x_start)
    max_span_z = max(0.0, z_start - z_cut_deepest)
    max_span = max(max_span_x, max_span_z)
    if max_span <= 1e-9:
        lines.append("( Profile Boring diagonal: nothing to cut – check x_start/profile/depth )")
        return

    pass_count = max(1, math.ceil(max_span / doc))
    last_points = None
    start_z_clear = z_start + retract

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(start_z_clear)}")
    for n in range(pass_count):
        step = min((n + 1) * doc, max_span)
        top_x = x_start + step
        left_z = z_start - step

        if top_x <= x_cut_max + 1e-9:
            start_x = top_x
            start_z = z_start
        else:
            hit = find_45deg_profile_intersection(path, top_x, z_start, -1.0, -1.0, -stock_x, stock_z)
            if hit is None:
                continue
            start_x, start_z = hit

        if left_z >= z_cut_deepest - 1e-9:
            end_x = x_start
            end_z = left_z
        else:
            hit = find_45deg_profile_intersection(path, x_start, left_z, 1.0, 1.0, -stock_x, stock_z)
            if hit is None:
                continue
            end_x, end_z = hit

        if start_x < x_safe - 1e-9 or end_x < x_safe - 1e-9:
            continue
        if start_z > z_start + 1e-9 or end_z > z_start + 1e-9:
            continue

        points = (round(start_x, 9), round(start_z, 9), round(end_x, 9), round(end_z, 9))
        if points == last_points:
            continue
        last_points = points

        if config.cut_toward == CutToward.INTERIOR:
            lines.append(f"{pfx}G0 X{fmt(start_x)}")
            lines.append(f"{pfx}G1 Z{fmt(start_z)}")
            lines.append(f"{pfx}G1 X{fmt(end_x)} Z{fmt(end_z)}")
            lines.append(f"{pfx}G1 X{fmt(end_x - retract)} Z{fmt(end_z)}")
            lines.append(f"{pfx}G0 X{fmt(start_x)} Z{fmt(start_z_clear)}")
            lines.append(f"{pfx}G0 Z{fmt(z_start + retract)}")
        else:
            lines.append(f"{pfx}G0 Z{fmt(end_z)}")
            lines.append(f"{pfx}G1 X{fmt(end_x)}")
            lines.append(f"{pfx}G1 X{fmt(start_x)} Z{fmt(start_z)}")
            lines.append(f"{pfx}G0 X{fmt(start_x - retract)} Z{fmt(start_z + retract)}")
            lines.append(f"{pfx}G0 X{fmt(x_safe)}")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(start_z_clear)}")
    lines.append("")
