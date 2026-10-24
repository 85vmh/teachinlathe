import math

from teachinlathe.conversational.model.data_types import Tapping

from ..config import fmt
from ..helpers.m1 import inspect_position_int
from ..helpers.spindle import build_spindle_gcode



def generate_tapping_gcode(op: Tapping, pitch=None):
    """``pitch``: the tap's, from the Tool Library; the op's own when None."""
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.speedsAndFeeds
    tapping = op.tappingParameters
    m1_params = op.m1Parameters
    pitch = tapping.pitch if pitch is None or pitch <= 0 else pitch
    # the tap starts, and every peck comes back to, the clearance in front
    # of Z Start
    retract_z = tapping.zStart + abs(tapping.toolClearance)

    lines = list(build_spindle_gcode(spindle, line_prefix, force_rpm=True))
    lines.append(f"{line_prefix}G0 X0 Z{fmt(retract_z)}")

    if tapping.peckDepth > 0.0 and abs(tapping.zEnd - tapping.zStart) > 0.0:
        total_depth = abs(tapping.zEnd - tapping.zStart)
        n_pecks = math.ceil(total_depth / tapping.peckDepth)
        sign = -1.0 if tapping.zEnd < tapping.zStart else 1.0
        peck_targets = [
            tapping.zStart + sign * min((i + 1) * tapping.peckDepth, total_depth)
            for i in range(n_pecks)
        ]
    else:
        peck_targets = [tapping.zEnd]

    direction = spindle.sign
    for z_target in peck_targets:
        lines.append(f"{line_prefix}G33.1 Z{fmt(z_target)} K{fmt(pitch)}")
        if m1_params.include_m1:
            lines.append(
                f"{line_prefix}o<m1_handling> call "
                f"[{inspect_position_int(m1_params)}]"
                f" [0.000] "
                f"[{fmt(retract_z)}] "
                f"[{direction}]"
            )

    lines.append(f"{line_prefix}G0 Z{fmt(retract_z)}")
    return lines
