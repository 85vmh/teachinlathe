from teachinlathe.conversational.model.data_types import Drilling

from ..config import fmt
from ..helpers.m1 import m1_handling_call
from ..helpers.spindle import build_spindle_gcode


#: How far short of the depth already drilled each peck goes back in at a rapid.
REENTRY_CLEARANCE = 0.2


def _peck_targets(z_start, z_end, peck_depth):
    """The Z each peck feeds to, the last one Z End; one peck straight to
    Z End without a peck depth."""
    if z_end >= z_start:
        return []
    step = abs(peck_depth)
    if step <= 0:
        return [z_end]
    targets = []
    z = z_start
    while z > z_end:
        z = max(z - step, z_end)
        targets.append(z)
    return targets


def generate_drilling_gcode(op: Drilling):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.speedsAndFeeds
    drilling = op.drillingParameters
    m1_params = op.m1Parameters

    # the drill starts, and every peck retracts, the clearance in front of
    # Z Start
    retract_z = drilling.zStart + abs(drilling.toolClearance)
    dwell = max(0.0, drilling.dwellTime)
    targets = _peck_targets(drilling.zStart, drilling.zEnd, drilling.peckDepth)
    if not targets:
        return ["( ERROR: Drilling -- Z End is not past Z Start )"]

    lines = list(build_spindle_gcode(spindle, line_prefix, force_rpm=True))
    lines.append(f"{line_prefix}G0 X0")
    lines.append(f"{line_prefix}G95 F{spindle.feed_rate}")
    lines.append(f"{line_prefix}G0 Z{fmt(retract_z)}")
    lines.append("")

    depth = drilling.zStart
    for index, target in enumerate(targets):
        # back in at a rapid, to just short of the depth already drilled
        if depth < retract_z:
            lines.append(f"{line_prefix}G0 Z{fmt(depth + REENTRY_CLEARANCE)}")
        lines.append(f"{line_prefix}G1 Z{fmt(target)}")
        if dwell > 0:
            lines.append(f"{line_prefix}G4 P{fmt(dwell)}")
        lines.append(f"{line_prefix}G0 Z{fmt(retract_z)}")
        # between pecks, not after the last
        if index < len(targets) - 1 and m1_params.include_m1:
            lines.append(m1_handling_call(line_prefix, m1_params, 0.0, retract_z, spindle.sign))
        lines.append("")
        depth = target

    return lines
