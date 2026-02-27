import math


def _f(v):
    return f"{v:.6f}"


def _line_direction(x0, z0, x1, z1):
    dx = x1 - x0
    dz = z1 - z0
    length = math.hypot(dx, dz)
    if length < 1e-12:
        return 0.0, 0.0
    return dx / length, dz / length


def _arc_tangent_at(px, pz, cx, cz, gcode_dir):
    """
    Unit tangent to an arc at point (px,pz) with centre (cx,cz).
    gcode_dir: 2 = G2 (CW in LinuxCNC G18), 3 = G3 (CCW).
    In the XZ visual plane, G2 is the short CW path.
    Tangent = radius rotated 90 deg in the direction of travel.
    """
    rx, rz = px - cx, pz - cz
    if gcode_dir == 2:
        return rz, -rx
    else:
        return -rz, rx


def _normalise(dx, dz):
    n = math.hypot(dx, dz)
    if n < 1e-12:
        return dx, dz
    return dx / n, dz / n


def _json_dir_to_gcode(direction_str):
    """JSON 'ccw' -> G2, 'cw' -> G3 (matches canvas orientation)."""
    return 2 if str(direction_str).lower() == "ccw" else 3


# ---------------------------------------------------------------------------
# Fillet between two consecutive segments
# ---------------------------------------------------------------------------

def _fillet_line_line_qml(start_x, start_z, corner_x, corner_z, next_x, next_z, rf):
    """
    Port of ProfileCanvas.Geometry.filletGeom for line-line fillet.
    Returns (t1x, t1z, t2x, t2z, fcx, fcz, anticlockwise) or None.
    """
    sdz = corner_z - start_z
    sdx = corner_x - start_x
    slen = math.hypot(sdz, sdx)
    if slen < 1e-6 or rf < 1e-6:
        return None

    ndz = next_z - corner_z
    ndx = next_x - corner_x
    nlen = math.hypot(ndz, ndx)
    if nlen < 1e-6:
        return None

    d1z = sdz / slen
    d1x = sdx / slen
    d2z = ndz / nlen
    d2x = ndx / nlen

    cross = d1z * d2x - d1x * d2z
    dot = d1z * d2z + d1x * d2x
    abs_cross = abs(cross)
    if abs_cross < 1e-6:
        return None

    t = rf * (1.0 - dot) / abs_cross
    t1z = corner_z - t * d1z
    t1x = corner_x - t * d1x
    t2z = corner_z + t * d2z
    t2x = corner_x + t * d2x

    perp_z = -d1x if cross > 0 else d1x
    perp_x = d1z if cross > 0 else -d1z

    fcz = t1z + rf * perp_z
    fcx = t1x + rf * perp_x

    anticlockwise = (cross < 0)
    return t1x, t1z, t2x, t2z, fcx, fcz, anticlockwise


def _fillet_arc_line(arc_cx, arc_cz, arc_r, gcode_dir, line_tx, line_tz, rf):
    """
    Fillet of radius rf between an arc (centre arc_c, radius arc_r, direction
    gcode_dir) and a line with unit tangent (line_tx, line_tz).

    The fillet circle is tangent externally to the arc and tangent to the line.
    Returns (t1x, t1z, t2x, t2z, fcx, fcz) or None.

    The line's outward normal pointing toward the fillet centre:
      if the line goes in direction (tx, tz), the fillet sits on the left or
      right side.  We choose the side consistent with the arc.
    """
    line_nx, line_nz = -line_tz, line_tx

    # Fillet centre is at distance rf from the line.
    # Try both sides and pick the one closer to arc centre.
    candidates = []
    for sign in (1, -1):
        # The line passes through the arc endpoint; we offset by rf * normal.
        # We don't know the corner point here - it's the arc endpoint.
        # Instead: fillet centre satisfies:
        #   dist(fc, arc_centre) = arc_r + rf   (external tangency)
        #   dist(fc, line) = rf
        # The line passes through the arc endpoint.  We need the arc endpoint.
        pass

    # This helper is not directly called; fillet_arc_line is handled
    # inline in generate_define_profile_gcode where the arc endpoint is known.
    return None


def _fillet_arc_line_geom(acz, acx, ar, is_cw, jz, jx, next_end_z, next_end_x, fr):
    """
    Port of ProfileCanvas.Geometry.filletArcLine.
    Returns (t1x, t1z, t2x, t2z, fcx, fcz, anticlockwise) or None.
    """
    d2zr = next_end_z - jz
    d2xr = next_end_x - jx
    d2len = math.hypot(d2zr, d2xr)
    if d2len < 1e-6 or fr < 1e-6 or ar < 1e-6:
        return None
    d2z = d2zr / d2len
    d2x = d2xr / d2len

    rez = jz - acz
    rex = jx - acx
    rlen = math.hypot(rez, rex)
    if rlen < 1e-6:
        return None
    d1z = (-rex if is_cw else rex) / rlen
    d1x = (rez if is_cw else -rez) / rlen

    cross = d1z * d2x - d1x * d2z
    if abs(cross) < 1e-6:
        return None

    n2z = -d2x if cross > 0 else d2x
    n2x = d2z if cross > 0 else -d2z

    dz = jz + fr * n2z - acz
    dx = jx + fr * n2x - acx

    dotd2 = dz * d2z + dx * d2x
    discrim = dotd2 * dotd2 - (dz * dz + dx * dx) + (ar + fr) * (ar + fr)
    if discrim < 0:
        return None

    t = -dotd2 + math.sqrt(discrim)

    fcz = jz + fr * n2z + t * d2z
    fcx = jx + fr * n2x + t * d2x
    t2z = jz + t * d2z
    t2x = jx + t * d2x
    vcz = fcz - acz
    vcx = fcx - acx
    vclen = math.hypot(vcz, vcx)
    if vclen < 1e-6:
        return None

    t1z = acz + ar * vcz / vclen
    t1x = acx + ar * vcx / vclen
    anticlockwise = (cross < 0)
    return t1x, t1z, t2x, t2z, fcx, fcz, anticlockwise


def _fillet_line_arc_geom(start_z, start_x, corner_z, corner_x, arc_cz, arc_cx, arc_r, is_cw, fr):
    """
    Port of ProfileCanvas.Geometry.filletLineArc.
    Returns (t1x, t1z, t2x, t2z, fcx, fcz, anticlockwise) or None.
    """
    if fr < 1e-6 or arc_r < 1e-6:
        return None

    sdz = corner_z - start_z
    sdx = corner_x - start_x
    slen = math.hypot(sdz, sdx)
    if slen < 1e-6:
        return None
    d1z = sdz / slen
    d1x = sdx / slen

    rsz = corner_z - arc_cz
    rsx = corner_x - arc_cx
    rlen = math.hypot(rsz, rsx)
    if rlen < 1e-6:
        return None
    d2z = (-rsx if is_cw else rsx) / rlen
    d2x = (rsz if is_cw else -rsz) / rlen

    cross = d1z * d2x - d1x * d2z
    if abs(cross) < 1e-6:
        return None

    n1z = -d1x if cross > 0 else d1x
    n1x = d1z if cross > 0 else -d1z

    dz = corner_z + fr * n1z - arc_cz
    dx = corner_x + fr * n1x - arc_cx

    dotd1 = dz * d1z + dx * d1x
    discrim = dotd1 * dotd1 - (dz * dz + dx * dx) + (arc_r + fr) * (arc_r + fr)
    if discrim < 0:
        return None

    t = dotd1 + math.sqrt(discrim)

    fcz = corner_z - t * d1z + fr * n1z
    fcx = corner_x - t * d1x + fr * n1x
    t1z = corner_z - t * d1z
    t1x = corner_x - t * d1x
    vcz = fcz - arc_cz
    vcx = fcx - arc_cx
    vclen = math.hypot(vcz, vcx)
    if vclen < 1e-6:
        return None

    t2z = arc_cz + arc_r * vcz / vclen
    t2x = arc_cx + arc_r * vcx / vclen
    anticlockwise = (cross < 0)
    return t1x, t1z, t2x, t2z, fcx, fcz, anticlockwise


def _gcode_from_anticlockwise(anticlockwise):
    # Keep consistent with _json_dir_to_gcode (ccw -> G2).
    return "G2" if anticlockwise else "G3"


def _fillet_gcode_dir(t1x, t1z, t2x, t2z, fcx, fcz):
    """
    Determine G2 or G3 for the fillet arc from T1 to T2 around centre F.
    Uses the cross product to find CW/CCW, then maps to LinuxCNC G18 convention
    (G2 = CW in visual XZ plane, G3 = CCW).
    """
    # Vectors F->T1 and F->T2
    ax, az = t1x - fcx, t1z - fcz
    bx, bz = t2x - fcx, t2z - fcz
    cross = ax * bz - az * bx  # positive = CCW (short path), negative = CW
    # LinuxCNC G18: G2=CW, G3=CCW (visual)
    # The previous mapping produced reversed direction for fillets.
    return 2 if cross > 0 else 3


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

    # Build a list of segments with resolved geometry
    # Each entry: dict with type, coords, gcode_dir (arcs), blend info
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
                "arc_r": float(p.get("arc_radius", 0.0) or 0.0),
                "gcode_dir": _json_dir_to_gcode(p.get("direction", "cw")),
                "blend_type": blend_type,
                "blend_rf": blend_rf,
                "blend_cw": blend_cw,
            })

    if not segs or segs[0]["type"] != "startPoint":
        return []

    # Current tool position
    cx = segs[0]["x"]
    cz = segs[0]["z"]
    body_lines.append(f"G0 X{_f(cx)} Z{_f(cz)}")

    for i in range(1, len(segs)):
        seg = segs[i]
        seg_type = seg["type"]
        blend_type = seg.get("blend_type", "none")
        blend_rf = seg.get("blend_rf", 0.0)

        # Endpoint of this segment (the theoretical corner)
        ex = seg["x_end"]
        ez = seg["z_end"]

        # Outgoing direction of the *next* segment (needed for fillet)
        def _next_tangent(idx, end_x, end_z):
            if idx + 1 >= len(segs):
                return None, None
            nxt = segs[idx + 1]
            if nxt["type"] == "lineTo":
                return _line_direction(end_x, end_z, nxt["x_end"], nxt["z_end"])
            elif nxt["type"] == "arcTo":
                nc = _json_dir_to_gcode(primitives[idx + 1].get("direction", "cw"))
                tx, tz = _arc_tangent_at(end_x, end_z, nxt["x_center"], nxt["z_center"], nc)
                return _normalise(tx, tz)
            return None, None

        if seg_type == "lineTo":
            if blend_type == "fillet" and blend_rf > 0:
                nxt = segs[i + 1] if i + 1 < len(segs) else None

                geo = None
                if nxt and nxt.get("type") == "arcTo":
                    arc_cx = nxt["x_center"]
                    arc_cz = nxt["z_center"]
                    arc_r = nxt.get("arc_r", 0.0) or math.hypot(nxt["x_end"] - arc_cx, nxt["z_end"] - arc_cz)
                    is_cw = (primitives[i + 1].get("direction", "cw") == "cw")
                    geo = _fillet_line_arc_geom(cz, cx, ez, ex, arc_cz, arc_cx, arc_r, is_cw, blend_rf)
                else:
                    # fallback: line-line fillet (same as canvas)
                    nxtp = segs[i + 1] if i + 1 < len(segs) else None
                    if nxtp and nxtp.get("type") == "lineTo":
                        nx = nxtp["x_end"]
                        nz = nxtp["z_end"]
                        fg = _fillet_line_line_qml(cx, cz, ex, ez, nx, nz, blend_rf)
                        geo = fg

                if geo:
                    t1x, t1z, t2x, t2z, fcx, fcz, anticlockwise = geo
                    fi = fcx - t1x
                    fk = fcz - t1z
                    gcmd = _gcode_from_anticlockwise(anticlockwise)
                    body_lines.append(f"G1 X{_f(t1x)} Z{_f(t1z)}")
                    body_lines.append(f"{gcmd} X{_f(t2x)} Z{_f(t2z)} I{_f(fi)} K{_f(fk)}")
                    cx, cz = t2x, t2z
                else:
                    body_lines.append(f"G1 X{_f(ex)} Z{_f(ez)}")
                    cx, cz = ex, ez

            elif blend_type == "chamfer" and blend_cw > 0:
                # Chamfer: insert a short line across the corner
                itx, itz = _line_direction(cx, cz, ex, ez)
                otx, otz = _next_tangent(i, ex, ez)
                cw = seg.get("blend_cw", 0.0)
                if otx is not None and cw > 0:
                    c1x = ex - itx * cw
                    c1z = ez - itz * cw
                    c2x = ex + otx * cw
                    c2z = ez + otz * cw
                    body_lines.append(f"G1 X{_f(c1x)} Z{_f(c1z)}")
                    body_lines.append(f"G1 X{_f(c2x)} Z{_f(c2z)}")
                    cx, cz = c2x, c2z
                else:
                    body_lines.append(f"G1 X{_f(ex)} Z{_f(ez)}")
                    cx, cz = ex, ez
            else:
                body_lines.append(f"G1 X{_f(ex)} Z{_f(ez)}")
                cx, cz = ex, ez

        elif seg_type == "arcTo":
            gdir = seg["gcode_dir"]
            acx, acz = seg["x_center"], seg["z_center"]
            gcmd = "G2" if gdir == 2 else "G3"
            ii = acx - cx
            ik = acz - cz

            if blend_type == "fillet" and blend_rf > 0:
                nxt = segs[i + 1] if i + 1 < len(segs) else None
                geo = None
                if nxt and nxt.get("type") == "lineTo":
                    arc_r = seg.get("arc_r", 0.0) or math.hypot(ex - acx, ez - acz)
                    is_cw = (primitives[i].get("direction", "cw") == "cw")
                    geo = _fillet_arc_line_geom(acz, acx, arc_r, is_cw, ez, ex, nxt["z_end"], nxt["x_end"], blend_rf)

                if geo:
                    t1x, t1z, t2x, t2z, fccx, fccz, anticlockwise = geo
                    ii_arc = acx - cx
                    ik_arc = acz - cz
                    fgcmd = _gcode_from_anticlockwise(anticlockwise)
                    fi = fccx - t1x
                    fk = fccz - t1z
                    body_lines.append(f"{gcmd} X{_f(t1x)} Z{_f(t1z)} I{_f(ii_arc)} K{_f(ik_arc)}")
                    body_lines.append(f"{fgcmd} X{_f(t2x)} Z{_f(t2z)} I{_f(fi)} K{_f(fk)}")
                    cx, cz = t2x, t2z
                else:
                    body_lines.append(f"{gcmd} X{_f(ex)} Z{_f(ez)} I{_f(ii)} K{_f(ik)}")
                    cx, cz = ex, ez
            else:
                body_lines.append(f"{gcmd} X{_f(ex)} Z{_f(ez)} I{_f(ii)} K{_f(ik)}")
                cx, cz = ex, ez

    lines.extend([f"\t{ln}" if ln else "" for ln in body_lines])
    lines.append(f"O{profile_id} ENDSUB")
    return lines
