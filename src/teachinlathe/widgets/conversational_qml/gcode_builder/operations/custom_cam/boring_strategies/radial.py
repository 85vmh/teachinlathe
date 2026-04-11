import math

from teachinlathe.conversational.data_types import BoringConfig

from ....config import fmt
from ..custom_profiling_geometry import find_profile_x_at_z


def emit_radial_roughing(lines: list, config: BoringConfig, path: list, x_safe: float, z_cut_deepest: float):
    """Step in Z (one doc per pass), cut radial in X at each depth."""
    pfx = config.optional_prefix
    x_start = config.x_start
    z_start = config.z_start
    doc = config.doc if config.doc > 0 else 0.5
    retract = config.retract
    stock_x = config.stock_x

    pass_count = max(1, math.ceil((z_start - z_cut_deepest) / doc))

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    for n in range(pass_count):
        cut_z = z_start - (n + 1) * doc
        if cut_z < z_cut_deepest:
            cut_z = z_cut_deepest

        cut_x = find_profile_x_at_z(path, cut_z, -stock_x, 0.0)
        if cut_x <= x_start:
            continue

        retract_z = cut_z + retract
        retract_x = max(x_start, cut_x - retract)

        lines.append(f"{pfx}G0 Z{fmt(cut_z)}")
        lines.append(f"{pfx}G0 X{fmt(x_start)}")
        lines.append(f"{pfx}G1 X{fmt(cut_x)}")
        lines.append(f"{pfx}G0 X{fmt(retract_x)} Z{fmt(retract_z)}")
        lines.append(f"{pfx}G0 X{fmt(x_start)}")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")
