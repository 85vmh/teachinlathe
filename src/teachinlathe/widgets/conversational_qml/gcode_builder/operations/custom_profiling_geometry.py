import math

from .custom_profiling_types import (
    ProfileArcSegment,
    ProfileLineSegment,
    StartPoint,
    ToolpathArc,
    ToolpathLine,
)


def json_dir_to_gcode(direction_str):
    # The lathe profile convention used here maps JSON ccw/cw to G2/G3.
    return 2 if str(direction_str).lower() == "ccw" else 3


def build_profile_segments(primitives):
    segments = []
    for primitive in (primitives or []):
        primitive_type = primitive.get("type", "")
        if primitive_type == "startPoint":
            segments.append(StartPoint(
                x=float(primitive.get("x_start", 0.0)),
                z=float(primitive.get("z_start", 0.0)),
            ))
            continue

        blend = primitive.get("blend") or {}
        if primitive_type == "lineTo":
            segments.append(ProfileLineSegment(
                end_x=float(primitive.get("x_end", 0.0)),
                end_z=float(primitive.get("z_end", 0.0)),
                blend_type=blend.get("type", "none"),
                blend_radius=float(blend.get("fillet_radius", 0.0) or 0.0),
                blend_width=float(blend.get("chamfer_width", 0.0) or 0.0),
            ))
            continue

        if primitive_type == "arcTo":
            end_x = float(primitive.get("x_end", 0.0))
            end_z = float(primitive.get("z_end", 0.0))
            center_x = float(primitive.get("x_center", 0.0))
            center_z = float(primitive.get("z_center", 0.0))
            segments.append(ProfileArcSegment(
                end_x=end_x,
                end_z=end_z,
                center_x=center_x,
                center_z=center_z,
                radius=math.sqrt((end_x - center_x) ** 2 + (end_z - center_z) ** 2),
                gcode_dir=json_dir_to_gcode(primitive.get("direction", "cw")),
                blend_type=blend.get("type", "none"),
                blend_radius=float(blend.get("fillet_radius", 0.0) or 0.0),
                blend_width=float(blend.get("chamfer_width", 0.0) or 0.0),
            ))
    return segments


def profile_extents(segments):
    x_values = []
    final_z = 0.0
    for segment in segments:
        if isinstance(segment, StartPoint):
            x_values.append(segment.x)
            final_z = segment.z
        else:
            x_values.append(segment.end_x)
            final_z = segment.end_z
    return (min(x_values) if x_values else 0.0), final_z


def _next_segment(segments, index):
    if index + 1 < len(segments):
        return segments[index + 1]
    return None


def _fillet_between_lines(start_x, start_z, corner_x, corner_z, next_segment, radius):
    if not isinstance(next_segment, ProfileLineSegment):
        return None
    delta1_x = corner_x - start_x
    delta1_z = corner_z - start_z
    length1 = math.sqrt(delta1_x ** 2 + delta1_z ** 2)
    if length1 < 0.001 or radius < 0.001:
        return None

    delta2_x = next_segment.end_x - corner_x
    delta2_z = next_segment.end_z - corner_z
    length2 = math.sqrt(delta2_x ** 2 + delta2_z ** 2)
    if length2 < 0.001:
        return None

    dir1_x = delta1_x / length1
    dir1_z = delta1_z / length1
    dir2_x = delta2_x / length2
    dir2_z = delta2_z / length2
    cross = dir1_z * dir2_x - dir1_x * dir2_z
    dot = dir1_z * dir2_z + dir1_x * dir2_x
    if abs(cross) < 0.001:
        return None

    tangent_distance = radius * (1.0 - dot) / abs(cross)
    tangent1_x = corner_x - tangent_distance * dir1_x
    tangent1_z = corner_z - tangent_distance * dir1_z
    tangent2_x = corner_x + tangent_distance * dir2_x
    tangent2_z = corner_z + tangent_distance * dir2_z

    normal_x = dir1_z if cross > 0 else -dir1_z
    normal_z = -dir1_x if cross > 0 else dir1_x
    return tangent1_x, tangent1_z, tangent2_x, tangent2_z, tangent1_x + radius * normal_x, tangent1_z + radius * normal_z, cross < 0


def _fillet_between_arc_and_line(center_x, center_z, arc_radius, is_cw, join_x, join_z, next_segment, radius):
    if not isinstance(next_segment, ProfileLineSegment):
        return None
    delta2_raw_x = next_segment.end_x - join_x
    delta2_raw_z = next_segment.end_z - join_z
    length2 = math.sqrt(delta2_raw_x ** 2 + delta2_raw_z ** 2)
    if length2 < 0.001 or radius < 0.001 or arc_radius < 0.001:
        return None
    dir2_x = delta2_raw_x / length2
    dir2_z = delta2_raw_z / length2

    radial_x = join_x - center_x
    radial_z = join_z - center_z
    radial_length = math.sqrt(radial_x ** 2 + radial_z ** 2)
    if radial_length < 0.001:
        return None
    dir1_x = (radial_z if is_cw else -radial_z) / radial_length
    dir1_z = (-radial_x if is_cw else radial_x) / radial_length

    cross = dir1_z * dir2_x - dir1_x * dir2_z
    if abs(cross) < 0.001:
        return None

    normal2_x = dir2_z if cross > 0 else -dir2_z
    normal2_z = -dir2_x if cross > 0 else dir2_x
    offset_x = join_x + radius * normal2_x - center_x
    offset_z = join_z + radius * normal2_z - center_z

    projection = offset_z * dir2_z + offset_x * dir2_x
    discriminant = projection ** 2 - (offset_z ** 2 + offset_x ** 2) + (arc_radius + radius) ** 2
    if discriminant < 0:
        return None

    tangent_distance = -projection + math.sqrt(discriminant)
    fillet_center_x = join_x + radius * normal2_x + tangent_distance * dir2_x
    fillet_center_z = join_z + radius * normal2_z + tangent_distance * dir2_z
    tangent2_x = join_x + tangent_distance * dir2_x
    tangent2_z = join_z + tangent_distance * dir2_z
    center_vector_x = fillet_center_x - center_x
    center_vector_z = fillet_center_z - center_z
    center_vector_length = math.sqrt(center_vector_x ** 2 + center_vector_z ** 2)
    if center_vector_length < 0.001:
        return None

    tangent1_x = center_x + arc_radius * center_vector_x / center_vector_length
    tangent1_z = center_z + arc_radius * center_vector_z / center_vector_length
    return tangent1_x, tangent1_z, tangent2_x, tangent2_z, fillet_center_x, fillet_center_z, cross < 0


def _fillet_between_line_and_arc(start_x, start_z, corner_x, corner_z, next_arc, radius):
    if not isinstance(next_arc, ProfileArcSegment):
        return None
    is_cw = next_arc.gcode_dir != 2
    if radius < 0.001 or next_arc.radius < 0.001:
        return None

    delta1_x = corner_x - start_x
    delta1_z = corner_z - start_z
    length1 = math.sqrt(delta1_x ** 2 + delta1_z ** 2)
    if length1 < 0.001:
        return None
    dir1_x = delta1_x / length1
    dir1_z = delta1_z / length1

    radial_x = corner_x - next_arc.center_x
    radial_z = corner_z - next_arc.center_z
    radial_length = math.sqrt(radial_x ** 2 + radial_z ** 2)
    if radial_length < 0.001:
        return None
    dir2_x = (radial_z if is_cw else -radial_z) / radial_length
    dir2_z = (-radial_x if is_cw else radial_x) / radial_length

    cross = dir1_z * dir2_x - dir1_x * dir2_z
    if abs(cross) < 0.001:
        return None

    normal1_x = dir1_z if cross > 0 else -dir1_z
    normal1_z = -dir1_x if cross > 0 else dir1_x
    offset_x = corner_x + radius * normal1_x - next_arc.center_x
    offset_z = corner_z + radius * normal1_z - next_arc.center_z

    projection = offset_z * dir1_z + offset_x * dir1_x
    discriminant = projection ** 2 - (offset_z ** 2 + offset_x ** 2) + (next_arc.radius + radius) ** 2
    if discriminant < 0:
        return None

    tangent_distance = projection + math.sqrt(discriminant)
    fillet_center_x = corner_x - tangent_distance * dir1_x + radius * normal1_x
    fillet_center_z = corner_z - tangent_distance * dir1_z + radius * normal1_z
    tangent1_x = corner_x - tangent_distance * dir1_x
    tangent1_z = corner_z - tangent_distance * dir1_z
    center_vector_x = fillet_center_x - next_arc.center_x
    center_vector_z = fillet_center_z - next_arc.center_z
    center_vector_length = math.sqrt(center_vector_x ** 2 + center_vector_z ** 2)
    if center_vector_length < 0.001:
        return None

    tangent2_x = next_arc.center_x + next_arc.radius * center_vector_x / center_vector_length
    tangent2_z = next_arc.center_z + next_arc.radius * center_vector_z / center_vector_length
    return tangent1_x, tangent1_z, tangent2_x, tangent2_z, fillet_center_x, fillet_center_z, cross < 0


def _chamfer_line(logical_x, logical_z, end_x, end_z, next_segment, width):
    delta_x = end_x - logical_x
    delta_z = end_z - logical_z
    length = math.sqrt(delta_x ** 2 + delta_z ** 2)
    if length < 0.001 or width < 0.001:
        return None
    chamfer_start_x = end_x - width * delta_x / length
    chamfer_start_z = end_z - width * delta_z / length
    chamfer_end_x = end_x
    chamfer_end_z = end_z

    if isinstance(next_segment, ProfileLineSegment):
        next_delta_x = next_segment.end_x - end_x
        next_delta_z = next_segment.end_z - end_z
        next_length = math.sqrt(next_delta_x ** 2 + next_delta_z ** 2)
        if next_length > 0.001:
            chamfer_end_x = end_x + width * next_delta_x / next_length
            chamfer_end_z = end_z + width * next_delta_z / next_length
    elif isinstance(next_segment, ProfileArcSegment):
        radial_x = end_x - next_segment.center_x
        radial_z = end_z - next_segment.center_z
        tangent_x = radial_z if next_segment.gcode_dir != 2 else -radial_z
        tangent_z = -radial_x if next_segment.gcode_dir != 2 else radial_x
        tangent_length = math.sqrt(tangent_x ** 2 + tangent_z ** 2)
        if tangent_length > 0.001:
            chamfer_end_x = end_x + width * tangent_x / tangent_length
            chamfer_end_z = end_z + width * tangent_z / tangent_length
    return chamfer_start_x, chamfer_start_z, chamfer_end_x, chamfer_end_z


def _chamfer_arc(center_x, center_z, radius, is_cw, end_x, end_z, next_segment, width):
    radial_x = end_x - center_x
    radial_z = end_z - center_z
    radial_length = math.sqrt(radial_x ** 2 + radial_z ** 2)
    if radial_length < 0.001 or width < 0.001:
        return None
    tangent_x = radial_z if is_cw else -radial_z
    tangent_z = -radial_x if is_cw else radial_x
    chamfer_start_x = end_x - width * tangent_x / radial_length
    chamfer_start_z = end_z - width * tangent_z / radial_length
    chamfer_end_x = end_x
    chamfer_end_z = end_z
    if isinstance(next_segment, ProfileLineSegment):
        next_delta_x = next_segment.end_x - end_x
        next_delta_z = next_segment.end_z - end_z
        next_length = math.sqrt(next_delta_x ** 2 + next_delta_z ** 2)
        if next_length > 0.001:
            chamfer_end_x = end_x + width * next_delta_x / next_length
            chamfer_end_z = end_z + width * next_delta_z / next_length
    return chamfer_start_x, chamfer_start_z, chamfer_end_x, chamfer_end_z


def _expand_line_segment(logical_x, logical_z, segment, next_segment):
    if segment.blend_type == "chamfer":
        chamfer = _chamfer_line(logical_x, logical_z, segment.end_x, segment.end_z, next_segment, segment.blend_width)
        if chamfer:
            start_x, start_z, end_x, end_z = chamfer
            return [ToolpathLine(start_x, start_z), ToolpathLine(end_x, end_z)]
        return [ToolpathLine(segment.end_x, segment.end_z)]

    if segment.blend_type == "fillet":
        radius = segment.blend_radius
        if isinstance(next_segment, ProfileArcSegment):
            fillet = _fillet_between_line_and_arc(logical_x, logical_z, segment.end_x, segment.end_z, next_segment, radius)
        else:
            fillet = _fillet_between_lines(logical_x, logical_z, segment.end_x, segment.end_z, next_segment, radius)
        if fillet:
            tangent1_x, tangent1_z, tangent2_x, tangent2_z, center_x, center_z, anticlockwise = fillet
            return [
                ToolpathLine(tangent1_x, tangent1_z),
                ToolpathArc(tangent2_x, tangent2_z, center_x, center_z, anticlockwise),
            ]
    return [ToolpathLine(segment.end_x, segment.end_z)]


def _expand_arc_segment(segment, next_segment):
    is_cw = segment.gcode_dir != 2
    if segment.blend_type == "chamfer":
        chamfer = _chamfer_arc(segment.center_x, segment.center_z, segment.radius, is_cw, segment.end_x, segment.end_z, next_segment, segment.blend_width)
        if chamfer:
            start_x, start_z, end_x, end_z = chamfer
            return [
                ToolpathArc(start_x, start_z, segment.center_x, segment.center_z, not is_cw),
                ToolpathLine(end_x, end_z),
            ]
    elif segment.blend_type == "fillet":
        fillet = _fillet_between_arc_and_line(segment.center_x, segment.center_z, segment.radius, is_cw, segment.end_x, segment.end_z, next_segment, segment.blend_radius)
        if fillet:
            tangent1_x, tangent1_z, tangent2_x, tangent2_z, center_x, center_z, anticlockwise = fillet
            return [
                ToolpathArc(tangent1_x, tangent1_z, segment.center_x, segment.center_z, not is_cw),
                ToolpathArc(tangent2_x, tangent2_z, center_x, center_z, anticlockwise),
            ]
    return [ToolpathArc(segment.end_x, segment.end_z, segment.center_x, segment.center_z, not is_cw)]


def build_render_path(segments):
    if not segments:
        return []

    path = []
    logical_x = 0.0
    logical_z = 0.0
    for index, segment in enumerate(segments):
        if isinstance(segment, StartPoint):
            logical_x = segment.x
            logical_z = segment.z
            path.append(segment)
            continue

        next_segment = _next_segment(segments, index)
        if isinstance(segment, ProfileLineSegment):
            path.extend(_expand_line_segment(logical_x, logical_z, segment, next_segment))
            logical_x = segment.end_x
            logical_z = segment.end_z
            continue

        path.extend(_expand_arc_segment(segment, next_segment))
        logical_x = segment.end_x
        logical_z = segment.end_z
    return path


def find_deepest_z_at_x_path(path, target_x, x_shift=0.0, z_shift=0.0):
    if not path:
        return 0.0

    current_x = path[0].x + x_shift
    current_z = path[0].z + z_shift
    final_z = current_z
    candidates = []

    for element in path[1:]:
        end_x = element.end_x + x_shift
        end_z = element.end_z + z_shift
        final_z = end_z
        x_min = min(current_x, end_x)
        x_max = max(current_x, end_x)

        if isinstance(element, ToolpathLine):
            if abs(end_x - current_x) > 1e-9:
                if x_min <= target_x <= x_max:
                    interpolated_z = current_z + (target_x - current_x) * (end_z - current_z) / (end_x - current_x)
                    candidates.append(interpolated_z)
            elif abs(target_x - current_x) < 1e-6:
                candidates.append(min(current_z, end_z))
        else:
            if x_min <= target_x <= x_max:
                center_x = element.center_x + x_shift
                center_z = element.center_z + z_shift
                radius = math.sqrt((current_x - center_x) ** 2 + (current_z - center_z) ** 2)
                delta_x = target_x - center_x
                if abs(delta_x) <= radius:
                    discriminant = radius ** 2 - delta_x ** 2
                    z_plus = center_z + math.sqrt(discriminant)
                    z_minus = center_z - math.sqrt(discriminant)
                    z_min = min(current_z, end_z)
                    z_max = max(current_z, end_z)
                    for candidate_z in (z_plus, z_minus):
                        if z_min - 1e-6 <= candidate_z <= z_max + 1e-6:
                            candidates.append(candidate_z)

        current_x, current_z = end_x, end_z

    if candidates:
        return min(candidates)
    return final_z
