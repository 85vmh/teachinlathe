from teachinlathe.conversational.data_types import MoveSequence, PositionAt


def _fmt(value):
    return f"{float(value):.3f}"


def _code_comment(prefix, code, comment):
    word = f"{prefix}{code}"
    return f"{word}{' ' * max(1, 5 - len(word))}({comment})"


def generate_position_at_gcode(op: PositionAt):
    line_prefix = "/" if op.is_optional_block else ""
    details = op.position_details
    lines = []

    if details.stop_spindle_before_positioning:
        lines.append(_code_comment(line_prefix, "M5", "stop the spindle"))
        lines.append("")

    lines.append(_code_comment(line_prefix, "G90", "absolute distance mode"))

    if details.move_sequence == MoveSequence.XZ:
        lines.append(f"{line_prefix}G0 X{_fmt(details.x_pos)}")
        lines.append(f"{line_prefix}G0 Z{_fmt(details.z_pos)}")
    elif details.move_sequence == MoveSequence.ZX:
        lines.append(f"{line_prefix}G0 Z{_fmt(details.z_pos)}")
        lines.append(f"{line_prefix}G0 X{_fmt(details.x_pos)}")
    else:
        lines.append(f"{line_prefix}G0 X{_fmt(details.x_pos)} Z{_fmt(details.z_pos)}")

    if details.include_m0:
        lines.append("")
        lines.append(_code_comment(line_prefix, "M0", "pause program"))

    return lines
