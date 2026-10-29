"""Facing: down from Z Start to Z End a depth of cut at a time, each pass
across the face from X Start to X End, away at 45 degrees and back to X Start.

facing_toolpath writes the G-code and keeps its moves, so the editor's
drawing (facing_preview) is the G-code's. All X values are diameters.
"""

from typing import Optional

from teachinlathe.conversational.model.data_types import Facing, Program

from ..helpers.spindle import build_feed_gcode, build_spindle_gcode
from ..toolpath import GcodeEmitter, OperationPreview



def facing_toolpath(op: Facing, path: GcodeEmitter, program: Optional[Program] = None):
    """``op``'s G-code, and its moves, onto ``path``. Z End becomes the new
    Z0, when the operation says so, of ``program``'s work offset - G54 with
    none."""
    spindle = op.speedsAndFeeds
    geometry = op.geometryParameters
    cutting = op.cuttingParameters
    m1_params = op.m1Parameters
    x_start, z_start, x_end, z_end = geometry.xStart, geometry.zStart, geometry.xEnd, geometry.zEnd
    doc = cutting.doc
    # a retract of zero would leave the tool rubbing the face it just cut on
    # the way back out: the depth of cut instead
    retract = cutting.retract if cutting.retract > 0 else doc

    if doc <= 0:
        path.error("Facing -- no depth of cut")
        return

    path.codes(build_spindle_gcode(spindle, ""))
    path.code(build_feed_gcode(spindle.feed_rate))
    path.blank()
    path.rapid(x_start, z_start)

    z = z_start
    # with a tolerance: Z End a whole number of cuts away, rounding must not
    # make the last of them a second pass at Z End
    while z > z_end + doc + 1e-6:
        z -= doc
        path.start_pass()
        path.feed(z=z)
        path.feed(x=x_end)
        # away at 45 degrees: X a diameter, so 2R on X is R on the part
        path.rapid(x_end + retract * 2, z + retract)
        path.rapid(x=x_start)
        path.rapid(z=z)
        # back at X Start, on the face it cut
        if m1_params.include_m1:
            path.inspect_stop(m1_params)
        path.blank()

    path.start_pass()
    path.feed(z=z_end)
    path.feed(x=x_end)
    path.rapid(x_end + retract * 2, z_end + retract)
    path.rapid(x=x_start + retract * 2)
    path.rapid(z=z_end)
    path.blank()

    if op.zEndBecomesNewZ0:
        datum = int(program.header.datum) if program is not None else 1
        path.code(f"G10 L20 P{datum} Z0 (Set the new datum at the current Z position)")
        path.set_z_zero()


def generate_facing_gcode(op: Facing):
    """``op``'s G-code on its own."""
    path = GcodeEmitter(op.is_optional_block)
    facing_toolpath(op, path)
    return path.lines


def facing_preview(op: Facing) -> OperationPreview:
    """What ``op`` cuts, as its editor draws it: its G-code's moves."""
    path = GcodeEmitter(op.is_optional_block)
    facing_toolpath(op, path)
    return path.preview()
