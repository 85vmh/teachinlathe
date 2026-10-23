"""A plan drawn on the profile canvas: its moves where the nose touches - along
the profile and its stock to leave, not at the compensated point the machine
is sent to, which the backplot shows - and the profile and the stock to leave
as points. All X values are diameters, as the canvas has them."""

import math

from .geometry import ToolpathArc

_ARC_STEP = math.radians(5)


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


def drawn_moves(plan):
    """(feeds, rapids) of ``plan`` as the canvas draws them: the feeds as
    [{x0, z0, x1, z1, pass, contour}] where the nose touches, the rapids that
    go somewhere as [{x0, z0, x1, z1}]."""
    feeds, rapids = [], []
    for move in plan.moves:
        z0, r0, z1, r1 = move.drawn or (move.z0, move.r0, move.z1, move.r1)
        line = {"x0": 2 * r0, "z0": z0, "x1": 2 * r1, "z1": z1}
        if move.feed:
            feeds.append({**line, "pass": move.pass_no, "contour": move.contour})
        elif (line["x0"], line["z0"]) != (line["x1"], line["z1"]):
            rapids.append(line)
    return feeds, rapids


def chain_points(chain):
    """A chain of (z, r) points - the stock to leave the plan keeps to, a
    region left over - as [{x, z}]."""
    return [{"x": 2 * r, "z": z} for z, r in chain]
