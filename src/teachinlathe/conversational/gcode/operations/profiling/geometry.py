"""A drawn profile as the G-code goes along it: its primitives (the model's
StartPoint, LineTo, ArcTo, each with its ProfileBlend) made into a path of
lines and arcs - the blends cut into the corners they are on: chamfers,
fillets and DIN 509 undercuts - and what is worked out on such a path.
All X values are diameters, as the G-code has them; the blends are worked
out in radius space (x = X / 2), where a corner's angles are as drawn.
"""

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from teachinlathe.conversational.model.data_types import ArcTo, BlendType, LineTo, ProfileBlend, ProfilingType
from teachinlathe.conversational.model.data_types import StartPoint as ProfileStart

# ── Tolerances: when two numbers are the same one ───────────────────────────

#: mm the G-code is written to: lengths shorter than this are nothing to the
#: machine - no blend is made on them, no point is apart from another by it.
RESOLUTION = 0.001

#: mm: two positions or lengths this close are the same one - a tenth of the
#: RESOLUTION, so nothing the machine is sent differs.
SAME_MM = 0.0001

#: What floating-point rounding leaves over in a computed value - an angle,
#: a distance - that is exactly at a limit: compared with this much slack.
ROUNDING = 1e-9

#: A length, a cross product or a tangent this small is zero: nothing is
#: divided by it.
DEGENERATE = 1e-12

#: Degrees from the floor a DIN 509 undercut's ramp rises at.
DIN509_RAMP_ANGLE = 15.0


# ── The path ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StartPoint:
    """Where a path starts."""
    x: float
    z: float


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


def line_end(line: LineTo, start_x: float, start_z: float) -> Tuple[float, float]:
    """Where ``line`` ends, from (start_x, start_z): at its X and Z ("xz"),
    or at one of them and its angle from the Z axis - its Z ("az") or its
    X ("ax")."""
    mode = str(line.input or "xz").lower()
    if mode not in ("xz", "ax", "az"):
        mode = "xz"
    end_x = float(line.x_end)
    end_z = float(line.z_end)
    if mode == "xz":
        return end_x, end_z

    tangent = math.tan(math.radians(float(line.angle or 0.0)))
    if mode == "az":
        return float(start_x) + 2.0 * (end_z - float(start_z)) * tangent, end_z
    if abs(tangent) < DEGENERATE:
        return end_x, float(start_z)
    radial_delta = (end_x - float(start_x)) / 2.0
    return end_x, float(start_z) + radial_delta / tangent


def build_path(primitives, profile_type: ProfilingType = ProfilingType.OD) -> list:
    """``primitives`` - a profile's, in order - as the G-code goes along
    them: a StartPoint, then ToolpathLines and ToolpathArcs, each corner cut
    by the blend of the primitive it ends - a start point's blend cuts the
    corner its stock makes with the first primitive, from outside the stock
    (``profile_type``: OD from above, ID from below). A path that does not
    begin with a start point starts at X0 Z0, with no StartPoint."""
    ends = _ends(primitives)
    is_id = profile_type is ProfilingType.ID
    path = []
    at_x = at_z = 0.0
    for index, (primitive, end_x, end_z) in enumerate(ends):
        after = _next(ends, index)
        blend = primitive.blend
        if isinstance(primitive, ProfileStart):
            at_x, at_z = end_x, end_z
            if blend.blend_type is not BlendType.NONE and after is not None:
                start_r = at_x / 2
                if blend.blend_type is BlendType.CHAMFER:
                    width = blend.chamfer_width
                    entry_r = start_r + width if is_id else start_r - width
                    chamfer = _chamfer_line(entry_r, at_z, start_r, at_z, after, width)
                    if chamfer:
                        path.append(StartPoint(chamfer.start_x * 2, chamfer.start_z))
                        path.append(ToolpathLine(chamfer.end_x * 2, chamfer.end_z))
                        continue
                elif blend.blend_type is BlendType.FILLET:
                    radius = blend.fillet_radius
                    entry_r = start_r + radius if is_id else start_r - radius
                    fillet = (_fillet_line_arc(entry_r, at_z, start_r, at_z, after, radius)
                              if isinstance(after, _NextArc)
                              else _fillet_line_line(entry_r, at_z, start_r, at_z, after, radius))
                    if fillet:
                        path.append(StartPoint(fillet.start_x * 2, fillet.start_z))
                        path.append(fillet.arc())
                        continue
            path.append(StartPoint(at_x, at_z))
            continue

        if isinstance(primitive, LineTo):
            next_x, next_z = end_x, end_z
            if blend.blend_type is BlendType.CHAMFER:
                chamfer = _chamfer_line(at_x / 2, at_z, end_x / 2, end_z, after, blend.chamfer_width)
                if chamfer:
                    path.append(ToolpathLine(chamfer.start_x * 2, chamfer.start_z))
                    path.append(ToolpathLine(chamfer.end_x * 2, chamfer.end_z))
                else:
                    path.append(ToolpathLine(end_x, end_z))
            elif blend.blend_type is BlendType.FILLET:
                radius = blend.fillet_radius
                fillet = (_fillet_line_arc(at_x / 2, at_z, end_x / 2, end_z, after, radius)
                          if isinstance(after, _NextArc)
                          else _fillet_line_line(at_x / 2, at_z, end_x / 2, end_z, after, radius))
                if fillet:
                    path.append(ToolpathLine(fillet.start_x * 2, fillet.start_z))
                    path.append(fillet.arc())
                else:
                    path.append(ToolpathLine(end_x, end_z))
            elif blend.blend_type is BlendType.UNDERCUT_DIN509:
                undercut = (undercut_din509(at_x / 2, at_z, end_x / 2, end_z, after.x, after.z, blend)
                            if isinstance(after, _NextLine) else None)
                if undercut:
                    path.append(ToolpathLine(undercut.entry_x * 2, undercut.entry_z))
                    path.append(ToolpathLine(undercut.ramp_end_x * 2, undercut.ramp_end_z))
                    path.append(ToolpathLine(undercut.arc_start_x * 2, undercut.arc_start_z))
                    path.append(ToolpathArc(undercut.exit_x * 2, undercut.exit_z,
                                            undercut.center_x * 2, undercut.center_z, undercut.anticlockwise))
                    next_x, next_z = undercut.exit_x * 2, undercut.exit_z
                else:
                    path.append(ToolpathLine(end_x, end_z))
            else:
                path.append(ToolpathLine(end_x, end_z))
            at_x, at_z = next_x, next_z
            continue

        # an arc
        center_x, center_z = primitive.x_center, primitive.z_center
        clockwise = not primitive.ccw
        end_r, center_r = end_x / 2, center_x / 2
        radius_r = math.sqrt((end_r - center_r) ** 2 + (end_z - center_z) ** 2)
        arc_end = ToolpathArc(end_x, end_z, center_x, center_z, not clockwise)
        if blend.blend_type is BlendType.CHAMFER:
            chamfer = _chamfer_arc(center_r, center_z, radius_r, clockwise, end_r, end_z, after, blend.chamfer_width)
            if chamfer:
                path.append(ToolpathArc(chamfer.start_x * 2, chamfer.start_z, center_x, center_z, not clockwise))
                path.append(ToolpathLine(chamfer.end_x * 2, chamfer.end_z))
            else:
                path.append(arc_end)
        elif blend.blend_type is BlendType.FILLET:
            fillet = _fillet_arc_line(center_r, center_z, radius_r, clockwise, end_r, end_z, after,
                                      blend.fillet_radius)
            if fillet:
                path.append(ToolpathArc(fillet.start_x * 2, fillet.start_z, center_x, center_z, not clockwise))
                path.append(fillet.arc())
            else:
                path.append(arc_end)
        else:
            path.append(arc_end)
        at_x, at_z = end_x, end_z
    return path


def _ends(primitives) -> List[tuple]:
    """(primitive, X, Z) of each of ``primitives``: where it ends - a start
    point where it is - from X0 Z0 before the first start point."""
    ends = []
    x = z = 0.0
    for primitive in primitives or []:
        if isinstance(primitive, ProfileStart):
            x, z = float(primitive.x_start), float(primitive.z_start)
        elif isinstance(primitive, LineTo):
            x, z = line_end(primitive, x, z)
        elif isinstance(primitive, ArcTo):
            x, z = float(primitive.x_end), float(primitive.z_end)
        else:
            continue
        ends.append((primitive, x, z))
    return ends


# ── The corners: in radius space ────────────────────────────────────────────

@dataclass(frozen=True)
class _NextLine:
    """The primitive after a corner, a line: where it ends."""
    x: float
    z: float


@dataclass(frozen=True)
class _NextArc:
    """The primitive after a corner, an arc: its centre, radius and way round."""
    center_x: float
    center_z: float
    radius: float
    clockwise: bool


@dataclass(frozen=True)
class _NextStart:
    """The primitive after a corner, another start point: nothing to blend with."""


def _next(ends, index):
    """The primitive after the one at ``index``, as the blend of its corner
    takes it (in radius space), or None after the last."""
    if index + 1 >= len(ends):
        return None
    primitive, x, z = ends[index + 1]
    if isinstance(primitive, LineTo):
        return _NextLine(x / 2, z)
    if isinstance(primitive, ArcTo):
        end_r, center_r = x / 2, primitive.x_center / 2
        return _NextArc(center_r, primitive.z_center,
                        math.sqrt((end_r - center_r) ** 2 + (z - primitive.z_center) ** 2), not primitive.ccw)
    return _NextStart()


@dataclass(frozen=True)
class _Chamfer:
    start_x: float
    start_z: float
    end_x: float
    end_z: float


@dataclass(frozen=True)
class _Fillet:
    """A fillet's arc, from (start) to (end) about (center)."""
    start_x: float
    start_z: float
    end_x: float
    end_z: float
    center_x: float
    center_z: float
    anticlockwise: bool

    def arc(self) -> ToolpathArc:
        return ToolpathArc(self.end_x * 2, self.end_z, self.center_x * 2, self.center_z, self.anticlockwise)


@dataclass(frozen=True)
class Undercut:
    """A DIN 509 undercut at a corner, in radius space (x = X / 2): in at
    ``entry``, up its ramp to ``ramp_end``, along its floor to ``arc_start``
    and round its radius about ``center`` out to ``exit``, on the next line."""
    entry_x: float
    entry_z: float
    ramp_end_x: float
    ramp_end_z: float
    arc_start_x: float
    arc_start_z: float
    center_x: float
    center_z: float
    exit_x: float
    exit_z: float
    anticlockwise: bool


def _fillet_line_line(start_x, start_z, corner_x, corner_z, after, radius) -> Optional[_Fillet]:
    if not isinstance(after, _NextLine):
        return None
    start_delta_x = corner_x - start_x
    start_delta_z = corner_z - start_z
    start_length = math.sqrt(start_delta_x ** 2 + start_delta_z ** 2)
    if start_length < RESOLUTION or radius < RESOLUTION:
        return None

    next_delta_x = after.x - corner_x
    next_delta_z = after.z - corner_z
    next_length = math.sqrt(next_delta_x ** 2 + next_delta_z ** 2)
    if next_length < RESOLUTION:
        return None

    dir1_x = start_delta_x / start_length
    dir1_z = start_delta_z / start_length
    dir2_x = next_delta_x / next_length
    dir2_z = next_delta_z / next_length
    cross = dir1_z * dir2_x - dir1_x * dir2_z
    dot = dir1_z * dir2_z + dir1_x * dir2_x
    if abs(cross) < RESOLUTION:
        return None

    tangent_distance = radius * (1.0 - dot) / abs(cross)
    tangent1_x = corner_x - tangent_distance * dir1_x
    tangent1_z = corner_z - tangent_distance * dir1_z
    tangent2_x = corner_x + tangent_distance * dir2_x
    tangent2_z = corner_z + tangent_distance * dir2_z

    normal_x = dir1_z if cross > 0 else -dir1_z
    normal_z = -dir1_x if cross > 0 else dir1_x
    return _Fillet(tangent1_x, tangent1_z, tangent2_x, tangent2_z,
                   tangent1_x + radius * normal_x, tangent1_z + radius * normal_z, cross < 0)


def _fillet_arc_line(center_x, center_z, arc_radius, is_cw, join_x, join_z, after, radius) -> Optional[_Fillet]:
    if not isinstance(after, _NextLine):
        return None
    next_delta_raw_x = after.x - join_x
    next_delta_raw_z = after.z - join_z
    next_length = math.sqrt(next_delta_raw_x ** 2 + next_delta_raw_z ** 2)
    if next_length < RESOLUTION or radius < RESOLUTION or arc_radius < RESOLUTION:
        return None
    dir2_x = next_delta_raw_x / next_length
    dir2_z = next_delta_raw_z / next_length

    radial_x = join_x - center_x
    radial_z = join_z - center_z
    radial_length = math.sqrt(radial_x ** 2 + radial_z ** 2)
    if radial_length < RESOLUTION:
        return None
    dir1_x = (radial_z if is_cw else -radial_z) / radial_length
    dir1_z = (-radial_x if is_cw else radial_x) / radial_length

    cross = dir1_z * dir2_x - dir1_x * dir2_z
    if abs(cross) < RESOLUTION:
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
    if center_vector_length < RESOLUTION:
        return None

    tangent1_x = center_x + arc_radius * center_vector_x / center_vector_length
    tangent1_z = center_z + arc_radius * center_vector_z / center_vector_length
    return _Fillet(tangent1_x, tangent1_z, tangent2_x, tangent2_z, fillet_center_x, fillet_center_z, cross < 0)


def _fillet_line_arc(start_x, start_z, corner_x, corner_z, after, radius) -> Optional[_Fillet]:
    if not isinstance(after, _NextArc):
        return None
    is_cw = after.clockwise
    arc_radius = after.radius
    if radius < RESOLUTION or arc_radius < RESOLUTION:
        return None

    delta1_x = corner_x - start_x
    delta1_z = corner_z - start_z
    length1 = math.sqrt(delta1_x ** 2 + delta1_z ** 2)
    if length1 < RESOLUTION:
        return None
    dir1_x = delta1_x / length1
    dir1_z = delta1_z / length1

    radial_x = corner_x - after.center_x
    radial_z = corner_z - after.center_z
    radial_length = math.sqrt(radial_x ** 2 + radial_z ** 2)
    if radial_length < RESOLUTION:
        return None
    dir2_x = (radial_z if is_cw else -radial_z) / radial_length
    dir2_z = (-radial_x if is_cw else radial_x) / radial_length

    cross = dir1_z * dir2_x - dir1_x * dir2_z
    if abs(cross) < RESOLUTION:
        return None

    normal1_x = dir1_z if cross > 0 else -dir1_z
    normal1_z = -dir1_x if cross > 0 else dir1_x
    offset_x = corner_x + radius * normal1_x - after.center_x
    offset_z = corner_z + radius * normal1_z - after.center_z

    projection = offset_z * dir1_z + offset_x * dir1_x
    discriminant = projection ** 2 - (offset_z ** 2 + offset_x ** 2) + (arc_radius + radius) ** 2
    if discriminant < 0:
        return None

    tangent_distance = projection + math.sqrt(discriminant)
    fillet_center_x = corner_x - tangent_distance * dir1_x + radius * normal1_x
    fillet_center_z = corner_z - tangent_distance * dir1_z + radius * normal1_z
    tangent1_x = corner_x - tangent_distance * dir1_x
    tangent1_z = corner_z - tangent_distance * dir1_z
    center_vector_x = fillet_center_x - after.center_x
    center_vector_z = fillet_center_z - after.center_z
    center_vector_length = math.sqrt(center_vector_x ** 2 + center_vector_z ** 2)
    if center_vector_length < RESOLUTION:
        return None

    tangent2_x = after.center_x + arc_radius * center_vector_x / center_vector_length
    tangent2_z = after.center_z + arc_radius * center_vector_z / center_vector_length
    return _Fillet(tangent1_x, tangent1_z, tangent2_x, tangent2_z, fillet_center_x, fillet_center_z, cross < 0)


def _chamfer_line(logical_x, logical_z, end_x, end_z, after, width) -> Optional[_Chamfer]:
    delta_x = end_x - logical_x
    delta_z = end_z - logical_z
    length = math.sqrt(delta_x ** 2 + delta_z ** 2)
    if length < RESOLUTION or width < RESOLUTION:
        return None
    chamfer_start_x = end_x - width * delta_x / length
    chamfer_start_z = end_z - width * delta_z / length
    chamfer_end_x = end_x
    chamfer_end_z = end_z

    if isinstance(after, _NextLine):
        next_delta_x = after.x - end_x
        next_delta_z = after.z - end_z
        next_length = math.sqrt(next_delta_x ** 2 + next_delta_z ** 2)
        if next_length > RESOLUTION:
            chamfer_end_x = end_x + width * next_delta_x / next_length
            chamfer_end_z = end_z + width * next_delta_z / next_length
    elif isinstance(after, _NextArc):
        radial_x = end_x - after.center_x
        radial_z = end_z - after.center_z
        tangent_x = radial_z if after.clockwise else -radial_z
        tangent_z = -radial_x if after.clockwise else radial_x
        tangent_length = math.sqrt(tangent_x ** 2 + tangent_z ** 2)
        if tangent_length > RESOLUTION:
            chamfer_end_x = end_x + width * tangent_x / tangent_length
            chamfer_end_z = end_z + width * tangent_z / tangent_length
    return _Chamfer(chamfer_start_x, chamfer_start_z, chamfer_end_x, chamfer_end_z)


def _chamfer_arc(center_x, center_z, radius, is_cw, end_x, end_z, after, width) -> Optional[_Chamfer]:
    radial_x = end_x - center_x
    radial_z = end_z - center_z
    radial_length = math.sqrt(radial_x ** 2 + radial_z ** 2)
    if radial_length < RESOLUTION or width < RESOLUTION:
        return None
    tangent_x = radial_z if is_cw else -radial_z
    tangent_z = -radial_x if is_cw else radial_x
    chamfer_start_x = end_x - width * tangent_x / radial_length
    chamfer_start_z = end_z - width * tangent_z / radial_length
    chamfer_end_x = end_x
    chamfer_end_z = end_z
    if isinstance(after, _NextLine):
        next_delta_x = after.x - end_x
        next_delta_z = after.z - end_z
        next_length = math.sqrt(next_delta_x ** 2 + next_delta_z ** 2)
        if next_length > RESOLUTION:
            chamfer_end_x = end_x + width * next_delta_x / next_length
            chamfer_end_z = end_z + width * next_delta_z / next_length
    return _Chamfer(chamfer_start_x, chamfer_start_z, chamfer_end_x, chamfer_end_z)


def undercut_din509(start_x, start_z, corner_x, corner_z, next_x, next_z,
                    blend: ProfileBlend) -> Optional[Undercut]:
    """The DIN 509 undercut ``blend`` cuts into the corner (corner_x,
    corner_z) between the line from (start_x, start_z) and the one on to
    (next_x, next_z), all in radius space; None where there is none to cut."""
    undercut_radius = blend.undercut_radius
    undercut_depth = blend.undercut_depth
    undercut_length = blend.undercut_length
    if (
        undercut_radius < RESOLUTION
        or undercut_depth < RESOLUTION
        or undercut_length < RESOLUTION
        or undercut_depth < undercut_radius
    ):
        return None

    delta1_x = corner_x - start_x
    delta1_z = corner_z - start_z
    length1 = math.sqrt(delta1_x ** 2 + delta1_z ** 2)
    if length1 < RESOLUTION:
        return None

    delta2_x = next_x - corner_x
    delta2_z = next_z - corner_z
    length2 = math.sqrt(delta2_x ** 2 + delta2_z ** 2)
    if length2 < RESOLUTION:
        return None

    dir1_x = delta1_x / length1
    dir1_z = delta1_z / length1
    dir2_x = delta2_x / length2
    dir2_z = delta2_z / length2

    cross = dir1_z * dir2_x - dir1_x * dir2_z
    dot = dir1_z * dir2_z + dir1_x * dir2_x
    if abs(cross) < RESOLUTION:
        return None

    ramp_len = undercut_depth / math.tan(math.radians(DIN509_RAMP_ANGLE))
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
    return Undercut(ramp_start_x, ramp_start_z, ramp_end_x, ramp_end_z, arc_start_x, arc_start_z,
                    arc_start_x + undercut_radius * normal_x, arc_start_z + undercut_radius * normal_z,
                    exit_x, exit_z, cross < 0)


# ── On a path ───────────────────────────────────────────────────────────────

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


def arc_x_at_z(sx, sz, ex, ez, cx, cz, anticlockwise, target_z) -> List[float]:
    """Every X (a diameter) where the arc (sx, sz) -> (ex, ez) about
    (cx, cz) crosses Z ``target_z``."""
    sx_r, ex_r, cx_r = sx / 2, ex / 2, cx / 2
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
            results.append(x_r_candidate * 2)
    return results
