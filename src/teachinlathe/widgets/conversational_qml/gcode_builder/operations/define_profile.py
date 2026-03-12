from ..config import fmt as _f

def _json_dir_to_gcode(direction_str):
    """JSON 'ccw' -> G2, 'cw' -> G3 (matches canvas orientation)."""
    return 2 if str(direction_str).lower() == "ccw" else 3


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_define_profile_gcode(op):
    if not bool(op.get("generate_gcode", True)):
        return []

    primitives = op.get("profile_primitives", []) or []
    if not primitives:
        return []

    profile_id = int(op.get("profile_id", 0) or 0)
    lines = [f"O{profile_id} SUB"]
    body_lines = []

    segs = []
    for p in primitives:
        t = p.get("type", "")
        blend = p.get("blend") or {}
        blend_type = blend.get("type", "none")
        blend_rf = float(blend.get("fillet_radius", 0.0) or 0.0)
        blend_cw = float(blend.get("chamfer_width", 0.0) or 0.0)

        if t == "startPoint":
            segs.append({
                "type": "startPoint",
                "x": float(p.get("x_start", 0)),
                "z": float(p.get("z_start", 0)),
            })
        elif t == "lineTo":
            segs.append({
                "type": "lineTo",
                "x_end": float(p.get("x_end", 0)),
                "z_end": float(p.get("z_end", 0)),
                "blend_type": blend_type,
                "blend_rf": blend_rf,
                "blend_cw": blend_cw,
            })
        elif t == "arcTo":
            segs.append({
                "type": "arcTo",
                "x_end": float(p.get("x_end", 0)),
                "z_end": float(p.get("z_end", 0)),
                "x_center": float(p.get("x_center", 0)),
                "z_center": float(p.get("z_center", 0)),
                "gcode_dir": _json_dir_to_gcode(p.get("direction", "cw")),
                "blend_type": blend_type,
                "blend_rf": blend_rf,
                "blend_cw": blend_cw,
            })

    if not segs or segs[0]["type"] != "startPoint":
        return []

    cx = segs[0]["x"]
    cz = segs[0]["z"]
    body_lines.append(f"G0 X{_f(cx)} Z{_f(cz)}")

    for i in range(1, len(segs)):
        seg = segs[i]
        seg_type = seg["type"]
        blend_type = seg.get("blend_type", "none")
        blend_rf = seg.get("blend_rf", 0.0)
        blend_cw = seg.get("blend_cw", 0.0)
        ex = seg["x_end"]
        ez = seg["z_end"]

        # LinuxCNC G71/G72 native fillet (A) and chamfer (C) support.
        # The interpreter computes the geometry automatically.
        blend_suffix = ""
        if blend_type == "fillet" and blend_rf > 0:
            blend_suffix = f" A{_f(blend_rf)}"
        elif blend_type == "chamfer" and blend_cw > 0:
            blend_suffix = f" C{_f(blend_cw)}"

        if seg_type == "lineTo":
            body_lines.append(f"G1 X{_f(ex)} Z{_f(ez)}{blend_suffix}")
            cx, cz = ex, ez

        elif seg_type == "arcTo":
            gdir = seg["gcode_dir"]
            acx, acz = seg["x_center"], seg["z_center"]
            gcmd = "G2" if gdir == 2 else "G3"
            ii = acx - cx
            ik = acz - cz
            body_lines.append(f"{gcmd} X{_f(ex)} Z{_f(ez)} I{_f(ii)} K{_f(ik)}{blend_suffix}")
            cx, cz = ex, ez

    lines.extend([f"\t{ln}" for ln in body_lines])
    lines.append(f"O{profile_id} ENDSUB")
    return lines