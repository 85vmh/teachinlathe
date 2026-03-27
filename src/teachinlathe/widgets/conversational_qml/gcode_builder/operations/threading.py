from teachinlathe.conversational.data_types import ThreadLocation, Threading

from ..config import fmt
from ..helpers.spindle import build_spindle_gcode



def generate_threading_gcode(op: Threading):
    line_prefix = "/" if op.is_optional_block else ""

    if op.location == ThreadLocation.ID:
        x_start = op.minor_diameter
        x_end = op.major_diameter
        retract = -abs(op.retract)
    else:
        x_start = op.major_diameter
        x_end = op.minor_diameter
        retract = abs(op.retract)

    lines = []
    lines.extend(build_spindle_gcode(op.spindleParameters, line_prefix))
    lines.append(
        f"{line_prefix}o<threading> call "
        f"[{fmt(x_start)}] "
        f"[{fmt(op.z_start)}] "
        f"[{fmt(x_end)}] "
        f"[{fmt(op.z_end)}] "
        f"[{fmt(retract)}] "
        f"[{fmt(op.pitch)}] "
        f"[{int(op.starts)}] "
        f"[{fmt(op.initial_doc)}] "
        f"[{fmt(op.depth_degression)}] "
        f"[{fmt(op.compound_angle)}] "
        f"[{int(op.taper_type)}] "
        f"[45] "
        f"[{int(op.spring_passes)}]"
    )
    return lines
