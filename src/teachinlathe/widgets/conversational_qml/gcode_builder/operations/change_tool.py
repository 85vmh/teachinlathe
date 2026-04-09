from teachinlathe.conversational.data_types import ChangeTool, PredefinedPosition



def generate_change_tool_gcode(op: ChangeTool):
    line_prefix = "/" if op.is_optional_block else ""
    position = getattr(op, "toolchange_position", PredefinedPosition.G28)
    subroutine = "tc_at_g30" if position == PredefinedPosition.G30 else "tc_at_g28"
    return [f"{line_prefix}o<{subroutine}> call [{int(op.tool_no)}]"]
