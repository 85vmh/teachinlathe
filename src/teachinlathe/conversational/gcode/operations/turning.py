"""OD Turning, planned as a three-primitive OD profile."""

from dataclasses import dataclass

from teachinlathe.conversational.model.data_types import (
    BlendType, DefineProfile, LineTo, PassType, ProfileBlend, ProfilingType,
    StartPoint, Turning,
)

from ..helpers.spindle import build_feed_gcode, build_spindle_gcode
from ..toolpath import GcodeEmitter, OperationPreview
from .profiling.geometry import build_path
from .profiling.plan import RoughingSetup
from .profiling.plan import RoughingPlan
from .profiling.plan_drawing import chain_points, flatten_path
from .profiling.planner import plan_roughing
from .profiling.tool_shape import insert_tool_shape
from .profiling.plan_gcode import write_plan


@dataclass(frozen=True)
class TurningPlan:
    roughing: RoughingPlan = None
    profile: list = None
    error: str = ""


def _profile_blend(blend):
    return ProfileBlend(
        blend_type=blend.blend_type,
        chamfer_width=max(0.0, float(blend.chamfer_width)),
        fillet_radius=max(0.0, float(blend.fillet_radius)),
    )


def turning_profile(op: Turning):
    """P1/P2 define an OD contour with the same primitives used by profiling."""
    g = op.geometryParameters
    return DefineProfile(
        order=op.order, type="defineProfile", generate_gcode=False,
        is_optional_block=False, profile_id=0, profile_type=ProfilingType.OD,
        profile_primitives=[
            StartPoint(1, "startPoint", float(g.xEnd), float(g.zStart), _profile_blend(g.startBlend)),
            LineTo(2, "lineTo", float(g.xEnd), float(g.zEnd), _profile_blend(g.shoulderBlend)),
            LineTo(3, "lineTo", float(g.xStart), float(g.zEnd),
                   ProfileBlend(blend_type=BlendType.NONE)),
        ],
    )


def plan_turning(op: Turning, tool=None) -> TurningPlan:
    g, c = op.geometryParameters, op.cuttingParameters
    ap, clearance = float(c.ap), float(c.toolClearance)
    if ap <= 0:
        return TurningPlan(error="Ap must be greater than zero")
    if clearance < 0:
        return TurningPlan(error="Tool clearance cannot be negative")
    if g.xStart <= g.xEnd or g.xEnd <= 0:
        return TurningPlan(error="P1 X must be greater than P2 X for OD turning")
    if g.zStart <= g.zEnd:
        return TurningPlan(error="P1 Z must be greater than P2 Z")

    profile = turning_profile(op)
    profile_path = build_path(profile.profile_primitives, profile.profile_type)
    try:
        tool_shape = insert_tool_shape(tool) if tool is not None else None
    except Exception:
        tool_shape = None
    setup = RoughingSetup(
        x_start=float(g.xStart) + 2 * clearance,
        z_start=float(g.zStart) + clearance,
        doc=ap,
        # Retract half an Ap between cuts, as defined for Turning.
        retract=ap / 2,
        stock_x=max(0.0, float(op.stockToLeave.stockToLeaveX)),
        stock_z=max(0.0, float(op.stockToLeave.stockToLeaveZ)),
        profiling_type=ProfilingType.OD,
        pass_type=op.passType if op.passType in (PassType.AXIAL, PassType.RADIAL) else PassType.AXIAL,
    )
    roughing = plan_roughing(setup, profile_path, tool_shape)
    return TurningPlan(roughing, profile_path, roughing.error)


def turning_toolpath(op: Turning, path: GcodeEmitter, program=None, tools=None):
    tool = None
    if program is not None and tools is not None:
        try:
            from teachinlathe.conversational.logic import program_tools
            check = program_tools.check_for(program, op, tools)
            if check.status is program_tools.ToolStatus.OK:
                tool = tools.tool_in(check.tool_holder_id)
        except Exception:
            tool = None
    plan = plan_turning(op, tool)
    if plan.error:
        path.error(f"Turning -- {plan.error}")
        return

    path.codes(build_spindle_gcode(op.speedsAndFeeds, ""))
    path.code(build_feed_gcode(op.speedsAndFeeds.feed))
    path.blank()
    stock = (float(op.stockToLeave.stockToLeaveX), float(op.stockToLeave.stockToLeaveZ))
    write_plan(path, plan.roughing, stock, op.m1Parameters,
               title=f"(---Profiling Type: {op.passType.value.title()} Passes---)")


def generate_turning_gcode(op: Turning):
    path = GcodeEmitter(op.is_optional_block)
    turning_toolpath(op, path)
    return path.lines


def turning_preview(op: Turning, tool=None) -> OperationPreview:
    plan = plan_turning(op, tool)
    if plan.error:
        return OperationPreview(error=plan.error)
    feeds, rapids = [], []
    from ..toolpath import drawn_lines
    feeds, rapids = drawn_lines(plan.roughing.moves)
    return OperationPreview(
        feeds=feeds, rapids=rapids,
        profile=flatten_path(plan.profile),
        offset=chain_points(plan.roughing.allowance),
        warnings=tuple(plan.roughing.warnings),
    )
