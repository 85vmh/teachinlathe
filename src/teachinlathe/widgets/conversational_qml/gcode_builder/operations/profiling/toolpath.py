from ...config import fmt
from .geometry import ToolpathArc, ToolpathLine


def emit_toolpath(lines, optional_prefix, path, offset_x=0.0, offset_z=0.0):
    if not path:
        return
    current_x = path[0].x + offset_x
    current_z = path[0].z + offset_z

    for element in path[1:]:
        end_x = element.end_x + offset_x
        end_z = element.end_z + offset_z
        if isinstance(element, ToolpathLine):
            lines.append(f"{optional_prefix}G1 X{fmt(end_x)} Z{fmt(end_z)}")
        elif isinstance(element, ToolpathArc):
            gcode = "G2" if element.anticlockwise else "G3"
            center_i = element.center_x + offset_x - current_x
            center_k = element.center_z + offset_z - current_z
            lines.append(f"{optional_prefix}{gcode} X{fmt(end_x)} Z{fmt(end_z)} I{fmt(center_i)} K{fmt(center_k)}")
        current_x, current_z = end_x, end_z
