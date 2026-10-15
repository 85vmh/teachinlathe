"""What Profile Roughing will cut, for drawing on the profile canvas.

Uses the same setup as generate_profile_roughing_gcode and reads the moves
from the G-code it generates, so the preview shows what the machine will do.
All X values are diameters.
"""

import math
import re

from .profile_roughing import (
    _resolve_profile,
    build_roughing_setup,
    generate_profile_roughing_gcode,
    parse_profile_roughing_config,
)
from .profiling.geometry import ToolpathArc

_ARC_STEP = math.radians(5)
_ROUGHING_START = "(----------Profiling Type:"
_CONTOUR_START = "( Contour with StockToLeave"
_MOTION = re.compile(
    r"^/?\s*(G[0-3])?\s*(?:X(-?[\d.]+))?\s*(?:Z(-?[\d.]+))?\s*(?:I(-?[\d.]+))?\s*(?:K(-?[\d.]+))?"
)


def _arc_points(prev_x, prev_z, arc):
    """The points strictly between the start and end of ``arc``, which starts at
    (prev_x, prev_z), as [(x, z)] a few degrees apart."""
    # in (z, radius) with radius growing downward, as the canvas draws it
    cz, cr = arc.center_z, arc.center_x / 2
    radius = math.hypot(prev_z - cz, prev_x / 2 - cr)
    start = math.atan2(prev_x / 2 - cr, prev_z - cz)
    end = math.atan2(arc.end_x / 2 - cr, arc.end_z - cz)
    sweep = end - start
    if arc.anticlockwise:
        while sweep > 0:
            sweep -= 2 * math.pi
    else:
        while sweep < 0:
            sweep += 2 * math.pi
    steps = max(1, int(math.ceil(abs(sweep) / _ARC_STEP)))
    return [(2 * (cr + radius * math.sin(start + sweep * k / steps)),
             cz + radius * math.cos(start + sweep * k / steps))
            for k in range(1, steps)]


def flatten_path(path):
    """The roughing path as [{x, z}] points, arcs split into short lines."""
    points = [{"x": path[0].x, "z": path[0].z}]
    prev_x, prev_z = path[0].x, path[0].z
    for element in path[1:]:
        if isinstance(element, ToolpathArc):
            points.extend({"x": x, "z": z} for x, z in _arc_points(prev_x, prev_z, element))
        points.append({"x": element.end_x, "z": element.end_z})
        prev_x, prev_z = element.end_x, element.end_z
    return points


def gcode_moves(lines, start=_ROUGHING_START):
    """The moves of generated G-code ``lines`` from the comment that begins
    with ``start`` on, as (feeds, rapids), each [{x0, z0, x1, z1}]; arcs come
    as short lines. A feed also carries ``pass``, counting the passes from 0,
    a pass being the feeds between two rapids, and ``contour``, true from the
    contour pass's comment on.
    """
    feeds, rapids = [], []
    pass_no = -1
    last_mode = None
    in_moves = in_contour = False
    mode = None
    x = z = None
    for line in lines:
        text = line.strip()
        if text.startswith(start):
            in_moves = True
        if text.startswith(_CONTOUR_START):
            in_contour = True
        if not in_moves or not text or text.startswith("(") or "o<" in text:
            continue
        match = _MOTION.match(text)
        if not match or (match.group(2) is None and match.group(3) is None):
            continue
        mode = match.group(1) or mode
        new_x = float(match.group(2)) if match.group(2) is not None else x
        new_z = float(match.group(3)) if match.group(3) is not None else z
        if x is not None and z is not None and new_x is not None and new_z is not None:
            if mode == "G0":
                rapids.append({"x0": x, "z0": z, "x1": new_x, "z1": new_z})
            else:
                if last_mode != "G1":
                    pass_no += 1
                points = [(new_x, new_z)]
                if mode in ("G2", "G3"):
                    # as emit_toolpath writes them: G2 for an anticlockwise
                    # ToolpathArc, I on the radius
                    arc = ToolpathArc(new_x, new_z,
                                      x + 2 * float(match.group(4) or 0), z + float(match.group(5) or 0),
                                      mode == "G2")
                    points = _arc_points(x, z, arc) + points
                px, pz = x, z
                for qx, qz in points:
                    feeds.append({"x0": px, "z0": pz, "x1": qx, "z1": qz,
                                  "pass": pass_no, "contour": in_contour})
                    px, pz = qx, qz
            last_mode = "G1" if mode != "G0" else "G0"
        x, z = new_x, new_z
    return feeds, rapids


def build_profile_roughing_preview(op):
    """{profile, offset, feeds, rapids, error} for an operation
    dict carrying its profile in ``_resolved_profile``:

    profile     the finished profile, as [{x, z}]
    offset      the profile offset by stock-to-leave, clipped to X Start, as [{x, z}]
    feeds       the cuts, the final contour pass included, as [{x0, z0, x1, z1, pass, contour}]
    rapids      the rapid moves between them (retracts included), likewise
    error       why there is nothing to show, or ""
    """
    config = parse_profile_roughing_config(op)
    ctx, roughing_path, error = build_roughing_setup(op, config)
    if error:
        return {"profile": [], "offset": [], "feeds": [], "rapids": [], "error": error}
    _, profile_path = _resolve_profile(op)
    feeds, rapids = gcode_moves(generate_profile_roughing_gcode(op))
    return {
        "profile": flatten_path(profile_path),
        "offset": flatten_path(roughing_path),
        "feeds": feeds,
        "rapids": rapids,
        "error": "",
    }
