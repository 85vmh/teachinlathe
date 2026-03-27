from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float, get_int


def generate_drilling_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    drilling = op.get("drilling_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}

    x_start = get_float(drilling, "x_start", 0.0)
    if x_start == 0.0:
        x_start = get_float(op, "x_start", 0.0)
    z_start = get_float(drilling, "z_start", 0.0)
    z_end = get_float(drilling, "z_end", 0.0)
    retract = get_float(drilling, "z_retract", 0.0)
    increment = get_float(drilling, "peck_depth", 0.0)
    rpm = get_int(spindle, "rpm_value", 0)
    feed = get_float(drilling, "feed_rate", 0.0)

    # Drilling always uses G97 (CSS not valid at centre-line)
    lines = list(build_spindle_gcode(spindle, line_prefix, force_rpm=True))
    lines.append(
        f"{line_prefix}o<drilling> call [{fmt(x_start)}] [{fmt(z_start)}] [{fmt(z_end)}] [{fmt(retract)}]"
        f" [{inspect_position_int(m1_params)}] [{fmt(increment)}] [{rpm}] [{feed}]"
    )
    return lines
