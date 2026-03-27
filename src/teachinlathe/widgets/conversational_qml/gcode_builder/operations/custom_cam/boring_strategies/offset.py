from teachinlathe.conversational.data_types import BoringConfig

from ..custom_profiling_geometry import ToolpathLine

from ....config import fmt
from . import find_offset_entry_idx, find_segment_entry


def emit_offset_roughing(lines: list, config: BoringConfig, path: list, x_safe: float, x_cut_max: float, z_cut_deepest: float):
    """Offset boring passes: translate profile by (-n*doc, +n*doc) per pass.

    Passes are ordered outermost (n_max) to innermost (n=1).
    Direction is always natural profile direction (Z- and X+).
    cut_toward does not apply to offset passes.
    """
    pfx = config.optional_prefix
    x_start = config.x_start
    z_start = config.z_start
    doc = config.doc if config.doc > 0 else 0.5
    stock_x = config.stock_x
    stock_z = config.stock_z

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

        pts = [(path[0].x + x_shift, path[0].z + z_shift)]
        for elem in path[1:]:
            pts.append((elem.end_x + x_shift, elem.end_z + z_shift))

        entry_idx = find_offset_entry_idx(pts, x_start, z_start)
        if entry_idx is None or entry_idx >= len(pts) - 1:
            continue

        actual_entry_x, actual_entry_z = pts[entry_idx]
        cut_from_idx = entry_idx + 1

        if entry_idx > 0:
            prev_x, prev_z = pts[entry_idx - 1]
            if prev_x < x_start - 1e-9 or prev_z > z_start + 1e-9:
                result = find_segment_entry(prev_x, prev_z, *pts[entry_idx], x_start, z_start)
                if result is not None:
                    _, actual_entry_x, actual_entry_z = result
                cut_from_idx = entry_idx

        lines.append(f"{pfx}G0 Z{fmt(actual_entry_z)}")
        lines.append(f"{pfx}G0 X{fmt(actual_entry_x)}")

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
                    done = True
            cur_x, cur_z = ex, ez

        diag_z = actual_exit_z + (actual_exit_x - x_safe)
        lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(diag_z)}")
        lines.append(f"{pfx}G0 Z{fmt(z_start)}")

    lines.append(f"{pfx}G0 X{fmt(x_safe)} Z{fmt(z_start)}")
    lines.append("")
