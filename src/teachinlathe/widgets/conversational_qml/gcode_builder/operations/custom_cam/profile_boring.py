"""CAM-style explicit G-code generator for Profile Boring.

Profile Boring is like Custom Profiling but operates on the bore interior.
Passes go from XStart (current bore diameter) outward toward the profile,
and retract is toward X- (bore centre).

Roughing strategies
-------------------
axially  – step in X (one doc per pass), cut axially in Z at each diameter
radially – step in Z (one doc per pass), cut radially in X at each depth
diagonal – step in Z (one doc per pass), cut at 45° (ΔX = ΔZ)
offset   – generate offset profiles by translating (-n*doc, +n*doc) per pass

cut_toward
----------
interior – the active feed approaches from the bore interior side
exterior – the active feed approaches from the material (outer) side
(not used for offset passes)
"""

import math

from teachinlathe.widgets.conversational_qml.gcode_builder.config import fmt
from teachinlathe.widgets.conversational_qml.gcode_builder.operations.custom_cam.custom_profiling_geometry import (
    build_profile_segments,
    build_render_path,
    find_deepest_z_at_x_path,
)
from teachinlathe.widgets.conversational_qml.gcode_builder.operations.custom_cam.custom_profiling_planner import (
    build_spindle_lines,
    emit_toolpath,
)
from teachinlathe.widgets.conversational_qml.gcode_builder.operations.custom_cam.custom_profiling_types import (
    StartPoint,
    ToolpathArc,
    ToolpathLine,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_float(source, key, default=0.0):
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)


def _parse_config(op):
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    options = op.get("profiling_options", {}) or {}
    strat = op.get("roughing_strategy", {}) or {}

    return {
        "x_start":      _get_float(params,  "x_start",            0.0),
        "z_start":      _get_float(params,  "z_start",            0.0),
        "doc":          _get_float(cutting, "doc",                 0.5),
        "retract":      abs(_get_float(cutting, "retract",         1.0)),
        "feed_rate":    _get_float(cutting, "feed_rate",           0.1),
        "stock_x":      _get_float(options, "stock_to_leave_x",   0.0),
        "stock_z":      _get_float(options, "stock_to_leave_z",   0.0),
        "finish_passes":  max(1, int(options.get("finish_passes",        1) or 1)),
        "spring_passes":  max(0, int(options.get("finish_spring_passes", 0) or 0)),
        "strategy":     str(options.get("strategy",        "rough")).lower(),
        "movement":     str(strat.get("movement",          "axially")).lower(),
        "cut_toward":   str(strat.get("cut_toward",        "interior")).lower(),
        "optional_prefix": "/" if bool(op.get("is_optional_block", False)) else "",
    }


def _resolve_profile(op):
    resolved = op.get("_resolved_profile") or {}
    primitives = resolved.get("profile_primitives", []) or []
    segments = build_profile_segments(primitives)
    path = build_render_path(segments)
    return segments, path


def _boring_extents(segments):
    """Return (x_max, z_min) of the profile for boring pass planning."""
    x_vals, z_vals = [], []
    for seg in segments:
        if isinstance(seg, StartPoint):
            x_vals.append(seg.x)
            z_vals.append(seg.z)
        else:
            x_vals.append(seg.end_x)
            z_vals.append(seg.end_z)
    return (max(x_vals) if x_vals else 0.0), (min(z_vals) if z_vals else 0.0)


def _find_profile_x_at_z(path, target_z, x_shift=0.0, z_shift=0.0):
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
            if z_lo <= target_z <= z_hi:
                cx = element.center_x + x_shift
                cz = element.center_z + z_shift
                r = math.sqrt((current_x - cx) ** 2 + (current_z - cz) ** 2)
                dz = target_z - cz
                if abs(dz) <= r:
                    disc = r ** 2 - dz ** 2
                    for candidate in (cx + math.sqrt(disc), cx - math.sqrt(disc)):
                        x_lo = min(current_x, end_x)
                        x_hi = max(current_x, end_x)
                        if x_lo - 1e-6 <= candidate <= x_hi + 1e-6:
                            candidates.append(candidate)

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



def _find_45deg_profile_intersection(path, start_x, start_z, dir_x, dir_z, x_shift=0.0, z_shift=0.0):
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
            rel_x = start_x - cx
            rel_z = start_z - cz
            a = dir_x * dir_x + dir_z * dir_z
            b = 2.0 * (rel_x * dir_x + rel_z * dir_z)
            radius = math.hypot(current_x - cx, current_z - cz)
            c = rel_x * rel_x + rel_z * rel_z - radius * radius
            disc = b * b - 4.0 * a * c
            if disc >= -1e-9:
                disc = max(0.0, disc)
                root = math.sqrt(disc)
                for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                    if t < -1e-9:
                        continue
                    hit_x = start_x + t * dir_x
                    hit_z = start_z + t * dir_z
                    angle = math.atan2(hit_z - cz, hit_x - cx)
                    start_angle = math.atan2(current_z - cz, current_x - cx)
                    end_angle = math.atan2(end_z - cz, end_x - cx)
                    if _angle_on_arc(angle, start_angle, end_angle, element.anticlockwise):
                        candidates.append((max(0.0, t), hit_x, hit_z))

        current_x, current_z = end_x, end_z

    if not candidates:
        return None
    _, hit_x, hit_z = min(candidates, key=lambda item: item[0])
    return hit_x, hit_z


# ---------------------------------------------------------------------------
# M1 emission
# ---------------------------------------------------------------------------

def _emit_m1_block(lines, m1_params, pfx):
    """Emit optional M1 pause-to-inspect block."""
    if not m1_params:
        return
    if not bool(m1_params.get("include_m1", True)):
        return
    inspect = m1_params.get("inspect_position", "G28")
    if inspect not in ("G28", "G30"):
        inspect = "G28"
    if bool(m1_params.get("stop_spindle", False)):
        lines.append(f"{pfx}M5")
    lines.append(f"{pfx}{inspect}")
    lines.append(f"{pfx}M1")
    lines.append("")


# ---------------------------------------------------------------------------
# Roughing strategies
# ---------------------------------------------------------------------------

def _emit_axial_roughing(lines, config, path, x_safe, x_cut_max):
    """Step in X (one doc per pass), cut axially in Z at each diameter."""
    pfx = config["optional_prefix"]
    x_start = config["x_start"]
    z_start = config["z_start"]
    doc = config["doc"] if config["doc"] > 0 else 0.5
    retract = config["retract"]
    stock_x = config["stock_x"]
    stock_z = config["stock_z"]
    cut_toward = config["cut_toward"]

    if x_cut_max <= x_start:
        lines.append("( Profile Boring axial: nothing to cut – check x_start vs profile )")
        return

    pass_count = max(1, math.ceil((x_cut_max - x_start) / doc))
    x_profile_limit = x_cut_max

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    for n in range(pass_count):
        cut_x = min(x_start + (n + 1) * doc, x_cut_max)
        # Find axial extent at cut_x: x_shift=-stock_x → samples profile at cut_x + stock_x
        cut_z = find_deepest_z_at_x_path(path, cut_x, -stock_x, stock_z)
        exit_x = cut_x - retract
        entry_z = z_start + retract if n == 0 or cut_x < x_profile_limit - 1e-9 else z_start

        if cut_toward == "interior":
            # When the tool is still inside the face profile opening, start from ZStart+clearance.
            # After the cut, retract on a Z-parallel line offset by the same clearance in X.
            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
            lines.append(f"{pfx}G0 X{fmt(cut_x)}")
            lines.append(f"{pfx}G1 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)}")
            lines.append(f"{pfx}G0 Z{fmt(entry_z)}")
            lines.append(f"( DEBUG axial pass {n + 1}/ {pass_count}: cut_x={fmt(cut_x)} cut_z={fmt(cut_z)} entry_z={fmt(entry_z)} exit_x={fmt(exit_x)} )")
        else:
            # Enter from deep end, cut toward ZStart (face)
            # Retract straight in X- (already at face level)
            lines.append(f"{pfx}G0 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(cut_x)}")
            lines.append(f"{pfx}G1 Z{fmt(z_start)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)}")
            lines.append(f"( DEBUG axial pass {n + 1}/ {pass_count}: cut_x={fmt(cut_x)} cut_z={fmt(cut_z)} z_end={fmt(z_start)} exit_x={fmt(exit_x)} )")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")


def _emit_radial_roughing(lines, config, path, x_safe, z_cut_deepest):
    """Step in Z (one doc per pass), cut radially in X at each depth."""
    pfx = config["optional_prefix"]
    x_start = config["x_start"]
    z_start = config["z_start"]
    doc = config["doc"] if config["doc"] > 0 else 0.5
    retract = config["retract"]
    stock_x = config["stock_x"]

    pass_count = max(1, math.ceil((z_start - z_cut_deepest) / doc))

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    for n in range(pass_count):
        cut_z = z_start - (n + 1) * doc
        if cut_z < z_cut_deepest:
            cut_z = z_cut_deepest

        # Profile X at this depth with stock offset (x_shift=-stock_x → profile at cut_x + stock_x)
        cut_x = _find_profile_x_at_z(path, cut_z, -stock_x, 0.0)
        if cut_x <= x_start:
            continue  # no material at this depth yet

        retract_z = cut_z + retract
        retract_x = max(x_start, cut_x - retract)

        # Radial boring roughing always feeds from XStart to the profile boundary,
        # then retracts diagonally and rapids back toward XStart for the next depth.
        lines.append(f"{pfx}G0 Z{fmt(cut_z)}")
        lines.append(f"{pfx}G0 X{fmt(x_start)}")
        lines.append(f"{pfx}G1 X{fmt(cut_x)}")
        lines.append(f"{pfx}G0 X{fmt(retract_x)} Z{fmt(retract_z)}")
        lines.append(f"{pfx}G0 X{fmt(x_start)}")
        lines.append(f"( DEBUG radial pass {n + 1}/ {pass_count}: cut_z={fmt(cut_z)} cut_x={fmt(cut_x)} retract_x={fmt(retract_x)} retract_z={fmt(retract_z)} )")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")


def _emit_diagonal_roughing(lines, config, path, x_safe, x_cut_max, z_cut_deepest):
    """Emit diagonal boring passes while preserving a parallel 45-degree line family."""
    pfx = config["optional_prefix"]
    x_start = config["x_start"]
    z_start = config["z_start"]
    doc = config["doc"] if config["doc"] > 0 else 0.5
    retract = config["retract"]
    stock_x = config["stock_x"]
    stock_z = config["stock_z"]
    cut_toward = config["cut_toward"]

    max_span_x = max(0.0, x_cut_max - x_start)
    max_span_z = max(0.0, z_start - z_cut_deepest)
    max_span = max(max_span_x, max_span_z)
    if max_span <= 1e-9:
        lines.append("( Profile Boring diagonal: nothing to cut – check x_start/profile/depth )")
        return

    pass_count = max(1, math.ceil(max_span / doc))
    last_points = None
    start_z_clear = z_start + retract

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(start_z_clear)}")
    for n in range(pass_count):
        step = min((n + 1) * doc, max_span)
        top_x = x_start + step
        left_z = z_start - step

        if top_x <= x_cut_max + 1e-9:
            start_x = top_x
            start_z = z_start
        else:
            hit = _find_45deg_profile_intersection(
                path, top_x, z_start, -1.0, -1.0, -stock_x, stock_z
            )
            if hit is None:
                continue
            start_x, start_z = hit

        if left_z >= z_cut_deepest - 1e-9:
            end_x = x_start
            end_z = left_z
        else:
            hit = _find_45deg_profile_intersection(
                path, x_start, left_z, 1.0, 1.0, -stock_x, stock_z
            )
            if hit is None:
                continue
            end_x, end_z = hit

        if start_x < x_safe - 1e-9 or end_x < x_safe - 1e-9:
            continue
        if start_z > z_start + 1e-9 or end_z > z_start + 1e-9:
            continue

        points = (round(start_x, 9), round(start_z, 9), round(end_x, 9), round(end_z, 9))
        if points == last_points:
            continue
        last_points = points

        if cut_toward == "interior":
            lines.append(f"{pfx}G0 X{fmt(start_x)}")
            lines.append(f"{pfx}G1 Z{fmt(start_z)}")
            lines.append(f"{pfx}G1 X{fmt(end_x)} Z{fmt(end_z)}")
            lines.append(f"{pfx}G1 X{fmt(end_x - retract)} Z{fmt(end_z)}")
            lines.append(f"{pfx}G0 X{fmt(start_x)} Z{fmt(start_z_clear)}")
            lines.append(f"{pfx}G0 Z{fmt(z_start + retract)}")
            lines.append(f"( DEBUG diagonal1 pass {n + 1}/ {pass_count}: start_x={fmt(start_x)} start_z={fmt(start_z)} end_x={fmt(end_x)} end_z={fmt(end_z)} )")
        else:
            lines.append(f"{pfx}G0 Z{fmt(end_z)}")
            lines.append(f"{pfx}G1 X{fmt(end_x)}")
            lines.append(f"{pfx}G1 X{fmt(start_x)} Z{fmt(start_z)}")
            lines.append(f"{pfx}G0 X{fmt(start_x - retract)} Z{fmt(start_z + retract)}")
            lines.append(f"{pfx}G0 X{fmt(x_safe)}")
            lines.append(f"( DEBUG diagonal2 pass {n + 1}/ {pass_count}: start_x={fmt(start_x)} start_z={fmt(start_z)} end_x={fmt(end_x)} end_z={fmt(end_z)} )")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(start_z_clear)}")
    lines.append("")


# ---------------------------------------------------------------------------
# Offset roughing
# ---------------------------------------------------------------------------

def _find_offset_entry_idx(pts, x_start, z_start):
    """Return the first index where both X >= x_start and Z <= z_start.

    For an offset-shifted boring path this is the entry into the valid
    cutting region (inside bore entrance AND not past face).
    Returns None if no such point exists.
    """
    for i, (x, z) in enumerate(pts):
        if x >= x_start - 1e-9 and z <= z_start + 1e-9:
            return i
    return None


def _find_segment_entry(p1x, p1z, p2x, p2z, x_start, z_start):
    """Return (t, x, z) on line p1→p2 where X>=x_start AND Z<=z_start first become true.

    t is in [0, 1].  Returns None if no such point exists on the segment.
    """
    dx = p2x - p1x
    dz = p2z - p1z
    t_min = 0.0

    if p1x < x_start - 1e-9:
        if abs(dx) < 1e-12:
            return None
        t_x = (x_start - p1x) / dx
        if t_x > 1.0 + 1e-9:
            return None
        t_min = max(t_min, t_x)

    if p1z > z_start + 1e-9:
        if abs(dz) < 1e-12:
            return None
        t_z = (z_start - p1z) / dz
        if t_z > 1.0 + 1e-9:
            return None
        t_min = max(t_min, t_z)

    t_min = min(t_min, 1.0)
    return t_min, p1x + t_min * dx, p1z + t_min * dz


def _emit_offset_roughing(lines, config, path, x_safe, x_cut_max, z_cut_deepest):
    """Offset boring passes: translate profile by (-n*doc, +n*doc) per pass.

    Passes are ordered outermost (n_max) to innermost (n=1).
    Direction is always natural profile direction (Z- and X+).
    cut_toward does not apply to offset passes.
    """
    pfx = config["optional_prefix"]
    x_start = config["x_start"]
    z_start = config["z_start"]
    doc = config["doc"] if config["doc"] > 0 else 0.5
    stock_x = config["stock_x"]
    stock_z = config["stock_z"]

    if x_cut_max <= x_start or not path or len(path) < 2:
        lines.append("( Profile Boring offset: nothing to cut – check x_start vs profile )")
        return

    n_max = max(0, int(min(
        (x_cut_max - x_start) / doc,
        max(0.0, z_start - z_cut_deepest) / doc,
    )))

    if n_max == 0:
        lines.append("( Profile Boring offset: no offset passes needed )")
        return

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")

    for n in range(n_max, 0, -1):
        x_shift = -(n * doc + stock_x)
        z_shift = n * doc + stock_z

        # Build shifted waypoints (one per path element endpoint)
        pts = [(path[0].x + x_shift, path[0].z + z_shift)]
        for elem in path[1:]:
            pts.append((elem.end_x + x_shift, elem.end_z + z_shift))

        entry_idx = _find_offset_entry_idx(pts, x_start, z_start)
        if entry_idx is None or entry_idx >= len(pts) - 1:
            continue

        # Determine actual entry point: may be mid-segment when the previous
        # waypoint was outside the valid region.
        actual_entry_x, actual_entry_z = pts[entry_idx]
        cut_from_idx = entry_idx + 1  # first segment index to emit as G1

        if entry_idx > 0:
            prev_x, prev_z = pts[entry_idx - 1]
            if prev_x < x_start - 1e-9 or prev_z > z_start + 1e-9:
                result = _find_segment_entry(prev_x, prev_z, *pts[entry_idx], x_start, z_start)
                if result is not None:
                    _, actual_entry_x, actual_entry_z = result
                cut_from_idx = entry_idx  # include entry segment itself

        # Approach: axial first (safe X), then radial to entry X
        lines.append(f"{pfx}G0 Z{fmt(actual_entry_z)}")
        lines.append(f"{pfx}G0 X{fmt(actual_entry_x)}")

        # Follow shifted path with exit clipping at X=x_start and Z=z_start
        cur_x, cur_z = actual_entry_x, actual_entry_z
        actual_exit_x, actual_exit_z = cur_x, cur_z
        done = False
        for seg_num in range(cut_from_idx, len(path)):
            if done:
                break
            elem = path[seg_num]
            ex, ez = pts[seg_num]
            in_region = ex >= x_start - 1e-9 and ez <= z_start + 1e-9
            if isinstance(elem, ToolpathLine):
                if in_region:
                    lines.append(f"{pfx}G1 X{fmt(ex)} Z{fmt(ez)}")
                    actual_exit_x, actual_exit_z = ex, ez
                else:
                    # Clip at X=x_start or Z=z_start boundary, whichever comes first
                    dx = ex - cur_x
                    dz = ez - cur_z
                    t_clip = 1.0
                    clip_x, clip_z = ex, ez
                    if ex < x_start - 1e-9 and abs(dx) > 1e-12:
                        t_x = (x_start - cur_x) / dx
                        if 0.0 <= t_x < t_clip:
                            t_clip, clip_x, clip_z = t_x, x_start, cur_z + t_x * dz
                    if ez > z_start + 1e-9 and abs(dz) > 1e-12:
                        t_z = (z_start - cur_z) / dz
                        if 0.0 <= t_z < t_clip:
                            t_clip, clip_x, clip_z = t_z, cur_x + t_z * dx, z_start
                    if t_clip > 1e-9:
                        lines.append(f"{pfx}G1 X{fmt(clip_x)} Z{fmt(clip_z)}")
                        actual_exit_x, actual_exit_z = clip_x, clip_z
                    done = True
            else:  # ToolpathArc
                cx = elem.center_x + x_shift
                cz = elem.center_z + z_shift
                i_val = cx - cur_x
                k_val = cz - cur_z
                cmd = "G2" if elem.anticlockwise else "G3"
                if in_region:
                    lines.append(f"{pfx}{cmd} X{fmt(ex)} Z{fmt(ez)} I{fmt(i_val)} K{fmt(k_val)}")
                    actual_exit_x, actual_exit_z = ex, ez
                else:
                    # Arc exits valid region — skip partial arc, stop here
                    done = True
            cur_x, cur_z = ex, ez

        # 45° retract from actual exit point
        diag_z = actual_exit_z + (actual_exit_x - x_safe)
        lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(diag_z)}")
        lines.append(f"{pfx}G0 Z{fmt(z_start)}")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")


# ---------------------------------------------------------------------------
# Equidistant offset roughing
# ---------------------------------------------------------------------------

def _offset_line_right(sx, sz, ex, ez, d):
    """Offset line segment by d toward bore center (right of traversal direction)."""
    dx, dz = ex - sx, ez - sz
    length = math.hypot(dx, dz)
    if length < 1e-12:
        return sx, sz, ex, ez
    # Right normal of (dx, dz): rotate CW = (dz, -dx) / length
    rx, rz = dz / length, -dx / length
    return sx + d * rx, sz + d * rz, ex + d * rx, ez + d * rz


def _line_line_intersect_dicts(s1, s2):
    """Intersection of infinite lines through s1(sx→ex) and s2(sx→ex). Returns (x,z) or None."""
    d1x, d1z = s1['ex'] - s1['sx'], s1['ez'] - s1['sz']
    d2x, d2z = s2['ex'] - s2['sx'], s2['ez'] - s2['sz']
    denom = d1x * d2z - d1z * d2x
    if abs(denom) < 1e-12:
        return None
    t = ((s2['sx'] - s1['sx']) * d2z - (s2['sz'] - s1['sz']) * d2x) / denom
    u = ((s2['sx'] - s1['sx']) * d1z - (s2['sz'] - s1['sz']) * d1x) / denom
    # If intersection is behind the start of either segment, using it would cause a
    # backward loop in the toolpath.  Return None to let segments connect directly.
    if t < -1e-9 or u < -1e-9:
        return None
    return s1['sx'] + t * d1x, s1['sz'] + t * d1z


def _build_equidistant_offset(path, d):
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
            # Cross product of chord with vector to center.
            # cross > 0 → center on left (CCW-like) → r' = r + d
            # cross < 0 → center on right (CW-like, concave corner) → r' = r - d
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
            pt = _line_line_intersect_dicts(segs[pi], segs[ni])
            if pt:
                segs[pi]['ex'], segs[pi]['ez'] = pt
                segs[ni]['sx'], segs[ni]['sz'] = pt

    # Pass 2: fix line-line corners that aren't already aligned
    for i in range(n - 1):
        if segs[i]['type'] == 'line' and segs[i + 1]['type'] == 'line':
            if abs(segs[i]['ex'] - segs[i + 1]['sx']) > 1e-6 or abs(segs[i]['ez'] - segs[i + 1]['sz']) > 1e-6:
                pt = _line_line_intersect_dicts(segs[i], segs[i + 1])
                if pt:
                    segs[i]['ex'], segs[i]['ez'] = pt
                    segs[i + 1]['sx'], segs[i + 1]['sz'] = pt

    # Build output (skip degenerate arcs)
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


def _emit_equidistant_offset_roughing(lines, config, path, x_safe, x_cut_max, z_cut_deepest):
    """Equidistant offset passes: geometrically offset profile by perpendicular n*doc per pass.

    Fillets shrink as n increases; when radius reaches zero the fillet disappears and the two
    surrounding offset lines meet at a sharp corner instead.
    """
    pfx = config["optional_prefix"]
    x_start = config["x_start"]
    z_start = config["z_start"]
    doc = config["doc"] if config["doc"] > 0 else 0.5
    stock_x = config["stock_x"]

    if x_cut_max <= x_start or not path or len(path) < 2:
        lines.append("( Profile Boring equidistant offset: nothing to cut )")
        return

    n_max = max(0, int(min(
        (x_cut_max - x_start) / doc,
        max(0.0, z_start - z_cut_deepest) / doc,
    )))
    if n_max == 0:
        lines.append("( Profile Boring equidistant offset: no offset passes needed )")
        return

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")

    for n in range(n_max, 0, -1):
        offset_d = n * doc + stock_x

        op = _build_equidistant_offset(path, offset_d)
        if len(op) < 2:
            continue

        # Build flat (x, z) list for entry search
        pts = [(item[1], item[2]) for item in op]

        entry_idx = _find_offset_entry_idx(pts, x_start, z_start)
        if entry_idx is None or entry_idx >= len(pts) - 1:
            continue

        actual_entry_x, actual_entry_z = pts[entry_idx]
        cut_from_idx = entry_idx + 1

        if entry_idx > 0:
            prev_x, prev_z = pts[entry_idx - 1]
            if prev_x < x_start - 1e-9 or prev_z > z_start + 1e-9:
                if op[entry_idx][0] == 'line':
                    result = _find_segment_entry(prev_x, prev_z, *pts[entry_idx], x_start, z_start)
                    if result is not None:
                        _, actual_entry_x, actual_entry_z = result
                cut_from_idx = entry_idx

        lines.append(f"{pfx}G0 Z{fmt(actual_entry_z)}")
        lines.append(f"{pfx}G0 X{fmt(actual_entry_x)}")

        cur_x, cur_z = actual_entry_x, actual_entry_z
        actual_exit_x, actual_exit_z = cur_x, cur_z
        done = False

        for ii in range(cut_from_idx, len(op)):
            if done:
                break
            item = op[ii]
            if item[0] == 'start':
                continue
            ex, ez = item[1], item[2]
            in_region = ex >= x_start - 1e-9 and ez <= z_start + 1e-9

            if item[0] == 'line':
                if in_region:
                    lines.append(f"{pfx}G1 X{fmt(ex)} Z{fmt(ez)}")
                    actual_exit_x, actual_exit_z = ex, ez
                else:
                    dx, dz = ex - cur_x, ez - cur_z
                    t_clip, clip_x, clip_z = 1.0, ex, ez
                    if ex < x_start - 1e-9 and abs(dx) > 1e-12:
                        t_x = (x_start - cur_x) / dx
                        if 0.0 <= t_x < t_clip:
                            t_clip, clip_x, clip_z = t_x, x_start, cur_z + t_x * dz
                    if ez > z_start + 1e-9 and abs(dz) > 1e-12:
                        t_z = (z_start - cur_z) / dz
                        if 0.0 <= t_z < t_clip:
                            t_clip, clip_x, clip_z = t_z, cur_x + t_z * dx, z_start
                    if t_clip > 1e-9:
                        lines.append(f"{pfx}G1 X{fmt(clip_x)} Z{fmt(clip_z)}")
                        actual_exit_x, actual_exit_z = clip_x, clip_z
                    done = True
            else:  # arc
                cx_a, cz_a, ccw = item[3], item[4], item[5]
                i_val, k_val = cx_a - cur_x, cz_a - cur_z
                cmd = "G2" if ccw else "G3"
                if in_region:
                    lines.append(f"{pfx}{cmd} X{fmt(ex)} Z{fmt(ez)} I{fmt(i_val)} K{fmt(k_val)}")
                    actual_exit_x, actual_exit_z = ex, ez
                else:
                    done = True
            cur_x, cur_z = ex, ez

        diag_z = actual_exit_z + (actual_exit_x - x_safe)
        lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(diag_z)}")
        lines.append(f"{pfx}G0 Z{fmt(z_start)}")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")


# ---------------------------------------------------------------------------
# Contour and finish passes
# ---------------------------------------------------------------------------

def _emit_boring_contour_pass(lines, config, path, x_safe, x_profile_start):
    """Contour pass at end of roughing: follow profile minus stock offsets."""
    pfx = config["optional_prefix"]
    stock_x = config["stock_x"]
    stock_z = config["stock_z"]
    z_start = config["z_start"]

    # For boring: shift path inward by stock_x (negative x offset)
    entry_x = x_profile_start - stock_x
    lines.append(f"( boring contour pass: stock_x={fmt(stock_x)} stock_z={fmt(stock_z)} )")
    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append(f"{pfx}G0 X{fmt(entry_x)}")
    emit_toolpath(lines, pfx, path, -stock_x, stock_z)
    lines.append(f"{pfx}G0 X{fmt(x_safe)}")
    lines.append(f"{pfx}G0 Z{fmt(z_start)}")
    lines.append("")


def _emit_boring_finish_gcode(lines, config, path, x_safe, x_profile_start):
    """Finish passes: follow profile from (stock offset) down to zero offset."""
    pfx = config["optional_prefix"]
    stock_x = config["stock_x"]
    stock_z = config["stock_z"]
    z_start = config["z_start"]

    passes = []
    for i in range(1, config["finish_passes"] + 1):
        factor = (config["finish_passes"] - i) / config["finish_passes"]
        passes.append((-stock_x * factor, stock_z * factor))
    for _ in range(config["spring_passes"]):
        passes.append((0.0, 0.0))

    for offset_x, offset_z in passes:
        entry_x = x_profile_start + offset_x
        lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
        lines.append(f"{pfx}G0 X{fmt(entry_x)}")
        emit_toolpath(lines, pfx, path, offset_x, offset_z)
    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_profile_boring_gcode(op):
    config = _parse_config(op)
    spindle = op.get("spindle_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}
    segments, render_path = _resolve_profile(op)

    lines = []
    lines.extend(build_spindle_lines(spindle, config["optional_prefix"], _get_float))
    lines.append(f"{config['optional_prefix']}G95 F{config['feed_rate']}")

    if not segments or not isinstance(segments[0], StartPoint):
        lines.append("( ERROR: Profile Boring -- no valid profile found )")
        return lines

    x_profile_start = segments[0].x
    x_max, z_min = _boring_extents(segments)
    x_safe = config["x_start"] - config["retract"]

    # Clamp stock so we don't overshoot
    x_cut_max = x_max - config["stock_x"]
    z_cut_deepest = z_min + config["stock_z"]

    pfx = config["optional_prefix"]

    if config["strategy"] == "rough":
        movement = config["movement"]
        if movement == "axially":
            _emit_axial_roughing(lines, config, render_path, x_safe, x_cut_max)
        elif movement == "radially":
            _emit_radial_roughing(lines, config, render_path, x_safe, z_cut_deepest)
        elif movement == "offset":
            _emit_offset_roughing(lines, config, render_path, x_safe, x_cut_max, z_cut_deepest)
        elif movement == "equidistant_offset":
            _emit_equidistant_offset_roughing(lines, config, render_path, x_safe, x_cut_max, z_cut_deepest)
        else:  # diagonal / 45°
            _emit_diagonal_roughing(lines, config, render_path, x_safe, x_cut_max, z_cut_deepest)

        _emit_boring_contour_pass(lines, config, render_path, x_safe, x_profile_start)
        _emit_m1_block(lines, m1_params, pfx)
        return lines

    # strategy == "finish"
    _emit_m1_block(lines, m1_params, pfx)
    _emit_boring_finish_gcode(lines, config, render_path, x_safe, x_profile_start)
    return lines
