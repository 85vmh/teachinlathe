from teachinlathe.conversational.data_types import BlendType

from ..config import fmt
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float


def _get_float_or_none(source, key, default=0.0):
    """Like get_float but returns None when default is None and value is missing."""
    if not isinstance(source, dict):
        return None if default is None else float(default)
    try:
        value = source.get(key, default)
    except Exception:
        value = default
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None if default is None else float(default)


def _edge_break_params(edge_break):
    if not isinstance(edge_break, dict):
        return 0, 0.0
    blend_str = str(edge_break.get("blend_type", "none")).lower()
    try:
        blend_type = BlendType(blend_str)
    except ValueError:
        blend_type = BlendType.NONE
    if blend_type == BlendType.CHAMFER:
        return 1, get_float(edge_break, "chamfer_width", 0.0)
    if blend_type == BlendType.FILLET:
        return 2, get_float(edge_break, "fillet_radius", 0.0)
    return 0, 0.0


def generate_parting_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    parting = op.get("parting_parameters", {}) or {}
    edge_break = op.get("edge_break", {}) or {}

    x_start = get_float(parting, "x_start", 0.0)
    x_end = get_float(parting, "x_end", 0.0)
    z_pos = get_float(parting, "z_pos", 0.0)

    # Support both current and legacy JSON key names
    fz1 = _get_float_or_none(parting, "first_feed_rate", None)
    if fz1 is None:
        fz1 = _get_float_or_none(parting, "1st_feed_rate", 0.0)

    fz2 = _get_float_or_none(parting, "second_feed_rate", None)
    if fz2 is None:
        fz2 = _get_float_or_none(parting, "2nd_feed_rate", 0.0)

    fz2_x_pos = _get_float_or_none(parting, "second_feed_x_pos", None)
    if fz2_x_pos is None:
        fz2_x_pos = _get_float_or_none(parting, "2nd_feed_x_pos", 0.0)
    x_clearance = get_float(parting, "x_clearance", 1.0)

    edge_break_type, edge_break_value = _edge_break_params(edge_break)

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(
        f"{line_prefix}o<parting> call [{fmt(x_clearance)}] [{fmt(x_start)}] [{fmt(x_end)}] [{fmt(z_pos)}]"
        f" [{fz1}] [{fz2}] [{fmt(fz2_x_pos)}] [{edge_break_type}] [{fmt(edge_break_value)}]"
    )
    return lines
