"""What Profile Roughing will cut, for drawing on the profile canvas.

The moves come from the tool-aware plan (profiling.machining), which the
G-code is to be written from as well. All X values are diameters.
"""

import math
import re

from .profile_roughing import (
    _resolve_profile,
    build_roughing_setup,
    parse_profile_roughing_config,
    plan_profile_roughing,
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
    """{profile, offset, feeds, rapids, residual, warnings, error} for
    an operation dict carrying its profile in ``_resolved_profile`` and its
    tool in ``_resolved_cutting_tool``:

    profile     the finished profile, as [{x, z}]
    offset      the profile offset by stock-to-leave, clipped to X Start, as [{x, z}]
    feeds       the cuts, the final contour pass included, as [{x0, z0, x1, z1, pass, contour}]
    rapids      the rapid moves between them (retracts included), likewise
    residual    the material left for another tool, as [[{x, z}]]
    restOffered whether a rest roughing can be added for it: there is some,
                and a tool that cut this one - not a rest roughing still
                waiting for its tool
    warnings    what the plan could not do, as [str]
    error       why there is nothing to show, or ""

    The moves are planned by profiling.machining (plan_profile_roughing), tool
    and all; the G-code is to be written from the same plan.
    """
    config = parse_profile_roughing_config(op)
    ctx, roughing_path, error = build_roughing_setup(op, config)
    empty = {"profile": [], "offset": [], "feeds": [], "rapids": [],
             "residual": [], "warnings": [], "error": error or ""}
    if error:
        return empty
    _, profile_path = _resolve_profile(op)
    plan = plan_profile_roughing(op)
    if plan.error:
        return {**empty, "error": plan.error}

    # the contour where the nose touches - along the profile and its stock -
    # not at the compensated point: the backplot shows that, as the machine
    # moves it
    feeds, rapids = [], []
    for move in plan.moves:
        z0, r0, z1, r1 = move.drawn or (move.z0, move.r0, move.z1, move.r1)
        line = {"x0": 2 * r0, "z0": z0, "x1": 2 * r1, "z1": z1}
        if move.feed:
            feeds.append({**line, "pass": move.pass_no, "contour": move.contour})
        elif (line["x0"], line["z0"]) != (line["x1"], line["z1"]):
            rapids.append(line)

    return {
        "profile": flatten_path(profile_path),
        # the stock to leave as the plan keeps to it: across the profile on
        # every face, the ones turned toward the chuck too
        "offset": [{"x": 2 * r, "z": z} for z, r in plan.allowance] or flatten_path(roughing_path),
        "feeds": feeds,
        "rapids": rapids,
        "residual": [[{"x": 2 * r, "z": z} for z, r in region] for region in plan.residual],
        "restOffered": bool(plan.residual and plan.tool is not None and plan.tool.known),
        "warnings": list(plan.warnings),
        "error": "",
    }
