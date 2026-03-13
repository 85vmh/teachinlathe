_SEQ_MAP = {"both": 0, "simultaneous": 0, "xz": 1, "zx": 2}


def generate_change_tool_gcode(op):
    tool_number = int(op.get("tool_no", 0))
    rules = op.get("toolchange_rules", {}) or {}
    is_optional = bool(op.get("is_optional_block", False))
    lp = "/" if is_optional else ""

    x_pos = float(rules.get("x_pos", 0.0))
    z_pos = float(rules.get("z_pos", 0.0))
    move_sequence = str(rules.get("move_sequence", "xz")).lower().strip()
    seq_num = _SEQ_MAP.get(move_sequence, 0)

    return [f"{lp}o<tc_at_g28> call [{tool_number}]"]
