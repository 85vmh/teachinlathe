from teachinlathe.conversational.model.data_types import InspectPosition, M1Parameters


def _inspect_position(m1_params: M1Parameters) -> InspectPosition:
    raw = m1_params.inspect_position
    # its value: G28 / G30 as PredefinedPosition has them too
    try:
        return InspectPosition(str(getattr(raw, "value", raw)).upper())
    except ValueError:
        return InspectPosition.G28


def inspect_position_int(m1_params: M1Parameters) -> int:
    """M1's P: 0 to stay where the tool is, 1 for G28, 2 for G30 - what the
    remap of M1 (subroutines/m1_remap.ngc) takes."""
    pos = _inspect_position(m1_params)
    return {InspectPosition.IN_PLACE: 0, InspectPosition.G28: 1, InspectPosition.G30: 2}[pos]


_M1_COMMENTS = {
    0: "Pause to inspect and stay there",
    1: "Pause to inspect and retract to G28 position",
    2: "Pause to inspect and retract to G30 position",
}


def m1_gcode(prefix: str, m1_params: M1Parameters) -> str:
    """M1 P<where the tool waits>, and what it does as a comment, at a point
    the operator may Pause to Inspect. M1 is remapped (subroutines/m1_remap.ngc):
    with Optional Stop on, it stops the spindle, waits there, then starts the
    spindle again as it was and goes back to where the tool was before going on."""
    p = inspect_position_int(m1_params)
    return f"{prefix}M1 P{p} ({_M1_COMMENTS[p]})"
