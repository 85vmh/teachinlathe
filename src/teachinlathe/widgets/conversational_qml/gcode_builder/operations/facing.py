from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float


def generate_facing_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    geometry = op.get("geometry_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}

    x_start = get_float(geometry, "x_start", 0.0)
    z_start = get_float(geometry, "z_start", 0.0)
    x_end = get_float(geometry, "x_end", 0.0)
    z_end = get_float(geometry, "z_end", 0.0)
    doc = get_float(cutting, "doc", 0.0)
    feed_rate = get_float(cutting, "feed_rate", 0.0)
    direction = spindle.get("direction", None)

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(f"{line_prefix}G95 F{feed_rate}")
    lines.append(
        f"{line_prefix}o<facing> call [{fmt(x_start)}] [{fmt(z_start)}] [{fmt(x_end)}] [{fmt(z_end)}]"
        f" [{inspect_position_int(m1_params)}] [{fmt(doc)}] [{direction}]"
    )

    if bool(op.get("z_end_becomes_new_z0", False)):
        datum = int(op.get("_datum", 1))
        lines.append(f"{line_prefix}G10 L20 P{datum} Z0 (Set the new datum at the current Z position)")

    return lines
