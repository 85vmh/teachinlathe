from teachinlathe.conversational.data_types import Facing

from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode



def generate_facing_gcode(op: Facing, datum: int = 1):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.spindleParameters
    geometry = op.geometryParameters
    cutting = op.cuttingParameters
    m1_params = op.m1Parameters

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(f"{line_prefix}G95 F{cutting.feedRate}")
    lines.append("")
    lines.append(
        f"{line_prefix}o<facing> call "
        f"[{fmt(geometry.xStart)}] "
        f"[{fmt(geometry.zStart)}] "
        f"[{fmt(geometry.xEnd)}] "
        f"[{fmt(geometry.zEnd)}] "
        f"[{inspect_position_int(m1_params)}] "
        f"[{fmt(cutting.doc)}] "
        f"[{spindle.direction}]"
    )

    if op.zEndBecomesNewZ0:
        lines.append(f"{line_prefix}G10 L20 P{int(datum)} Z0 (Set the new datum at the current Z position)")

    return lines
