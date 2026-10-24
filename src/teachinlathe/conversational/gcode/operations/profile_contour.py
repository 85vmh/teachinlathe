"""G-code generator for Profile Contour (OD and ID): the contour alone, planned
as Profile Roughing plans the one it finishes with (profiling/machining.py) -
tool-aware, compensated for the insert's nose - and written the same way."""

from teachinlathe.conversational.model.data_types import PassType, ProfileContourConfig

from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float
from .profiling.operation_input import (
    NO_PROFILE,
    as_dict,
    common_config,
    profile_and_tool_key,
    profile_path,
    resolve_tool_shape,
)
from .profiling.plan_cache import PlanCache, plan_key
from .profiling.plan_gcode import comment, write_plan


def parse_profile_contour_config(op) -> ProfileContourConfig:
    op = as_dict(op)
    strategy = op.get("profile_contour_strategy", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}
    stock_enabled = bool(op.get("stock_to_leave_enabled", False))
    return ProfileContourConfig(
        **common_config(op, strategy),
        stock_x=get_float(stock, "radial", 0.0) if stock_enabled else 0.0,
        stock_z=get_float(stock, "axial", 0.0) if stock_enabled else 0.0,
        stock_enabled=stock_enabled,
    )


#: Plans already worked out, by their inputs (contour_plan_key).
_PLANS = PlanCache()


def contour_plan_key(op) -> str:
    """What a Profile Contour's plan depends on: where it starts, the stock
    to leave, which way; the profile; the tool - not the feed, the spindle,
    its place in the program."""
    op = as_dict(op)
    config = parse_profile_contour_config(op)
    return plan_key(
        setup=[config.x_start, config.z_start, config.doc, config.retract, config.stock_x, config.stock_z,
               config.profiling_type.value],
        **profile_and_tool_key(op),
    )


def plan_profile_contour(op):
    """The tool-aware plan of a Profile Contour - the contour alone, see
    profiling.machining - for an operation dict carrying its profile in
    ``_resolved_profile`` and its tool in ``_resolved_cutting_tool``: the same
    contour Profile Roughing finishes with, compensated for the insert's
    nose, bridged over what it cannot enter. The one kept when it was planned
    already with the same inputs (contour_plan_key)."""
    op = as_dict(op)
    return _PLANS.get(contour_plan_key(op), lambda: _plan(op))


def _plan(op):
    from .profiling.machining import RoughingPlan, RoughingSetup, plan_contour

    config = parse_profile_contour_config(op)
    path = profile_path(op)
    if path is None:
        return RoughingPlan(error=NO_PROFILE)
    setup = RoughingSetup(
        x_start=config.x_start, z_start=config.z_start, doc=config.doc,
        retract=config.retract, stock_x=config.stock_x, stock_z=config.stock_z,
        profiling_type=config.profiling_type, pass_type=PassType.AXIAL)
    return plan_contour(setup, path, resolve_tool_shape(op))


def generate_profile_contour_gcode(op):
    """The G-code of a Profile Contour: the moves of its plan
    (plan_profile_contour) as the machine makes them - the control point,
    compensated for the nose, the profile's arcs as G2 / G3. The profile
    canvas draws the same plan."""
    op = as_dict(op)

    config = parse_profile_contour_config(op)
    spindle = op.get("speeds_and_feeds", {}) or {}
    prefix = config.optional_prefix

    lines = []
    lines.extend(build_spindle_gcode(spindle, prefix))
    lines.append(f"{prefix}G95 F{config.feed_rate}")
    lines.append("")

    plan = plan_profile_contour(op)
    if plan.error:
        lines.append(comment(f"ERROR: Profile Contour -- {plan.error}"))
        return lines

    write_plan(lines, plan, prefix, (config.stock_x, config.stock_z))
    return lines
