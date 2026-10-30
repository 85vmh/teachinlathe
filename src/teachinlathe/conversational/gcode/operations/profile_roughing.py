"""G-code generator for Profile Roughing (OD and ID).

The moves are planned by profiling/planner.py, tool and all, for the
ProfilingType (OD/ID) and PassType (AXIAL / RADIAL / DIAGONAL_*); this reads
the operation, finds its profile and tool, keeps the plans made, and writes the
G-code of a plan.
"""

import dataclasses
from dataclasses import dataclass
from typing import Tuple

from teachinlathe.conversational.model.data_types import PassType, ProfileRoughingConfig

from ..helpers.spindle import build_feed_gcode, build_spindle_gcode
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
from ..toolpath import GcodeEmitter, OperationPreview, Point, drawn_lines
from .profiling.plan_cache import PlanCache, plan_key
from .profiling.plan_gcode import write_plan


def _pass_type_label(pass_type: PassType) -> str:
    angle = f"{_diagonal_angle():g}°"
    return {
        PassType.AXIAL: "Axial Passes",
        PassType.RADIAL: "Radial Passes",
        PassType.DIAGONAL_INTERIOR: f"{angle} Passes toward interior",
        PassType.DIAGONAL_EXTERIOR: f"{angle} Passes toward exterior",
    }.get(pass_type, str(pass_type.value if hasattr(pass_type, "value") else pass_type))


def _diagonal_angle() -> float:
    """The angle diagonal passes run at: the constant for now (profiling.plan),
    read when planning, not when this module was loaded."""
    from .profiling import plan
    return plan.DIAGONAL_ANGLE


def parse_profile_roughing_config(cut: ProfileCut) -> ProfileRoughingConfig:
    strategy = cut.op.profileRoughingStrategy
    stock = cut.op.stockToLeave
    return ProfileRoughingConfig(
        **common_config(cut, strategy.profiling_type),
        stock_x=float(stock.stockToLeaveX),
        stock_z=float(stock.stockToLeaveZ),
        pass_type=strategy.pass_type,
    )


def profile_roughing_toolpath(cut: ProfileCut, path: GcodeEmitter):
    """The G-code of a Profile Roughing onto ``path``: the moves of its
    tool-aware plan (plan_profile_roughing) as the machine makes them -
    compensated for the insert's nose, every one checked against the part
    and what is left of the stock. The profile canvas draws the same plan."""
    op = cut.op
    config = parse_profile_roughing_config(cut)

    path.codes(build_spindle_gcode(op.speedsAndFeeds, ""))
    path.code(build_feed_gcode(config.feed_rate))
    path.blank()

    plan = plan_profile_roughing(cut)
    if plan.error:
        path.error(f"Profile Roughing -- {plan.error}")
        return

    write_plan(path, plan, (config.stock_x, config.stock_z), op.m1Parameters,
               title=f"(---Profiling Type: {_pass_type_label(config.pass_type)}---)")


def generate_profile_roughing_gcode(cut: ProfileCut):
    """A Profile Roughing's G-code on its own."""
    path = GcodeEmitter(cut.op.is_optional_block)
    profile_roughing_toolpath(cut, path)
    return path.lines


#: Plans already worked out, by their inputs (roughing_plan_key): the
#: preview's plan is the one the G-code is written from.
_PLANS = PlanCache()

_NO_SOURCE = "rest material, but no Profile Roughing of this profile above it"
_CHOOSE_TOOL = "Choose the tool to cut what is left"


def _planned_config(cut: ProfileCut) -> ProfileRoughingConfig:
    """The config a Profile Roughing is planned with: its own - a rest
    roughing's with its source's start position and stock to leave: the same
    finished size, and the same bar."""
    config = parse_profile_roughing_config(cut)
    if cut.op.restMaterial and cut.source is not None:
        source_config = parse_profile_roughing_config(dataclasses.replace(cut, op=cut.source))
        config = dataclasses.replace(
            config, x_start=source_config.x_start, z_start=source_config.z_start,
            stock_x=source_config.stock_x, stock_z=source_config.stock_z)
    return config


def roughing_plan_key(cut: ProfileCut) -> str:
    """What a Profile Roughing's plan depends on, and nothing else - not the
    feed, the spindle, M1, its place in the program, the workpiece drawn
    with the profile: where it starts and cuts, how deep and how much it
    leaves, which way; the profile; the tool; the stock it finds; and for
    rest material whether it has a source and the last tool's nose."""
    config = _planned_config(cut)
    rest = cut.op.restMaterial
    return plan_key(
        setup=[config.x_start, config.z_start, config.doc, config.retract, config.stock_x, config.stock_z,
               config.profiling_type.value, config.pass_type.value, _diagonal_angle()],
        **profile_and_tool_key(cut),
        stock=cut.stock.key() if cut.stock is not None else None,
        rest=[cut.source is not None, cut.last_nose_radius] if rest else None,
    )


def plan_profile_roughing(cut: ProfileCut):
    """The tool-aware plan of a Profile Roughing - see profiling.planner -
    against ``cut``'s profile, with its tool, from the stock it finds; the
    one kept when it was planned already with the same inputs
    (roughing_plan_key).

    Rest material (``restMaterial``): it keeps to the stock to leave and the
    start position of its source, the last Profile Roughing above it on the
    same profile that is not rest material itself, and cuts what the
    operations above leave of that - the stock it finds."""
    return _PLANS.get(roughing_plan_key(cut), lambda: _plan(cut))


def _plan(cut: ProfileCut):
    from .profiling.plan import RoughingPlan, RoughingSetup
    from .profiling.planner import plan_leftover, plan_roughing

    path = profile_path(cut)
    if path is None:
        return RoughingPlan(error=NO_PROFILE)
    rest = cut.op.restMaterial
    if rest and cut.source is None:
        return RoughingPlan(error=_NO_SOURCE)
    config = _planned_config(cut)
    air = cut.stock.air if cut.stock is not None else None
    setup = RoughingSetup(
        x_start=config.x_start, z_start=config.z_start, doc=config.doc,
        retract=config.retract, stock_x=config.stock_x, stock_z=config.stock_z,
        profiling_type=config.profiling_type, pass_type=config.pass_type,
        diagonal_angle=_diagonal_angle())
    tool = resolve_tool_shape(cut)
    if rest and tool is None:
        plan = plan_leftover(setup, path, cut.last_nose_radius, air_before=air)
        plan.warnings.insert(0, _CHOOSE_TOOL)
        return plan
    return plan_roughing(setup, path, tool, rest=rest,
                         sliver_radius=cut.last_nose_radius if rest else 0.0, air_before=air)


# ── what the editor draws ───────────────────────────────────────────────────

@dataclass(frozen=True)
class ProfileRoughingPreview(OperationPreview):
    """A Profile Roughing as the editor draws it, from the plan its G-code is
    written from (plan_profile_roughing): the cuts - the final contour pass
    included, drawn where the nose touches - and the rapids between them; the
    profile, and the line the stock to leave is kept to across it, on every
    face - the ones turned toward the chuck too. ``residual`` the material
    left for another tool, ``rest_offered`` whether a rest roughing can be
    added for it: there is some, and a tool that cut this one - not a rest
    roughing still waiting for its tool."""
    residual: Tuple[Tuple[Point, ...], ...] = ()
    rest_offered: bool = False


def profile_roughing_preview(cut: ProfileCut) -> ProfileRoughingPreview:
    """What a Profile Roughing - as it is cut, ``cut`` - will cut, as the
    editor draws it (ProfileRoughingPreview)."""
    plan = plan_profile_roughing(cut)
    if plan.error:
        return ProfileRoughingPreview(error=plan.error)
    path = resolve_profile(cut)
    feeds, rapids = drawn_lines(plan.moves)
    return ProfileRoughingPreview(
        feeds=feeds, rapids=rapids, profile=flatten_path(path), offset=chain_points(plan.allowance),
        warnings=tuple(plan.warnings),
        residual=tuple(chain_points(region) for region in plan.residual),
        rest_offered=bool(plan.residual and plan.tool is not None and plan.tool.known))
