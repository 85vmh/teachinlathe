from teachinlathe.conversational.data_types import InspectPosition


def inspect_position_int(m1_params: dict) -> int:
    """Return 0 for G28 or 1 for G30, for passing to LinuxCNC subroutines."""
    if not m1_params:
        return 0
    inspect_str = m1_params.get("inspect_position", "G28")
    try:
        pos = InspectPosition(inspect_str)
    except ValueError:
        pos = InspectPosition.G28
    return 0 if pos == InspectPosition.G28 else 1


def emit_m1_block(m1_params: dict, prefix: str) -> list:
    """Build M1 pause-to-inspect G-code lines.

    Returns an empty list when include_m1 is falsy.
    """
    if not m1_params or not bool(m1_params.get("include_m1", False)):
        return []

    inspect_str = m1_params.get("inspect_position", "G28")
    try:
        pos = InspectPosition(inspect_str)
    except ValueError:
        pos = InspectPosition.G28

    lines = []
    if bool(m1_params.get("stop_spindle", False)):
        lines.append(f"{prefix}M5")
    lines.append(f"{prefix}{pos.value}")
    lines.append(f"{prefix}M1")
    lines.append("")
    return lines
