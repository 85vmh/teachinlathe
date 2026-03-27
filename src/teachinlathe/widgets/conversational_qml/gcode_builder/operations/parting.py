from teachinlathe.conversational.data_types import BlendType, Parting

from ..config import fmt
from ..helpers.spindle import build_spindle_gcode



def _edge_break_params(edge_break):
    if edge_break.blend_type == BlendType.CHAMFER:
        return 1, edge_break.chamfer_width
    if edge_break.blend_type == BlendType.FILLET:
        return 2, edge_break.fillet_radius
    return 0, 0.0



def generate_parting_gcode(op: Parting):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.spindleParameters
    parting = op.partingParameters
    edge_break_type, edge_break_value = _edge_break_params(op.edgeBreak)

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(
        f"{line_prefix}o<parting> call "
        f"[{fmt(parting.x_clearance)}] "
        f"[{fmt(parting.xStart)}] "
        f"[{fmt(parting.xEnd)}] "
        f"[{fmt(parting.zPos)}] "
        f"[{parting.first_feed_rate}] "
        f"[{parting.second_feed_rate}] "
        f"[{fmt(parting.second_feed_x_pos)}] "
        f"[{edge_break_type}] "
        f"[{fmt(edge_break_value)}]"
    )
    return lines
