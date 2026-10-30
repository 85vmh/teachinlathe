"""What the operations that follow a drawn profile are cut from, and where
it comes from in a program: Profile Roughing and Contour (ProfileCut,
profile_cut) and what both read of it alike - the profile, the tool, which
side they cut and where they start, and those as a plan's key has them - and
Groove Roughing and Finishing (GrooveCut, groove_cut).

The stock each finds (``stock``, a stock.StockBefore) is the program's:
a program's toolpath hands over its own as it goes; an operation on its own
- its editor - has it worked out from those above it (with_stock). None:
not worked out, nothing of it known."""

from __future__ import annotations

import dataclasses
import logging
from dataclasses import dataclass
from typing import Optional, Union

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
    chosen), the stock it finds (see the module), and for a rest roughing
    its source - the last Profile Roughing of the same profile above it that
    is not rest material itself, whose start and stock to leave it keeps -
    and the nose radius of the last tool that roughed that profile."""
    op: Union[ProfileRoughing, ProfileContour]
    profile: Optional[DefineProfile] = None
    tool: Optional[CuttingTool] = None
    stock: Optional["StockBefore"] = None
    source: Optional[ProfileRoughing] = None
    last_nose_radius: float = 0.0


def profile_cut(program: Program, op_index: int, op, tools, stock=None) -> ProfileCut:
    """``op`` - the Profile Roughing or Contour at ``op_index`` of
    ``program``, or a draft of it - with what it is planned against there.
    ``tools``: where its tool is looked up (the Tool Library, a ToolSnapshot);
    only a tool still as chosen is taken. ``stock``: what it finds there, a
    StockBefore."""
    from teachinlathe.conversational.logic import program_tools

    profile_id = int(op.profilingParameters.profile_id or 0)
    above = program.operations[:max(op_index, 0)]
    # the first of its id above it, as the G-code takes it
    profile = next((o for o in above if isinstance(o, DefineProfile) and int(o.profile_id) == profile_id),
                   None) if profile_id else None
    check = program_tools.check_for(program, op, tools)
    tool = tools.tool_in(check.tool_holder_id) if check.status is program_tools.ToolStatus.OK else None
    source, nose_radius = None, 0.0
    if isinstance(op, ProfileRoughing) and op.restMaterial:
        for prev in above:
            if not (isinstance(prev, ProfileRoughing) and int(prev.profilingParameters.profile_id or 0) == profile_id):
                continue
            if not prev.restMaterial:
                source = prev
            prev_check = program_tools.check_for(program, prev, tools)
            prev_tool = (tools.tool_in(prev_check.tool_holder_id)
                         if prev_check.status is program_tools.ToolStatus.OK else None)
            shape = resolve_tool_shape(ProfileCut(prev, tool=prev_tool))
            if shape is not None:
                nose_radius = shape.nose_radius
    return ProfileCut(op, profile, tool, stock, source, nose_radius)


def with_stock(cut, program: Program, op_index: int, tools):
    """``cut`` - a ProfileCut or a GrooveCut, of the operation at
    ``op_index`` of ``program`` - with the stock it finds there
    (stock.stock_before), when it has none yet."""
    from ...stock import stock_before

    if cut.stock is not None:
        return cut
    return dataclasses.replace(cut, stock=stock_before(program, op_index, tools))


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
    longer as chosen), for a finishing the stock to leave of the Groove
    Roughing of its profile above (None for none left), and the stock it
    finds (see the module)."""
    op: Union[GrooveRoughing, GrooveFinishing]
    radial_profile: Optional[DefineRadialProfile] = None
    tool: Optional[MountedTool] = None
    roughing_stock: Optional[StockToLeave] = None
    stock: Optional["StockBefore"] = None

    @property
    def profile_id(self) -> int:
        parameters = (self.op.finishingParameters if isinstance(self.op, GrooveFinishing)
                      else self.op.roughingParameters)
        return int(parameters.profile_id or 0)


def groove_cut(program: Program, op_index: int, op, tools, stock=None) -> GrooveCut:
    """``op`` - the Groove Roughing or Finishing at ``op_index`` of
    ``program``, or a draft of it - with what it is cut against there.
    ``tools``: where its tool is looked up; only a tool still as chosen is
    taken. ``stock``: what it finds there, a StockBefore."""
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
    roughing_stock = None
    if isinstance(op, GrooveFinishing):
        # what the last Groove Roughing of its profile above left
        roughing = next((o for o in reversed(above) if isinstance(o, GrooveRoughing)
                         and int(o.roughingParameters.profile_id or 0) == profile_id), None)
        if roughing is not None and roughing.stockToLeaveEnabled:
            roughing_stock = roughing.stockToLeave
    return GrooveCut(op, radial_profile, tool, roughing_stock, stock)
