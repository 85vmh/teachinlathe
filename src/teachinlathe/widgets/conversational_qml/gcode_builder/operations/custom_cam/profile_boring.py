"""CAM-style explicit G-code generator for Profile Boring.

Profile Boring is like Custom Profiling but operates on the bore interior.
Passes go from XStart (current bore diameter) outward toward the profile,
and retract is toward X- (bore centre).

Roughing strategies
-------------------
axially  – step in X (one doc per pass), cut axially in Z at each diameter
radially – step in Z (one doc per pass), cut radially in X at each depth
diagonal – step in Z (one doc per pass), cut at 45° (ΔX = ΔZ)

cut_toward
----------
interior – the active feed approaches from the bore interior side
exterior – the active feed approaches from the material (outer) side
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

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    for n in range(pass_count):
        cut_x = min(x_start + (n + 1) * doc, x_cut_max)
        # Find axial extent at cut_x: x_shift=-stock_x → samples profile at cut_x + stock_x
        cut_z = find_deepest_z_at_x_path(path, cut_x, -stock_x, stock_z)
        exit_x = cut_x - retract

        if cut_toward == "interior":
            # Enter from ZStart (face), cut axially toward Z-
            # Retract at 45° (X- and Z+ simultaneously) then straight to ZStart
            retract_z = cut_z + retract
            lines.append(f"{pfx}G0 X{fmt(cut_x)}")
            lines.append(f"{pfx}G1 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)} Z{fmt(retract_z)}")
            lines.append(f"{pfx}G0 Z{fmt(z_start)}")
        else:
            # Enter from deep end, cut toward ZStart (face)
            # Retract straight in X- (already at face level)
            lines.append(f"{pfx}G0 Z{fmt(cut_z)}")
            lines.append(f"{pfx}G0 X{fmt(cut_x)}")
            lines.append(f"{pfx}G1 Z{fmt(z_start)}")
            lines.append(f"{pfx}G0 X{fmt(exit_x)}")

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

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")


def _emit_diagonal_roughing(lines, config, path, x_safe, x_cut_max, z_cut_deepest):
    """Emit diagonal boring passes following the explicit plunge-cut-retract cycle."""
    pfx = config["optional_prefix"]
    x_start = config["x_start"]
    z_start = config["z_start"]
    doc = config["doc"] if config["doc"] > 0 else 0.5
    retract = config["retract"]
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
        face_x = min(x_start + step, x_cut_max)
        deep_z = max(z_start - step, z_cut_deepest)
        points = (face_x, deep_z)
        if points == last_points:
            continue
        last_points = points

        if cut_toward == "interior":
            lines.append(f"{pfx}G0 X{fmt(face_x)}")
            lines.append(f"{pfx}G1 Z{fmt(z_start)}")
            lines.append(f"{pfx}G1 X{fmt(x_start)} Z{fmt(deep_z)}")
            lines.append(f"{pfx}G0 X{fmt(x_start + retract)} Z{fmt(deep_z + retract)}")
            lines.append(f"{pfx}G0 Z{fmt(z_start)}")
        else:
            lines.append(f"{pfx}G0 Z{fmt(deep_z)}")
            lines.append(f"{pfx}G1 X{fmt(x_start)}")
            lines.append(f"{pfx}G1 X{fmt(face_x)} Z{fmt(z_start)}")
            lines.append(f"{pfx}G0 X{fmt(face_x - retract)} Z{fmt(z_start + retract)}")
            lines.append(f"{pfx}G0 X{fmt(x_safe)}")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(start_z_clear)}")
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
        else:  # diagonal / 45°
            _emit_diagonal_roughing(lines, config, render_path, x_safe, x_cut_max, z_cut_deepest)

        _emit_boring_contour_pass(lines, config, render_path, x_safe, x_profile_start)
        _emit_m1_block(lines, m1_params, pfx)
        return lines

    # strategy == "finish"
    _emit_m1_block(lines, m1_params, pfx)
    _emit_boring_finish_gcode(lines, config, render_path, x_safe, x_profile_start)
    return lines
