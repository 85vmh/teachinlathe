"""What Profile Roughing and Profile Contour read from their operation dicts
alike: the profile (``_resolved_profile``), the tool (``_resolved_cutting_tool``),
which side of it they cut and where they start - and those, as a plan's key
has them."""

import logging

from teachinlathe.conversational.model.data_types import ProfilingType

from ...helpers.spindle import feed_rate_of
from ...helpers.utils import get_float
from .geometry import StartPoint, build_profile_segments, build_render_path

log = logging.getLogger(__name__)

NO_PROFILE = "no valid profile found"


def as_dict(op):
    return op.to_dict() if hasattr(op, "to_dict") else op


def resolve_profile(op):
    """(segments, path) of the profile the operation carries."""
    resolved = op.get("_resolved_profile") or {}
    primitives = resolved.get("profile_primitives", []) or []
    profile_type = str(resolved.get("profile_type", "od")).lower()
    segments = build_profile_segments(primitives)
    path = build_render_path(segments, profile_type)
    return segments, path


def profile_path(op):
    """The profile's path to plan along, or None when it has none."""
    segments, path = resolve_profile(op)
    if not segments or not isinstance(segments[0], StartPoint) or len(path) < 2:
        return None
    return path


def resolve_tool_shape(op):
    """The insert the Change Tool above puts in, as ``_resolved_cutting_tool``
    carries it (the Tool Library's JSON); None when there is none to go by."""
    from teachinlathe.tooling.model.data_types import CuttingTool
    from .tool_shape import insert_tool_shape

    raw = op.get("_resolved_cutting_tool") or None
    if not raw:
        return None
    try:
        return insert_tool_shape(CuttingTool.from_json(raw))
    except Exception:
        # planned with the stand-in square tool then: say why
        log.warning("roughing plan: the tool could not be read, planned without it", exc_info=True)
        return None


def profiling_type(op, strategy) -> ProfilingType:
    """OD or ID: the profile's own, else what ``strategy`` says."""
    resolved = op.get("_resolved_profile") or {}
    raw = resolved.get("profile_type", "od") if resolved else strategy.get("profiling_type", "od")
    try:
        return ProfilingType(str(raw).lower())
    except ValueError:
        return ProfilingType.OD


def common_config(op, strategy) -> dict:
    """The fields both operations' configs have, but the stock to leave:
    where they start, how deep and how far back, the feed, which side, and
    the optional-block prefix."""
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    return dict(
        x_start=get_float(params, "x_start", 0.0),
        z_start=get_float(params, "z_start", 0.0),
        doc=get_float(cutting, "doc", 0.5),
        retract=get_float(cutting, "retract", 1.0),
        feed_rate=feed_rate_of(op, 0.1),
        profiling_type=profiling_type(op, strategy),
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


def profile_and_tool_key(op) -> dict:
    """The profile and the tool, as a plan's key (plan_cache.plan_key) has them."""
    resolved = op.get("_resolved_profile") or {}
    return dict(
        profile=[str(resolved.get("profile_type", "od")).lower(), resolved.get("profile_primitives") or []],
        tool=op.get("_resolved_cutting_tool") or None,
    )
