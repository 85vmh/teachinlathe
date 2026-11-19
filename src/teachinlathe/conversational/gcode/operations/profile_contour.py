"""G-code generator for Profile Contour (OD and ID): the contour alone, in one
pass or more from the stock on the part down to the profile, each planned as
Profile Roughing plans the one it finishes with (profiling/planner.py) -
tool-aware, compensated for the insert's nose - and written the same way."""

import dataclasses
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from teachinlathe.conversational.model.data_types import (
    FinishingDirection, PassType, ProfileContour, ProfileContourConfig, TurningFinish,
    ProfilingType,
)

from ..helpers.spindle import build_feed_gcode, build_spindle_gcode
from .profiling.operation_input import (
    NO_PROFILE,
    ProfileCut,
    profile_and_tool_key,
    profiling_type,
    profile_path,
    resolve_profile,
    resolve_tool_shape,
)
from .profiling.plan_drawing import chain_points, flatten_path
from ..config import fmt
from ..toolpath import Arrows, GcodeEmitter, OperationPreview, comment, drawn_lines
from .profiling.plan import RoughingPlan, RoughingSetup
from .profiling.plan_cache import PlanCache, plan_key
from .profiling.plan_gcode import emit_moves, write_home
from .profiling.shapes import FAR, _mirror
from .profiling.tool_shape import ToolShape


#: How far off P1 a Turning-Finish starts and ends, on both axes (mm).
TURNING_FINISH_CLEARANCE = 0.5


def parse_profile_contour_config(cut: ProfileCut) -> ProfileContourConfig:
    """What the Profile Contour or Turning-Finish ``cut`` is planned from: P1
    - a Profile Contour starts there, a Turning-Finish TURNING_FINISH_CLEARANCE
    off it - its stock and passes, the feed, which side."""
    op = cut.op
    finish = isinstance(op, TurningFinish)
    if finish:
        x_start, z_start = op.p1X, op.p1Z
    else:
        x_start, z_start = op.profilingParameters.xStart, op.profilingParameters.zStart
    return ProfileContourConfig(
        x_start=float(x_start), z_start=float(z_start),
        retract=TURNING_FINISH_CLEARANCE if finish else 0.0,
        feed_rate=op.speedsAndFeeds.feed,
        stock_x=float(op.initialStockToLeave.stockToLeaveX),
        stock_z=float(op.initialStockToLeave.stockToLeaveZ),
        passes=op.passesCount,
        profiling_type=(ProfilingType.OD if finish
                        else profiling_type(cut, op.profileContourStrategy.profiling_type)),
        optional_prefix="/" if op.is_optional_block else "",
    )


def pass_stocks(config: ProfileContourConfig):
    """The stock each pass leaves, (radial, axial), the first first: the
    initial stock taken off in equal steps, on X and on Z apart - the last
    pass on the profile."""
    n = config.passes
    return [(config.stock_x * (n - k) / n, config.stock_z * (n - k) / n) for k in range(1, n + 1)]


@dataclass
class ContourPass:
    """One pass of a Profile Contour or a Turning-Finish: its plan, and the
    stock it leaves."""
    plan: RoughingPlan
    stock: Tuple[float, float]


@dataclass
class ContourPlan:
    """A Profile Contour's or a Turning-Finish's passes, planned
    (plan_profile_contour): each from its start point along the profile
    offset by the stock it leaves, and back; ``allowance`` the profile offset
    by the initial stock - what is there before the first - and
    ``part_at_most`` the part as that says it is, (z, r): with its stock, no
    more, as far back as the profile goes (OperationPath.part_at_most)."""
    passes: List[ContourPass] = field(default_factory=list)
    allowance: list = field(default_factory=list)
    part_at_most: object = None
    tool: Optional[ToolShape] = None
    warnings: List[str] = field(default_factory=list)
    error: str = ""


#: Plans already worked out, by their inputs (contour_plan_key).
_PLANS = PlanCache()


def contour_plan_key(cut: ProfileCut) -> str:
    """What a Profile Contour's plan depends on: where it starts, the stock
    and its passes, which way; the profile; the tool - not the feed, the
    spindle, its place in the program."""
    config = parse_profile_contour_config(cut)
    return plan_key(
        setup=[config.x_start, config.z_start, config.retract, config.stock_x, config.stock_z,
               config.passes, config.profiling_type.value, _contour_pass_type(cut).value,
               _home_z_first(cut)],
        **profile_and_tool_key(cut),
    )


def _contour_pass_type(cut: ProfileCut) -> PassType:
    direction = None
    if isinstance(cut.op, TurningFinish):
        direction = cut.op.finishingDirection
    elif isinstance(cut.op, ProfileContour):
        direction = cut.op.profileContourStrategy.finishing_direction
    if direction is FinishingDirection.TOWARDS_Z_PLUS:
        return PassType.RADIAL
    return PassType.AXIAL


def _home_z_first(cut: ProfileCut) -> bool:
    """Back to P1 along Z first, then X, from where a pass ends - not out
    along X first: a Profile Contour after every pass, a Turning-Finish
    toward Z-, which ends on the shoulder's largest diameter."""
    if isinstance(cut.op, ProfileContour):
        return True
    return isinstance(cut.op, TurningFinish) and _contour_pass_type(cut) is PassType.AXIAL


def plan_profile_contour(cut: ProfileCut) -> ContourPlan:
    """The tool-aware plan of a Profile Contour - its passes, each the
    contour alone, see profiling.planner - against ``cut``'s profile, with
    its tool: the same contour Profile Roughing finishes with, compensated
    for the insert's nose, bridged over what it cannot enter. The one kept
    when it was planned already with the same inputs (contour_plan_key)."""
    return _PLANS.get(contour_plan_key(cut), lambda: _plan(cut))


def _plan(cut: ProfileCut) -> ContourPlan:
    from .profiling.planner import _Planner, plan_contour

    config = parse_profile_contour_config(cut)
    path = profile_path(cut)
    if path is None:
        return ContourPlan(error=NO_PROFILE)
    tool = resolve_tool_shape(cut)

    def setup(stock_x, stock_z):
        # the contour alone: no passes of a depth
        return RoughingSetup(
            x_start=config.x_start, z_start=config.z_start, doc=0.0,
            retract=config.retract, stock_x=stock_x, stock_z=stock_z,
            profiling_type=config.profiling_type,
            pass_type=_contour_pass_type(cut), home_z_first=_home_z_first(cut))

    result = ContourPlan()
    stocks = pass_stocks(config)
    for k, stock in enumerate(stocks):
        plan = plan_contour(setup(*stock), path, tool)
        if plan.error:
            return ContourPlan(error=plan.error, tool=plan.tool)
        if k < len(stocks) - 1 and plan.home_blocked:
            return ContourPlan(error=f"pass {k + 1}: {plan.home_blocked}", tool=plan.tool)
        result.passes.append(ContourPass(plan, stock))
        result.tool = plan.tool
        result.warnings.extend(w for w in plan.warnings if w not in result.warnings)
    # the part with the initial stock on it: what there is before the first
    initial = _Planner(setup(config.stock_x, config.stock_z), path, tool, Polygon(), False, 0.0)
    result.allowance = initial.allowance_chain()
    # past the profile's end nothing is known: nothing said there
    part = unary_union([initial.part_allow, box(initial.z_end_limit - FAR, -FAR, initial.z_end_limit, FAR)])
    result.part_at_most = _mirror(part) if initial.is_id else part
    return result


def profile_contour_toolpath(cut: ProfileCut, path: GcodeEmitter, return_to_start: bool = False):
    """The G-code of a Profile Contour or a Turning-Finish onto ``path``: the
    moves of its passes (plan_profile_contour) as the machine makes them -
    the control point, compensated for the nose, the profile's arcs as G2 /
    G3 - each back to its start point (write_home) - where it ends the nose
    is on the part - and a Pause to Inspect there when it asks for one, so
    it comes back to the start point from it too. The profile canvas draws
    the same plan. ``return_to_start`` (the writers' signature,
    gcode_builder) changes nothing: it goes back always."""
    config = parse_profile_contour_config(cut)
    op = cut.op

    path.codes(build_spindle_gcode(op.speedsAndFeeds, ""))
    path.code(build_feed_gcode(config.feed_rate))
    path.blank()

    plan = plan_profile_contour(cut)
    if plan.error:
        label = "Turning-Finish" if isinstance(op, TurningFinish) else "Profile Contour"
        path.error(f"{label} -- {plan.error}")
        return

    # the part is no more than the profile with its initial stock: the stock
    # model takes the rest as air
    path.part_at_most(plan.part_at_most)
    if plan.tool is not None and plan.tool.known:
        path.note(comment(f"Planned for {plan.tool.label}, nose R{fmt(plan.tool.nose_radius)}"))
    for warning in plan.warnings:
        path.note(comment(warning))
    count = len(plan.passes)
    for k, contour_pass in enumerate(plan.passes):
        stock = contour_pass.stock
        title = f"Pass {k + 1} of {count}: " if count > 1 else ""
        path.note(comment(f"{title}StockToLeave[radial={fmt(stock[0])} axial={fmt(stock[1])}]"))
        emit_moves(path, contour_pass.plan.moves, stock)
        write_home(path, contour_pass.plan)
        if op.m1Parameters.include_m1:
            path.inspect_stop(op.m1Parameters)
            path.blank()


def generate_profile_contour_gcode(cut: ProfileCut):
    """A Profile Contour's or a Turning-Finish's G-code on its own."""
    path = GcodeEmitter(cut.op.is_optional_block)
    profile_contour_toolpath(cut, path)
    return path.lines


def profile_contour_preview(cut: ProfileCut) -> OperationPreview:
    """What a Profile Contour or a Turning-Finish - as it is cut, ``cut`` -
    will cut, as the editor draws it, from the plan its G-code is written
    from (plan_profile_contour): each pass - in along Z from Z Start to where the
    profile begins, then along it - drawn where the nose touches, no rapids,
    the last thick, with the arrows that show which way it cuts; the profile,
    and it offset by the initial stock."""
    plan = plan_profile_contour(cut)
    if plan.error:
        return OperationPreview(error=plan.error)
    path = resolve_profile(cut)
    count = len(plan.passes)
    feeds = []
    for k, contour_pass in enumerate(plan.passes):
        final = k == count - 1
        drawn, _rapids = drawn_lines(contour_pass.plan.moves)
        feeds.extend(dataclasses.replace(line, pass_no=k, contour=final,
                                         arrows=Arrows.ALONG if final else Arrows.NONE)
                     for line in drawn)
    return OperationPreview(feeds=tuple(feeds), profile=flatten_path(path), offset=chain_points(plan.allowance),
                            warnings=tuple(plan.warnings))
