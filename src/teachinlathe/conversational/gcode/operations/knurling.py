import math

from teachinlathe.conversational.model.data_types import Knurling

from ..config import fmt
from ..helpers.m1 import m1_gcode
from ..helpers.spindle import build_spindle_gcode



def generate_knurling_gcode(op: Knurling):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.speedsAndFeeds
    geometry = op.geometryParameters
    cutting = op.cuttingParameters
    m1_params = op.m1Parameters

    grooves = max(1, int(abs(cutting.groovesCount)))
    x_drive = geometry.xStart - 2 * cutting.doc
    x_clear = geometry.xStart + cutting.retract
    # one turn of the part per circumference: the knurl rolls at 45 degrees
    lead = math.pi * geometry.xStart
    angle_step = 360.0 / grooves

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append("")
    # every groove there, then every groove back, each starting at its own
    # spindle angle
    for z_from, z_to in ((geometry.zStart, geometry.zEnd), (geometry.zEnd, geometry.zStart)):
        for index in range(grooves):
            lines.append(f"{line_prefix}G0 X{fmt(x_clear)} Z{fmt(z_from)}")
            lines.append(f"{line_prefix}G0 X{fmt(x_drive)}")
            lines.append(f"{line_prefix}G33 Z{fmt(z_to)} K{fmt(lead)} D{fmt(index * angle_step)}")
            lines.append(f"{line_prefix}G0 X{fmt(x_clear)}")
            if m1_params.include_m1:
                lines.append(m1_gcode(line_prefix, m1_params))
            lines.append("")

    lines.append(f"{line_prefix}G0 X{fmt(x_clear)} Z{fmt(geometry.zStart)}")
    return lines
