from teachinlathe.conversational.model.data_types import InspectPosition, M1Parameters


def _inspect_position(m1_params: M1Parameters) -> InspectPosition:
    raw = m1_params.inspect_position
    # its value: G28 / G30 as PredefinedPosition has them too
    try:
        return InspectPosition(str(getattr(raw, "value", raw)).upper())
    except ValueError:
        return InspectPosition.G28


def inspect_position_int(m1_params: M1Parameters) -> int:
    """0 for G28, 1 for G30, 2 to stay where the tool is - what the LinuxCNC
    subroutines (m1_handling.ngc) take."""
    pos = _inspect_position(m1_params)
    return {InspectPosition.G28: 0, InspectPosition.G30: 1, InspectPosition.IN_PLACE: 2}[pos]


def m1_handling_call(prefix: str, m1_params: M1Parameters, x_return, z_return, spindle_sign: int) -> str:
    """The call to o<m1_handling> (subroutines/m1_handling.ngc) at a point the
    operator may Pause to Inspect: where the tool waits, and where it goes
    back to - ``x_return`` (a diameter), ``z_return`` - before going on, the
    spindle started again ``spindle_sign`` 1 (M3) or -1 (M4)."""
    from ..config import fmt
    return (f"{prefix}o<m1_handling> call [{inspect_position_int(m1_params)}] "
            f"[{fmt(x_return)}] [{fmt(z_return)}] [{int(spindle_sign)}]")
