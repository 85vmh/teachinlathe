from .change_tool import generate_change_tool_gcode
from .define_profile import generate_define_profile_gcode
from .facing import generate_facing_gcode
from .drilling import generate_drilling_gcode
from .profiling import generate_profiling_gcode
from .threading import generate_threading_gcode
from .parting import generate_parting_gcode
from .custom_profiling import generate_custom_profiling_gcode

OPERATION_GENERATORS = {
    "changeTool": generate_change_tool_gcode,
    "defineProfile": generate_define_profile_gcode,
    "facing": generate_facing_gcode,
    "drilling": generate_drilling_gcode,
    "profiling": generate_profiling_gcode,
    "customProfiling": generate_custom_profiling_gcode,
    "threading": generate_threading_gcode,
    "parting": generate_parting_gcode,
}
