import math

from teachinlathe.conversational.data_types import BoringConfig, CutToward

from ....config import fmt
from ..custom_profiling_geometry import find_deepest_z_at_x_path


def emit_axial_roughing(lines: list, config: BoringConfig, path: list, x_safe: float, x_cut_max: float):
    """Step in X (one doc per pass), cut axially in Z at each diameter."""
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
    x_profile_limit = x_cut_max

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    for n in range(pass_count):
        cut_x = min(x_start + (n + 1) * doc, x_cut_max)
        cut_z = find_deepest_z_at_x_path(path, cut_x, -stock_x, stock_z)
        exit_x = cut_x - retract
        entry_z = z_start + retract if n == 0 or cut_x < x_profile_limit - 1e-9 else z_start

        if config.cut_toward == CutToward.INTERIOR:
            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
            lines.append(f"{pfx}G0 X{fmt(cut_x)}")
            lines.append(f"{pfx}G1 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)}")
            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
        else:
            lines.append(f"{pfx}G0 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(cut_x)}")
            lines.append(f"{pfx}G1 Z{fmt(z_start)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)}")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")
