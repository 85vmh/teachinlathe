import math
from dataclasses import dataclass


@dataclass(frozen=True)
class StartPoint:
    x: float
    z: float
    blend_type: str = "none"
    blend_width: float = 0.0
    blend_radius: float = 0.0


@dataclass(frozen=True)
class ProfileLineSegment:
    end_x: float
    end_z: float
    blend_type: str = "none"
    blend_radius: float = 0.0
    blend_width: float = 0.0
    undercut_radius: float = 0.4
    undercut_depth: float = 0.4
    undercut_length: float = 2.5
    angle: float = 0.0
    input_mode: str = "xz"


@dataclass(frozen=True)
class ProfileArcSegment:
    end_x: float
    end_z: float
    center_x: float
    center_z: float
    radius: float
    gcode_dir: int
    blend_type: str = "none"
    blend_radius: float = 0.0
    blend_width: float = 0.0
    undercut_radius: float = 0.4
    undercut_depth: float = 0.4
    undercut_length: float = 2.5


@dataclass(frozen=True)
class ToolpathLine:
    end_x: float
    end_z: float


@dataclass(frozen=True)
class ToolpathArc:
    end_x: float
    end_z: float
    center_x: float
    center_z: float
    anticlockwise: bool


def json_dir_to_gcode(direction_str):
    # The lathe profile convention used here maps JSON ccw/cw to G2/G3.
    return 2 if str(direction_str).lower() == "ccw" else 3


def resolve_line_endpoint(start_x, start_z, end_x, end_z, angle, input_mode):
    """Resolve LineTo endpoint. X values are diameters; angle is from the Z axis."""
    mode = str(input_mode or "xz").lower()
    if mode not in ("xz", "ax", "az"):
        mode = "xz"
    end_x = float(end_x)
    end_z = float(end_z)
    if mode == "xz":
        return end_x, end_z

    angle_rad = math.radians(float(angle or 0.0))
    tangent = math.tan(angle_rad)
    if mode == "az":
        return float(start_x) + 2.0 * (end_z - float(start_z)) * tangent, end_z
    if abs(tangent) < 1e-12:
        return end_x, float(start_z)
    radial_delta = (end_x - float(start_x)) / 2.0
    return end_x, float(start_z) + radial_delta / tangent


def build_profile_segments(primitives):
    segments = []
    current_x = 0.0
    current_z = 0.0
    for primitive in (primitives or []):
        primitive_type = primitive.get("type", "")
        if primitive_type == "startPoint":
            current_x = float(primitive.get("x_start", 0.0))
            current_z = float(primitive.get("z_start", 0.0))
            blend = primitive.get("blend") or {}
            segments.append(StartPoint(
                x=current_x,
                z=current_z,
                blend_type=blend.get("type", "none"),
                blend_width=float(blend.get("chamfer_width", 0.0) or 0.0),
                blend_radius=float(blend.get("fillet_radius", 0.0) or 0.0),
            ))
            continue

        blend = primitive.get("blend") or {}
        if primitive_type == "lineTo":
            end_x, end_z = resolve_line_endpoint(
                current_x, current_z,
                primitive.get("x_end", 0.0), primitive.get("z_end", 0.0),
                primitive.get("angle", 0.0), primitive.get("input", "xz"),
            )
            segments.append(ProfileLineSegment(
                end_x=end_x,
                end_z=end_z,
                blend_type=blend.get("type", "none"),
                blend_radius=float(blend.get("fillet_radius", 0.0) or 0.0),
                blend_width=float(blend.get("chamfer_width", 0.0) or 0.0),
                undercut_radius=float(blend.get("undercut_radius", 0.4) or 0.4),
                undercut_depth=float(blend.get("undercut_depth", 0.4) or 0.4),
                undercut_length=float(blend.get("undercut_length", 2.5) or 2.5),
                angle=float(primitive.get("angle", 0.0) or 0.0),
                input_mode=str(primitive.get("input", "xz") or "xz").lower(),
            ))
            current_x = end_x
            current_z = end_z
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
                undercut_radius=float(blend.get("undercut_radius", 0.4) or 0.4),
                undercut_depth=float(blend.get("undercut_depth", 0.4) or 0.4),
                undercut_length=float(blend.get("undercut_length", 2.5) or 2.5),
            ))
            current_x = end_x
            current_z = end_z
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
        return {
            "type": "startPoint", "x": segment.x, "z": segment.z,
            "blend_type": segment.blend_type,
            "blend_cw": segment.blend_width,
            "blend_rf": segment.blend_radius,
        }
    if isinstance(segment, ProfileLineSegment):
        return {
            "type": "lineTo",
            "x_end": segment.end_x,
            "z_end": segment.end_z,
            "blend_type": segment.blend_type,
            "blend_rf": segment.blend_radius,
            "blend_cw": segment.blend_width,
            "undercut_radius": segment.undercut_radius,
            "undercut_depth": segment.undercut_depth,
            "undercut_length": segment.undercut_length,
            "angle": segment.angle,
            "input": segment.input_mode,
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
        "undercut_radius": segment.undercut_radius,
        "undercut_depth": segment.undercut_depth,
        "undercut_length": segment.undercut_length,
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


def _legacy_undercut_din509_line(
    start_x,
    start_z,
    corner_x,
    corner_z,
    next_segment,
    undercut_radius,
    undercut_depth,
    undercut_length,
):
    if not next_segment or next_segment["type"] != "lineTo":
        return None
    if (
        undercut_radius < 0.001
        or undercut_depth < 0.001
        or undercut_length < 0.001
        or undercut_depth < undercut_radius
    ):
        return None

    delta1_x = corner_x - start_x
    delta1_z = corner_z - start_z
    length1 = math.sqrt(delta1_x ** 2 + delta1_z ** 2)
    if length1 < 0.001:
        return None

    delta2_x = next_segment["x_end"] - corner_x
    delta2_z = next_segment["z_end"] - corner_z
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

    ramp_len = undercut_depth / math.tan(math.radians(15.0))
    depth_x = dir1_z
    depth_z = -dir1_x
    if depth_x * dir2_x + depth_z * dir2_z > 0:
        depth_x = -depth_x
        depth_z = -depth_z

    floor_base_x = corner_x + undercut_depth * depth_x
    floor_base_z = corner_z + undercut_depth * depth_z
    to_corner_x = corner_x - floor_base_x
    to_corner_z = corner_z - floor_base_z
    floor_to_next_intersection = (to_corner_z * dir2_x - to_corner_x * dir2_z) / cross
    join_x = floor_base_x + floor_to_next_intersection * dir1_x
    join_z = floor_base_z + floor_to_next_intersection * dir1_z

    tangent_len = undercut_radius * (1.0 - dot) / abs(cross)
    min_length = ramp_len + tangent_len
    effective_length = max(undercut_length, min_length)
    flat_len = effective_length - min_length

    arc_start_x = join_x - tangent_len * dir1_x
    arc_start_z = join_z - tangent_len * dir1_z
    ramp_start_x = arc_start_x - (flat_len + ramp_len) * dir1_x - undercut_depth * depth_x
    ramp_start_z = arc_start_z - (flat_len + ramp_len) * dir1_z - undercut_depth * depth_z
    ramp_end_x = ramp_start_x + ramp_len * dir1_x + undercut_depth * depth_x
    ramp_end_z = ramp_start_z + ramp_len * dir1_z + undercut_depth * depth_z
    exit_x = join_x + tangent_len * dir2_x
    exit_z = join_z + tangent_len * dir2_z
    normal_x = dir1_z if cross > 0 else -dir1_z
    normal_z = -dir1_x if cross > 0 else dir1_x
    arc_center_x = arc_start_x + undercut_radius * normal_x
    arc_center_z = arc_start_z + undercut_radius * normal_z

    return {
        "entry_x": ramp_start_x,
        "entry_z": ramp_start_z,
        "ramp_end_x": ramp_end_x,
        "ramp_end_z": ramp_end_z,
        "arc_start_x": arc_start_x,
        "arc_start_z": arc_start_z,
        "arc_center_x": arc_center_x,
        "arc_center_z": arc_center_z,
        "exit_x": exit_x,
        "exit_z": exit_z,
        "anticlockwise": cross < 0,
    }


def _half_x_seg(seg):
    """Return seg dict with all X fields halved (diameter → physical radius) for geometry calls."""
    if seg is None:
        return None
    if seg["type"] == "lineTo":
        return {**seg, "x_end": seg["x_end"] / 2}
    if seg["type"] == "arcTo":
        xeh = seg["x_end"] / 2
        xch = seg["x_center"] / 2
        return {
            **seg,
            "x_end": xeh,
            "x_center": xch,
            "arc_radius": math.sqrt((xeh - xch) ** 2 + (seg["z_end"] - seg["z_center"]) ** 2),
        }
    return seg


def build_render_path(segments, profile_type: str = "od"):
    if not segments:
        return []

    is_id = str(profile_type or "od").lower() == "id"
    legacy_segments = [_as_legacy_segment(segment) for segment in segments]
    path = []
    logical_x = 0.0
    logical_z = 0.0
    for index, segment in enumerate(legacy_segments):
        if segment["type"] == "startPoint":
            logical_x = segment["x"]
            logical_z = segment["z"]
            blend_type = segment.get("blend_type", "none")
            next_seg = _legacy_next_segment(legacy_segments, index)
            if blend_type != "none" and next_seg:
                next_seg_h = _half_x_seg(next_seg)
                sx_r = logical_x / 2
                sz = logical_z
                if blend_type == "chamfer":
                    cw = segment.get("blend_cw", 0.0)
                    entry_x = sx_r + cw if is_id else sx_r - cw
                    chamfer = _legacy_chamfer_line(entry_x, sz, sx_r, sz, next_seg_h, cw)
                    if chamfer:
                        cs_x, cs_z, ce_x, ce_z = chamfer
                        path.append(StartPoint(cs_x * 2, cs_z))
                        path.append(ToolpathLine(ce_x * 2, ce_z))
                        continue
                elif blend_type == "fillet":
                    fr = segment.get("blend_rf", 0.0)
                    entry_x = sx_r + fr if is_id else sx_r - fr
                    if next_seg["type"] == "arcTo":
                        fillet = _legacy_fillet_line_arc(entry_x, sz, sx_r, sz, next_seg_h, fr)
                    else:
                        fillet = _legacy_fillet_line_line(entry_x, sz, sx_r, sz, next_seg_h, fr)
                    if fillet:
                        t1x, t1z, t2x, t2z, fcx, fcz, acw = fillet
                        path.append(StartPoint(t1x * 2, t1z))
                        path.append(ToolpathArc(t2x * 2, t2z, fcx * 2, fcz, acw))
                        continue
            path.append(StartPoint(logical_x, logical_z))
            continue

        next_segment = _legacy_next_segment(legacy_segments, index)
        if segment["type"] == "lineTo":
            end_x = segment["x_end"]
            end_z = segment["z_end"]
            logical_next_x = end_x
            logical_next_z = end_z
            if segment.get("blend_type") == "chamfer":
                chamfer = _legacy_chamfer_line(
                    logical_x / 2, logical_z, end_x / 2, end_z,
                    _half_x_seg(next_segment), segment.get("blend_cw", 0.0),
                )
                if chamfer:
                    sx, sz, cex, cez = chamfer
                    path.append(ToolpathLine(sx * 2, sz))
                    path.append(ToolpathLine(cex * 2, cez))
                else:
                    path.append(ToolpathLine(end_x, end_z))
            elif segment.get("blend_type") == "fillet":
                radius = segment.get("blend_rf", 0.0)
                if next_segment and next_segment["type"] == "arcTo":
                    fillet = _legacy_fillet_line_arc(
                        logical_x / 2, logical_z, end_x / 2, end_z,
                        _half_x_seg(next_segment), radius,
                    )
                else:
                    fillet = _legacy_fillet_line_line(
                        logical_x / 2, logical_z, end_x / 2, end_z,
                        _half_x_seg(next_segment), radius,
                    )
                if fillet:
                    t1x, t1z, t2x, t2z, cx, cz, acw = fillet
                    path.append(ToolpathLine(t1x * 2, t1z))
                    path.append(ToolpathArc(t2x * 2, t2z, cx * 2, cz, acw))
                else:
                    path.append(ToolpathLine(end_x, end_z))
            elif segment.get("blend_type") == "undercut_din509":
                undercut = _legacy_undercut_din509_line(
                    logical_x / 2, logical_z,
                    end_x / 2, end_z,
                    _half_x_seg(next_segment),
                    segment.get("undercut_radius", 0.4),
                    segment.get("undercut_depth", 0.4),
                    segment.get("undercut_length", 2.5),
                )
                if undercut:
                    path.append(ToolpathLine(undercut["entry_x"] * 2, undercut["entry_z"]))
                    path.append(ToolpathLine(undercut["ramp_end_x"] * 2, undercut["ramp_end_z"]))
                    path.append(ToolpathLine(undercut["arc_start_x"] * 2, undercut["arc_start_z"]))
                    path.append(ToolpathArc(
                        undercut["exit_x"] * 2,
                        undercut["exit_z"],
                        undercut["arc_center_x"] * 2,
                        undercut["arc_center_z"],
                        undercut["anticlockwise"],
                    ))
                    logical_next_x = undercut["exit_x"] * 2
                    logical_next_z = undercut["exit_z"]
                else:
                    path.append(ToolpathLine(end_x, end_z))
            else:
                path.append(ToolpathLine(end_x, end_z))
            logical_x = logical_next_x
            logical_z = logical_next_z
            continue

        end_x = segment["x_end"]
        end_z = segment["z_end"]
        cx_d = segment["x_center"]
        cz = segment["z_center"]
        is_cw = segment["gcode_dir"] != 2
        end_x_h = end_x / 2
        cx_h = cx_d / 2
        arc_r_h = math.sqrt((end_x_h - cx_h) ** 2 + (end_z - cz) ** 2)
        if segment.get("blend_type") == "chamfer":
            chamfer = _legacy_chamfer_arc(
                cx_h, cz, arc_r_h, is_cw, end_x_h, end_z,
                _half_x_seg(next_segment), segment.get("blend_cw", 0.0),
            )
            if chamfer:
                sx, sz, cex, cez = chamfer
                path.append(ToolpathArc(sx * 2, sz, cx_d, cz, not is_cw))
                path.append(ToolpathLine(cex * 2, cez))
            else:
                path.append(ToolpathArc(end_x, end_z, cx_d, cz, not is_cw))
        elif segment.get("blend_type") == "fillet":
            fillet = _legacy_fillet_arc_line(
                cx_h, cz, arc_r_h, is_cw, end_x_h, end_z,
                _half_x_seg(next_segment), segment.get("blend_rf", 0.0),
            )
            if fillet:
                t1x, t1z, t2x, t2z, fcx, fcz, acw = fillet
                path.append(ToolpathArc(t1x * 2, t1z, cx_d, cz, not is_cw))
                path.append(ToolpathArc(t2x * 2, t2z, fcx * 2, fcz, acw))
            else:
                path.append(ToolpathArc(end_x, end_z, cx_d, cz, not is_cw))
        else:
            path.append(ToolpathArc(end_x, end_z, cx_d, cz, not is_cw))
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
            center_x = element.center_x + x_shift
            center_z = element.center_z + z_shift
            for z_candidate in _arc_x_intersections_z(
                current_x, current_z, end_x, end_z,
                center_x, center_z, element.anticlockwise, target_x,
            ):
                candidates.append(z_candidate)

        current_x, current_z = end_x, end_z

    if candidates:
        return min(candidates)
    return final_z


def find_profile_x_at_z(path, target_z, x_shift=0.0, z_shift=0.0):
    """Return the maximum X on the render path at a given Z (for boring).

    Analogous to find_deepest_z_at_x_path but transposed: given Z, find X.
    x_shift / z_shift are added to each path point before the search so that
    stock offsets can be applied.
    """
    if not path:
        return 0.0

    current_x = path[0].x + x_shift
    current_z = path[0].z + z_shift
    candidates = []

    for element in path[1:]:
        end_x = element.end_x + x_shift
        end_z = element.end_z + z_shift
        z_lo = min(current_z, end_z)
        z_hi = max(current_z, end_z)

        if isinstance(element, ToolpathLine):
            if abs(end_z - current_z) > 1e-9:
                if z_lo <= target_z <= z_hi:
                    interp = current_x + (target_z - current_z) * (end_x - current_x) / (end_z - current_z)
                    candidates.append(interp)
            elif abs(target_z - current_z) < 1e-6:
                candidates.append(max(current_x, end_x))
        else:  # ToolpathArc
            cx_s = element.center_x + x_shift
            cz_s = element.center_z + z_shift
            for x_candidate in _arc_z_intersections_x(
                current_x, current_z, end_x, end_z,
                cx_s, cz_s, element.anticlockwise, target_z,
            ):
                candidates.append(x_candidate)

        current_x, current_z = end_x, end_z

    return max(candidates) if candidates else current_x


def _normalize_angle(angle):
    two_pi = 2.0 * math.pi
    while angle < 0.0:
        angle += two_pi
    while angle >= two_pi:
        angle -= two_pi
    return angle


def _angle_on_arc(angle, start_angle, end_angle, anticlockwise):
    angle = _normalize_angle(angle)
    start_angle = _normalize_angle(start_angle)
    end_angle = _normalize_angle(end_angle)

    if anticlockwise:
        if end_angle < start_angle:
            end_angle += 2.0 * math.pi
        if angle < start_angle:
            angle += 2.0 * math.pi
        return start_angle - 1e-9 <= angle <= end_angle + 1e-9

    if start_angle < end_angle:
        start_angle += 2.0 * math.pi
    if angle > start_angle:
        angle -= 2.0 * math.pi
    return end_angle - 1e-9 <= angle <= start_angle + 1e-9


def _arc_angle_progress(angle, start_angle, end_angle, anticlockwise):
    angle = _normalize_angle(angle)
    start_angle = _normalize_angle(start_angle)
    end_angle = _normalize_angle(end_angle)

    if anticlockwise:
        if end_angle < start_angle:
            end_angle += 2.0 * math.pi
        if angle < start_angle:
            angle += 2.0 * math.pi
        return angle - start_angle

    if start_angle < end_angle:
        start_angle += 2.0 * math.pi
    if angle > start_angle:
        angle -= 2.0 * math.pi
    return start_angle - angle


def _line_x_intersection(sx, sz, ex, ez, target_x):
    if abs(ex - sx) <= 1e-9:
        return None
    t = (target_x - sx) / (ex - sx)
    if -1e-9 <= t <= 1.0 + 1e-9:
        return target_x, sz + t * (ez - sz)
    return None


def _arc_x_intersection(sx, sz, ex, ez, cx, cz, anticlockwise, target_x):
    radius = math.hypot(sx - cx, sz - cz)
    dx = target_x - cx
    if abs(dx) > radius + 1e-9:
        return None

    disc = max(0.0, radius * radius - dx * dx)
    start_angle = math.atan2(sz - cz, sx - cx)
    end_angle = math.atan2(ez - cz, ex - cx)
    candidates = []
    for z in (cz + math.sqrt(disc), cz - math.sqrt(disc)):
        angle = math.atan2(z - cz, target_x - cx)
        if _angle_on_arc(angle, start_angle, end_angle, anticlockwise):
            candidates.append((_arc_angle_progress(angle, start_angle, end_angle, anticlockwise), target_x, z))

    if not candidates:
        return None
    _, hit_x, hit_z = min(candidates, key=lambda item: item[0])
    return hit_x, hit_z


def _arc_x_intersections_z(sx, sz, ex, ez, cx, cz, anticlockwise, target_x):
    """Return all Z values where arc (sx,sz)->(ex,ez) crosses the vertical line x=target_x.
    X coords are in diameter; geometry is computed in physical radius-Z space."""
    sx_r, ex_r, cx_r, tx_r = sx / 2, ex / 2, cx / 2, target_x / 2
    radius = math.hypot(sx_r - cx_r, sz - cz)
    dx = tx_r - cx_r
    if abs(dx) > radius + 1e-9:
        return []
    disc = max(0.0, radius * radius - dx * dx)
    start_angle = math.atan2(sz - cz, sx_r - cx_r)
    end_angle = math.atan2(ez - cz, ex_r - cx_r)
    results = []
    for z_candidate in (cz + math.sqrt(disc), cz - math.sqrt(disc)):
        angle = math.atan2(z_candidate - cz, dx)
        if _angle_on_arc(angle, start_angle, end_angle, anticlockwise):
            results.append(z_candidate)
    return results


def _arc_z_intersections_x(sx, sz, ex, ez, cx, cz, anticlockwise, target_z):
    """Return all X values (diameter) where arc (sx,sz)->(ex,ez) crosses z=target_z.
    X coords are in diameter; geometry is computed in physical radius-Z space."""
    sx_r, ex_r, cx_r = sx / 2, ex / 2, cx / 2
    radius = math.hypot(sx_r - cx_r, sz - cz)
    dz = target_z - cz
    if abs(dz) > radius + 1e-9:
        return []
    disc = max(0.0, radius * radius - dz * dz)
    start_angle = math.atan2(sz - cz, sx_r - cx_r)
    end_angle = math.atan2(ez - cz, ex_r - cx_r)
    results = []
    for x_r_candidate in (cx_r + math.sqrt(disc), cx_r - math.sqrt(disc)):
        angle = math.atan2(dz, x_r_candidate - cx_r)
        if _angle_on_arc(angle, start_angle, end_angle, anticlockwise):
            results.append(x_r_candidate * 2)
    return results


def build_shifted_path_clipped_to_x_boundary(path, offset_x, offset_z, x_boundary, keep_side):
    """Return shifted path clipped to one side of a vertical X boundary."""
    if not path:
        return []

    if keep_side not in ("lte", "gte"):
        raise ValueError("keep_side must be 'lte' or 'gte'")

    def is_inside(x):
        if keep_side == "lte":
            return x <= x_boundary + 1e-9
        return x >= x_boundary - 1e-9

    current_x = path[0].x + offset_x
    current_z = path[0].z + offset_z
    clipped = []

    if is_inside(current_x):
        clipped.append(StartPoint(current_x, current_z))

    for element in path[1:]:
        end_x = element.end_x + offset_x
        end_z = element.end_z + offset_z
        current_inside = is_inside(current_x)
        end_inside = is_inside(end_x)

        if isinstance(element, ToolpathLine):
            hit = _line_x_intersection(current_x, current_z, end_x, end_z, x_boundary)
            if not clipped:
                if not current_inside and end_inside and hit:
                    clipped.append(StartPoint(*hit))
                    clipped.append(ToolpathLine(end_x, end_z))
            elif end_inside:
                clipped.append(ToolpathLine(end_x, end_z))
            elif hit:
                clipped.append(ToolpathLine(*hit))
                break
        else:
            center_x = element.center_x + offset_x
            center_z = element.center_z + offset_z
            hit = _arc_x_intersection(
                current_x,
                current_z,
                end_x,
                end_z,
                center_x,
                center_z,
                element.anticlockwise,
                x_boundary,
            )
            if not clipped:
                if not current_inside and end_inside and hit:
                    clipped.append(StartPoint(*hit))
                    clipped.append(ToolpathArc(end_x, end_z, center_x, center_z, element.anticlockwise))
            elif end_inside:
                clipped.append(ToolpathArc(end_x, end_z, center_x, center_z, element.anticlockwise))
            elif hit:
                clipped.append(ToolpathArc(hit[0], hit[1], center_x, center_z, element.anticlockwise))
                break

        current_x, current_z = end_x, end_z

    return clipped

def find_45deg_profile_intersection(path, start_x, start_z, dir_x, dir_z, x_shift=0.0, z_shift=0.0):
    """Return the first intersection between a 45-degree ray and the render path."""
    if not path:
        return None

    current_x = path[0].x + x_shift
    current_z = path[0].z + z_shift
    candidates = []

    for element in path[1:]:
        end_x = element.end_x + x_shift
        end_z = element.end_z + z_shift

        if isinstance(element, ToolpathLine):
            seg_dx = end_x - current_x
            seg_dz = end_z - current_z
            denom = dir_x * seg_dz - dir_z * seg_dx
            if abs(denom) > 1e-9:
                rel_x = current_x - start_x
                rel_z = current_z - start_z
                t = (rel_x * seg_dz - rel_z * seg_dx) / denom
                u = (rel_x * dir_z - rel_z * dir_x) / denom
                if t >= -1e-9 and -1e-9 <= u <= 1.0 + 1e-9:
                    hit_x = start_x + t * dir_x
                    hit_z = start_z + t * dir_z
                    candidates.append((max(0.0, t), hit_x, hit_z))
        else:
            cx = element.center_x + x_shift
            cz = element.center_z + z_shift
            # Convert to radius space for correct arc geometry (X is in diameter)
            sx_r = current_x / 2
            ex_r = end_x / 2
            cx_r = cx / 2
            ray_sx_r = start_x / 2
            ray_dx_r = dir_x / 2
            rel_x_r = ray_sx_r - cx_r
            rel_z = start_z - cz
            a = ray_dx_r * ray_dx_r + dir_z * dir_z
            b = 2.0 * (rel_x_r * ray_dx_r + rel_z * dir_z)
            radius = math.hypot(sx_r - cx_r, current_z - cz)
            c = rel_x_r * rel_x_r + rel_z * rel_z - radius * radius
            disc = b * b - 4.0 * a * c
            if disc >= -1e-9:
                disc = max(0.0, disc)
                root = math.sqrt(disc)
                for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                    if t < -1e-9:
                        continue
                    hit_x_r = ray_sx_r + t * ray_dx_r
                    hit_z = start_z + t * dir_z
                    angle = math.atan2(hit_z - cz, hit_x_r - cx_r)
                    start_angle = math.atan2(current_z - cz, sx_r - cx_r)
                    end_angle = math.atan2(end_z - cz, ex_r - cx_r)
                    if _angle_on_arc(angle, start_angle, end_angle, element.anticlockwise):
                        candidates.append((max(0.0, t), hit_x_r * 2, hit_z))

        current_x, current_z = end_x, end_z

    if not candidates:
        return None
    _, hit_x, hit_z = min(candidates, key=lambda item: item[0])
    return hit_x, hit_z


def _offset_line_right(sx, sz, ex, ez, d):
    """Offset line segment by d toward bore center (right of traversal direction)."""
    dx, dz = ex - sx, ez - sz
    length = math.hypot(dx, dz)
    if length < 1e-12:
        return sx, sz, ex, ez
    rx, rz = dz / length, -dx / length
    return sx + d * rx, sz + d * rz, ex + d * rx, ez + d * rz


def _line_line_intersect(s1, s2):
    """Intersection of infinite lines through s1(sx→ex) and s2(sx→ex). Returns (x,z) or None."""
    d1x, d1z = s1['ex'] - s1['sx'], s1['ez'] - s1['sz']
    d2x, d2z = s2['ex'] - s2['sx'], s2['ez'] - s2['sz']
    denom = d1x * d2z - d1z * d2x
    if abs(denom) < 1e-12:
        return None
    t = ((s2['sx'] - s1['sx']) * d2z - (s2['sz'] - s1['sz']) * d2x) / denom
    u = ((s2['sx'] - s1['sx']) * d1z - (s2['sz'] - s1['sz']) * d1x) / denom
    if t < -1e-9 or u < -1e-9:
        return None
    return s1['sx'] + t * d1x, s1['sz'] + t * d1z


def build_equidistant_offset(path, d):
    """Build equidistant offset of boring path by perpendicular distance d toward bore center.

    For each line: shift right (bore center side) by d.
    For each arc:
      - Center on right of chord (CW-like, concave from bore): r' = r - d (can shrink to zero)
      - Center on left of chord (CCW-like, convex from bore): r' = r + d

    When a fillet arc shrinks to zero, the two surrounding offset lines are connected at
    their intersection point instead (sharp corner, no fillet).

    Returns list of ('start', x, z) + ('line', x, z) / ('arc', x, z, cx, cz, anticlockwise).
    """
    if not path or len(path) < 2:
        return []

    segs = []
    cur_x, cur_z = path[0].x, path[0].z

    for elem in path[1:]:
        end_x, end_z = elem.end_x, elem.end_z

        if isinstance(elem, ToolpathLine):
            sx, sz, ex, ez = _offset_line_right(cur_x, cur_z, end_x, end_z, d)
            segs.append({'type': 'line', 'sx': sx, 'sz': sz, 'ex': ex, 'ez': ez})
        else:
            cx, cz = elem.center_x, elem.center_z
            r = math.hypot(cur_x - cx, cur_z - cz)
            cross = (end_x - cur_x) * (cz - cur_z) - (end_z - cur_z) * (cx - cur_x)
            r_prime = (r + d) if cross > 0 else (r - d)

            if r_prime < 1e-9:
                segs.append({'type': 'degen'})
            else:
                a_s = math.atan2(cur_z - cz, cur_x - cx)
                a_e = math.atan2(end_z - cz, end_x - cx)
                segs.append({
                    'type': 'arc',
                    'sx': cx + r_prime * math.cos(a_s), 'sz': cz + r_prime * math.sin(a_s),
                    'ex': cx + r_prime * math.cos(a_e), 'ez': cz + r_prime * math.sin(a_e),
                    'cx': cx, 'cz': cz, 'r': r_prime, 'anticlockwise': elem.anticlockwise,
                })

        cur_x, cur_z = end_x, end_z

    n = len(segs)

    # Pass 1: resolve degenerate arcs → connect surrounding lines at their intersection
    for i in range(n):
        if segs[i]['type'] != 'degen':
            continue
        pi, ni = i - 1, i + 1
        while pi >= 0 and segs[pi]['type'] == 'degen':
            pi -= 1
        while ni < n and segs[ni]['type'] == 'degen':
            ni += 1
        if 0 <= pi < n and ni < n and segs[pi]['type'] == 'line' and segs[ni]['type'] == 'line':
            pt = _line_line_intersect(segs[pi], segs[ni])
            if pt:
                segs[pi]['ex'], segs[pi]['ez'] = pt
                segs[ni]['sx'], segs[ni]['sz'] = pt

    # Pass 2: fix line-line corners that aren't already aligned
    for i in range(n - 1):
        if segs[i]['type'] == 'line' and segs[i + 1]['type'] == 'line':
            if abs(segs[i]['ex'] - segs[i + 1]['sx']) > 1e-6 or abs(segs[i]['ez'] - segs[i + 1]['sz']) > 1e-6:
                pt = _line_line_intersect(segs[i], segs[i + 1])
                if pt:
                    segs[i]['ex'], segs[i]['ez'] = pt
                    segs[i + 1]['sx'], segs[i + 1]['sz'] = pt

    result = []
    for seg in segs:
        if seg['type'] == 'degen':
            continue
        if not result:
            result.append(('start', seg['sx'], seg['sz']))
        if seg['type'] == 'line':
            result.append(('line', seg['ex'], seg['ez']))
        else:
            result.append(('arc', seg['ex'], seg['ez'], seg['cx'], seg['cz'], seg['anticlockwise']))
    return result
