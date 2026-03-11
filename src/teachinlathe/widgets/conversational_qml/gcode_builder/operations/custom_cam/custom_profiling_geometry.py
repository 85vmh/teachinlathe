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


def _as_legacy_segment(segment):
    if isinstance(segment, StartPoint):
        return {"type": "startPoint", "x": segment.x, "z": segment.z}
    if isinstance(segment, ProfileLineSegment):
        return {
            "type": "lineTo",
            "x_end": segment.end_x,
            "z_end": segment.end_z,
            "blend_type": segment.blend_type,
            "blend_rf": segment.blend_radius,
            "blend_cw": segment.blend_width,
        }
    return {
        "type": "arcTo",
        "x_end": segment.end_x,
        "z_end": segment.end_z,
        "x_center": segment.center_x,
        "z_center": segment.center_z,
        "arc_radius": segment.radius,
        "gcode_dir": segment.gcode_dir,
        "blend_type": segment.blend_type,
        "blend_rf": segment.blend_radius,
        "blend_cw": segment.blend_width,
    }


def _legacy_next_segment(segments, index):
    if index + 1 < len(segments):
        return segments[index + 1]
    return None


def _legacy_fillet_line_line(start_x, start_z, corner_x, corner_z, next_segment, radius):
    if not next_segment or next_segment["type"] != "lineTo":
        return None
    start_delta_x = corner_x - start_x
    start_delta_z = corner_z - start_z
    start_length = math.sqrt(start_delta_x ** 2 + start_delta_z ** 2)
    if start_length < 0.001 or radius < 0.001:
        return None

    next_delta_x = next_segment["x_end"] - corner_x
    next_delta_z = next_segment["z_end"] - corner_z
    next_length = math.sqrt(next_delta_x ** 2 + next_delta_z ** 2)
    if next_length < 0.001:
        return None

    dir1_x = start_delta_x / start_length
    dir1_z = start_delta_z / start_length
    dir2_x = next_delta_x / next_length
    dir2_z = next_delta_z / next_length
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


def _legacy_fillet_arc_line(center_x, center_z, arc_radius, is_cw, join_x, join_z, next_segment, radius):
    if not next_segment or next_segment["type"] != "lineTo":
        return None
    next_delta_raw_x = next_segment["x_end"] - join_x
    next_delta_raw_z = next_segment["z_end"] - join_z
    next_length = math.sqrt(next_delta_raw_x ** 2 + next_delta_raw_z ** 2)
    if next_length < 0.001 or radius < 0.001 or arc_radius < 0.001:
        return None
    dir2_x = next_delta_raw_x / next_length
    dir2_z = next_delta_raw_z / next_length

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


def _legacy_fillet_line_arc(start_x, start_z, corner_x, corner_z, next_arc, radius):
    if not next_arc or next_arc["type"] != "arcTo":
        return None
    is_cw = next_arc["gcode_dir"] != 2
    arc_radius = next_arc["arc_radius"]
    if radius < 0.001 or arc_radius < 0.001:
        return None

    delta1_x = corner_x - start_x
    delta1_z = corner_z - start_z
    length1 = math.sqrt(delta1_x ** 2 + delta1_z ** 2)
    if length1 < 0.001:
        return None
    dir1_x = delta1_x / length1
    dir1_z = delta1_z / length1

    radial_x = corner_x - next_arc["x_center"]
    radial_z = corner_z - next_arc["z_center"]
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
    offset_x = corner_x + radius * normal1_x - next_arc["x_center"]
    offset_z = corner_z + radius * normal1_z - next_arc["z_center"]

    projection = offset_z * dir1_z + offset_x * dir1_x
    discriminant = projection ** 2 - (offset_z ** 2 + offset_x ** 2) + (arc_radius + radius) ** 2
    if discriminant < 0:
        return None

    tangent_distance = projection + math.sqrt(discriminant)
    fillet_center_x = corner_x - tangent_distance * dir1_x + radius * normal1_x
    fillet_center_z = corner_z - tangent_distance * dir1_z + radius * normal1_z
    tangent1_x = corner_x - tangent_distance * dir1_x
    tangent1_z = corner_z - tangent_distance * dir1_z
    center_vector_x = fillet_center_x - next_arc["x_center"]
    center_vector_z = fillet_center_z - next_arc["z_center"]
    center_vector_length = math.sqrt(center_vector_x ** 2 + center_vector_z ** 2)
    if center_vector_length < 0.001:
        return None

    tangent2_x = next_arc["x_center"] + arc_radius * center_vector_x / center_vector_length
    tangent2_z = next_arc["z_center"] + arc_radius * center_vector_z / center_vector_length
    return tangent1_x, tangent1_z, tangent2_x, tangent2_z, fillet_center_x, fillet_center_z, cross < 0


def _legacy_chamfer_line(logical_x, logical_z, end_x, end_z, next_segment, width):
    delta_x = end_x - logical_x
    delta_z = end_z - logical_z
    length = math.sqrt(delta_x ** 2 + delta_z ** 2)
    if length < 0.001 or width < 0.001:
        return None
    chamfer_start_x = end_x - width * delta_x / length
    chamfer_start_z = end_z - width * delta_z / length
    chamfer_end_x = end_x
    chamfer_end_z = end_z

    if next_segment and next_segment["type"] == "lineTo":
        next_delta_x = next_segment["x_end"] - end_x
        next_delta_z = next_segment["z_end"] - end_z
        next_length = math.sqrt(next_delta_x ** 2 + next_delta_z ** 2)
        if next_length > 0.001:
            chamfer_end_x = end_x + width * next_delta_x / next_length
            chamfer_end_z = end_z + width * next_delta_z / next_length
    elif next_segment and next_segment["type"] == "arcTo":
        radial_x = end_x - next_segment["x_center"]
        radial_z = end_z - next_segment["z_center"]
        tangent_x = radial_z if next_segment["gcode_dir"] != 2 else -radial_z
        tangent_z = -radial_x if next_segment["gcode_dir"] != 2 else radial_x
        tangent_length = math.sqrt(tangent_x ** 2 + tangent_z ** 2)
        if tangent_length > 0.001:
            chamfer_end_x = end_x + width * tangent_x / tangent_length
            chamfer_end_z = end_z + width * tangent_z / tangent_length
    return chamfer_start_x, chamfer_start_z, chamfer_end_x, chamfer_end_z


def _legacy_chamfer_arc(center_x, center_z, radius, is_cw, end_x, end_z, next_segment, width):
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
    if next_segment and next_segment["type"] == "lineTo":
        next_delta_x = next_segment["x_end"] - end_x
        next_delta_z = next_segment["z_end"] - end_z
        next_length = math.sqrt(next_delta_x ** 2 + next_delta_z ** 2)
        if next_length > 0.001:
            chamfer_end_x = end_x + width * next_delta_x / next_length
            chamfer_end_z = end_z + width * next_delta_z / next_length
    return chamfer_start_x, chamfer_start_z, chamfer_end_x, chamfer_end_z


def build_render_path(segments):
    if not segments:
        return []

    legacy_segments = [_as_legacy_segment(segment) for segment in segments]
    path = []
    logical_x = 0.0
    logical_z = 0.0
    for index, segment in enumerate(legacy_segments):
        if segment["type"] == "startPoint":
            logical_x = segment["x"]
            logical_z = segment["z"]
            path.append(StartPoint(logical_x, logical_z))
            continue

        next_segment = _legacy_next_segment(legacy_segments, index)
        if segment["type"] == "lineTo":
            end_x = segment["x_end"]
            end_z = segment["z_end"]
            if segment.get("blend_type") == "chamfer":
                chamfer = _legacy_chamfer_line(logical_x, logical_z, end_x, end_z, next_segment, segment.get("blend_cw", 0.0))
                if chamfer:
                    start_x, start_z, chamfer_end_x, chamfer_end_z = chamfer
                    path.append(ToolpathLine(start_x, start_z))
                    path.append(ToolpathLine(chamfer_end_x, chamfer_end_z))
                else:
                    path.append(ToolpathLine(end_x, end_z))
            elif segment.get("blend_type") == "fillet":
                radius = segment.get("blend_rf", 0.0)
                if next_segment and next_segment["type"] == "arcTo":
                    fillet = _legacy_fillet_line_arc(logical_x, logical_z, end_x, end_z, next_segment, radius)
                else:
                    fillet = _legacy_fillet_line_line(logical_x, logical_z, end_x, end_z, next_segment, radius)
                if fillet:
                    tangent1_x, tangent1_z, tangent2_x, tangent2_z, center_x, center_z, anticlockwise = fillet
                    path.append(ToolpathLine(tangent1_x, tangent1_z))
                    path.append(ToolpathArc(tangent2_x, tangent2_z, center_x, center_z, anticlockwise))
                else:
                    path.append(ToolpathLine(end_x, end_z))
            else:
                path.append(ToolpathLine(end_x, end_z))
            logical_x = end_x
            logical_z = end_z
            continue

        end_x = segment["x_end"]
        end_z = segment["z_end"]
        is_cw = segment["gcode_dir"] != 2
        if segment.get("blend_type") == "chamfer":
            chamfer = _legacy_chamfer_arc(segment["x_center"], segment["z_center"], segment["arc_radius"], is_cw, end_x, end_z, next_segment, segment.get("blend_cw", 0.0))
            if chamfer:
                start_x, start_z, chamfer_end_x, chamfer_end_z = chamfer
                path.append(ToolpathArc(start_x, start_z, segment["x_center"], segment["z_center"], not is_cw))
                path.append(ToolpathLine(chamfer_end_x, chamfer_end_z))
            else:
                path.append(ToolpathArc(end_x, end_z, segment["x_center"], segment["z_center"], not is_cw))
        elif segment.get("blend_type") == "fillet":
            fillet = _legacy_fillet_arc_line(segment["x_center"], segment["z_center"], segment["arc_radius"], is_cw, end_x, end_z, next_segment, segment.get("blend_rf", 0.0))
            if fillet:
                tangent1_x, tangent1_z, tangent2_x, tangent2_z, center_x, center_z, anticlockwise = fillet
                path.append(ToolpathArc(tangent1_x, tangent1_z, segment["x_center"], segment["z_center"], not is_cw))
                path.append(ToolpathArc(tangent2_x, tangent2_z, center_x, center_z, anticlockwise))
            else:
                path.append(ToolpathArc(end_x, end_z, segment["x_center"], segment["z_center"], not is_cw))
        else:
            path.append(ToolpathArc(end_x, end_z, segment["x_center"], segment["z_center"], not is_cw))
        logical_x = end_x
        logical_z = end_z
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
