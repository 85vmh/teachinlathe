from teachinlathe.conversational.model.data_types import Drilling

from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode



def generate_drilling_gcode(op: Drilling):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.speedsAndFeeds
    drilling = op.drillingParameters
    m1_params = op.m1Parameters

    # the drill starts, and every peck retracts, the clearance in front of
    # Z Start
    retract_z = drilling.zStart + abs(drilling.toolClearance)
    # how the spindle turns - and starts again after Pause to Inspect: 1 M3,
    # -1 M4
    spindle_direction = spindle.sign

    lines = list(build_spindle_gcode(spindle, line_prefix, force_rpm=True))
    lines.append(
        f"{line_prefix}o<drilling> call "
        f"[0.000] "
        f"[{fmt(drilling.zStart)}] "
        f"[{fmt(drilling.zEnd)}] "
        f"[{fmt(retract_z)}] "
        f"[{inspect_position_int(m1_params)}] "
        f"[{fmt(drilling.peckDepth)}] "
        f"[{0 if spindle.rpm_value is None else int(spindle.rpm_value)}] "
        f"[{spindle.feed_rate}] "
        f"[{fmt(max(0.0, drilling.dwellTime))}] "
        f"[{spindle_direction}]"
    )
    return lines
