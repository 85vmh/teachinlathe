from teachinlathe.conversational.data_types import G33Threading, ThreadLocation
from teachinlathe.conversational.g33_threading_pass_planner import plan_g33_threading_passes

from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode


def _safe_x(op: G33Threading, x_reference: float) -> float:
    retract = abs(float(op.retract))
    if op.location == ThreadLocation.ID:
        return x_reference - retract
    return x_reference + retract


def _x_reference(op: G33Threading) -> float:
    if op.location == ThreadLocation.ID:
        return float(op.minor_diameter)
    return float(op.major_diameter)


def _emit_m1_handling(lines, prefix, op: G33Threading, x_return: float, z_return: float) -> None:
    if not bool(op.m1Parameters.include_m1):
        return
    spindle_direction = int(op.spindleParameters.direction or 0)
    lines.append(
        f"{prefix}o<m1_handling> call "
        f"[{inspect_position_int(op.m1Parameters)}] "
        f"[{fmt(x_return)}] "
        f"[{fmt(z_return)}] "
        f"[{spindle_direction}]"
    )
    lines.append("")


def generate_g33_threading_gcode(op: G33Threading):
    prefix = "/" if op.is_optional_block else ""
    x_reference = _x_reference(op)
    final_radial_depth = op.final_radial_depth
    starts = max(1, int(op.starts or 1))
    lead = float(op.pitch) * starts
    lead_angle_step = 360.0 / starts if starts > 1 else 0.0
    safe_x = _safe_x(op, x_reference)

    lines = []
    lines.extend(build_spindle_gcode(op.spindleParameters, prefix, force_rpm=True))

    if int(op.taper_type or 0) != 0:
        lines.append("( G33 Threading: thread taper is not implemented yet )")

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
        return lines + [f"( ERROR: G33 Threading -- {exc} )"]

    for start_index in range(starts):
        lead_angle_offset = lead_angle_step * start_index
        for thread_pass in passes:
            pass_comment = f"{thread_pass.type.value.lower()} pass #{thread_pass.index}"
            if starts > 1:
                pass_comment = f"{pass_comment}, start {start_index + 1}"
            lines.append(f"{prefix}({pass_comment})")
            lines.append(f"{prefix}G0 X{fmt(safe_x)} Z{fmt(thread_pass.zStart)}")
            lines.append(f"{prefix}G0 X{fmt(thread_pass.x)}")
            lines.append(f"{prefix}G33 Z{fmt(thread_pass.zEnd)} K{fmt(thread_pass.pitch)} D{fmt(lead_angle_offset)}")
            lines.append(f"{prefix}G0 X{fmt(safe_x)}")
            _emit_m1_handling(lines, prefix, op, safe_x, thread_pass.zEnd)

    return lines
