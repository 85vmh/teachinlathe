from teachinlathe.conversational.data_types import MoveSequence, PositionAt


def _fmt(value):
    return f"{float(value):.3f}"


def generate_position_at_gcode(op: PositionAt):
    line_prefix = "/" if op.is_optional_block else ""
    details = op.position_details
    lines = []

    lines.append(f"{line_prefix}G90")

    if details.move_sequence == MoveSequence.XZ:
        lines.append(f"{line_prefix}G0 X{_fmt(details.x_pos)}")
        lines.append(f"{line_prefix}G0 Z{_fmt(details.z_pos)}")
    elif details.move_sequence == MoveSequence.ZX:
        lines.append(f"{line_prefix}G0 Z{_fmt(details.z_pos)}")
        lines.append(f"{line_prefix}G0 X{_fmt(details.x_pos)}")
    else:
        lines.append(f"{line_prefix}G0 X{_fmt(details.x_pos)} Z{_fmt(details.z_pos)}")

    return lines
