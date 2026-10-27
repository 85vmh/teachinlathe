from teachinlathe.conversational.model.data_types import Facing

from ..config import fmt
from ..helpers.m1 import m1_handling_call
from ..helpers.spindle import build_spindle_gcode
from .facing_preview import facing_passes



def generate_facing_gcode(op: Facing, datum: int = 1):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.speedsAndFeeds
    geometry = op.geometryParameters
    cutting = op.cuttingParameters
    m1_params = op.m1Parameters

    passes = facing_passes(geometry.xStart, geometry.zStart, geometry.xEnd, geometry.zEnd,
                           cutting.doc, cutting.retract)
    if not passes:
        return ["( ERROR: Facing -- no depth of cut )"]

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(f"{line_prefix}G95 F{spindle.feed_rate}")
    lines.append("")
    lines.append(f"{line_prefix}G0 X{fmt(geometry.xStart)} Z{fmt(geometry.zStart)}")
    for index, moves in enumerate(passes):
        for feed, x, z in moves:
            lines.append(f"{line_prefix}{'G1' if feed else 'G0'} X{fmt(x)} Z{fmt(z)}")
        # every pass but the last ends at X Start, on the face it cut
        if index < len(passes) - 1 and m1_params.include_m1:
            _, x, z = moves[-1]
            lines.append(m1_handling_call(line_prefix, m1_params, x, z, spindle.sign))
        lines.append("")

    if op.zEndBecomesNewZ0:
        lines.append(f"{line_prefix}G10 L20 P{int(datum)} Z0 (Set the new datum at the current Z position)")

    return lines
