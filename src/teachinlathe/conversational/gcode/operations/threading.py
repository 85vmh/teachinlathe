import math

from teachinlathe.conversational.model.data_types import ThreadLocation, Threading

from ..config import fmt
from ..helpers.spindle import build_spindle_gcode


#: The angle of a thread's taper (G76 E), in degrees.
TAPER_ANGLE = 45.0


def generate_threading_gcode(op: Threading):
    line_prefix = "/" if op.is_optional_block else ""

    # the retract is + for an external thread, - for an internal one
    if op.location == ThreadLocation.ID:
        x_start = op.minor_diameter
        x_end = op.major_diameter
        retract = -abs(op.retract)
    else:
        x_start = op.major_diameter
        x_end = op.minor_diameter
        retract = abs(op.retract)

    starts = max(1, int(op.starts))
    diameter_diff = abs(x_start - x_end)
    taper_length = math.tan(math.radians(TAPER_ANGLE)) * diameter_diff / 2
    # from the drive line, X Start + retract, to the thread's peak
    thread_peak = -retract
    lead_angle_step = 360.0 / starts if starts > 1 else 0.0

    lines = []
    lines.extend(build_spindle_gcode(op.speedsAndFeeds, line_prefix))
    # a multi-start thread: each start cut at its own spindle angle
    for index in range(starts):
        lines.append(f"{line_prefix}G0 X{fmt(x_start)} Z{fmt(op.z_start)}")
        lines.append(
            f"{line_prefix}G76 P{fmt(op.pitch * starts)} Z{fmt(op.z_end)} "
            f"I{fmt(thread_peak)} J{fmt(op.initial_doc)} K{fmt(diameter_diff)} "
            f"R{fmt(op.depth_degression)} Q{fmt(op.compound_angle)} "
            f"L{int(op.taper_type)} E{fmt(taper_length)} H{int(op.spring_passes)} "
            f"D{fmt(lead_angle_step * index)}"
        )
    lines.append(f"{line_prefix}G0 Z{fmt(op.z_start)}")
    return lines
