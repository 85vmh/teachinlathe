"""CAM-style explicit G-code generator for Custom Profiling.

Generates Z-parallel roughing passes and exact profile finishing passes
using explicit G0/G1/G2/G3 moves — no G71/G70 canned cycles.
"""

import math
from ..config import fmt


def _get_float(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def _json_dir_to_gcode(direction_str):
    """JSON 'ccw' -> G2, 'cw' -> G3."""
    return 2 if str(direction_str).lower() == "ccw" else 3


def _build_segs(primitives):
    """Convert raw primitive dicts to normalised segment dicts."""
    segs = []
    for p in (primitives or []):
        t = p.get("type", "")
        if t == "startPoint":
            segs.append({
                "type": "startPoint",
                "x": float(p.get("x_start", 0)),
                "z": float(p.get("z_start", 0)),
            })
        elif t == "lineTo":
            blend = p.get("blend") or {}
            segs.append({
                "type": "lineTo",
                "x_end": float(p.get("x_end", 0)),
                "z_end": float(p.get("z_end", 0)),
                "blend_type": blend.get("type", "none"),
                "blend_rf": float(blend.get("fillet_radius", 0.0) or 0.0),
                "blend_cw": float(blend.get("chamfer_width", 0.0) or 0.0),
            })
        elif t == "arcTo":
            blend = p.get("blend") or {}
            x_end = float(p.get("x_end", 0))
            z_end = float(p.get("z_end", 0))
            x_center = float(p.get("x_center", 0))
            z_center = float(p.get("z_center", 0))
            segs.append({
                "type": "arcTo",
                "x_end": x_end,
                "z_end": z_end,
                "x_center": x_center,
                "z_center": z_center,
                "arc_radius": math.sqrt((x_end - x_center) ** 2 + (z_end - z_center) ** 2),
                "gcode_dir": _json_dir_to_gcode(p.get("direction", "cw")),
                "blend_type": blend.get("type", "none"),
                "blend_rf": float(blend.get("fillet_radius", 0.0) or 0.0),
                "blend_cw": float(blend.get("chamfer_width", 0.0) or 0.0),
            })
    return segs


def _profile_extents(segs):
    """Return (x_min, z_end) from the segment list."""
    x_vals = []
    z_end = 0.0
    for s in segs:
        t = s["type"]
        if t == "startPoint":
            x_vals.append(s["x"])
            z_end = s["z"]
        elif t in ("lineTo", "arcTo"):
            x_vals.append(s["x_end"])
            z_end = s["z_end"]
    x_min = min(x_vals) if x_vals else 0.0
    return x_min, z_end


def _find_z_at_x(segs, x_target):
    """Return the deepest Z coordinate on the profile at x_target.

    For LineTo segments, linear interpolation is used.
    For ArcTo segments, valid circle intersections on the swept arc are considered.
    Falls back to z_end of the profile if no intersection found.
    """
    prev_x = segs[0]["x"] if segs and segs[0]["type"] == "startPoint" else 0.0
    prev_z = segs[0]["z"] if segs and segs[0]["type"] == "startPoint" else 0.0
    z_end = prev_z
    candidates = []

    for seg in segs[1:]:
        t = seg["type"]
        ex = seg["x_end"]
        ez = seg["z_end"]
        z_end = ez
        x_lo = min(prev_x, ex)
        x_hi = max(prev_x, ex)

        if t == "lineTo":
            if abs(ex - prev_x) > 1e-9:
                if x_lo <= x_target <= x_hi:
                    z = prev_z + (x_target - prev_x) * (ez - prev_z) / (ex - prev_x)
                    candidates.append(z)
            else:
                if abs(x_target - prev_x) < 1e-6:
                    candidates.append(min(prev_z, ez))

        elif t == "arcTo":
            if x_lo <= x_target <= x_hi:
                cx = seg["x_center"]
                cz = seg["z_center"]
                r = math.sqrt((ex - cx) ** 2 + (ez - cz) ** 2)
                dx = x_target - cx
                if abs(dx) <= r:
                    discriminant = r ** 2 - dx ** 2
                    z_plus = cz + math.sqrt(discriminant)
                    z_minus = cz - math.sqrt(discriminant)
                    # Pick the Z that lies between prev_z and ez (on the arc)
                    z_lo = min(prev_z, ez)
                    z_hi = max(prev_z, ez)
                    for zc in (z_plus, z_minus):
                        if z_lo - 1e-6 <= zc <= z_hi + 1e-6:
                            candidates.append(zc)

        prev_x, prev_z = ex, ez

    if candidates:
        return min(candidates)

    return z_end


def _find_z_at_x_path(path, x_target, x_shift=0.0, z_shift=0.0):
    """Return the deepest Z coordinate on an emitted path at x_target."""
    if not path:
        return 0.0

    prev_x = path[0]["x"] + x_shift
    prev_z = path[0]["z"] + z_shift
    z_end = prev_z
    candidates = []

    for seg in path[1:]:
        ex = seg["x"] + x_shift
        ez = seg["z"] + z_shift
        z_end = ez
        x_lo = min(prev_x, ex)
        x_hi = max(prev_x, ex)

        if seg["type"] == "line":
            if abs(ex - prev_x) > 1e-9:
                if x_lo <= x_target <= x_hi:
                    z = prev_z + (x_target - prev_x) * (ez - prev_z) / (ex - prev_x)
                    candidates.append(z)
            else:
                if abs(x_target - prev_x) < 1e-6:
                    candidates.append(min(prev_z, ez))

        elif seg["type"] == "arc":
            if x_lo <= x_target <= x_hi:
                cx = seg["xc"] + x_shift
                cz = seg["zc"] + z_shift
                r = math.sqrt((prev_x - cx) ** 2 + (prev_z - cz) ** 2)
                dx = x_target - cx
                if abs(dx) <= r:
                    disc = r ** 2 - dx ** 2
                    z_plus = cz + math.sqrt(disc)
                    z_minus = cz - math.sqrt(disc)
                    z_lo = min(prev_z, ez)
                    z_hi = max(prev_z, ez)
                    for zc in (z_plus, z_minus):
                        if z_lo - 1e-6 <= zc <= z_hi + 1e-6:
                            candidates.append(zc)

        prev_x, prev_z = ex, ez

    if candidates:
        return min(candidates)
    return z_end


def _spindle_lines(spindle, line_prefix):
    mode = spindle.get("mode", None)
    direction = spindle.get("direction", None)
    rpm_value = _get_float(spindle, "rpm_value", 0.0)
    css_value = _get_float(spindle, "css_value", 0.0)
    css_max = _get_float(spindle, "css_max_speed", 0.0)

    parts = []
    if str(mode).lower() == "rpm":
        parts.append("G97")
    elif str(mode).lower() == "css":
        parts.append("G96")

    if direction == -1:
        parts.append("M4")
    elif direction == 1:
        parts.append("M3")

    if str(mode).lower() == "rpm":
        parts.append(f"S{rpm_value}")
    elif str(mode).lower() == "css":
        parts.append(f"S{css_value} D{css_max}")

    lines = []
    if parts:
        lines.append(f"{line_prefix}{' '.join(parts)}")
    return lines


def _next_seg(segs, i):
    if i + 1 < len(segs):
        return segs[i + 1]
    return None


def _fillet_line_line(start_x, start_z, corner_x, corner_z, next_seg, fr):
    if not next_seg or next_seg["type"] != "lineTo":
        return None
    sdx = corner_x - start_x
    sdz = corner_z - start_z
    slen = math.sqrt(sdx ** 2 + sdz ** 2)
    if slen < 0.001 or fr < 0.001:
        return None

    ndx = next_seg["x_end"] - corner_x
    ndz = next_seg["z_end"] - corner_z
    nlen = math.sqrt(ndx ** 2 + ndz ** 2)
    if nlen < 0.001:
        return None

    d1x = sdx / slen
    d1z = sdz / slen
    d2x = ndx / nlen
    d2z = ndz / nlen
    cross = d1z * d2x - d1x * d2z
    dot = d1z * d2z + d1x * d2x
    if abs(cross) < 0.001:
        return None

    t = fr * (1.0 - dot) / abs(cross)
    t1x = corner_x - t * d1x
    t1z = corner_z - t * d1z
    t2x = corner_x + t * d2x
    t2z = corner_z + t * d2z

    perp_x = d1z if cross > 0 else -d1z
    perp_z = -d1x if cross > 0 else d1x
    return {
        "t1x": t1x,
        "t1z": t1z,
        "t2x": t2x,
        "t2z": t2z,
        "fcx": t1x + fr * perp_x,
        "fcz": t1z + fr * perp_z,
        "anticlockwise": cross < 0,
    }


def _fillet_arc_line(acx, acz, ar, is_cw, jx, jz, next_seg, fr):
    if not next_seg or next_seg["type"] != "lineTo":
        return None
    d2x_raw = next_seg["x_end"] - jx
    d2z_raw = next_seg["z_end"] - jz
    d2len = math.sqrt(d2x_raw ** 2 + d2z_raw ** 2)
    if d2len < 0.001 or fr < 0.001 or ar < 0.001:
        return None
    d2x = d2x_raw / d2len
    d2z = d2z_raw / d2len

    rex = jx - acx
    rez = jz - acz
    rlen = math.sqrt(rex ** 2 + rez ** 2)
    if rlen < 0.001:
        return None
    d1x = (rez if is_cw else -rez) / rlen
    d1z = (-rex if is_cw else rex) / rlen

    cross = d1z * d2x - d1x * d2z
    if abs(cross) < 0.001:
        return None

    n2x = d2z if cross > 0 else -d2z
    n2z = -d2x if cross > 0 else d2x
    dx = jx + fr * n2x - acx
    dz = jz + fr * n2z - acz

    dot_d2 = dz * d2z + dx * d2x
    discrim = dot_d2 ** 2 - (dz ** 2 + dx ** 2) + (ar + fr) ** 2
    if discrim < 0:
        return None

    t = -dot_d2 + math.sqrt(discrim)
    fcx = jx + fr * n2x + t * d2x
    fcz = jz + fr * n2z + t * d2z
    t2x = jx + t * d2x
    t2z = jz + t * d2z
    vcx = fcx - acx
    vcz = fcz - acz
    vclen = math.sqrt(vcx ** 2 + vcz ** 2)
    if vclen < 0.001:
        return None

    return {
        "t1x": acx + ar * vcx / vclen,
        "t1z": acz + ar * vcz / vclen,
        "t2x": t2x,
        "t2z": t2z,
        "fcx": fcx,
        "fcz": fcz,
        "anticlockwise": cross < 0,
    }


def _fillet_line_arc(start_x, start_z, corner_x, corner_z, next_arc, fr):
    if not next_arc or next_arc["type"] != "arcTo":
        return None
    is_cw = next_arc["gcode_dir"] != 2
    acx = next_arc["x_center"]
    acz = next_arc["z_center"]
    ar = next_arc["arc_radius"]
    if fr < 0.001 or ar < 0.001:
        return None

    sdx = corner_x - start_x
    sdz = corner_z - start_z
    slen = math.sqrt(sdx ** 2 + sdz ** 2)
    if slen < 0.001:
        return None
    d1x = sdx / slen
    d1z = sdz / slen

    rsx = corner_x - acx
    rsz = corner_z - acz
    rlen = math.sqrt(rsx ** 2 + rsz ** 2)
    if rlen < 0.001:
        return None
    d2x = (rsz if is_cw else -rsz) / rlen
    d2z = (-rsx if is_cw else rsx) / rlen

    cross = d1z * d2x - d1x * d2z
    if abs(cross) < 0.001:
        return None

    n1x = d1z if cross > 0 else -d1z
    n1z = -d1x if cross > 0 else d1x
    dx = corner_x + fr * n1x - acx
    dz = corner_z + fr * n1z - acz

    dot_d1 = dz * d1z + dx * d1x
    discrim = dot_d1 ** 2 - (dz ** 2 + dx ** 2) + (ar + fr) ** 2
    if discrim < 0:
        return None

    t = dot_d1 + math.sqrt(discrim)
    fcx = corner_x - t * d1x + fr * n1x
    fcz = corner_z - t * d1z + fr * n1z
    t1x = corner_x - t * d1x
    t1z = corner_z - t * d1z
    vcx = fcx - acx
    vcz = fcz - acz
    vclen = math.sqrt(vcx ** 2 + vcz ** 2)
    if vclen < 0.001:
        return None

    return {
        "t1x": t1x,
        "t1z": t1z,
        "t2x": acx + ar * vcx / vclen,
        "t2z": acz + ar * vcz / vclen,
        "fcx": fcx,
        "fcz": fcz,
        "anticlockwise": cross < 0,
    }


def _chamfer_line(log_x, log_z, ex, ez, next_seg, cw):
    sdx = ex - log_x
    sdz = ez - log_z
    slen = math.sqrt(sdx ** 2 + sdz ** 2)
    if slen < 0.001 or cw < 0.001:
        return None
    csx = ex - cw * sdx / slen
    csz = ez - cw * sdz / slen
    cex = ex
    cez = ez

    if next_seg and next_seg["type"] == "lineTo":
        ndx = next_seg["x_end"] - ex
        ndz = next_seg["z_end"] - ez
        nlen = math.sqrt(ndx ** 2 + ndz ** 2)
        if nlen > 0.001:
            cex = ex + cw * ndx / nlen
            cez = ez + cw * ndz / nlen
    elif next_seg and next_seg["type"] == "arcTo":
        nrx = ex - next_seg["x_center"]
        nrz = ez - next_seg["z_center"]
        nndx = nrz if next_seg["gcode_dir"] != 2 else -nrz
        nndz = -nrx if next_seg["gcode_dir"] != 2 else nrx
        nlen2 = math.sqrt(nndx ** 2 + nndz ** 2)
        if nlen2 > 0.001:
            cex = ex + cw * nndx / nlen2
            cez = ez + cw * nndz / nlen2
    return {"csx": csx, "csz": csz, "cex": cex, "cez": cez}


def _chamfer_arc(acx, acz, ar, is_cw, aex, aez, next_seg, cw):
    arex = aex - acx
    arez = aez - acz
    arlen = math.sqrt(arex ** 2 + arez ** 2)
    if arlen < 0.001 or cw < 0.001:
        return None
    atdx = arez if is_cw else -arez
    atdz = -arex if is_cw else arex
    csx = aex - cw * atdx / arlen
    csz = aez - cw * atdz / arlen
    cex = aex
    cez = aez
    if next_seg and next_seg["type"] == "lineTo":
        andx = next_seg["x_end"] - aex
        andz = next_seg["z_end"] - aez
        anlen = math.sqrt(andx ** 2 + andz ** 2)
        if anlen > 0.001:
            cex = aex + cw * andx / anlen
            cez = aez + cw * andz / anlen
    return {"csx": csx, "csz": csz, "cex": cex, "cez": cez}


def _build_render_path(segs):
    path = []
    if not segs:
        return path

    log_x = 0.0
    log_z = 0.0
    for i, seg in enumerate(segs):
        if seg["type"] == "startPoint":
            log_x = seg["x"]
            log_z = seg["z"]
            path.append({"type": "move", "x": log_x, "z": log_z})
            continue

        next_seg = _next_seg(segs, i)
        if seg["type"] == "lineTo":
            ex = seg["x_end"]
            ez = seg["z_end"]
            if seg.get("blend_type") == "chamfer":
                cg = _chamfer_line(log_x, log_z, ex, ez, next_seg, seg.get("blend_cw", 0.0))
                if cg:
                    path.append({"type": "line", "x": cg["csx"], "z": cg["csz"]})
                    path.append({"type": "line", "x": cg["cex"], "z": cg["cez"]})
                else:
                    path.append({"type": "line", "x": ex, "z": ez})
            elif seg.get("blend_type") == "fillet":
                fr = seg.get("blend_rf", 0.0)
                fg = _fillet_line_arc(log_x, log_z, ex, ez, next_seg, fr) if next_seg and next_seg["type"] == "arcTo" else _fillet_line_line(log_x, log_z, ex, ez, next_seg, fr)
                if fg:
                    path.append({"type": "line", "x": fg["t1x"], "z": fg["t1z"]})
                    path.append({"type": "arc", "x": fg["t2x"], "z": fg["t2z"], "xc": fg["fcx"], "zc": fg["fcz"], "anticlockwise": fg["anticlockwise"]})
                else:
                    path.append({"type": "line", "x": ex, "z": ez})
            else:
                path.append({"type": "line", "x": ex, "z": ez})
            log_x = ex
            log_z = ez
            continue

        if seg["type"] == "arcTo":
            ex = seg["x_end"]
            ez = seg["z_end"]
            is_cw = seg["gcode_dir"] != 2
            if seg.get("blend_type") == "chamfer":
                cg = _chamfer_arc(seg["x_center"], seg["z_center"], seg["arc_radius"], is_cw, ex, ez, next_seg, seg.get("blend_cw", 0.0))
                if cg:
                    path.append({"type": "arc", "x": cg["csx"], "z": cg["csz"], "xc": seg["x_center"], "zc": seg["z_center"], "anticlockwise": not is_cw})
                    path.append({"type": "line", "x": cg["cex"], "z": cg["cez"]})
                else:
                    path.append({"type": "arc", "x": ex, "z": ez, "xc": seg["x_center"], "zc": seg["z_center"], "anticlockwise": not is_cw})
            elif seg.get("blend_type") == "fillet":
                fr = seg.get("blend_rf", 0.0)
                fg = _fillet_arc_line(seg["x_center"], seg["z_center"], seg["arc_radius"], is_cw, ex, ez, next_seg, fr)
                if fg:
                    path.append({"type": "arc", "x": fg["t1x"], "z": fg["t1z"], "xc": seg["x_center"], "zc": seg["z_center"], "anticlockwise": not is_cw})
                    path.append({"type": "arc", "x": fg["t2x"], "z": fg["t2z"], "xc": fg["fcx"], "zc": fg["fcz"], "anticlockwise": fg["anticlockwise"]})
                else:
                    path.append({"type": "arc", "x": ex, "z": ez, "xc": seg["x_center"], "zc": seg["z_center"], "anticlockwise": not is_cw})
            else:
                path.append({"type": "arc", "x": ex, "z": ez, "xc": seg["x_center"], "zc": seg["z_center"], "anticlockwise": not is_cw})
            log_x = ex
            log_z = ez
    return path


def _emit_path(lines, lp, path, x_shift=0.0, z_shift=0.0):
    if not path:
        return
    cx = path[0]["x"] + x_shift
    cz = path[0]["z"] + z_shift
    for seg in path[1:]:
        ex = seg["x"] + x_shift
        ez = seg["z"] + z_shift
        if seg["type"] == "line":
            lines.append(f"{lp}G1 X{fmt(ex)} Z{fmt(ez)}")
        elif seg["type"] == "arc":
            gcmd = "G2" if seg["anticlockwise"] else "G3"
            ii = seg["xc"] + x_shift - cx
            ik = seg["zc"] + z_shift - cz
            lines.append(f"{lp}{gcmd} X{fmt(ex)} Z{fmt(ez)} I{fmt(ii)} K{fmt(ik)}")
        cx, cz = ex, ez


def generate_custom_profiling_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    lp = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    options = op.get("profiling_options", {}) or {}

    x_start = _get_float(params, "x_start", 0.0)
    z_start = _get_float(params, "z_start", 0.0)
    doc = _get_float(cutting, "doc", 0.5)
    retract = _get_float(cutting, "retract", 1.0)
    feed_rate = _get_float(cutting, "feed_rate", 0.1)
    stock_x = _get_float(options, "stock_to_leave_x", 0.0)
    stock_z = _get_float(options, "stock_to_leave_z", 0.0)
    finish_passes = max(1, int(options.get("finish_passes", 1) or 1))
    spring_passes = int(options.get("finish_spring_passes", 0) or 0)
    strategy = str(options.get("strategy", "rough")).lower()

    resolved = op.get("_resolved_profile") or {}
    primitives = resolved.get("profile_primitives", []) or []
    segs = _build_segs(primitives)
    render_path = _build_render_path(segs)

    lines = []
    lines.extend(_spindle_lines(spindle, lp))
    lines.append(f"{lp}G95 F{feed_rate}")

    if not segs or segs[0]["type"] != "startPoint":
        lines.append("( ERROR: Custom Profiling -- no valid profile found )")
        return lines

    x_profile_start = segs[0]["x"]
    x_min, _ = _profile_extents(segs)
    x_safe = x_start + retract

    if strategy == "rough":
        x_cut_min = x_min + stock_x
        if doc <= 0:
            doc = 0.5
        n_passes = max(1, math.ceil((x_start - x_cut_min) / doc))

        # Initial safe position
        lines.append(f"{lp}G0 X{fmt(x_safe)} Z{fmt(z_start)}")

        for i in range(n_passes):
            x_current = max(x_start - (i + 1) * doc, x_cut_min)
            z_stop = _find_z_at_x_path(render_path, x_current, stock_x, stock_z)
            x_exit = x_current + abs(retract)
            # Exit toward z_start (face), regardless of Z sign convention or retract sign
            z_exit = z_stop + math.copysign(abs(retract), z_start - z_stop)

            lines.append(f"{lp}G0 X{fmt(x_current)}")                 # approach X only
            lines.append(f"{lp}G1 Z{fmt(z_stop)}")                    # Z-parallel cut
            lines.append(f"{lp}G0 X{fmt(x_exit)} Z{fmt(z_exit)}")     # 45-degree exit
            lines.append(f"{lp}G0 Z{fmt(z_start)}")                   # rapid Z back

        # Move to safe X before contour
        lines.append(f"{lp}G0 X{fmt(x_safe)}")
        lines.append("")

        # Semi-finish contour pass following profile at stock-to-leave offsets
        lines.append(f"( contour pass: stock_x={fmt(stock_x)} stock_z={fmt(stock_z)} )")
        lines.append(f"{lp}G0 X{fmt(x_profile_start + stock_x)} Z{fmt(z_start)}")
        _emit_path(lines, lp, render_path, stock_x, stock_z)

        lines.append(f"{lp}G0 X{fmt(x_safe)} Z{fmt(z_start)}")

    else:
        # Finishing: remove the roughing allowance in equal finish increments.
        finish_offsets = []
        for pass_index in range(1, finish_passes + 1):
            factor = (finish_passes - pass_index) / finish_passes
            finish_offsets.append((stock_x * factor, stock_z * factor))
        finish_offsets.extend([(0.0, 0.0)] * spring_passes)

        for x_shift, z_shift in finish_offsets:
            lines.append(f"{lp}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
            lines.append(f"{lp}G0 X{fmt(x_profile_start + x_shift)} Z{fmt(z_start)}")
            _emit_path(lines, lp, render_path, x_shift, z_shift)

        lines.append(f"{lp}G0 X{fmt(x_safe)} Z{fmt(z_start)}")

    return lines
