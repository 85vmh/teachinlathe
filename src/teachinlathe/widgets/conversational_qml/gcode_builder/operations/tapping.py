import math

from ..config import fmt


def _get_float_value(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def generate_tapping_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    tapping = op.get("tapping_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}

    z_start = _get_float_value(tapping, "z_start", 0.0)
    z_end = _get_float_value(tapping, "z_end", 0.0)
    z_retract = _get_float_value(tapping, "z_retract", 0.0)
    peck_depth = _get_float_value(tapping, "peck_depth", 0.0)
    pitch = _get_float_value(tapping, "pitch", 0.0)

    rpm_value = _get_float_value(spindle, "rpm_value", 0.0)
    direction = spindle.get("direction", 1)

    include_m1 = bool(m1_params.get("include_m1", False))
    stop_spindle = bool(m1_params.get("stop_spindle", False))
    x_inspect = _get_float_value(m1_params, "x_inspect", 0.0)
    z_inspect = _get_float_value(m1_params, "z_inspect", 0.0)

    lines = []

    # Spindle — rigid tapping requires G97 (RPM mode)
    spindle_cmd = "M3" if direction != -1 else "M4"
    lines.append(f"{line_prefix}G97 {spindle_cmd} S{fmt(rpm_value)}")

    # Rapid to clearance position (X0 = lathe centre)
    lines.append(f"{line_prefix}G0 X0 Z{fmt(z_start)}")

    # Build list of peck targets
    if peck_depth > 0.0 and abs(z_end - z_start) > 0.0:
        total_depth = abs(z_end - z_start)
        n_pecks = math.ceil(total_depth / peck_depth)
        sign = -1.0 if z_end < z_start else 1.0
        peck_targets = [
            z_start + sign * min((i + 1) * peck_depth, total_depth)
            for i in range(n_pecks)
        ]
    else:
        peck_targets = [z_end]

    # G33.1 rigid tapping — each call returns the tool to z_start automatically
    for z_target in peck_targets:
        lines.append(f"{line_prefix}G33.1 Z{fmt(z_target)} K{fmt(pitch)}")
        if include_m1:
            lines.append(
                f"{line_prefix}o<m1_handling> call [{fmt(x_inspect)}] [{fmt(z_inspect)}] [0.000] [{fmt(z_start)}] [{direction}]"
            )

    # Retract to safe position
    lines.append(f"{line_prefix}G0 Z{fmt(z_retract)}")

    return lines