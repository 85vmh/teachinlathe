from teachinlathe.conversational.data_types import InspectPosition, M1Parameters


def _inspect_position(value) -> InspectPosition:
    if isinstance(value, M1Parameters):
        return value.inspect_position
    if not value:
        return InspectPosition.G28
    inspect_str = value.get("inspect_position", InspectPosition.G28.value)
    try:
        return InspectPosition(inspect_str)
    except ValueError:
        return InspectPosition.G28


def inspect_position_int(m1_params) -> int:
    """Return 0 for G28 or 1 for G30, for passing to LinuxCNC subroutines."""
    pos = _inspect_position(m1_params)
    return 0 if pos == InspectPosition.G28 else 1



def emit_m1_block(m1_params, prefix: str) -> list:
    """Build M1 pause-to-inspect G-code lines.

    Returns an empty list when include_m1 is falsy.
    """
    if isinstance(m1_params, M1Parameters):
        include_m1 = bool(m1_params.include_m1)
        stop_spindle = bool(m1_params.stop_spindle)
    else:
        include_m1 = bool(m1_params and m1_params.get("include_m1", False))
        stop_spindle = bool(m1_params and m1_params.get("stop_spindle", False))

    if not include_m1:
        return []

    pos = _inspect_position(m1_params)

    lines = []
    if stop_spindle:
        lines.append(f"{prefix}M5")
    lines.append(f"{prefix}{pos.value}")
    lines.append(f"{prefix}M1")
    lines.append("")
    return lines
