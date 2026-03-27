from teachinlathe.conversational.data_types import BoringConfig

from ....config import fmt
from ..custom_profiling_geometry import build_equidistant_offset
from . import find_offset_entry_idx, find_segment_entry


def emit_equidistant_offset_roughing(lines: list, config: BoringConfig, path: list, x_safe: float, x_cut_max: float, z_cut_deepest: float):
    """Equidistant offset passes: geometrically offset profile by perpendicular n*doc per pass.

    Fillets shrink as n increases; when radius reaches zero the fillet disappears and the two
    surrounding offset lines meet at a sharp corner instead.
    """
    pfx = config.optional_prefix
    x_start = config.x_start
    z_start = config.z_start
    doc = config.doc if config.doc > 0 else 0.5
    stock_x = config.stock_x

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

        op = build_equidistant_offset(path, offset_d)
        if len(op) < 2:
            continue

        pts = [(item[1], item[2]) for item in op]

        entry_idx = find_offset_entry_idx(pts, x_start, z_start)
        if entry_idx is None or entry_idx >= len(pts) - 1:
            continue

        actual_entry_x, actual_entry_z = pts[entry_idx]
        cut_from_idx = entry_idx + 1

        if entry_idx > 0:
            prev_x, prev_z = pts[entry_idx - 1]
            if prev_x < x_start - 1e-9 or prev_z > z_start + 1e-9:
                if op[entry_idx][0] == 'line':
                    result = find_segment_entry(prev_x, prev_z, *pts[entry_idx], x_start, z_start)
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
