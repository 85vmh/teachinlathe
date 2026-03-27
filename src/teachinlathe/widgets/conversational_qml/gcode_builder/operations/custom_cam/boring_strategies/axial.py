import math

from teachinlathe.conversational.data_types import BoringConfig, CutToward

from ....config import fmt
from ..custom_profiling_geometry import find_deepest_z_at_x_path



def emit_axial_roughing(lines: list, config: BoringConfig, path: list, x_safe: float, x_cut_max: float):
    """Step in X (one doc per pass), cut axially in Z at each diameter.

    The boring tool retracts on a 45-degree move, traverses straight to the next
    pass approach point, then re-enters on another 45-degree move.
    """
    pfx = config.optional_prefix
    x_start = config.x_start
    z_start = config.z_start
    doc = config.doc if config.doc > 0 else 0.5
    retract = config.retract
    stock_x = config.stock_x
    stock_z = config.stock_z

    if x_cut_max <= x_start:
        lines.append("( Profile Boring axial: nothing to cut – check x_start vs profile )")
        return

    pass_count = max(1, math.ceil((x_cut_max - x_start) / doc))
    pass_points = []
    for n in range(pass_count):
        cut_x = min(x_start + (n + 1) * doc, x_cut_max)
        cut_z = find_deepest_z_at_x_path(path, cut_x, -stock_x, stock_z)
        if cut_z > z_start + 1e-9:
            continue
        pass_points.append((cut_x, cut_z))

    if not pass_points:
        lines.append("( Profile Boring axial: no valid passes after stock/retract checks )")
        return

    if config.cut_toward == CutToward.INTERIOR:
        prev_exit_x = x_safe
        prev_exit_z = z_start
        lines.append(f"{pfx}G0 X{fmt(prev_exit_x)} Z{fmt(prev_exit_z)}")

        for cut_x, cut_z in pass_points:
            entry_x = cut_x - retract
            entry_z = z_start + retract
            exit_x = cut_x - retract
            exit_z = cut_z + retract

            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
            lines.append(f"{pfx}G0 X{fmt(entry_x)}")
            lines.append(f"{pfx}G0 X{fmt(cut_x)} Z{fmt(z_start)}")
            lines.append(f"{pfx}G1 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")

            prev_exit_x = exit_x
            prev_exit_z = exit_z

        lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
        lines.append("")
        return

    prev_exit_x = x_safe
    prev_exit_z = z_start + retract
    lines.append(f"{pfx}G0 X{fmt(prev_exit_x)} Z{fmt(prev_exit_z)}")

    for cut_x, cut_z in pass_points:
        entry_x = cut_x - retract
        entry_z = cut_z + retract
        exit_x = cut_x - retract
        exit_z = z_start + retract

        lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
        lines.append(f"{pfx}G0 X{fmt(entry_x)}")
        lines.append(f"{pfx}G0 X{fmt(cut_x)} Z{fmt(cut_z)}")
        lines.append(f"{pfx}G1 Z{fmt(z_start)}")
        lines.append(f"{pfx}G0 X{fmt(exit_x)} Z{fmt(exit_z)}")

        prev_exit_x = exit_x
        prev_exit_z = exit_z

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")
