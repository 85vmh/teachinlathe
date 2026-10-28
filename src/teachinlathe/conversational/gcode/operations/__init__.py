"""The generators of the operations' G-code: on the program's emitter
(*_toolpath) or as lines (generate_*_gcode). gcode_builder says which
writes each operation class."""

from .define_profile import generate_define_profile_gcode
from .facing import facing_toolpath
from .knurling import generate_knurling_gcode
from .drilling import drilling_toolpath
from .g7x_profiling import generate_profiling_gcode
from .g33_threading import g33_threading_toolpath, generate_g33_threading_gcode
from .threading import generate_threading_gcode
from .parting import parting_toolpath
from .position_at import generate_position_at_gcode, position_at_toolpath
from .profile_contour import generate_profile_contour_gcode, profile_contour_toolpath
from .profile_roughing import generate_profile_roughing_gcode, profile_roughing_toolpath
from .groove_roughing import generate_groove_roughing_gcode, groove_roughing_toolpath
from .groove_finishing import generate_groove_finishing_gcode, groove_finishing_toolpath
from .tapping import tapping_toolpath
