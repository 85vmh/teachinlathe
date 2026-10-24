from teachinlathe.conversational.model.data_types import Knurling

from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode



def generate_knurling_gcode(op: Knurling):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.speedsAndFeeds
    geometry = op.geometryParameters
    cutting = op.cuttingParameters
    m1_params = op.m1Parameters

    include_m1 = 1 if m1_params.include_m1 else 0
    direction = spindle.sign

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(
        f"{line_prefix}o<knurling> call "
        f"[{fmt(geometry.xStart)}] "
        f"[{fmt(geometry.zStart)}] "
        f"[{fmt(geometry.zEnd)}] "
        f"[{fmt(cutting.doc)}] "
        f"[{fmt(cutting.retract)}] "
        f"[{max(1, int(cutting.groovesCount))}] "
        f"[{inspect_position_int(m1_params)}] "
        f"[{include_m1}] "
        f"[{direction}]"
    )
    return lines
