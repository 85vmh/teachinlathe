"""A plan drawn on the profile canvas: its moves where the nose touches - along
the profile and its stock to leave, not at the compensated point the machine
is sent to, which the backplot shows - and the profile and the stock to leave
as points. All X values are diameters, as the canvas has them."""

from ...toolpath import Point, arc_points
from .geometry import ToolpathArc


def _arc_points(prev_x, prev_z, arc):
    """The points strictly between the start and end of ``arc`` (a
    ToolpathArc, anticlockwise in the profile's own sense: clockwise as the
    canvas draws it), which starts at (prev_x, prev_z), as [(x, z)] a few
    degrees apart."""
    return [(2 * r, z) for z, r in arc_points(prev_z, prev_x / 2, arc.end_z, arc.end_x / 2,
                                               arc.center_z, arc.center_x / 2, arc.anticlockwise)]


def flatten_path(path):
    """The roughing path as Points, arcs split into short lines."""
    points = [Point(path[0].x, path[0].z)]
    prev_x, prev_z = path[0].x, path[0].z
    for element in path[1:]:
        if isinstance(element, ToolpathArc):
            points.extend(Point(x, z) for x, z in _arc_points(prev_x, prev_z, element))
        points.append(Point(element.end_x, element.end_z))
        prev_x, prev_z = element.end_x, element.end_z
    return tuple(points)


def chain_points(chain):
    """A chain of (z, r) points - the stock to leave the plan keeps to, a
    region left over - as Points."""
    return tuple(Point(2 * r, z) for z, r in chain)
