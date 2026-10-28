"""What the operations that follow a drawn profile are cut from, and where
it comes from in a program: Profile Roughing and Contour (ProfileCut,
profile_cut) and what both read of it alike - the profile, the tool, which
side they cut and where they start, and those as a plan's key has them - and
Groove Roughing and Finishing (GrooveCut, groove_cut)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple, Union

from teachinlathe.conversational.model.data_types import (
    DefineProfile, DefineRadialProfile, GrooveFinishing, GrooveRoughing, ProfileContour, ProfileRoughing,
    ProfilingType, Program, StockToLeave,
)
from teachinlathe.tooling.model.data_types import CuttingTool, MountedTool

from .geometry import StartPoint, build_path

log = logging.getLogger(__name__)

NO_PROFILE = "no valid profile found"


@dataclass(frozen=True)
class ProfileCut:
    """A Profile Roughing or Contour with what it is planned against: the
    profile it follows (None when the program has none of its id above it),
    the cutting tool it cuts with (None with none chosen, or one no longer as
    chosen) and, for a rest roughing, the Profile Roughings of the same
    profile above it, in order, each with what it is planned against."""
    op: Union[ProfileRoughing, ProfileContour]
    profile: Optional[DefineProfile] = None
    tool: Optional[CuttingTool] = None
    previous: Tuple["ProfileCut", ...] = ()


def profile_cut(program: Program, op_index: int, op, tools) -> ProfileCut:
    """``op`` - the Profile Roughing or Contour at ``op_index`` of
    ``program``, or a draft of it - with what it is planned against there.
    ``tools``: where its tool is looked up (the Tool Library, a ToolSnapshot);
    only a tool still as chosen is taken."""
    from teachinlathe.conversational.logic import program_tools

    profile_id = int(op.profilingParameters.profile_id or 0)
    above = program.operations[:max(op_index, 0)]
    # the first of its id above it, as the G-code takes it
    profile = next((o for o in above if isinstance(o, DefineProfile) and int(o.profile_id) == profile_id),
                   None) if profile_id else None
    check = program_tools.check_for(program, op, tools)
    tool = tools.tool_in(check.tool_holder_id) if check.status is program_tools.ToolStatus.OK else None
    previous = ()
    if isinstance(op, ProfileRoughing) and op.restMaterial:
        previous = tuple(profile_cut(program, index, prev, tools) for index, prev in enumerate(above)
                         if isinstance(prev, ProfileRoughing)
                         and int(prev.profilingParameters.profile_id or 0) == profile_id)
    return ProfileCut(op, profile, tool, previous)


def resolve_profile(cut: ProfileCut) -> list:
    """The path of the profile ``cut`` follows (geometry.build_path); empty
    without one."""
    if cut.profile is None:
        return []
    return build_path(cut.profile.profile_primitives, cut.profile.profile_type)


def profile_path(cut: ProfileCut):
    """The profile's path to plan along, or None when it has none: one that
    starts at a start point and goes somewhere from it."""
    path = resolve_profile(cut)
    if not path or not isinstance(path[0], StartPoint) or len(path) < 2:
        return None
    return path


def resolve_tool_shape(cut: ProfileCut):
    """The insert ``cut`` is made with, as a ToolShape; None when there is
    none to go by."""
    from .tool_shape import insert_tool_shape

    if cut.tool is None:
        return None
    try:
        return insert_tool_shape(cut.tool)
    except Exception:
        # planned with the stand-in square tool then: say why
        log.warning("roughing plan: the tool could not be read, planned without it", exc_info=True)
        return None


def profiling_type(cut: ProfileCut, strategy_type: ProfilingType) -> ProfilingType:
    """OD or ID: the profile's own, else what the operation's strategy says."""
    return cut.profile.profile_type if cut.profile is not None else ProfilingType(strategy_type)


def common_config(cut: ProfileCut, strategy_type: ProfilingType) -> dict:
    """The fields both operations' configs have, but the stock to leave:
    where they start, how deep and how far back, the feed, which side, and
    the optional-block prefix - as keyword arguments of the configs."""
    op = cut.op
    return dict(
        x_start=float(op.profilingParameters.xStart),
        z_start=float(op.profilingParameters.zStart),
        doc=float(op.cuttingParameters.doc),
        retract=float(op.cuttingParameters.retract),
        feed_rate=op.speedsAndFeeds.feed,
        profiling_type=profiling_type(cut, strategy_type),
        optional_prefix="/" if op.is_optional_block else "",
    )


def profile_and_tool_key(cut: ProfileCut) -> dict:
    """The profile and the tool, as a plan's key (plan_cache.plan_key) has them."""
    profile = cut.profile
    return dict(
        profile=([profile.profile_type.value, [p.to_dict() for p in profile.profile_primitives]]
                 if profile is not None else ["od", []]),
        tool=cut.tool.to_json() if cut.tool is not None else None,
    )


# ── grooves ─────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GrooveCut:
    """A Groove Roughing or Finishing with what it is cut against: the
    radial profile it cuts (None when the program has none of its id above
    it), the tool it cuts with as mounted (None with none chosen, or one no
    longer as chosen) and, for a finishing, the stock the Groove Roughing of
    its profile above left (None for none left)."""
    op: Union[GrooveRoughing, GrooveFinishing]
    radial_profile: Optional[DefineRadialProfile] = None
    tool: Optional[MountedTool] = None
    roughing_stock: Optional[StockToLeave] = None

    @property
    def profile_id(self) -> int:
        parameters = (self.op.finishingParameters if isinstance(self.op, GrooveFinishing)
                      else self.op.roughingParameters)
        return int(parameters.profile_id or 0)


def groove_cut(program: Program, op_index: int, op, tools) -> GrooveCut:
    """``op`` - the Groove Roughing or Finishing at ``op_index`` of
    ``program``, or a draft of it - with what it is cut against there.
    ``tools``: where its tool is looked up; only a tool still as chosen is
    taken."""
    from teachinlathe.conversational.logic import program_tools

    cut = GrooveCut(op)
    above = program.operations[:max(op_index, 0)]
    profile_id = cut.profile_id
    # the first of its id above it, as the G-code takes it
    radial_profile = next((o for o in above if isinstance(o, DefineRadialProfile)
                           and int(o.profile_id) == profile_id), None) if profile_id else None
    check = program_tools.check_for(program, op, tools)
    tool = (MountedTool.of(tools, check.tool_holder_id)
            if check.status is program_tools.ToolStatus.OK else None)
    stock = None
    if isinstance(op, GrooveFinishing):
        # what the last Groove Roughing of its profile above left
        roughing = next((o for o in reversed(above) if isinstance(o, GrooveRoughing)
                         and int(o.roughingParameters.profile_id or 0) == profile_id), None)
        if roughing is not None and roughing.stockToLeaveEnabled:
            stock = roughing.stockToLeave
    return GrooveCut(op, radial_profile, tool, stock)
