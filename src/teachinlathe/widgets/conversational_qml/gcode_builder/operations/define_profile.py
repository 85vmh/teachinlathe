import math

from teachinlathe.conversational.data_types import ArcTo, BlendType, DefineProfile, LineTo, StartPoint

from ..config import fmt as _f



def _primitive_dir_to_gcode(direction_str):
    """Canvas ccw/cw mapping to lathe G2/G3 commands."""
    return 2 if str(direction_str).lower() == "ccw" else 3


def _undercut_din509_geometry(blend, prev_x, prev_z, end_x, end_z, next_x, next_z):
    """Return DIN 509 Form E undercut geometry between two perpendicular lines.

    All coordinates are diameter-mode X (as stored in the profile).
    Geometry is computed in radius space internally, then converted back.
    """
    undercut_radius = float(blend.undercut_radius)
    undercut_depth = float(blend.undercut_depth)
    undercut_length = float(blend.undercut_length)
    if (
        undercut_radius < 1e-4
        or undercut_depth < 1e-4
        or undercut_length < 1e-4
        or undercut_depth < undercut_radius
    ):
        return None

    # Work in radius-Z space
    px, pz = prev_x / 2, prev_z
    ex, ez = end_x  / 2, end_z
    nx, nz = next_x / 2, next_z

    sdz, sdx = ez - pz, ex - px
    slen = math.hypot(sdz, sdx)
    ndz, ndx = nz - ez, nx - ex
    nlen = math.hypot(ndz, ndx)
    if slen < 1e-4 or nlen < 1e-4:
        return None

    d1z, d1x = sdz / slen, sdx / slen
    d2z, d2x = ndz / nlen, ndx / nlen

    cross = d1z * d2x - d1x * d2z
    dot = d1z * d2z + d1x * d2x
    if abs(cross) < 1e-4:
        return None

    ramp_len = undercut_depth / math.tan(math.radians(15.0))
    depth_z, depth_x = -d1x, d1z
    if depth_z * d2z + depth_x * d2x > 0:
        depth_z, depth_x = -depth_z, -depth_x

    floor_base_z = ez + undercut_depth * depth_z
    floor_base_x = ex + undercut_depth * depth_x
    to_corner_z = ez - floor_base_z
    to_corner_x = ex - floor_base_x
    floor_to_next_intersection = (to_corner_z * d2x - to_corner_x * d2z) / cross
    join_z = floor_base_z + floor_to_next_intersection * d1z
    join_x = floor_base_x + floor_to_next_intersection * d1x

    tangent_len = undercut_radius * (1.0 - dot) / abs(cross)
    min_length = ramp_len + tangent_len
    effective_length = max(undercut_length, min_length)
    flat_len = effective_length - min_length

    arc_start_z = join_z - tangent_len * d1z
    arc_start_x = join_x - tangent_len * d1x
    ramp_start_z = arc_start_z - (flat_len + ramp_len) * d1z - undercut_depth * depth_z
    ramp_start_x = arc_start_x - (flat_len + ramp_len) * d1x - undercut_depth * depth_x
    ramp_end_z = ramp_start_z + ramp_len * d1z + undercut_depth * depth_z
    ramp_end_x = ramp_start_x + ramp_len * d1x + undercut_depth * depth_x
    exit_z = join_z + tangent_len * d2z
    exit_x = join_x + tangent_len * d2x
    normal_z = -d1x if cross > 0 else d1x
    normal_x = d1z if cross > 0 else -d1z
    arc_center_z = arc_start_z + undercut_radius * normal_z
    arc_center_x = arc_start_x + undercut_radius * normal_x

    g_arc1 = "G3" if cross < 0 else "G2"

    return {
        "exit_x": exit_x * 2,
        "exit_z": exit_z,
        "lines": [
            f"G1 X{_f(ramp_start_x * 2)} Z{_f(ramp_start_z)}",
            f"G1 X{_f(ramp_end_x * 2)} Z{_f(ramp_end_z)}",
            f"G1 X{_f(arc_start_x * 2)} Z{_f(arc_start_z)}",
            f"{g_arc1} X{_f(exit_x * 2)} Z{_f(exit_z)} I{_f(arc_center_x - arc_start_x)} K{_f(arc_center_z - arc_start_z)}",
        ],
    }



def generate_define_profile_gcode(op: DefineProfile):
    if not op.generate_gcode or not op.profile_primitives:
        return []

    if not isinstance(op.profile_primitives[0], StartPoint):
        return []

    profile_id = int(op.profile_id)
    lines = [f"O{profile_id} SUB"]
    body_lines = []

    start = op.profile_primitives[0]
    cx = float(start.x_start)
    cz = float(start.z_start)
    blend_type = start.blend.blend_type
    if blend_type == BlendType.CHAMFER and start.blend.chamfer_width > 0:
        cw = float(start.blend.chamfer_width)
        body_lines.append(f"G0 X{_f(cx + cw * 2 + 1)} Z{_f(cz)}")
        body_lines.append(f"G1 X{_f(cx)} Z{_f(cz)} C{_f(cw)}")
    elif blend_type == BlendType.FILLET and start.blend.fillet_radius > 0:
        fr = float(start.blend.fillet_radius)
        body_lines.append(f"G0 X{_f(cx + fr * 2 + 1)} Z{_f(cz)}")
        body_lines.append(f"G1 X{_f(cx)} Z{_f(cz)} A{_f(fr)}")
    else:
        body_lines.append(f"G0 X{_f(cx)} Z{_f(cz)}")

    rest = op.profile_primitives[1:]
    for idx, primitive in enumerate(rest):
        if isinstance(primitive, LineTo):
            blend_type = primitive.blend.blend_type
            if blend_type == BlendType.UNDERCUT_DIN509:
                next_prim = rest[idx + 1] if idx + 1 < len(rest) else None
                if next_prim is not None and isinstance(next_prim, LineTo):
                    uc_geom = _undercut_din509_geometry(
                        primitive.blend,
                        cx, cz,
                        primitive.x_end, primitive.z_end,
                        next_prim.x_end, next_prim.z_end,
                    )
                    if uc_geom:
                        body_lines.extend(uc_geom["lines"])
                        cx, cz = uc_geom["exit_x"], uc_geom["exit_z"]
                        continue
            blend_suffix = ""
            if blend_type == BlendType.FILLET and primitive.blend.fillet_radius > 0:
                blend_suffix = f" A{_f(primitive.blend.fillet_radius)}"
            elif blend_type == BlendType.CHAMFER and primitive.blend.chamfer_width > 0:
                blend_suffix = f" C{_f(primitive.blend.chamfer_width)}"
            body_lines.append(f"G1 X{_f(primitive.x_end)} Z{_f(primitive.z_end)}{blend_suffix}")
            cx, cz = primitive.x_end, primitive.z_end
            continue

        if isinstance(primitive, ArcTo):
            blend_type = primitive.blend.blend_type
            blend_suffix = ""
            if blend_type == BlendType.FILLET and primitive.blend.fillet_radius > 0:
                blend_suffix = f" A{_f(primitive.blend.fillet_radius)}"
            elif blend_type == BlendType.CHAMFER and primitive.blend.chamfer_width > 0:
                blend_suffix = f" C{_f(primitive.blend.chamfer_width)}"
            gdir = _primitive_dir_to_gcode(primitive.direction)
            gcmd = "G2" if gdir == 2 else "G3"
            ii = (primitive.x_center - cx) / 2
            ik = primitive.z_center - cz
            body_lines.append(
                f"{gcmd} X{_f(primitive.x_end)} Z{_f(primitive.z_end)} I{_f(ii)} K{_f(ik)}{blend_suffix}"
            )
            cx, cz = primitive.x_end, primitive.z_end

    lines.extend([f"\t{ln}" for ln in body_lines])
    lines.append(f"O{profile_id} ENDSUB")
    return lines
