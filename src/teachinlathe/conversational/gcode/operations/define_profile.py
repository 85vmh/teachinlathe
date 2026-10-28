from teachinlathe.conversational.model.data_types import ArcTo, BlendType, DefineProfile, LineTo, StartPoint

from ..config import fmt as _f
from .profiling.geometry import line_end, undercut_din509


def _undercut_lines(blend, prev_x, prev_z, end_x, end_z, next_x, next_z):
    """(lines, exit X, exit Z) of the DIN 509 undercut ``blend`` cuts into
    the corner at (end_x, end_z) - the G-code's X, diameters - or None."""
    undercut = undercut_din509(prev_x / 2, prev_z, end_x / 2, end_z, next_x / 2, next_z, blend)
    if undercut is None:
        return None
    arc = "G3" if undercut.anticlockwise else "G2"
    return [
        f"G1 X{_f(undercut.entry_x * 2)} Z{_f(undercut.entry_z)}",
        f"G1 X{_f(undercut.ramp_end_x * 2)} Z{_f(undercut.ramp_end_z)}",
        f"G1 X{_f(undercut.arc_start_x * 2)} Z{_f(undercut.arc_start_z)}",
        f"{arc} X{_f(undercut.exit_x * 2)} Z{_f(undercut.exit_z)} "
        f"I{_f(undercut.center_x - undercut.arc_start_x)} K{_f(undercut.center_z - undercut.arc_start_z)}",
    ], undercut.exit_x * 2, undercut.exit_z


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
            end_x, end_z = line_end(primitive, cx, cz)
            blend_type = primitive.blend.blend_type
            if blend_type == BlendType.UNDERCUT_DIN509:
                next_prim = rest[idx + 1] if idx + 1 < len(rest) else None
                if next_prim is not None and isinstance(next_prim, LineTo):
                    next_x, next_z = line_end(next_prim, end_x, end_z)
                    undercut = _undercut_lines(primitive.blend, cx, cz, end_x, end_z, next_x, next_z)
                    if undercut:
                        lines_of_it, cx, cz = undercut
                        body_lines.extend(lines_of_it)
                        continue
            blend_suffix = ""
            if blend_type == BlendType.FILLET and primitive.blend.fillet_radius > 0:
                blend_suffix = f" A{_f(primitive.blend.fillet_radius)}"
            elif blend_type == BlendType.CHAMFER and primitive.blend.chamfer_width > 0:
                blend_suffix = f" C{_f(primitive.blend.chamfer_width)}"
            body_lines.append(f"G1 X{_f(end_x)} Z{_f(end_z)}{blend_suffix}")
            cx, cz = end_x, end_z
            continue

        if isinstance(primitive, ArcTo):
            blend_type = primitive.blend.blend_type
            blend_suffix = ""
            if blend_type == BlendType.FILLET and primitive.blend.fillet_radius > 0:
                blend_suffix = f" A{_f(primitive.blend.fillet_radius)}"
            elif blend_type == BlendType.CHAMFER and primitive.blend.chamfer_width > 0:
                blend_suffix = f" C{_f(primitive.blend.chamfer_width)}"
            # the canvas's counter-clockwise is the lathe's G2
            gcmd = "G2" if primitive.ccw else "G3"
            ii = (primitive.x_center - cx) / 2
            ik = primitive.z_center - cz
            body_lines.append(
                f"{gcmd} X{_f(primitive.x_end)} Z{_f(primitive.z_end)} I{_f(ii)} K{_f(ik)}{blend_suffix}"
            )
            cx, cz = primitive.x_end, primitive.z_end

    lines.extend([f"\t{ln}" for ln in body_lines])
    lines.append(f"O{profile_id} ENDSUB")
    return lines
