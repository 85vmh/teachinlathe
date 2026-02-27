def _get_float_value(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def generate_profiling_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    options = op.get("profiling_options", {}) or {}

    profile_id = int(params.get("profile_id", 0) or 0)
    x_start = _get_float_value(params, "x_start", 0.0)
    z_start = _get_float_value(params, "z_start", 0.0)

    doc = _get_float_value(cutting, "doc", 0.0)
    retract = _get_float_value(cutting, "retract", 0.0)
    feed_rate = _get_float_value(cutting, "feed_rate", 0.0)

    stock_x = _get_float_value(options, "stock_to_leave_x", 0.0)
    stock_z = _get_float_value(options, "stock_to_leave_z", 0.0)
    stock = max(stock_x, stock_z)

    mode = spindle.get("mode", None)
    direction = spindle.get("direction", None)
    rpm_value = _get_float_value(spindle, "rpm_value", 0.0)
    css_value = _get_float_value(spindle, "css_value", 0.0)
    css_max = _get_float_value(spindle, "css_max_speed", 0.0)

    lines = []

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

    # Feed per rev for profiling
    lines.append(f"{line_prefix}G95 F{feed_rate}")

    strategy = str(options.get("strategy", "rough")).lower()
    if strategy == "finish":
        passes = int(options.get("finish_spring_passes", 1) or 1)
        # G70 uses D (start distance) and E (end distance)
        lines.append(
            f"{line_prefix}G70 Q{profile_id} X{x_start} Z{z_start}"
            f" D{stock} E0 P{passes}"
        )
    else:
        lines.append(
            f"{line_prefix}G71.1 Q{profile_id} X{x_start} Z{z_start}"
            f" D{stock} I{doc} R{retract}"
        )
    return lines
