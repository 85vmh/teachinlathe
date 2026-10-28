"""Drilling: from the clearance in front of Z Start, a peck at a time down
to Z End, back out to the clearance after each, and in again at a rapid to
just short of the depth already drilled.

drilling_toolpath writes the G-code and keeps its moves, so the editor's
drawing (drilling_preview) is the G-code's.
"""

from typing import Optional

from teachinlathe.conversational.model.data_types import Drilling, Program

from ..helpers.spindle import build_spindle_gcode
from ..toolpath import GcodeEmitter, OperationPreview


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


def drilling_toolpath(op: Drilling, path: GcodeEmitter, program: Optional[Program] = None):
    """``op``'s G-code, and its moves - a pass a peck - onto ``path``."""
    spindle = op.speedsAndFeeds
    drilling = op.drillingParameters
    m1_params = op.m1Parameters

    # the drill starts, and every peck retracts, the clearance in front of
    # Z Start
    retract_z = drilling.zStart + abs(drilling.toolClearance)
    dwell = max(0.0, drilling.dwellTime)
    targets = _peck_targets(drilling.zStart, drilling.zEnd, drilling.peckDepth)

    if not targets:
        path.error("Drilling -- Z End is not past Z Start")
        return

    path.codes(build_spindle_gcode(spindle, "", force_rpm=True))
    path.rapid(x=0)
    path.code(f"G95 F{spindle.feed_rate}")
    path.rapid(z=retract_z)
    path.blank()

    depth = drilling.zStart
    for index, target in enumerate(targets):
        path.start_pass()
        # back in at a rapid, to just short of the depth already drilled
        if depth < retract_z:
            path.rapid(z=depth + REENTRY_CLEARANCE)
        path.feed(z=target)
        if dwell > 0:
            path.dwell(dwell)
        path.rapid(z=retract_z)
        # between pecks, not after the last
        if index < len(targets) - 1 and m1_params.include_m1:
            path.inspect_stop(m1_params, spindle.sign)
        path.blank()
        depth = target


def drilling_preview(op: Drilling) -> OperationPreview:
    """What ``op`` cuts, as its editor draws it: its G-code's moves - a feed
    each peck, to the depth it goes to."""
    path = GcodeEmitter(op.is_optional_block)
    drilling_toolpath(op, path)
    return path.preview()
