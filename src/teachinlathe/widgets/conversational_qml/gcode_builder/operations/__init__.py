from .change_tool import generate_change_tool_gcode

OPERATION_GENERATORS = {
    "changeTool": generate_change_tool_gcode,
}
