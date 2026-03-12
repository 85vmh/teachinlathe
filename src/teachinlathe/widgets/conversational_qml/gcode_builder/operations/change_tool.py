def _get_rule_value(rules, key, default):
    if not isinstance(rules, dict):
        return default
    return rules.get(key, default)


def generate_change_tool_gcode(op):
    tool_number = int(op.get("tool_no", 0))
    rules = op.get("toolchange_rules", {}) or {}
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    x_pos = float(_get_rule_value(rules, "x_pos", 0.0))
    z_pos = float(_get_rule_value(rules, "z_pos", 0.0))
    coordinate_type = _get_rule_value(rules, "coordinate_type", "absolute")
    move_sequence = _get_rule_value(rules, "move_sequence", "xz")
    stop_spindle = bool(_get_rule_value(rules, "stop_spindle", False))

    use_machine_coords = str(coordinate_type).lower() == "absolute"
    g53_prefix = "G53 " if use_machine_coords else ""

    move_sequence_value = str(move_sequence).lower()
    if move_sequence_value == "simultaneous":
        move_sequence_value = "both"

    lines = []
    if move_sequence_value == "xz":
        if stop_spindle:
            lines.append(f"{line_prefix}M5")
        lines.append(f"{line_prefix}{g53_prefix}G0 X{x_pos}")
        lines.append(f"{line_prefix}{g53_prefix}G0 Z{z_pos}")
    elif move_sequence_value == "zx":
        if stop_spindle:
            lines.append(f"{line_prefix}M5")
        lines.append(f"{line_prefix}{g53_prefix}G0 Z{z_pos}")
        lines.append(f"{line_prefix}{g53_prefix}G0 X{x_pos}")
    else:
        if stop_spindle:
            lines.append(f"{line_prefix}M5")
        lines.append(f"{line_prefix}{g53_prefix}G0 X{x_pos} Z{z_pos}")

    lines.append(f"{line_prefix}M6 T{tool_number} G43")
    return lines
