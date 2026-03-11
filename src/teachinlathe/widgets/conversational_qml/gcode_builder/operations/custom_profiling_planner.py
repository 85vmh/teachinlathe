import math

from ..config import fmt
from .custom_profiling_types import ProfilePass, RoughPass, ToolpathArc, ToolpathLine


def build_spindle_lines(spindle, optional_prefix, get_float):
    mode = spindle.get("mode", None)
    direction = spindle.get("direction", None)
    rpm_value = get_float(spindle, "rpm_value", 0.0)
    css_value = get_float(spindle, "css_value", 0.0)
    css_max = get_float(spindle, "css_max_speed", 0.0)

    words = []
    if str(mode).lower() == "rpm":
        words.append("G97")
    elif str(mode).lower() == "css":
        words.append("G96")

    if direction == -1:
        words.append("M4")
    elif direction == 1:
        words.append("M3")

    if str(mode).lower() == "rpm":
        words.append(f"S{rpm_value}")
    elif str(mode).lower() == "css":
        words.append(f"S{css_value} D{css_max}")

    if words:
        return [f"{optional_prefix}{' '.join(words)}"]
    return []


def plan_roughing_passes(config, x_min, x_profile_start, find_deepest_z_at_x):
    x_cut_min = x_min + config.stock_x
    doc = config.doc if config.doc > 0 else 0.5
    pass_count = max(1, math.ceil((config.x_start - x_cut_min) / doc))
    rough_passes = []

    for pass_index in range(pass_count):
        cut_x = max(config.x_start - (pass_index + 1) * doc, x_cut_min)
        cut_z = find_deepest_z_at_x(cut_x, config.stock_x, config.stock_z)
        exit_x = cut_x + abs(config.retract)
        exit_z = cut_z + math.copysign(abs(config.retract), config.z_start - cut_z)
        rough_passes.append(RoughPass(cut_x=cut_x, cut_z=cut_z, exit_x=exit_x, exit_z=exit_z))

    contour_offset_pass = ProfilePass(offset_x=config.stock_x, offset_z=config.stock_z)
    return pass_count, x_cut_min, rough_passes, contour_offset_pass, x_profile_start + config.stock_x


def plan_finish_passes(config):
    finish_passes = []
    for pass_index in range(1, config.finish_passes + 1):
        factor = (config.finish_passes - pass_index) / config.finish_passes
        finish_passes.append(ProfilePass(
            offset_x=config.stock_x * factor,
            offset_z=config.stock_z * factor,
        ))
    finish_passes.extend(ProfilePass(0.0, 0.0) for _ in range(config.spring_passes))
    return finish_passes


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


def emit_roughing_gcode(lines, optional_prefix, config, x_safe, rough_passes):
    lines.append(f"{optional_prefix}G0 X{fmt(x_safe)} Z{fmt(config.z_start)}")
    for rough_pass in rough_passes:
        lines.append(f"{optional_prefix}G0 X{fmt(rough_pass.cut_x)}")
        lines.append(f"{optional_prefix}G1 Z{fmt(rough_pass.cut_z)}")
        lines.append(f"{optional_prefix}G0 X{fmt(rough_pass.exit_x)} Z{fmt(rough_pass.exit_z)}")
        lines.append(f"{optional_prefix}G0 Z{fmt(config.z_start)}")
    lines.append(f"{optional_prefix}G0 X{fmt(x_safe)}")
    lines.append("")


def emit_contour_pass_gcode(lines, optional_prefix, config, x_safe, path, contour_pass, entry_x):
    lines.append(f"( contour pass: stock_x={fmt(contour_pass.offset_x)} stock_z={fmt(contour_pass.offset_z)} )")
    lines.append(f"{optional_prefix}G0 X{fmt(entry_x)} Z{fmt(config.z_start)}")
    emit_toolpath(lines, optional_prefix, path, contour_pass.offset_x, contour_pass.offset_z)
    lines.append(f"{optional_prefix}G0 X{fmt(x_safe)} Z{fmt(config.z_start)}")


def emit_finish_gcode(lines, optional_prefix, config, x_safe, x_profile_start, path, finish_passes):
    for finish_pass in finish_passes:
        lines.append(f"{optional_prefix}G0 X{fmt(x_safe)} Z{fmt(config.z_start)}")
        lines.append(f"{optional_prefix}G0 X{fmt(x_profile_start + finish_pass.offset_x)} Z{fmt(config.z_start)}")
        emit_toolpath(lines, optional_prefix, path, finish_pass.offset_x, finish_pass.offset_z)
    lines.append(f"{optional_prefix}G0 X{fmt(x_safe)} Z{fmt(config.z_start)}")
