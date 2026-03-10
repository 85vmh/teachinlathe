def _get_float_value(source, key, default=0.0):
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
    blend_type = str(edge_break.get("blend_type", "none")).lower()
    if blend_type == "chamfer":
        return 1, _get_float_value(edge_break, "chamfer_width", 0.0)
    if blend_type == "fillet":
        return 2, _get_float_value(edge_break, "fillet_radius", 0.0)
    return 0, 0.0


def generate_parting_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    parting = op.get("parting_parameters", {}) or {}
    edge_break = op.get("edge_break", {}) or {}

    x_start = _get_float_value(parting, "x_start", 0.0)
    x_end = _get_float_value(parting, "x_end", 0.0)
    z_pos = _get_float_value(parting, "z_pos", 0.0)

    fz1 = _get_float_value(parting, "first_feed_rate", None)
    if fz1 is None:
        fz1 = _get_float_value(parting, "1st_feed_rate", 0.0)

    fz2 = _get_float_value(parting, "second_feed_rate", None)
    if fz2 is None:
        fz2 = _get_float_value(parting, "2nd_feed_rate", 0.0)

    fz2_x_pos = _get_float_value(parting, "second_feed_x_pos", None)
    if fz2_x_pos is None:
        fz2_x_pos = _get_float_value(parting, "2nd_feed_x_pos", 0.0)
    x_clearance = _get_float_value(parting, "x_clearance", 1.0)

    edge_break_type, edge_break_value = _edge_break_params(edge_break)

    lines = []

    direction = spindle.get("direction", None)
    mode = spindle.get("mode", None)
    rpm_value = _get_float_value(spindle, "rpm_value", 0.0)
    css_value = _get_float_value(spindle, "css_value", 0.0)
    css_max = _get_float_value(spindle, "css_max_speed", 0.0)

    parts = []
    if str(mode).lower() == "rpm":
        parts.append("G97")
    elif str(mode).lower() == "css":
        parts.append("G96")

    if direction == -1:
        parts.append("M4")
    elif direction == 1:
        parts.append("M3")

    if str(mode).lower() == "rpm":
        parts.append(f"S{rpm_value}")
    elif str(mode).lower() == "css":
        parts.append(f"S{css_value} D{css_max}")

    if parts:
        lines.append(f"{line_prefix}{' '.join(parts)}")

    lines.append(
        f"{line_prefix}o<parting> call [{x_clearance}] [{x_start}] [{x_end}] [{z_pos}]"
        f" [{fz1}] [{fz2}] [{fz2_x_pos}] [{edge_break_type}] [{edge_break_value}]"
    )
    return lines
