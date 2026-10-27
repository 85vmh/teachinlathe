from teachinlathe.conversational.model.data_types import PredefinedPosition



def generate_change_tool_gcode(tool_no: int, position: PredefinedPosition):
    """The tool change to holder ``tool_no``, at G28 or G30
    (subroutines/tc_at_g28.ngc, tc_at_g30.ngc)."""
    subroutine = "tc_at_g30" if position == PredefinedPosition.G30 else "tc_at_g28"
    return [f"o<{subroutine}> call [{int(tool_no)}]"]
