import math

from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float


def generate_tapping_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    tapping = op.get("tapping_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}

    z_start = get_float(tapping, "z_start", 0.0)
    z_end = get_float(tapping, "z_end", 0.0)
    z_retract = get_float(tapping, "z_retract", 0.0)
    peck_depth = get_float(tapping, "peck_depth", 0.0)
    pitch = get_float(tapping, "pitch", 0.0)

    include_m1 = bool(m1_params.get("include_m1", False))

    # Rigid tapping requires G97 (RPM mode)
    lines = list(build_spindle_gcode(spindle, line_prefix, force_rpm=True))
    lines.append(f"{line_prefix}G0 X0 Z{fmt(z_start)}")

    if peck_depth > 0.0 and abs(z_end - z_start) > 0.0:
        total_depth = abs(z_end - z_start)
        n_pecks = math.ceil(total_depth / peck_depth)
        sign = -1.0 if z_end < z_start else 1.0
        peck_targets = [
            z_start + sign * min((i + 1) * peck_depth, total_depth)
            for i in range(n_pecks)
        ]
    else:
        peck_targets = [z_end]

    direction = spindle.get("direction", 1)
    for z_target in peck_targets:
        lines.append(f"{line_prefix}G33.1 Z{fmt(z_target)} K{fmt(pitch)}")
        if include_m1:
            lines.append(
                f"{line_prefix}o<m1_handling> call [{inspect_position_int(m1_params)}]"
                f" [0.000] [{fmt(z_start)}] [{direction}]"
            )

    lines.append(f"{line_prefix}G0 Z{fmt(z_retract)}")
    return lines
