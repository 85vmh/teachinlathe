from teachinlathe.conversational.model.data_types import G33Threading, ThreadLocation
from teachinlathe.conversational.gcode.g33_threading_pass_planner import plan_g33_threading_passes

from ..helpers.spindle import build_spindle_gcode
from ..toolpath import GcodeEmitter


def _safe_x(op: G33Threading, x_reference: float) -> float:
    retract = abs(float(op.retract))
    if op.location == ThreadLocation.ID:
        return x_reference - retract
    return x_reference + retract


def _x_reference(op: G33Threading) -> float:
    if op.location == ThreadLocation.ID:
        return float(op.minor_diameter)
    return float(op.major_diameter)


def g33_threading_toolpath(op: G33Threading, path: GcodeEmitter, program=None):
    """``op``'s G-code, and its moves, onto ``path``: each pass of the plan
    (plan_g33_threading_passes), for each start, in from the safe diameter,
    along Z synchronized with the spindle (G33), and back out."""
    x_reference = _x_reference(op)
    final_radial_depth = op.final_radial_depth
    starts = max(1, int(op.starts or 1))
    lead = float(op.pitch) * starts
    lead_angle_step = 360.0 / starts if starts > 1 else 0.0
    safe_x = _safe_x(op, x_reference)

    path.codes(build_spindle_gcode(op.speedsAndFeeds, "", force_rpm=True))

    if int(op.taper_type or 0) != 0:
        path.note("( G33 Threading: thread taper is not implemented yet )")

    try:
        passes = plan_g33_threading_passes(
            xReference=x_reference,
            zStart=op.z_start,
            zEnd=op.z_end,
            pitch=lead,
            firstRadialDepth=op.initial_doc,
            finalRadialDepth=final_radial_depth,
            minimumRadialIncrement=op.minimum_radial_increment,
            springPasses=op.spring_passes,
            infeedAngleDegrees=op.compound_angle,
            threadLocation=op.location,
        )
    except Exception as exc:
        path.error(f"G33 Threading -- {exc}")
        return

    for thread_pass in passes:
        for start_index in range(starts):
            lead_angle_offset = lead_angle_step * start_index
            pass_comment = f"{thread_pass.type.value.lower()} pass #{thread_pass.index}"
            if starts > 1:
                pass_comment = f"{pass_comment}, start #{start_index + 1}"
            path.start_pass()
            path.code(f"({pass_comment})")
            path.rapid(safe_x, thread_pass.zStart)
            path.rapid(x=thread_pass.x)
            path.thread(thread_pass.zEnd, thread_pass.pitch, lead_angle_offset)
            path.rapid(x=safe_x)
            path.rapid(z=thread_pass.zStart)
            if op.m1Parameters.include_m1:
                path.inspect_stop(op.m1Parameters)
                path.blank()


def generate_g33_threading_gcode(op: G33Threading):
    """``op``'s G-code on its own."""
    path = GcodeEmitter(op.is_optional_block)
    g33_threading_toolpath(op, path)
    return path.lines
