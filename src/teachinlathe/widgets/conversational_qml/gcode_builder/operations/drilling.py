def _get_float_value(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def generate_drilling_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    drilling = op.get("drilling_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}

    x_start = _get_float_value(drilling, "x_start", 0.0)
    if x_start == 0.0:
        x_start = _get_float_value(op, "x_start", 0.0)
    z_start = _get_float_value(drilling, "z_start", 0.0)
    z_end = _get_float_value(drilling, "z_end", 0.0)
    retract = _get_float_value(drilling, "z_retract", 0.0)
    x_inspect = _get_float_value(m1_params, "x_inspect", 0.0)
    z_inspect = _get_float_value(m1_params, "z_inspect", 0.0)
    increment = _get_float_value(drilling, "peck_depth", 0.0)
    rpm = _get_float_value(spindle, "rpm_value", 0.0)
    feed = _get_float_value(drilling, "feed_rate", 0.0)
    mode = spindle.get("mode", None)
    direction = spindle.get("direction", None)
    rpm_value = _get_float_value(spindle, "rpm_value", 0.0)

    lines = []

    parts = ["G97"]

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
        f"{line_prefix}o<drilling> call [{x_start}] [{z_start}] [{z_end}] [{retract}]"
        f" [{x_inspect}] [{z_inspect}] [{increment}] [{rpm}] [{feed}]"
    )
    return lines
