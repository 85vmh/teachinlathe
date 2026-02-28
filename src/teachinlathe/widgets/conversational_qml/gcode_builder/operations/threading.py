def _get_float_value(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def generate_threading_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    location = str(op.get("location", "OD"))
    major_d = _get_float_value(op, "major_diameter", 0.0)
    minor_d = _get_float_value(op, "minor_diameter", 0.0)

    if location.upper() == "ID":
        x_start = minor_d
        x_end = major_d
    else:
        x_start = major_d
        x_end = minor_d

    z_start = _get_float_value(op, "z_start", 0.0)
    z_end = _get_float_value(op, "z_end", 0.0)
    pitch = _get_float_value(op, "pitch", 0.0)
    starts = int(op.get("starts", 1) or 1)
    initial_doc = _get_float_value(op, "initial_doc", 0.0)
    depth_degression = _get_float_value(op, "depth_degression", 1.0)
    compound_angle = _get_float_value(op, "compound_angle", 0.0)
    taper_type = int(op.get("taper_type", 0) or 0)
    spring_passes = int(op.get("spring_passes", 0) or 0)

    taper_angle = 45

    lines = []

    mode = spindle.get("mode", None)
    direction = spindle.get("direction", None)
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
        f"{line_prefix}o<threading> call "
        f"[{x_start}] "
        f"[{z_start}] "
        f"[{x_end}] "
        f"[{z_end}] "
        f"[{pitch}] "
        f"[{starts}] "
        f"[{initial_doc}] "
        f"[{depth_degression}] "
        f"[{compound_angle}] "
        f"[{taper_type}] "
        f"[{taper_angle}] "
        f"[{spring_passes}]"
    )
    return lines
