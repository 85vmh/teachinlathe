from teachinlathe.conversational.data_types import ArcTo, BlendType, DefineProfile, LineTo, StartPoint

from ..config import fmt as _f



def _primitive_dir_to_gcode(direction_str):
    """Canvas ccw/cw mapping to lathe G2/G3 commands."""
    return 2 if str(direction_str).lower() == "ccw" else 3



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

    for primitive in op.profile_primitives[1:]:
        if isinstance(primitive, LineTo):
            blend_type = primitive.blend.blend_type
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
