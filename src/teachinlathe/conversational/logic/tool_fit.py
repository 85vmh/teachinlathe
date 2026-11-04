"""Which tools an operation can cut with.

One rule per operation that has its tool chosen in its editor: the kinds of
tool it takes (tooling's ToolKind), and for a groove how the tool must be
held. The editors' tool pickers show only the tools that fit, and a tool
that does not is never taken (program_tools.choose_tool) nor turned into
G-code (program_tools.not_ready).
"""

from __future__ import annotations

from teachinlathe.conversational.model.data_types import (
    DefineRadialProfile, Drilling, Facing, G33Threading, GrooveBidirectional, GrooveFinishing, GrooveRoughing,
    Parting,
    ProfileContour, ProfileRoughing, ProfilingType, Program, Tapping, ThreadLocation, Turning, TurningFinish,
)
from teachinlathe.tooling.model.data_types import BladeTool, CuttingTool, ToolKind, TurningTool, kind_of

#: How a groove's tool is held - neutral - for an OD groove and an ID one.
NEUTRAL_ORIENTATION = {ProfilingType.OD: 6, ProfilingType.ID: 8}


def _is_id(profiling_type) -> bool:
    return ProfilingType(getattr(profiling_type, "value", profiling_type) or "od") is ProfilingType.ID


def _radial_profile(program: Program, op, profile_id: int):
    """The radial profile a groove at ``op`` cuts: the Define Radial Profile
    ``profile_id`` above it - the last one above with no id - or None."""
    index = program.index_of(op)
    for other in reversed(program.operations[:index]):
        if isinstance(other, DefineRadialProfile) and (not profile_id or int(other.profile_id) == profile_id):
            return other
    return None


def _radial_profile_type(program: Program, op, profile_id: int):
    """The type of the radial profile a groove at ``op`` cuts; OD with none."""
    profile = _radial_profile(program, op, profile_id)
    return profile.profile_type if profile is not None else ProfilingType.OD


def _profile_kinds(profiling_type):
    return {ToolKind.BORING} if _is_id(profiling_type) else {ToolKind.TURNING}


def _groove_fits(program, op, tool) -> bool:
    # a blade, or a turning tool, held neutral
    if not isinstance(tool, (BladeTool, TurningTool)):
        return False
    profile_type = _radial_profile_type(program, op, op.radial_profile_id)
    neutral = NEUTRAL_ORIENTATION[ProfilingType.ID if _is_id(profile_type) else ProfilingType.OD]
    return int(tool.orientation) == neutral


#: The inserts a BiDirectional Grooving cuts with, held neutral: a round one
#: as wide as the groove's mouth at most, and these - their corner angle
#: (inserts.RHOMBIC_ANGLE) - when half of it is less than either flank's.
BIDIRECTIONAL_ROUND_INSERT = "RCMT"
BIDIRECTIONAL_POINTED_INSERTS = ("DCMT", "VBMT")


def _bidirectional_fits(program, op, tool) -> bool:
    """An OD groove's tool held neutral: a blade, or a round insert, no
    wider than the groove's mouth - it goes down as far as it fits - or a
    DCMT or VBMT whose corner leans less than either flank, so it goes down
    them both."""
    from teachinlathe.tooling.model import insert_catalog
    from teachinlathe.tooling.model.inserts import RHOMBIC_ANGLE

    profile = _radial_profile(program, op, op.radial_profile_id)
    groove = profile.first_groove() if profile is not None else None
    if groove is None or _is_id(profile.profile_type):
        return False
    if int(getattr(tool, "orientation", 0)) != NEUTRAL_ORIENTATION[ProfilingType.OD]:
        return False
    mouth = abs(groove.right_flank.z_start - groove.left_flank.z_start)
    if isinstance(tool, BladeTool):
        return 0.0 < float(tool.blade_width) <= mouth
    if kind_of(tool) is not ToolKind.TURNING:
        return False
    family = insert_catalog.family_of(tool.insert)
    if family == BIDIRECTIONAL_ROUND_INSERT:
        return insert_catalog.insert_for(tool.insert).ic <= mouth
    if family in BIDIRECTIONAL_POINTED_INSERTS:
        half_angle = RHOMBIC_ANGLE[family[0]] / 2.0
        return half_angle < min(abs(groove.right_flank.angle), abs(groove.left_flank.angle))
    return False


def fits(program: Program, op, tool: CuttingTool) -> bool:
    """Whether operation ``op`` of ``program`` can cut with ``tool``."""
    if tool is None:
        return False
    if isinstance(op, GrooveBidirectional):
        return _bidirectional_fits(program, op, tool)
    if isinstance(op, (GrooveRoughing, GrooveFinishing)):
        return _groove_fits(program, op, tool)
    if isinstance(op, Facing):
        kinds = {ToolKind.TURNING, ToolKind.PARTING_BLADE}
    elif isinstance(op, (Turning, TurningFinish)):
        kinds = {ToolKind.TURNING}
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
