from .change_tool import generate_change_tool_gcode
from .define_profile import generate_define_profile_gcode
from .facing import generate_facing_gcode
from .drilling import generate_drilling_gcode

OPERATION_GENERATORS = {
    "changeTool": generate_change_tool_gcode,
    "defineProfile": generate_define_profile_gcode,
    "facing": generate_facing_gcode,
    "drilling": generate_drilling_gcode,
}
