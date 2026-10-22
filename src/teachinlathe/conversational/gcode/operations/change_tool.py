from teachinlathe.conversational.model.data_types import ChangeTool, PredefinedPosition



def generate_change_tool_gcode(op: ChangeTool):
    line_prefix = "/" if op.is_optional_block else ""
    position = getattr(op, "toolchange_position", PredefinedPosition.G28)
    subroutine = "tc_at_g30" if position == PredefinedPosition.G30 else "tc_at_g28"
    if int(op.tool_no) <= 0:
        # T0 would take the tool out: say what is missing instead
        return ["( ERROR: Tool Change -- no tool chosen )"]
    return [f"{line_prefix}o<{subroutine}> call [{int(op.tool_no)}]"]
