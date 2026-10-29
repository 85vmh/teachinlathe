import math
from typing import Optional

from teachinlathe.conversational.model.data_types import Tapping

from ..helpers.spindle import build_spindle_gcode
from ..toolpath import GcodeEmitter



def _peck_targets(tapping):
    """The Z each peck taps to, the last one Z End; one straight to Z End
    without a peck depth."""
    if tapping.peckDepth > 0.0 and abs(tapping.zEnd - tapping.zStart) > 0.0:
        total_depth = abs(tapping.zEnd - tapping.zStart)
        n_pecks = math.ceil(total_depth / tapping.peckDepth)
        sign = -1.0 if tapping.zEnd < tapping.zStart else 1.0
        return [tapping.zStart + sign * min((i + 1) * tapping.peckDepth, total_depth)
                for i in range(n_pecks)]
    return [tapping.zEnd]


def tapping_toolpath(op: Tapping, path: GcodeEmitter, pitch: Optional[float] = None):
    """``op``'s G-code, and its moves, onto ``path``: from the clearance in
    front of Z Start, rigid tapping (G33.1) a peck at a time, each back out to
    the clearance. ``pitch``: the tap's, from the Tool Library; the
    operation's own when None."""
    spindle = op.speedsAndFeeds
    tapping = op.tappingParameters
    m1_params = op.m1Parameters
    pitch = tapping.pitch if pitch is None or pitch <= 0 else pitch
    # the tap starts, and every peck comes back to, the clearance in front
    # of Z Start
    retract_z = tapping.zStart + abs(tapping.toolClearance)

    path.codes(build_spindle_gcode(spindle, "", force_rpm=True))
    path.rapid(0.0, retract_z)
    for z_target in _peck_targets(tapping):
        path.start_pass()
        path.rigid_tap(z_target, pitch)
        if m1_params.include_m1:
            path.inspect_stop(m1_params)
    path.rapid(z=retract_z)
