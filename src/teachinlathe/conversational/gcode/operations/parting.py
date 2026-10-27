from teachinlathe.conversational.model.data_types import BlendType, Parting

from ..config import fmt
from ..helpers.spindle import build_spindle_gcode



def generate_parting_gcode(op: Parting):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.speedsAndFeeds
    parting = op.partingParameters
    edge_break = op.edgeBreak
    x_start, z_pos = parting.xStart, parting.zPos
    # the clearance is a radius, X a diameter: the blade starts and retracts
    # here
    x_clear = x_start + 2 * parting.x_clearance

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    if edge_break.blend_type in (BlendType.CHAMFER, BlendType.FILLET):
        size = (edge_break.chamfer_width if edge_break.blend_type == BlendType.CHAMFER
                else edge_break.fillet_radius)
        # X a diameter: the edge break's depth, a radius, twice over
        x_break = x_start - 2 * size
        # in to the edge break's depth, then back out and across it in Z+
        lines.append(f"{line_prefix}G0 Z{fmt(z_pos)}")
        lines.append(f"{line_prefix}G0 X{fmt(x_clear)}")
        lines.append(f"{line_prefix}G95 F{spindle.feed_rate}")
        lines.append(f"{line_prefix}G1 X{fmt(x_break)}")
        lines.append(f"{line_prefix}G0 X{fmt(x_clear)}")
        lines.append(f"{line_prefix}G0 Z{fmt(z_pos + size)}")
        lines.append(f"{line_prefix}G1 X{fmt(x_start)}")
        if edge_break.blend_type == BlendType.CHAMFER:
            lines.append(f"{line_prefix}G1 X{fmt(x_break)} Z{fmt(z_pos)}")
        else:
            # the quarter round the corner, from (X Start, Z + size) to
            # (X Start - 2 size, Z) about its centre a radius ``size`` below
            # the start: CCW in ZX - G2 is the other three quarters, through
            # the part. I a radius, in G7 too.
            lines.append(f"{line_prefix}G3 X{fmt(x_break)} Z{fmt(z_pos)} I{fmt(-size)} K0")
    else:
        lines.append(f"{line_prefix}G0 Z{fmt(z_pos)}")
        lines.append(f"{line_prefix}G0 X{fmt(x_start)}")
        lines.append(f"{line_prefix}G95 F{spindle.feed_rate}")
    lines.append(f"{line_prefix}G1 X{fmt(parting.second_feed_x_pos)} F{spindle.feed_rate}")
    lines.append(f"{line_prefix}G1 X{fmt(parting.xEnd)} F{spindle.feed_rate_2}")
    lines.append(f"{line_prefix}G0 X{fmt(x_clear)}")
    return lines
