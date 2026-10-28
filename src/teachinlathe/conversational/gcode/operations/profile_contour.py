"""G-code generator for Profile Contour (OD and ID): the contour alone, planned
as Profile Roughing plans the one it finishes with (profiling/planner.py) -
tool-aware, compensated for the insert's nose - and written the same way."""

from teachinlathe.conversational.model.data_types import PassType, ProfileContourConfig

from ..helpers.spindle import build_spindle_gcode
from .profiling.operation_input import (
    NO_PROFILE,
    ProfileCut,
    common_config,
    profile_and_tool_key,
    profile_path,
    resolve_profile,
    resolve_tool_shape,
)
from .profiling.plan_drawing import chain_points, flatten_path
from ..toolpath import GcodeEmitter, OperationPreview, drawn_lines
from .profiling.plan_cache import PlanCache, plan_key
from .profiling.plan_gcode import write_plan


def parse_profile_contour_config(cut: ProfileCut) -> ProfileContourConfig:
    op = cut.op
    stock_enabled = bool(op.stockToLeaveEnabled)
    return ProfileContourConfig(
        **common_config(cut, op.profileContourStrategy.profiling_type),
        stock_x=float(op.stockToLeave.stockToLeaveX) if stock_enabled else 0.0,
        stock_z=float(op.stockToLeave.stockToLeaveZ) if stock_enabled else 0.0,
        stock_enabled=stock_enabled,
    )


#: Plans already worked out, by their inputs (contour_plan_key).
_PLANS = PlanCache()


def contour_plan_key(cut: ProfileCut) -> str:
    """What a Profile Contour's plan depends on: where it starts, the stock
    to leave, which way; the profile; the tool - not the feed, the spindle,
    its place in the program."""
    config = parse_profile_contour_config(cut)
    return plan_key(
        setup=[config.x_start, config.z_start, config.doc, config.retract, config.stock_x, config.stock_z,
               config.profiling_type.value],
        **profile_and_tool_key(cut),
    )


def plan_profile_contour(cut: ProfileCut):
    """The tool-aware plan of a Profile Contour - the contour alone, see
    profiling.planner - against ``cut``'s profile, with its tool: the same
    contour Profile Roughing finishes with, compensated for the insert's
    nose, bridged over what it cannot enter. The one kept when it was planned
    already with the same inputs (contour_plan_key)."""
    return _PLANS.get(contour_plan_key(cut), lambda: _plan(cut))


def _plan(cut: ProfileCut):
    from .profiling.plan import RoughingPlan, RoughingSetup
    from .profiling.planner import plan_contour

    config = parse_profile_contour_config(cut)
    path = profile_path(cut)
    if path is None:
        return RoughingPlan(error=NO_PROFILE)
    setup = RoughingSetup(
        x_start=config.x_start, z_start=config.z_start, doc=config.doc,
        retract=config.retract, stock_x=config.stock_x, stock_z=config.stock_z,
        profiling_type=config.profiling_type, pass_type=PassType.AXIAL)
    return plan_contour(setup, path, resolve_tool_shape(cut))


def profile_contour_toolpath(cut: ProfileCut, path: GcodeEmitter):
    """The G-code of a Profile Contour onto ``path``: the moves of its plan
    (plan_profile_contour) as the machine makes them - the control point,
    compensated for the nose, the profile's arcs as G2 / G3. The profile
    canvas draws the same plan."""
    config = parse_profile_contour_config(cut)

    path.codes(build_spindle_gcode(cut.op.speedsAndFeeds, ""))
    path.code(f"G95 F{config.feed_rate}")
    path.blank()

    plan = plan_profile_contour(cut)
    if plan.error:
        path.error(f"Profile Contour -- {plan.error}")
        return

    write_plan(path, plan, (config.stock_x, config.stock_z))


def generate_profile_contour_gcode(cut: ProfileCut):
    """A Profile Contour's G-code on its own."""
    path = GcodeEmitter(cut.op.is_optional_block)
    profile_contour_toolpath(cut, path)
    return path.lines


def profile_contour_preview(cut: ProfileCut) -> OperationPreview:
    """What a Profile Contour - as it is cut, ``cut`` - will cut, as the
    editor draws it, from the plan its G-code is written from
    (plan_profile_contour): the contour - in along Z from Z Start to where the
    profile begins, then along it - drawn where the nose touches, no rapids;
    the profile, and it offset by the stock to leave."""
    plan = plan_profile_contour(cut)
    if plan.error:
        return OperationPreview(error=plan.error)
    path = resolve_profile(cut)
    feeds, _rapids = drawn_lines(plan.moves)
    return OperationPreview(feeds=feeds, profile=flatten_path(path), offset=chain_points(plan.allowance),
                            warnings=tuple(plan.warnings))
