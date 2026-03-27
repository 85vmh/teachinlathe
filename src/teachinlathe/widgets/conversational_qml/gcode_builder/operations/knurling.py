from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float


def generate_knurling_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    geometry = op.get("geometry_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}

    x_start = get_float(geometry, "x_start", 0.0)
    z_start = get_float(geometry, "z_start", 0.0)
    z_end = get_float(geometry, "z_end", 0.0)
    doc = get_float(cutting, "doc", 0.0)
    retract = get_float(cutting, "retract", 0.0)
    grooves_count = max(1, int(cutting.get("grooves_count", 1) or 1))
    include_m1 = 1 if bool(m1_params.get("include_m1", False)) else 0
    direction = spindle.get("direction", None)

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(
        f"{line_prefix}o<knurling> call "
        f"[{fmt(x_start)}] "
        f"[{fmt(z_start)}] "
        f"[{fmt(z_end)}] "
        f"[{fmt(doc)}] "
        f"[{fmt(retract)}] "
        f"[{grooves_count}] "
        f"[{inspect_position_int(m1_params)}] "
        f"[{include_m1}] "
        f"[{direction if direction is not None else 0}]"
    )
    return lines
