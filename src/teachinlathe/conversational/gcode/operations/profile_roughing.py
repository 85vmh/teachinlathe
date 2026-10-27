"""G-code generator for Profile Roughing (OD and ID).

The moves are planned by profiling/machining.py, tool and all, for the
ProfilingType (OD/ID) and PassType (AXIAL / RADIAL / DIAGONAL_*); this reads
the operation, finds its profile and tool, keeps the plans made, and writes the
G-code of a plan.
"""

import dataclasses

from teachinlathe.conversational.model.data_types import PassType, ProfileRoughingConfig

from ..helpers.spindle import build_spindle_gcode, direction_sign
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


def parse_profile_roughing_config(op) -> ProfileRoughingConfig:
    op = as_dict(op)
    strategy = op.get("profile_roughing_strategy", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}
    try:
        pass_type = PassType(str(strategy.get("pass_type", "axial")).lower())
    except ValueError:
        pass_type = PassType.AXIAL
    return ProfileRoughingConfig(
        **common_config(op, strategy),
        stock_x=get_float(stock, "radial", 0.0),
        stock_z=get_float(stock, "axial", 0.0),
        pass_type=pass_type,
    )


def generate_profile_roughing_gcode(op):
    """The G-code of a Profile Roughing: the moves of its tool-aware plan
    (plan_profile_roughing) as the machine makes them - compensated for the
    insert's nose, every one checked against the part and what is left of
    the stock. The profile canvas draws the same plan."""
    op = as_dict(op)

    config = parse_profile_roughing_config(op)
    spindle = op.get("speeds_and_feeds", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}
    spindle_direction = direction_sign(op)
    prefix = config.optional_prefix

    lines = []
    lines.extend(build_spindle_gcode(spindle, prefix))
    lines.append(f"{prefix}G95 F{config.feed_rate}")
    lines.append("")

    plan = plan_profile_roughing(op)
    if plan.error:
        lines.append(comment(f"ERROR: Profile Roughing -- {plan.error}"))
        return lines

    write_plan(lines, plan, prefix, (config.stock_x, config.stock_z), m1_params, spindle_direction,
               title=f"(----------Profiling Type: {_pass_type_label(config.pass_type)}----------)")
    return lines


#: Plans already worked out, by their inputs (roughing_plan_key): the
#: preview's plan is the one the G-code is written from.
_PLANS = PlanCache()

_NO_SOURCE = "rest material, but no Profile Roughing of this profile above it"
_CHOOSE_TOOL = "Choose the tool to cut what is left"


def roughing_plan_key(op) -> str:
    """What a Profile Roughing's plan depends on, and nothing else - not the
    feed, the spindle, M1, its place in the program, the workpiece drawn
    with the profile: where it starts and cuts, how deep and how much it
    leaves, which way; the profile; the tool; and for rest material what
    the roughings above it leave, by their own keys."""
    op = as_dict(op)
    config = parse_profile_roughing_config(op)
    rest = bool(op.get("rest_material", False))
    return plan_key(
        setup=[config.x_start, config.z_start, config.doc, config.retract, config.stock_x, config.stock_z,
               config.profiling_type.value, config.pass_type.value, _diagonal_angle()],
        **profile_and_tool_key(op),
        rest=[roughing_plan_key(prev) for prev in op.get("_resolved_previous_roughing") or []] if rest else None,
    )


def plan_profile_roughing(op):
    """The tool-aware plan of a Profile Roughing - see profiling.machining -
    for an operation dict carrying its profile in ``_resolved_profile`` and
    its tool in ``_resolved_cutting_tool``; the one kept when it was planned
    already with the same inputs (roughing_plan_key).

    Rest material (``rest_material``): it starts from what the Profile
    Roughings above it on the same profile leave - given, in order, as
    ``_resolved_previous_roughing``, each an operation dict as this takes -
    and keeps to the stock to leave and the start position of the last one
    that is not rest material itself, its source."""
    op = as_dict(op)
    return _PLANS.get(roughing_plan_key(op), lambda: _plan(op))


def _plan(op):
    from .profiling.machining import RoughingPlan, RoughingSetup, plan_leftover, plan_roughing

    config = parse_profile_roughing_config(op)
    path = profile_path(op)
    if path is None:
        return RoughingPlan(error=NO_PROFILE)
    rest = bool(op.get("rest_material", False))
    stock_before, last_tool = None, None
    if rest:
        source, stock_before, last_tool = _rest_start(op.get("_resolved_previous_roughing") or [])
        if source is None:
            return RoughingPlan(error=_NO_SOURCE)
        # the source's stock to leave and start position: the same finished
        # size, and the same bar
        source_config = parse_profile_roughing_config(source)
        config = dataclasses.replace(
            config, x_start=source_config.x_start, z_start=source_config.z_start,
            stock_x=source_config.stock_x, stock_z=source_config.stock_z)
    setup = RoughingSetup(
        x_start=config.x_start, z_start=config.z_start, doc=config.doc,
        retract=config.retract, stock_x=config.stock_x, stock_z=config.stock_z,
        profiling_type=config.profiling_type, pass_type=config.pass_type,
        diagonal_angle=_diagonal_angle())
    tool = resolve_tool_shape(op)
    if rest and tool is None:
        plan = plan_leftover(setup, path, stock_before,
                             last_tool.nose_radius if last_tool is not None else 0.0)
        plan.warnings.insert(0, _CHOOSE_TOOL)
        return plan
    return plan_roughing(setup, path, tool, stock_before, rest=rest,
                         sliver_radius=last_tool.nose_radius if rest and last_tool is not None else 0.0)


def _rest_start(previous):
    """(source, stock, tool) for a rest roughing below the roughings
    ``previous``: the last of them that is not rest material, the material all
    of them together leave and the last tool that cut it - or
    (None, None, None) with no source."""
    source, stock, tool = None, None, None
    for index, prev in enumerate(previous):
        if not prev.get("rest_material", False):
            source, stock = prev, None
        elif source is None:
            continue
        else:
            # a rest roughing too: it starts from those above it in turn
            prev = {**prev, "_resolved_previous_roughing": previous[:index]}
        plan = plan_profile_roughing(prev)
        if plan.error or plan.remaining_stock is None:
            continue
        stock = plan.remaining_stock
        tool = plan.tool
    return source, stock, tool
