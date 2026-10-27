from teachinlathe.conversational.model.data_types import InspectPosition, M1Parameters


def _inspect_position(value) -> InspectPosition:
    if isinstance(value, M1Parameters):
        raw = value.inspect_position
    elif not value:
        return InspectPosition.G28
    else:
        raw = value.get("inspect_position", InspectPosition.G28.value)
    # its value: G28 / G30 as PredefinedPosition has them too
    try:
        return InspectPosition(str(getattr(raw, "value", raw)).upper())
    except ValueError:
        return InspectPosition.G28


def inspect_position_int(m1_params) -> int:
    """0 for G28, 1 for G30, 2 to stay where the tool is - what the LinuxCNC
    subroutines (m1_handling.ngc) take."""
    pos = _inspect_position(m1_params)
    return {InspectPosition.G28: 0, InspectPosition.G30: 1, InspectPosition.IN_PLACE: 2}[pos]


def _code_comment(prefix, code, comment):
    word = f"{prefix}{code}"
    return f"{word}{' ' * max(1, 5 - len(word))}({comment})"


def emit_m1_block(m1_params, prefix: str) -> list:
    """Build M1 pause-to-inspect G-code lines: to G28 or G30 first, or an M1
    where the tool is.

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
        lines.append(_code_comment(prefix, "M5", "stop the spindle"))
    if pos is not InspectPosition.IN_PLACE:
        lines.append(f"{prefix}{pos.value}")
    lines.append(f"{prefix}M1")
    lines.append("")
    return lines


def m1_handling_call(prefix: str, m1_params, x_return, z_return, spindle_sign: int) -> str:
    """The call to o<m1_handling> (subroutines/m1_handling.ngc) at a point the
    operator may Pause to Inspect: where the tool waits, and where it goes
    back to - ``x_return`` (a diameter), ``z_return`` - before going on, the
    spindle started again ``spindle_sign`` 1 (M3) or -1 (M4)."""
    from ..config import fmt
    return (f"{prefix}o<m1_handling> call [{inspect_position_int(m1_params)}] "
            f"[{fmt(x_return)}] [{fmt(z_return)}] [{int(spindle_sign)}]")
