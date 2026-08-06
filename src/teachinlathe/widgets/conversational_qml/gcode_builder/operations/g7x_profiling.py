from teachinlathe.conversational.data_types import Profiling, Strategy

from ..config import fmt
from ..helpers.spindle import build_spindle_gcode



def generate_profiling_gcode(op: Profiling):
    line_prefix = "/" if op.is_optional_block else ""

    spindle = op.spindleParameters
    cutting = op.cuttingParameters
    params = op.profilingParameters
    options = op.profilingOptions

    stock = max(options.stockToLeaveX, options.stockToLeaveZ)
    finish_passes = max(1, int(options.finishPasses))
    spring_passes = max(0, int(options.finishSpringPasses))

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(f"{line_prefix}G95 F{cutting.feedRate}")
    lines.append("")

    if options.strategy == Strategy.FINISH:
        passes = finish_passes + spring_passes
        lines.append(
            f"{line_prefix}G70 Q{int(params.profile_id)} X{fmt(params.xStart)} Z{fmt(params.zStart)} D{fmt(stock)} E0 P{passes}"
        )
    else:
        lines.append(
            f"{line_prefix}G71.1 Q{int(params.profile_id)} X{fmt(params.xStart)} Z{fmt(params.zStart)} D{fmt(stock)} I{fmt(cutting.doc)} R{fmt(cutting.retract)}"
        )
    return lines
