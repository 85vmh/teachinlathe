from teachinlathe.conversational.data_types import ChangeTool



def generate_change_tool_gcode(op: ChangeTool):
    line_prefix = "/" if op.is_optional_block else ""
    return [f"{line_prefix}o<tc_at_g28> call [{int(op.tool_no)}]"]
