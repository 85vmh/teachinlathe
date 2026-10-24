import math

from shapely.affinity import translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import linemerge, unary_union
from shapely.prepared import prep

from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float
from .profiling.geometry import (
    StartPoint,
    ToolpathArc,
    ToolpathLine,
    build_profile_segments,
    build_render_path,
)
from .profiling.plan_drawing import _arc_points
from .profiling.shapes import minkowski, path_points
from .profiling.toolpath import emit_toolpath

# ── Tolerances ───────────────────────────────────────────────────────────────

#: mm: two positions or lengths this close are the same one - a tenth of the
#: 0.001 mm the G-code is written to, so nothing the machine is sent differs.
SAME_MM = 0.0001

#: What floating-point rounding leaves over in a computed value - an angle,
#: a distance - that is exactly at a limit: compared with this much slack.
ROUNDING = 1e-9

# ── Checking the blade against the part (_Blade, _clear_part_of) ─────────────

#: mm the part is shrunk by before the blade is checked against it. The
#: profile's arcs are drawn as chords, which bulge into a concave fillet; a
#: blade following the fillet exactly would otherwise touch them.
CONTACT_MARGIN = 0.005

#: mm a contour cut short at the part backs off by: past CONTACT_MARGIN, so
#: the blade stops clear of the real flank, not in the margin.
BACK_OFF = CONTACT_MARGIN + 0.001

#: mm^2 of overlap still taken as no contact: rounding of the polygons only.
CONTACT_AREA = 1e-6

#: Segments a corner radius of the blade is drawn with, for the check.
CORNER_SEGMENTS = 16

#: Points a stretch of contour is checked at before the contact is narrowed
#: down, and how many halvings narrow it - to 2**-20 of the step.
CHECK_STEPS = 8
NARROWING_STEPS = 20

# ── Geometry ─────────────────────────────────────────────────────────────────

#: Chords a fillet on a groove's corner is drawn with in its profile.
FILLET_CHORDS = 10

#: mm the bar is carried on past the groove's ends, either side, for the
#: part's outline - more for more stock, so it still reaches past it.
BAR_PAST_GROOVE = 10.0

#: mm above the pulley's outside, with its stock, the stock-to-leave line is
#: taken up to: past the top of it, so the line keeps its ends.
OVER_THE_OUTSIDE = 1.0

#: mm the depth a plunge may go to is carried on along the outside past the
#: groove (_depth_path): farther than any blade reaches out of it.
OUTSIDE_REACH = 1000.0


def _on_diameter(radial):
    """A distance along X, such as the clearance - given on the radius, as
    the canvas dimensions it - on the diameter the G-code's X is."""
    return 2.0 * abs(radial)


def _outward(profile_type):
    """Which way out of the groove is along X: +1 for an OD one, -1 for ID."""
    return -1.0 if str(profile_type).lower() == "id" else 1.0


def _top_x(path, profile_type):
    """The pulley's outside, the groove's mouth: the largest diameter of its
    profile ``path``, the smallest for ID."""
    x_min, x_max, _z_min, _z_max = _profile_bounds_from_path(path)
    return x_min if str(profile_type).lower() == "id" else x_max


def _start_x(path, profile_type, stock_radial):
    """The start diameter: the pulley's outside with ``stock_radial`` - the
    radial stock to leave, or the one left - on it."""
    return _top_x(path, profile_type) + _outward(profile_type) * _on_diameter(stock_radial)


def _blade_start_x(start_x, profile_type, clearance):
    """Where the blade starts, and backs off to: ``clearance`` out from the
    start diameter ``start_x``."""
    return start_x + _outward(profile_type) * _on_diameter(clearance)


def _groove_path(profile):
    """The profile of the first groove of the radial ``profile``, as the
    G-code goes along it - from its Z+ end to its Z- one - or None."""
    groove = _first_groove(profile)
    if not groove:
        return None
    segments = build_profile_segments(_radial_profile_primitives(groove))
    path = build_render_path(segments, profile_type=str(profile.get("profile_type", "od")).lower())
    if not path or not isinstance(path[0], StartPoint):
        return None
    return path


def _fmt(value):
    return f"{float(value):.3f}"


def _code(prefix, words):
    return f"{prefix}{words}" if prefix else words


def _first_groove(profile):
    for primitive in (profile.get("profile_primitives", []) or []):
        if isinstance(primitive, dict) and primitive.get("type") == "groove":
            return primitive
    return None


def _blend(blend):
    blend = blend or {}
    blend_type = str(blend.get("type", "none") or "none").lower()
    if blend_type == "radius":
        blend_type = "fillet"
    return {
        "type": blend_type,
        "chamfer_width": get_float(blend, "chamfer_width", 0.0),
        "fillet_radius": get_float(blend, "fillet_radius", 0.0),
    }


def _point(z, xh):
    return {"z": z, "x": xh * 2.0, "xh": xh}


def _unit_from(corner, point):
    dz = point["z"] - corner["z"]
    dx = point["xh"] - corner["xh"]
    length = math.hypot(dz, dx)
    if length < SAME_MM:
        return None
    return {"z": dz / length, "xh": dx / length, "len": length}


def _corner_blend(corner_d, leg_a_end_d, leg_b_end_d, blend):
    b = _blend(blend)
    corner = _point(corner_d["z"], corner_d["x"] / 2.0)
    leg_a_end = _point(leg_a_end_d["z"], leg_a_end_d["x"] / 2.0)
    leg_b_end = _point(leg_b_end_d["z"], leg_b_end_d["x"] / 2.0)
    ua = _unit_from(corner, leg_a_end)
    ub = _unit_from(corner, leg_b_end)
    if not ua or not ub or b["type"] == "none":
        return {"start": corner_d, "end": corner_d, "arc": []}

    amount = b["fillet_radius"] if b["type"] == "fillet" else b["chamfer_width"]
    if amount <= SAME_MM:
        return {"start": corner_d, "end": corner_d, "arc": []}

    dot = max(-0.9999, min(0.9999, ua["z"] * ub["z"] + ua["xh"] * ub["xh"]))
    theta = math.acos(dot)
    if theta < 0.001:
        return {"start": corner_d, "end": corner_d, "arc": []}

    tangent_distance = amount / math.tan(theta / 2.0) if b["type"] == "fillet" else amount
    tangent_distance = min(tangent_distance, ua["len"], ub["len"])
    t1 = _point(corner["z"] + ua["z"] * tangent_distance, corner["xh"] + ua["xh"] * tangent_distance)
    t2 = _point(corner["z"] + ub["z"] * tangent_distance, corner["xh"] + ub["xh"] * tangent_distance)

    if b["type"] != "fillet":
        return {"start": t1, "end": t2, "arc": []}

    bis_z = ua["z"] + ub["z"]
    bis_x = ua["xh"] + ub["xh"]
    bis_len = math.hypot(bis_z, bis_x)
    if bis_len < SAME_MM:
        return {"start": t1, "end": t2, "arc": []}

    center_distance = amount / math.sin(theta / 2.0)
    center = _point(
        corner["z"] + bis_z / bis_len * center_distance,
        corner["xh"] + bis_x / bis_len * center_distance,
    )
    start_angle = math.atan2(t1["xh"] - center["xh"], t1["z"] - center["z"])
    end_angle = math.atan2(t2["xh"] - center["xh"], t2["z"] - center["z"])
    delta = end_angle - start_angle
    while delta > math.pi:
        delta -= math.pi * 2.0
    while delta < -math.pi:
        delta += math.pi * 2.0

    arc = []
    for index in range(1, FILLET_CHORDS + 1):
        angle = start_angle + delta * index / float(FILLET_CHORDS)
        arc.append(_point(center["z"] + math.cos(angle) * amount, center["xh"] + math.sin(angle) * amount))
    return {"start": t1, "end": t2, "arc": arc}


def _same_point(a, b):
    return abs(a["z"] - b["z"]) < SAME_MM and abs(a["x"] - b["x"]) < SAME_MM


def _append_line_primitive(out, primitive_id, point, blend=None):
    if out:
        last = out[-1]
        if last["type"] == "startPoint":
            last_point = {"z": get_float(last, "z_start", 0.0), "x": get_float(last, "x_start", 0.0)}
        else:
            last_point = {"z": get_float(last, "z_end", 0.0), "x": get_float(last, "x_end", 0.0)}
        if _same_point(last_point, point) and (not blend or _blend(blend)["type"] == "none"):
            return primitive_id
    out.append({
        "primitive_id": primitive_id,
        "type": "lineTo",
        "input": "xz",
        "x_end": point["x"],
        "z_end": point["z"],
        "blend": blend or _blend(None),
    })
    return primitive_id + 1


def _groove_corner_points(groove):
    right = groove.get("right_flank", {}) or {}
    bottom = groove.get("bottom", {}) or {}
    left = groove.get("left_flank", {}) or {}

    rx0 = get_float(right, "x_start", 0.0)
    rz0 = get_float(right, "z_start", 0.0)
    lx0 = get_float(left, "x_start", 0.0)
    lz0 = get_float(left, "z_start", 0.0)
    rxe = get_float(bottom, "x_end_right", 0.0)
    lxe = get_float(bottom, "x_end_left", 0.0)
    ra = abs(get_float(right, "angle", 0.0)) * math.pi / 180.0
    la = abs(get_float(left, "angle", 0.0)) * math.pi / 180.0
    rdz = abs((rx0 - rxe) / 2.0 * math.tan(ra))
    ldz = abs((lx0 - lxe) / 2.0 * math.tan(la))

    return {
        "right_top": {"x": rx0, "z": rz0},
        "right_bottom": {"x": rxe, "z": rz0 - rdz},
        "left_bottom": {"x": lxe, "z": lz0 + ldz},
        "left_top": {"x": lx0, "z": lz0},
    }


def _radial_profile_primitives(groove):
    points = _groove_corner_points(groove)
    right = groove.get("right_flank", {}) or {}
    left = groove.get("left_flank", {}) or {}
    bottom = groove.get("bottom", {}) or {}
    imaginary_span = 10000.0

    right_blend = _corner_blend(
        points["right_top"],
        {"z": points["right_top"]["z"] + imaginary_span, "x": points["right_top"]["x"]},
        points["right_bottom"],
        right.get("start_blend"),
    )
    left_blend = _corner_blend(
        points["left_top"],
        points["left_bottom"],
        {"z": points["left_top"]["z"] - imaginary_span, "x": points["left_top"]["x"]},
        left.get("start_blend"),
    )

    out = []
    primitive_id = 1
    out.append({
        "primitive_id": primitive_id,
        "type": "startPoint",
        "x_start": right_blend["start"]["x"],
        "z_start": right_blend["start"]["z"],
        "blend": _blend(None),
    })
    primitive_id += 1
    if right_blend["arc"]:
        for point in right_blend["arc"]:
            primitive_id = _append_line_primitive(out, primitive_id, point, _blend(None))
    else:
        primitive_id = _append_line_primitive(out, primitive_id, right_blend["end"], _blend(None))
    primitive_id = _append_line_primitive(out, primitive_id, points["right_bottom"], _blend(bottom.get("blend_right")))
    primitive_id = _append_line_primitive(out, primitive_id, points["left_bottom"], _blend(bottom.get("blend_left")))
    primitive_id = _append_line_primitive(out, primitive_id, left_blend["start"], _blend(None))
    if left_blend["arc"]:
        for point in left_blend["arc"]:
            primitive_id = _append_line_primitive(out, primitive_id, point, _blend(None))
    else:
        _append_line_primitive(out, primitive_id, left_blend["end"], _blend(None))
    return out


def _profile_bounds_from_path(path):
    xs = []
    zs = []
    for element in path:
        if isinstance(element, StartPoint):
            xs.append(element.x)
            zs.append(element.z)
        else:
            xs.append(element.end_x)
            zs.append(element.end_z)
    return min(xs), max(xs), min(zs), max(zs)


def _x_bounds_from_path(path):
    xs = []
    for element in path or []:
        if isinstance(element, StartPoint):
            xs.append(element.x)
        else:
            xs.append(element.end_x)
    if not xs:
        return 0.0, 0.0
    return min(xs), max(xs)


def _arc_z_intersections_x(sx, sz, ex, ez, cx, cz, anticlockwise, target_z):
    sx_r, ex_r, cx_r = sx / 2.0, ex / 2.0, cx / 2.0
    radius = math.hypot(sx_r - cx_r, sz - cz)
    dz = target_z - cz
    if abs(dz) > radius + ROUNDING:
        return []
    disc = max(0.0, radius * radius - dz * dz)
    start_angle = math.atan2(sz - cz, sx_r - cx_r)
    end_angle = math.atan2(ez - cz, ex_r - cx_r)
    results = []
    for x_r_candidate in (cx_r + math.sqrt(disc), cx_r - math.sqrt(disc)):
        angle = math.atan2(dz, x_r_candidate - cx_r)
        if _angle_on_arc(angle, start_angle, end_angle, anticlockwise):
            results.append(x_r_candidate * 2.0)
    return results


def _normalize_angle(angle):
    two_pi = math.pi * 2.0
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
            end_angle += math.pi * 2.0
        if angle < start_angle:
            angle += math.pi * 2.0
        return start_angle - ROUNDING <= angle <= end_angle + ROUNDING
    if start_angle < end_angle:
        start_angle += math.pi * 2.0
    if angle > start_angle:
        angle -= math.pi * 2.0
    return end_angle - ROUNDING <= angle <= start_angle + ROUNDING


def _profile_x_at_z(path, target_z, profile_type, x_shift=0.0):
    if not path:
        return None
    current_x = path[0].x + x_shift
    current_z = path[0].z
    candidates = []
    for element in path[1:]:
        end_x = element.end_x + x_shift
        end_z = element.end_z
        z_lo = min(current_z, end_z)
        z_hi = max(current_z, end_z)
        if isinstance(element, ToolpathLine):
            if abs(end_z - current_z) > ROUNDING:
                if z_lo - ROUNDING <= target_z <= z_hi + ROUNDING:
                    candidates.append(current_x + (target_z - current_z) * (end_x - current_x) / (end_z - current_z))
            elif abs(target_z - current_z) < SAME_MM:
                candidates.extend([current_x, end_x])
        elif isinstance(element, ToolpathArc):
            candidates.extend(_arc_z_intersections_x(
                current_x,
                current_z,
                end_x,
                end_z,
                element.center_x + x_shift,
                element.center_z,
                element.anticlockwise,
                target_z,
            ))
        current_x = end_x
        current_z = end_z
    if not candidates:
        return None
    return max(candidates) if str(profile_type).lower() == "id" else min(candidates)


def _profile_x_for_blade(path, center_z, half_width, profile_type, x_shift=0.0):
    samples = []
    sample_count = 9
    for index in range(sample_count):
        ratio = index / float(sample_count - 1)
        z_pos = center_z - half_width + ratio * half_width * 2.0
        x_pos = _profile_x_at_z(path, z_pos, profile_type, x_shift)
        if x_pos is not None:
            samples.append(x_pos)
    if not samples:
        return None
    return min(samples) if str(profile_type).lower() == "id" else max(samples)


def _translate_path(path, x_shift, z_shift):
    """``path`` moved by ``x_shift`` (on the diameter) and ``z_shift``."""
    shifted = []
    for element in path:
        if isinstance(element, StartPoint):
            shifted.append(StartPoint(element.x + x_shift, element.z + z_shift))
        elif isinstance(element, ToolpathLine):
            shifted.append(ToolpathLine(element.end_x + x_shift, element.end_z + z_shift))
        elif isinstance(element, ToolpathArc):
            shifted.append(ToolpathArc(
                element.end_x + x_shift,
                element.end_z + z_shift,
                element.center_x + x_shift,
                element.center_z + z_shift,
                element.anticlockwise,
            ))
    return shifted


_CONTROL_NAMES = {-1: "left corner", 0: "middle", 1: "right corner"}


def _blade_control(tool):
    """Which point of the blade it was touched off on, so the G-code is
    written for: -1 its left corner, 0 the middle of its end, 1 its right
    corner."""
    control = int(get_float(tool or {}, "control", 0.0))
    return control if control in (-1, 0, 1) else 0


def _corner_to_control(path, corner, radius, half_width, control, profile_type):
    """``path``, the one the centre of the blade's ``corner`` radius
    ("right": its Z+ side, "left": its Z- side) follows, as the point it was
    touched off on (``control``) follows it then: along Z from that corner's
    centre to the touch-off point, along X from the centre to the blade's
    end - inward for OD, outward for ID."""
    side = 1.0 if corner == "right" else -1.0
    z_shift = control * half_width - side * (half_width - radius)
    x_shift = -_outward(profile_type) * _on_diameter(radius)
    return _translate_path(path, x_shift, z_shift)


def _path_end_point(path):
    if not path:
        return None
    last = path[-1]
    if isinstance(last, StartPoint):
        return last.x, last.z
    return last.end_x, last.end_z


def _reverse_path(path):
    if not path:
        return []

    end_point = _path_end_point(path)
    if end_point is None:
        return []

    reversed_path = [StartPoint(end_point[0], end_point[1])]
    current_x = path[0].x
    current_z = path[0].z
    segments = []
    for element in path[1:]:
        segments.append((current_x, current_z, element))
        current_x = element.end_x
        current_z = element.end_z

    for start_x, start_z, element in reversed(segments):
        if isinstance(element, ToolpathLine):
            reversed_path.append(ToolpathLine(start_x, start_z))
        elif isinstance(element, ToolpathArc):
            reversed_path.append(ToolpathArc(
                start_x,
                start_z,
                element.center_x,
                element.center_z,
                not element.anticlockwise,
            ))
    return reversed_path


def _line_point_at_z(start_x, start_z, end_x, end_z, target_z):
    if abs(end_z - start_z) <= ROUNDING:
        return end_x, target_z
    ratio = (target_z - start_z) / (end_z - start_z)
    return start_x + ratio * (end_x - start_x), target_z


def _arc_point_at_z(start_x, start_z, element, target_z):
    xs = _arc_z_intersections_x(
        start_x,
        start_z,
        element.end_x,
        element.end_z,
        element.center_x,
        element.center_z,
        element.anticlockwise,
        target_z,
    )
    if not xs:
        return None
    x = min(xs, key=lambda candidate: abs(candidate - start_x))
    return x, target_z


def _split_path_at_z(path, target_z):
    if not path or not isinstance(path[0], StartPoint):
        return [], []

    first = [StartPoint(path[0].x, path[0].z)]
    current_x = path[0].x
    current_z = path[0].z

    for index, element in enumerate(path[1:], start=1):
        end_x = element.end_x
        end_z = element.end_z
        crosses = min(current_z, end_z) - ROUNDING <= target_z <= max(current_z, end_z) + ROUNDING

        if crosses:
            if isinstance(element, ToolpathLine):
                split_x, split_z = _line_point_at_z(current_x, current_z, end_x, end_z, target_z)
                first.append(ToolpathLine(split_x, split_z))
            elif isinstance(element, ToolpathArc):
                hit = _arc_point_at_z(current_x, current_z, element, target_z)
                if not hit:
                    first.append(element)
                    current_x = end_x
                    current_z = end_z
                    continue
                split_x, split_z = hit
                first.append(ToolpathArc(
                    split_x,
                    split_z,
                    element.center_x,
                    element.center_z,
                    element.anticlockwise,
                ))
            else:
                first.append(element)
                split_x, split_z = end_x, end_z

            second = [StartPoint(split_x, split_z)]
            if isinstance(element, ToolpathLine):
                if abs(split_x - end_x) > SAME_MM or abs(split_z - end_z) > SAME_MM:
                    second.append(ToolpathLine(end_x, end_z))
            elif isinstance(element, ToolpathArc):
                if abs(split_x - end_x) > SAME_MM or abs(split_z - end_z) > SAME_MM:
                    second.append(ToolpathArc(
                        end_x,
                        end_z,
                        element.center_x,
                        element.center_z,
                        element.anticlockwise,
                    ))
            second.extend(path[index + 1:])
            return first, second

        first.append(element)
        current_x = end_x
        current_z = end_z

    return first, []


def _offset_line_segment_radius_space(sx, sz, ex, ez, radius, side):
    dx = ex - sx
    dz = ez - sz
    length = math.hypot(dx, dz)
    if length < 1e-12:
        return sx, sz, ex, ez
    if side == "left":
        nx = -dz / length
        nz = dx / length
    else:
        nx = dz / length
        nz = -dx / length
    return sx + nx * radius, sz + nz * radius, ex + nx * radius, ez + nz * radius


def _offset_arc_segment_radius_space(sx, sz, element, radius, side):
    cx = element.center_x / 2.0
    cz = element.center_z
    start_radius = math.hypot(sx - cx, sz - cz)
    if start_radius < 1e-12:
        return None

    left_side_is_inward = bool(element.anticlockwise)
    if (side == "left" and left_side_is_inward) or (side == "right" and not left_side_is_inward):
        offset_radius = start_radius - radius
    else:
        offset_radius = start_radius + radius
    if offset_radius <= ROUNDING:
        return None

    end_x = element.end_x / 2.0
    end_z = element.end_z
    start_angle = math.atan2(sz - cz, sx - cx)
    end_angle = math.atan2(end_z - cz, end_x - cx)
    return {
        "type": "arc",
        "sx": cx + math.cos(start_angle) * offset_radius,
        "sz": cz + math.sin(start_angle) * offset_radius,
        "ex": cx + math.cos(end_angle) * offset_radius,
        "ez": cz + math.sin(end_angle) * offset_radius,
        "cx": cx,
        "cz": cz,
        "anticlockwise": element.anticlockwise,
    }


def _line_line_intersection(seg_a, seg_b):
    d1x = seg_a["ex"] - seg_a["sx"]
    d1z = seg_a["ez"] - seg_a["sz"]
    d2x = seg_b["ex"] - seg_b["sx"]
    d2z = seg_b["ez"] - seg_b["sz"]
    denom = d1x * d2z - d1z * d2x
    if abs(denom) < 1e-12:
        return None
    t = ((seg_b["sx"] - seg_a["sx"]) * d2z - (seg_b["sz"] - seg_a["sz"]) * d2x) / denom
    return seg_a["sx"] + t * d1x, seg_a["sz"] + t * d1z


def _offset_path_for_tool_radius(path, radius, side):
    radius = abs(float(radius or 0.0))
    if radius <= SAME_MM or not path or not isinstance(path[0], StartPoint):
        return path

    segments = []
    current_x = path[0].x / 2.0
    current_z = path[0].z
    for element in path[1:]:
        end_x = element.end_x / 2.0
        end_z = element.end_z
        if isinstance(element, ToolpathLine):
            sx, sz, ex, ez = _offset_line_segment_radius_space(current_x, current_z, end_x, end_z, radius, side)
            segments.append({"type": "line", "sx": sx, "sz": sz, "ex": ex, "ez": ez})
        elif isinstance(element, ToolpathArc):
            arc = _offset_arc_segment_radius_space(current_x, current_z, element, radius, side)
            if arc:
                segments.append(arc)
        current_x = end_x
        current_z = end_z

    for index in range(len(segments) - 1):
        current = segments[index]
        next_seg = segments[index + 1]
        if current["type"] == "line" and next_seg["type"] == "line":
            hit = _line_line_intersection(current, next_seg)
            if hit:
                current["ex"], current["ez"] = hit
                next_seg["sx"], next_seg["sz"] = hit
        else:
            current["ex"], current["ez"] = next_seg["sx"], next_seg["sz"]

    out = []
    for segment in segments:
        if not out:
            out.append(StartPoint(segment["sx"] * 2.0, segment["sz"]))
        if segment["type"] == "line":
            out.append(ToolpathLine(segment["ex"] * 2.0, segment["ez"]))
        else:
            out.append(ToolpathArc(
                segment["ex"] * 2.0,
                segment["ez"],
                segment["cx"] * 2.0,
                segment["cz"],
                segment["anticlockwise"],
            ))
    return out


def _tool_is_blade(tool):
    tool_type = str((tool or {}).get("tool_type", "")).lower()
    orientation = int((tool or {}).get("q", 0) or 0)
    return tool_type in ("parting_blade", "grooving_blade") or orientation in (6, 8)


def _blade_width(tool):
    width = get_float(tool or {}, "width", 0.0)
    if width <= 0:
        width = get_float(tool or {}, "d", 0.0)
    return width


def _append_peck(lines, prefix, z_pos, safe_x, final_x, peck_depth, clearance, feed_rate, dwell_time):
    if peck_depth <= 0:
        peck_depth = abs(safe_x - final_x)
    direction = -1 if final_x < safe_x else 1
    outside = -direction
    current_x = safe_x

    lines.append(_code(prefix, f"G0 X{_fmt(safe_x)}"))
    lines.append(_code(prefix, f"G0 Z{_fmt(z_pos)}"))
    while True:
        remaining = abs(final_x - current_x)
        if remaining <= SAME_MM:
            break
        next_x = current_x + direction * min(abs(peck_depth), remaining)
        lines.append(_code(prefix, f"G1 X{_fmt(next_x)} F{_fmt(feed_rate)}"))
        if dwell_time > 0:
            lines.append(_code(prefix, f"G4 P{_fmt(dwell_time)}"))
        current_x = next_x
        if abs(final_x - current_x) <= SAME_MM:
            break
        retract_x = current_x + outside * _on_diameter(clearance)
        lines.append(_code(prefix, f"G0 X{_fmt(retract_x)}"))
        lines.append(_code(prefix, f"G0 X{_fmt(current_x)}"))
    lines.append(_code(prefix, f"G0 X{_fmt(safe_x)}"))


def _next_depth(current_x, final_x, peck_depth):
    if peck_depth <= 0:
        return final_x
    direction = -1 if final_x < current_x else 1
    next_x = current_x + direction * abs(peck_depth)
    if direction < 0:
        return max(next_x, final_x)
    return min(next_x, final_x)


def _next_center_depth(current_x, final_x, peck_depth):
    return _next_depth(current_x, final_x, abs(peck_depth) * 2.0)


def _is_at_depth(current_x, final_x):
    if final_x < current_x:
        return current_x <= final_x + SAME_MM
    return current_x >= final_x - SAME_MM


def _append_incremental_cut(
    lines,
    prefix,
    z_pos,
    current_x,
    target_x,
    clearance,
    feed_rate,
    dwell_time,
    retract_reference_x=None,
):
    if abs(target_x - current_x) <= SAME_MM:
        return
    # out of the cut is back the way it came in, from wherever it goes to
    outward = 1.0 if current_x > target_x else -1.0
    approach_x = current_x + outward * _on_diameter(clearance)
    lines.append(_code(prefix, f"G0 X{_fmt(approach_x)}"))
    lines.append(_code(prefix, f"G0 Z{_fmt(z_pos)}"))
    lines.append(_code(prefix, f"G1 X{_fmt(target_x)} F{_fmt(feed_rate)}"))
    if dwell_time > 0:
        lines.append(_code(prefix, f"G4 P{_fmt(dwell_time)}"))
    # backed off to clear the other plunge too, so the move over to it is
    # in the air: out past the shallower of the two - never deeper than
    # this cut, whatever depth the other is at
    if retract_reference_x is None:
        retract_reference_x = target_x
    shallower = max(retract_reference_x, target_x) if outward > 0 else min(retract_reference_x, target_x)
    retract_x = shallower + outward * _on_diameter(clearance)
    lines.append(_code(prefix, f"G0 X{_fmt(retract_x)}"))


def _append_center_pair_roughing(
    lines,
    prefix,
    first_z,
    first_final_x,
    second_z,
    second_final_x,
    top_x,
    peck_depth,
    clearance,
    feed_rate,
    dwell_time,
):
    first_depth = top_x
    second_depth = top_x

    first_target = _next_depth(first_depth, first_final_x, peck_depth)
    _append_incremental_cut(
        lines,
        prefix,
        first_z,
        first_depth,
        first_target,
        clearance,
        feed_rate,
        dwell_time,
        retract_reference_x=second_depth,
    )
    first_depth = first_target

    while not (_is_at_depth(first_depth, first_final_x) and _is_at_depth(second_depth, second_final_x)):
        if not _is_at_depth(second_depth, second_final_x):
            next_depth = _next_center_depth(second_depth, second_final_x, peck_depth)
            _append_incremental_cut(
                lines,
                prefix,
                second_z,
                second_depth,
                next_depth,
                clearance,
                feed_rate,
                dwell_time,
                retract_reference_x=first_depth,
            )
            second_depth = next_depth

        if not _is_at_depth(first_depth, first_final_x):
            next_depth = _next_center_depth(first_depth, first_final_x, peck_depth)
            _append_incremental_cut(
                lines,
                prefix,
                first_z,
                first_depth,
                next_depth,
                clearance,
                feed_rate,
                dwell_time,
                retract_reference_x=second_depth,
            )
            first_depth = next_depth


def _append_unique_position(positions, value, z_min, z_max):
    if value < z_min - SAME_MM or value > z_max + SAME_MM:
        return
    if not any(abs(existing - value) < SAME_MM for existing in positions):
        positions.append(value)


def _center_positions(center, left_limit, right_limit, initial_offset, afterwards_offset):
    positions = []
    if initial_offset > 0:
        right_seed = center + initial_offset / 2.0
        left_seed = center - initial_offset / 2.0
        _append_unique_position(positions, right_seed, left_limit, right_limit)
        _append_unique_position(positions, left_seed, left_limit, right_limit)
    else:
        right_seed = center
        left_seed = center
        _append_unique_position(positions, center, left_limit, right_limit)

    if afterwards_offset <= 0:
        afterwards_offset = initial_offset if initial_offset > 0 else 1.0

    z = right_seed + afterwards_offset
    while z <= right_limit + SAME_MM:
        _append_unique_position(positions, z, left_limit, right_limit)
        z += afterwards_offset

    z = left_seed - afterwards_offset
    while z >= left_limit - SAME_MM:
        _append_unique_position(positions, z, left_limit, right_limit)
        z -= afterwards_offset

    return positions


#: The comment put over a contour cut with one of the blade's corners, which
#: the backplot reads to draw it along that corner (backplot.blade_middle).
CORNER_COMMENT = "( blade {} corner on the contour )"


def corner_comment(corner):
    """The comment over a contour cut with the blade's ``corner``: "right"
    or "left"."""
    return CORNER_COMMENT.format(corner)


def _emit_contour_section(lines, prefix, safe_x, path, corner=None):
    if not path or not isinstance(path[0], StartPoint):
        return

    if corner:
        lines.append(_code(prefix, corner_comment(corner)))
    start = path[0]
    lines.append(_code(prefix, f"G0 X{_fmt(safe_x)}"))
    lines.append(_code(prefix, f"G0 Z{_fmt(start.z)}"))
    lines.append(_code(prefix, f"G1 X{_fmt(start.x)} Z{_fmt(start.z)}"))
    emit_toolpath(lines, prefix, path)
    lines.append(_code(prefix, f"G0 X{_fmt(safe_x)}"))


def _safe_x_for_contour(path, safe_x, clearance, profile_type):
    x_min, x_max = _x_bounds_from_path(path)
    if str(profile_type).lower() == "id":
        return min(safe_x, x_min - _on_diameter(clearance))
    return max(safe_x, x_max + _on_diameter(clearance))


def _part_with_stock(path, profile_type, radial, axial):
    """The part under the groove's profile ``path``, the bar carried on past
    it either side, grown by the stock to leave - ``radial`` off the bottom,
    ``axial`` off the flanks - as a shapely Polygon in (z, r), r turned over
    for ID so the part is under it either way; with ``points``, the profile's
    (z, r) from its right end to its left, in the same frame."""
    sign = _outward(profile_type)
    points = [(z, sign * r) for z, r in path_points(path)]
    if points[0][0] < points[-1][0]:
        points.reverse()                        # from the right end to the left
    (z_right, r_right), (z_left, r_left) = points[0], points[-1]
    far = BAR_PAST_GROOVE + 2 * (radial + axial)
    floor = min(r for _z, r in points) - far
    part = Polygon([(z_right + far, r_right)] + points + [(z_left - far, r_left), (z_left - far, floor),
                                                          (z_right + far, floor)]).buffer(0)
    if radial > 0 or axial > 0:
        part = minkowski(part, [(-axial, -radial), (axial, -radial), (axial, radial), (-axial, radial)])
    return part, points


def _stock_allowance(path, profile_type, radial, axial):
    """The groove's profile ``path`` offset by the stock to leave - ``radial``
    off its bottom, ``axial`` off its flanks, as the stock it is left with is
    the part grown by both - as [(z, x)] (X a diameter) from its right end
    to its left, between the profile's ends, out to the pulley's outside
    with its stock; [] with none to leave."""
    if radial <= 0 and axial <= 0:
        return []
    sign = _outward(profile_type)
    allowance, points = _part_with_stock(path, profile_type, radial, axial)
    (z_right, r_right), (z_left, r_left) = points[0], points[-1]
    floor = min(r for _z, r in points) - BAR_PAST_GROOVE - 2 * (radial + axial)
    # its edge between the profile's ends, up to the outside with its stock
    outside = max(r_right, r_left) + radial + OVER_THE_OUTSIDE
    inside = allowance.exterior.intersection(box(z_left, floor, z_right, outside))
    pieces = [g for g in getattr(inside, "geoms", [inside]) if isinstance(g, LineString) and not g.is_empty]
    if not pieces:
        return []
    line = linemerge(pieces) if len(pieces) > 1 else pieces[0]
    if not isinstance(line, LineString):
        line = max(line.geoms, key=lambda g: g.length)
    coords = list(line.coords)
    if coords[0][0] < coords[-1][0]:
        coords.reverse()
    return [(z, 2 * sign * r) for z, r in coords]


class _Blade:
    """The blade as it stands at a point of the G-code, to be checked
    against the part: its end ``half`` either side of its middle - ``control``
    half-widths off the point along Z, the one it was touched off on - its
    corners rounded, its body going on out of the groove."""

    #: How far the body is drawn out from its end, mm: past any groove, so a
    #: body that would rub a flank on its way down is caught as well.
    BODY = 100.0

    def __init__(self, half, left_radius, right_radius, control, profile_type):
        self.half = half
        self.left = min(max(left_radius, 0.0), half)
        self.right = min(max(right_radius, 0.0), half)
        self.control = control
        self.sign = _outward(profile_type)
        # its shape with its end's middle at (0, 0), built once and moved to
        # each point checked: a contour is checked at hundreds of them
        half, left, right = self.half, self.left, self.right
        # each half of its end rounded by its own corner's radius
        shapes = [box(-half + left, 0.0, half - right, self.BODY),
                  box(-half, left, 0.0, self.BODY),
                  box(0.0, right, half, self.BODY)]
        if left > 0:
            shapes.append(Point(-half + left, left).buffer(left, CORNER_SEGMENTS))
        if right > 0:
            shapes.append(Point(half - right, right).buffer(right, CORNER_SEGMENTS))
        self._shape = unary_union(shapes)
        self._part = self._prepared = None

    def at(self, x, z):
        """Its shape with the G-code at (x, z), in the part's frame."""
        return translate(self._shape, z - self.control * self.half, self.sign * x / 2.0)

    def clear_of(self, part, x, z):
        if part is not self._part:
            # the part prepared once, for the quick test of whether the
            # blade is anywhere near it
            self._part, self._prepared = part, prep(part)
        shape = self.at(x, z)
        return not self._prepared.intersects(shape) or shape.intersection(part).area < CONTACT_AREA


def _clear_part_of(section, blade, part, steps=CHECK_STEPS):
    """``section`` - a contour, as the G-code goes along it - as far as the
    blade, there, stays out of ``part``: cut short where it would go in -
    where a blade wider than half the groove, running its corner along the
    bottom to the middle, would put its other side into the far flank."""
    if not section or not isinstance(section[0], StartPoint) or blade is None or part is None:
        return section
    kept = [section[0]]
    x, z = section[0].x, section[0].z
    if not blade.clear_of(part, x, z):
        return []
    for element in section[1:]:
        end = (element.end_x, element.end_z)
        along = (_arc_points(x, z, element) if isinstance(element, ToolpathArc) else []) + [end]
        # steps along it, each a straight stretch: the last point clear of it
        points = []
        px, pz = x, z
        for qx, qz in along:
            points.extend((px + (qx - px) * k / steps, pz + (qz - pz) * k / steps) for k in range(1, steps + 1))
            px, pz = qx, qz
        last = (x, z)
        for qx, qz in points:
            if not blade.clear_of(part, qx, qz):
                # between the last clear point and this one, closer
                lo, hi = 0.0, 1.0
                for _ in range(NARROWING_STEPS):
                    mid = (lo + hi) / 2
                    if blade.clear_of(part, last[0] + (qx - last[0]) * mid, last[1] + (qz - last[1]) * mid):
                        lo = mid
                    else:
                        hi = mid
                # and back off by BACK_OFF along it - X is a diameter, so
                # halved for the distance - clear of the flank, not in the
                # CONTACT_MARGIN the part was shrunk by
                length = math.hypot((qx - last[0]) / 2.0, qz - last[1])
                lo = max(0.0, lo - (BACK_OFF / length if length > 0 else 0.0))
                cut = (last[0] + (qx - last[0]) * lo, last[1] + (qz - last[1]) * lo)
                if isinstance(element, ToolpathArc):
                    kept.extend(ToolpathLine(px_, pz_) for px_, pz_ in points[:points.index((qx, qz))])
                kept.append(ToolpathLine(*cut))
                return kept
            last = (qx, qz)
        kept.append(element)
        x, z = end
    return kept


def _depth_path(cut_path, top_x):
    """``cut_path`` carried on past both its ends, along the pulley's
    outside: what a blade wider than what is left of the groove there is
    stopped by, so a plunge near a flank goes no deeper than its edge may."""
    if not cut_path or not isinstance(cut_path[0], StartPoint):
        return cut_path
    start = cut_path[0]
    end_x, end_z = _path_end_point(cut_path)
    far = OUTSIDE_REACH
    right_first = start.z > end_z
    out_start = start.z + (far if right_first else -far)
    out_end = end_z + (-far if right_first else far)
    return ([StartPoint(top_x, out_start), ToolpathLine(start.x, start.z)]
            + cut_path[1:] + [ToolpathLine(top_x, out_end)])


def _cut_path(path, profile_type, radial, axial):
    """What the blade cuts to: ``path``, the groove's profile, offset by the
    stock to leave (_stock_allowance) - as lines - or itself with none."""
    allowance = _stock_allowance(path, profile_type, radial, axial)
    if len(allowance) < 2:
        return path
    z, x = allowance[0]
    return [StartPoint(x, z)] + [ToolpathLine(x, z) for z, x in allowance[1:]]


def _append_contour(
    lines,
    prefix,
    safe_x,
    path,
    center_z,
    clearance,
    profile_type,
    left_radius,
    right_radius,
    half_width=0.0,
    control=0,
    blade=None,
    part=None,
):
    contour_path = path
    if not contour_path or not isinstance(contour_path[0], StartPoint):
        return

    z_plus_path, z_minus_path = _split_path_at_z(contour_path, center_z)
    if str(profile_type).lower() == "id":
        z_plus_comp_side = "right"
        z_minus_comp_side = "left"
    else:
        z_plus_comp_side = "left"
        z_minus_comp_side = "right"

    z_plus_path = _offset_path_for_tool_radius(z_plus_path, right_radius, z_plus_comp_side)
    z_minus_path = _offset_path_for_tool_radius(_reverse_path(z_minus_path), left_radius, z_minus_comp_side)
    # the Z+ flank cut with the blade's right corner, the Z- one with its
    # left: each written for the point it was touched off on
    z_plus_path = _corner_to_control(z_plus_path, "right", right_radius, half_width, control, profile_type)
    z_minus_path = _corner_to_control(z_minus_path, "left", left_radius, half_width, control, profile_type)
    # each as far as the blade stays out of the part and its stock: one
    # wider than half the groove meets the far flank before the middle
    z_plus_path = _clear_part_of(z_plus_path, blade, part)
    z_minus_path = _clear_part_of(z_minus_path, blade, part)
    contour_safe_x = _safe_x_for_contour(z_plus_path + z_minus_path, safe_x, clearance, profile_type)

    lines.append(_code(prefix, "(----------Groove Roughing Finish Contour Z+ to Center----------)"))
    _emit_contour_section(lines, prefix, contour_safe_x, z_plus_path, "right")

    lines.append(_code(prefix, "(----------Groove Roughing Finish Contour Z- to Center----------)"))
    _emit_contour_section(lines, prefix, contour_safe_x, z_minus_path, "left")


def generate_groove_roughing_gcode(op):
    if hasattr(op, "to_dict"):
        op = op.to_dict()

    prefix = "/" if bool(op.get("is_optional_block", False)) else ""
    spindle = op.get("spindle_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    roughing = op.get("roughing_parameters", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}
    stock_enabled = bool(op.get("stock_to_leave_enabled", False))
    profile = op.get("_resolved_radial_profile", {}) or {}
    tool = op.get("_resolved_tool", {}) or {}

    lines = []
    lines.extend(build_spindle_gcode(spindle, prefix))
    feed_rate = get_float(cutting, "feed_rate", 0.1)
    peck_depth = abs(get_float(cutting, "peck_depth", 3.0))
    clearance = abs(get_float(cutting, "retract", 1.0))
    dwell_time = get_float(cutting, "dwell_time", 0.0)
    initial_offset = abs(get_float(roughing, "initial_offset", 0.0))
    afterwards_offset = abs(get_float(roughing, "afterwards_offset", 0.0))
    strategy = str(roughing.get("strategy", "start_center")).lower()
    stock_radial = get_float(stock, "radial", 0.0) if stock_enabled else 0.0
    stock_axial = get_float(stock, "axial", 0.0) if stock_enabled else 0.0

    lines.append(_code(prefix, f"G95 F{_fmt(feed_rate)}"))
    lines.append("")

    if strategy != "start_center":
        lines.append("( ERROR: Groove Roughing -- only start_center strategy is implemented )")
        return lines
    if not profile:
        lines.append("( ERROR: Groove Roughing -- no Define Radial Profile found above this operation )")
        return lines
    if not _tool_is_blade(tool):
        lines.append("( ERROR: Groove Roughing -- current tool must be a parting or grooving blade )")
        return lines

    width = _blade_width(tool)
    if width <= 0:
        lines.append("( ERROR: Groove Roughing -- blade width is not defined in tool extras )")
        return lines

    groove = _first_groove(profile)
    if not groove:
        lines.append("( ERROR: Groove Roughing -- radial profile has no groove primitive )")
        return lines

    path = _groove_path(profile)
    if path is None:
        lines.append("( ERROR: Groove Roughing -- radial profile did not produce a valid toolpath )")
        return lines

    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    center_z = (z_min + z_max) / 2.0
    half_width = width / 2.0

    profile_type = str(profile.get("profile_type", "od")).lower()
    # the pulley's outside; the start diameter, the plunges' start: that with
    # its radial stock to leave on; where the blade starts and backs off to:
    # the clearance out from the start diameter
    top_x = _top_x(path, profile_type)
    start_x = _start_x(path, profile_type, stock_radial)
    safe_x = _blade_start_x(start_x, profile_type, clearance)
    # what the blade cuts to: the profile with the stock to leave - radial
    # off the bottom, axial off the flanks
    cut_path = _cut_path(path, profile_type, stock_radial, stock_axial)
    # how deep a plunge may go: the cut path, and past its ends the pulley's
    # outside with its stock, under a blade wider than the groove is there
    depth_path = _depth_path(cut_path, start_x)

    def _plunges_into(target_x):
        """Whether a plunge to ``target_x`` goes into the groove at all."""
        if target_x is None:
            return False
        return target_x > top_x + SAME_MM if profile_type == "id" else target_x < top_x - SAME_MM

    right_limit = z_max - stock_axial - half_width
    left_limit = z_min + stock_axial + half_width
    if left_limit > right_limit:
        lines.append("( ERROR: Groove Roughing -- blade is wider than available groove after axial stock )")
        return lines

    positions = _center_positions(center_z, left_limit, right_limit, initial_offset, afterwards_offset)
    # the plunges are planned for the blade's middle; the G-code is written
    # for the point it was touched off on
    control = _blade_control(tool)
    z_control = control * half_width
    left_radius = get_float(tool, "left_radius", 0.0)
    right_radius = get_float(tool, "right_radius", 0.0)

    lines.append(
        _code(
            prefix,
            f"(----------Groove Roughing: Start Center P{int(roughing.get('profile_id', 0) or 0)}----------)",
        )
    )
    lines.append(
        _code(
            prefix,
            f"( blade width={_fmt(width)} left radius={_fmt(left_radius)} right radius={_fmt(right_radius)} touched off at {_CONTROL_NAMES[control]} )",
        )
    )

    start_index = 0
    if len(positions) >= 2 and initial_offset > 0:
        first_z = positions[0]
        second_z = positions[1]
        first_target_x = _profile_x_for_blade(depth_path, first_z, half_width, profile_type)
        second_target_x = _profile_x_for_blade(depth_path, second_z, half_width, profile_type)
        if _plunges_into(first_target_x) and _plunges_into(second_target_x):
            lines.append(_code(prefix, "(----------Groove Roughing Initial Center Pair----------)"))
            _append_center_pair_roughing(
                lines,
                prefix,
                first_z + z_control,
                first_target_x,
                second_z + z_control,
                second_target_x,
                start_x,
                peck_depth,
                clearance,
                feed_rate,
                dwell_time,
            )
            start_index = 2

    for z_pos in positions[start_index:]:
        target_x = _profile_x_for_blade(depth_path, z_pos, half_width, profile_type)
        if not _plunges_into(target_x):
            continue
        _append_peck(lines, prefix, z_pos + z_control, safe_x, target_x, peck_depth, clearance, feed_rate,
                     dwell_time)

    _append_contour(
        lines,
        prefix,
        safe_x,
        cut_path,
        center_z,
        clearance,
        profile_type,
        left_radius,
        right_radius,
        half_width,
        control,
        _Blade(half_width, left_radius, right_radius, control, profile_type),
        _part_with_stock(path, profile_type, stock_radial, stock_axial)[0].buffer(-CONTACT_MARGIN),
    )

    return lines
