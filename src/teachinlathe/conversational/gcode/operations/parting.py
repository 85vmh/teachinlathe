from teachinlathe.conversational.model.data_types import BlendType, Parting

from ..helpers.spindle import build_spindle_gcode
from ..toolpath import GcodeEmitter, OperationPreview



def parting_toolpath(op: Parting, path: GcodeEmitter, program=None):
    """``op``'s G-code, and its moves, onto ``path``: an edge break first
    when it has one, then in to X End, the feed changing at the second feed's
    X, and back out to the clearance."""
    spindle = op.speedsAndFeeds
    parting = op.partingParameters
    edge_break = op.edgeBreak
    x_start, z_pos = parting.xStart, parting.zPos
    # the clearance is a radius, X a diameter: the blade starts and retracts
    # here
    x_clear = x_start + 2 * parting.x_clearance

    path.codes(build_spindle_gcode(spindle, ""))
    if edge_break.blend_type in (BlendType.CHAMFER, BlendType.FILLET):
        size = (edge_break.chamfer_width if edge_break.blend_type == BlendType.CHAMFER
                else edge_break.fillet_radius)
        # X a diameter: the edge break's depth, a radius, twice over
        x_break = x_start - 2 * size
        # in to the edge break's depth, then back out and across it in Z+
        path.rapid(z=z_pos)
        path.rapid(x=x_clear)
        path.code(f"G95 F{spindle.feed_rate}")
        path.feed(x=x_break)
        path.rapid(x=x_clear)
        path.rapid(z=z_pos + size)
        path.feed(x=x_start)
        if edge_break.blend_type == BlendType.CHAMFER:
            path.feed(x_break, z_pos)
        else:
            # the quarter round the corner, from (X Start, Z + size) to
            # (X Start - 2 size, Z) about its centre a radius ``size`` below
            # the start: CCW in ZX - G2 is the other three quarters, through
            # the part. I a radius, in G7 too.
            path.arc(x_break, z_pos, -size, 0.0, clockwise=False)
    else:
        path.rapid(z=z_pos)
        path.rapid(x=x_start)
        path.code(f"G95 F{spindle.feed_rate}")
    path.feed(x=parting.second_feed_x_pos, f=spindle.feed_rate)
    path.feed(x=parting.xEnd, f=spindle.feed_rate_2)
    path.rapid(x=x_clear)


def parting_preview(op: Parting) -> OperationPreview:
    """What ``op`` cuts, as its editor draws it: its G-code's moves - the
    edge break, the two feeds, the rapids between."""
    path = GcodeEmitter(op.is_optional_block)
    parting_toolpath(op, path)
    return path.preview()
