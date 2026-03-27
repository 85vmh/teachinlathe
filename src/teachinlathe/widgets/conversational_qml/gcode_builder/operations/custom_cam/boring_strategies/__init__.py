def find_offset_entry_idx(pts, x_start, z_start):
    """Return the first index where both X >= x_start and Z <= z_start."""
    for i, (x, z) in enumerate(pts):
        if x >= x_start - 1e-9 and z <= z_start + 1e-9:
            return i
    return None


def find_segment_entry(p1x, p1z, p2x, p2z, x_start, z_start):
    """Return (t, x, z) on line p1→p2 where X>=x_start AND Z<=z_start first become true.

    t is in [0, 1]. Returns None if no such point exists on the segment.
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
