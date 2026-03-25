from ..config import fmt


def _get_float_value(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def generate_knurling_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    geometry = op.get("geometry_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}

    x_start = _get_float_value(geometry, "x_start", 0.0)
    z_start = _get_float_value(geometry, "z_start", 0.0)
    z_end = _get_float_value(geometry, "z_end", 0.0)
    doc = _get_float_value(cutting, "doc", 0.0)
    retract = _get_float_value(cutting, "retract", 0.0)
    grooves_count = max(1, int(cutting.get("grooves_count", 1) or 1))
    include_m1 = 1 if bool(m1_params.get("include_m1", False)) else 0
    inspect_pos = m1_params.get("inspect_position", "G28")
    inspect_pos_int = 0 if inspect_pos == "G28" else 1

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
        parts.append(f"S{fmt(rpm_value)}")
    elif str(mode).lower() == "css":
        parts.append(f"S{fmt(css_value)} D{fmt(css_max)}")

    if parts:
        lines.append(f"{line_prefix}{' '.join(parts)}")

    lines.append(
        f"{line_prefix}o<knurling> call "
        f"[{fmt(x_start)}] "
        f"[{fmt(z_start)}] "
        f"[{fmt(z_end)}] "
        f"[{fmt(doc)}] "
        f"[{fmt(retract)}] "
        f"[{grooves_count}] "
        f"[{inspect_pos_int}] "
        f"[{include_m1}] "
        f"[{direction if direction is not None else 0}]"
    )
    return lines
