"""Which tools an operation can cut with.

One rule per operation that has its tool chosen in its editor: the kinds of
tool it takes (tooling's ToolKind), and for a groove how the tool must be
held. The editors' tool pickers show only the tools that fit, and a tool
that does not is never taken (program_tools.choose_tool) nor turned into
G-code (program_tools.not_ready).
"""

from __future__ import annotations

from teachinlathe.conversational.model.data_types import (
    DefineRadialProfile, Drilling, Facing, G33Threading, GrooveFinishing, GrooveRoughing, Parting,
    ProfileContour, ProfileRoughing, ProfilingType, Program, Tapping, ThreadLocation,
)
from teachinlathe.tooling.model.data_types import BladeTool, CuttingTool, ToolKind, TurningTool, kind_of

#: How a groove's tool is held - neutral - for an OD groove and an ID one.
NEUTRAL_ORIENTATION = {ProfilingType.OD: 6, ProfilingType.ID: 8}


def _is_id(profiling_type) -> bool:
    return ProfilingType(getattr(profiling_type, "value", profiling_type) or "od") is ProfilingType.ID


def _radial_profile_type(program: Program, op, profile_id: int):
    """The type of the radial profile a groove at ``op`` cuts: the Define
    Radial Profile ``profile_id`` above it - the last one above with no id."""
    index = next(i for i, o in enumerate(program.operations) if o is op)
    for other in reversed(program.operations[:index]):
        if isinstance(other, DefineRadialProfile) and (not profile_id or int(other.profile_id) == profile_id):
            return other.profile_type
    return ProfilingType.OD


def _profile_kinds(profiling_type):
    return {ToolKind.BORING} if _is_id(profiling_type) else {ToolKind.TURNING}


def _groove_fits(program, op, tool, profile_id) -> bool:
    # a blade, or a turning tool, held neutral
    if not isinstance(tool, (BladeTool, TurningTool)):
        return False
    profile_type = _radial_profile_type(program, op, int(profile_id or 0))
    neutral = NEUTRAL_ORIENTATION[ProfilingType.ID if _is_id(profile_type) else ProfilingType.OD]
    return int(tool.orientation) == neutral


def fits(program: Program, op, tool: CuttingTool) -> bool:
    """Whether operation ``op`` of ``program`` can cut with ``tool``."""
    if tool is None:
        return False
    if isinstance(op, GrooveRoughing):
        return _groove_fits(program, op, tool, op.roughingParameters.profile_id)
    if isinstance(op, GrooveFinishing):
        return _groove_fits(program, op, tool, op.finishingParameters.profile_id)
    if isinstance(op, Facing):
        kinds = {ToolKind.TURNING, ToolKind.PARTING_BLADE}
    elif isinstance(op, ProfileRoughing):
        kinds = _profile_kinds(op.profileRoughingStrategy.profiling_type)
    elif isinstance(op, ProfileContour):
        kinds = _profile_kinds(op.profileContourStrategy.profiling_type)
    elif isinstance(op, G33Threading):
        kinds = {ToolKind.ID_THREADING if op.location == ThreadLocation.ID else ToolKind.OD_THREADING}
    elif isinstance(op, Drilling):
        kinds = {ToolKind.DRILL}
    elif isinstance(op, Tapping):
        kinds = {ToolKind.TAP}
    elif isinstance(op, Parting):
        kinds = {ToolKind.PARTING_BLADE}
    else:
        # its tool is not chosen in its editor (yet): none fits
        return False
    return kind_of(tool) in kinds
