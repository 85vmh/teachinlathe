"""G-code generator for Profile Contour (OD and ID): the contour alone, planned
as Profile Roughing plans the one it finishes with (profiling/machining.py) -
tool-aware, compensated for the insert's nose - and written the same way."""

from teachinlathe.conversational.model.data_types import PassType, ProfileContourConfig, ProfilingType

from ..config import fmt
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float
from .profile_roughing import _comment, _emit_moves, _resolve_profile, resolve_tool_shape
from .profiling.geometry import StartPoint


def parse_profile_contour_config(op) -> ProfileContourConfig:
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    strategy = op.get("profile_contour_strategy", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}

    resolved = op.get("_resolved_profile") or {}
    if resolved:
        try:
            profiling_type = ProfilingType(str(resolved.get("profile_type", "od")).lower())
        except ValueError:
            profiling_type = ProfilingType.OD
    else:
        try:
            profiling_type = ProfilingType(str(strategy.get("profiling_type", "od")).lower())
        except ValueError:
            profiling_type = ProfilingType.OD

    stock_enabled = bool(op.get("stock_to_leave_enabled", False))

    return ProfileContourConfig(
        x_start=get_float(params, "x_start", 0.0),
        z_start=get_float(params, "z_start", 0.0),
        doc=get_float(cutting, "doc", 0.5),
        retract=get_float(cutting, "retract", 1.0),
        feed_rate=get_float(cutting, "feed_rate", 0.1),
        stock_x=get_float(stock, "radial", 0.0) if stock_enabled else 0.0,
        stock_z=get_float(stock, "axial", 0.0) if stock_enabled else 0.0,
        stock_enabled=stock_enabled,
        profiling_type=profiling_type,
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


#: Plans already worked out, by everything that went into them: the editor
#: asks again for every value changed, and the G-code once more.
_PLANS = {}
_PLANS_KEPT = 16

_NO_PROFILE = "no valid profile found"


def plan_profile_contour(op):
    """The tool-aware plan of a Profile Contour - the contour alone, see
    profiling.machining - for an operation dict carrying its profile in
    ``_resolved_profile`` and its tool in ``_resolved_cutting_tool``: the same
    contour Profile Roughing finishes with, compensated for the insert's
    nose, bridged over what it cannot enter."""
    import json

    if hasattr(op, "to_dict"):
        op = op.to_dict()
    key = json.dumps(op, sort_keys=True, default=str)
    plan = _PLANS.get(key)
    if plan is None:
        plan = _plan(op)
        if len(_PLANS) >= _PLANS_KEPT:
            _PLANS.pop(next(iter(_PLANS)))
        _PLANS[key] = plan
    return plan


def _plan(op):
    from .profiling.machining import RoughingPlan, RoughingSetup, plan_contour

    config = parse_profile_contour_config(op)
    segments, path = _resolve_profile(op)
    if not segments or not isinstance(segments[0], StartPoint) or len(path) < 2:
        return RoughingPlan(error=_NO_PROFILE)
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
    if hasattr(op, "to_dict"):
        op = op.to_dict()

    config = parse_profile_contour_config(op)
    spindle = op.get("spindle_parameters", {}) or {}
    prefix = config.optional_prefix

    lines = []
    lines.extend(build_spindle_gcode(spindle, prefix))
    lines.append(f"{prefix}G95 F{config.feed_rate}")
    lines.append("")

    plan = plan_profile_contour(op)
    if plan.error:
        lines.append(_comment(f"ERROR: Profile Contour -- {plan.error}"))
        return lines

    if plan.tool is not None and plan.tool.known:
        lines.append(_comment(f"Planned for {plan.tool.label}, nose R{fmt(plan.tool.nose_radius)}"))
    for warning in plan.warnings:
        lines.append(_comment(warning))
    _emit_moves(lines, plan.moves, prefix, config, None, 0)
    return lines
