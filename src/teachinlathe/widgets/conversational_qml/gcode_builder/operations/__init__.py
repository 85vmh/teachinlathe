from .change_tool import generate_change_tool_gcode
from .define_profile import generate_define_profile_gcode
from .facing import generate_facing_gcode
from .knurling import generate_knurling_gcode
from .drilling import generate_drilling_gcode
from .g7x_profiling import generate_profiling_gcode
from .threading import generate_threading_gcode
from .parting import generate_parting_gcode
from .position_at import generate_position_at_gcode
from .profile_contour import generate_profile_contour_gcode
from .profile_roughing import generate_profile_roughing_gcode
from .tapping import generate_tapping_gcode
from teachinlathe.widgets.conversational_qml.gcode_builder.operations.custom_cam.custom_profiling import generate_custom_profiling_gcode
from teachinlathe.widgets.conversational_qml.gcode_builder.operations.custom_cam.profile_boring import generate_profile_boring_gcode

OPERATION_GENERATORS = {
    "changeTool": generate_change_tool_gcode,
    "positionAt": generate_position_at_gcode,
    "defineProfile": generate_define_profile_gcode,
    "facing": generate_facing_gcode,
    "knurling": generate_knurling_gcode,
    "drilling": generate_drilling_gcode,
    "profiling": generate_profiling_gcode,
    "customProfiling": generate_custom_profiling_gcode,
    "profileBoring": generate_profile_boring_gcode,
    "profileRoughing": generate_profile_roughing_gcode,
    "profileContour": generate_profile_contour_gcode,
    "threading": generate_threading_gcode,
    "parting": generate_parting_gcode,
    "tapping": generate_tapping_gcode,
}
