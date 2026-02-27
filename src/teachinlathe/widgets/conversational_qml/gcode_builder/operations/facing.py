def _get_float_value(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def generate_facing_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    geometry = op.get("geometry_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}

    x_start = _get_float_value(geometry, "x_start", 0.0)
    z_start = _get_float_value(geometry, "z_start", 0.0)
    x_end = _get_float_value(geometry, "x_end", 0.0)
    z_end = _get_float_value(geometry, "z_end", 0.0)
    x_inspect = _get_float_value(m1_params, "x_inspect", 0.0)
    z_inspect = _get_float_value(m1_params, "z_inspect", 0.0)
    doc = _get_float_value(cutting, "doc", 0.0)
    feed_rate = _get_float_value(cutting, "feed_rate", 0.0)

    lines = []

    direction = spindle.get("direction", None)
    mode = spindle.get("mode", None)
    rpm_value = _get_float_value(spindle, "rpm_value", 0.0)
    css_value = _get_float_value(spindle, "css_value", 0.0)
    css_max = _get_float_value(spindle, "css_max_speed", 0.0)

    parts = []
    if str(mode).lower() == "rpm":
        parts.append(f"G97")
    elif str(mode).lower() == "css":
        parts.append(f"G96")

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

    lines.append(f"{line_prefix}G95 F{feed_rate}")

    lines.append(
        f"{line_prefix}o<facing> call [{x_start}] [{z_start}] [{x_end}] [{z_end}]"
        f" [{x_inspect}] [{z_inspect}] [{doc}] [{direction}]"
    )
    return lines
