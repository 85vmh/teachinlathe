from teachinlathe.conversational.data_types import Strategy

from ..config import fmt
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float


def generate_profiling_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    options = op.get("profiling_options", {}) or {}

    profile_id = int(params.get("profile_id", 0) or 0)
    x_start = get_float(params, "x_start", 0.0)
    z_start = get_float(params, "z_start", 0.0)

    doc = get_float(cutting, "doc", 0.0)
    retract = get_float(cutting, "retract", 0.0)
    feed_rate = get_float(cutting, "feed_rate", 0.0)

    stock_x = get_float(options, "stock_to_leave_x", 0.0)
    stock_z = get_float(options, "stock_to_leave_z", 0.0)
    stock = max(stock_x, stock_z)
    finish_passes = max(1, int(options.get("finish_passes", 1) or 1))
    spring_passes = max(0, int(options.get("finish_spring_passes", 0) or 0))

    try:
        strategy = Strategy(str(options.get("strategy", "rough")).lower())
    except ValueError:
        strategy = Strategy.ROUGH

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(f"{line_prefix}G95 F{feed_rate}")

    if strategy == Strategy.FINISH:
        passes = finish_passes + spring_passes
        lines.append(
            f"{line_prefix}G70 Q{profile_id} X{fmt(x_start)} Z{fmt(z_start)} D{fmt(stock)} E0 P{passes}"
        )
    else:
        lines.append(
            f"{line_prefix}G71.1 Q{profile_id} X{fmt(x_start)} Z{fmt(z_start)} D{fmt(stock)} I{fmt(doc)} R{fmt(retract)}"
        )
    return lines
