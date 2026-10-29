"""Closed 2D outlines of cutting tools, in the tool's own frame: an insert's
corners rounded to its nose radius, a round insert or a bore. Plain vertex
lists, for the backplot to draw and for the planner to cut with."""

import math


def _unit(x, y):
    length = math.hypot(x, y)
    if length < 1e-12:
        return 0.0, 0.0
    return x / length, y / length


def rounded_polygon(verts, radius, segments_per_corner=10):
    """``verts`` with every corner rounded to ``radius``, as a closed 2D loop.

    The QML insert draws this with ``ctx.arcTo()``, which works the tangent
    arc out for itself. There is no such thing here, so the same arc is built
    explicitly: for a corner between neighbours A and B, the centre lies along
    the bisector at ``radius / sin(half angle)`` - the distance
    ``TurningInsertBase.noseCenter()`` already computes - and the arc runs
    between the two tangent points at ``radius / tan(half angle)`` along each
    edge.

    ``verts`` must be in order around the outline. Out of order, the corners
    are built against the wrong neighbours and the result is a star - the same
    trap the QML file warns about.
    """
    count = len(verts)
    if count < 3:
        return list(verts)
    if radius <= 0:
        return list(verts)

    loop = []
    for i in range(count):
        vertex = verts[i]
        before = verts[(i - 1) % count]
        after = verts[(i + 1) % count]

        to_before = _unit(before[0] - vertex[0], before[1] - vertex[1])
        to_after = _unit(after[0] - vertex[0], after[1] - vertex[1])

        dot = max(-1.0, min(1.0, to_before[0] * to_after[0]
                                 + to_before[1] * to_after[1]))
        half_angle = math.acos(dot) / 2.0
        if half_angle < 1e-6 or abs(math.sin(half_angle)) < 1e-9:
            loop.append(vertex)
            continue

        bisector = _unit(to_before[0] + to_after[0], to_before[1] + to_after[1])
        if bisector == (0.0, 0.0):
            loop.append(vertex)
            continue

        centre_distance = radius / math.sin(half_angle)
        tangent_distance = radius / math.tan(half_angle)
        edge = min(math.hypot(before[0] - vertex[0], before[1] - vertex[1]),
                   math.hypot(after[0] - vertex[0], after[1] - vertex[1])) / 2.0
        if tangent_distance > edge:
            # The radius does not fit this corner; leaving it sharp is wrong
            # in a visible way, which is what should happen - a nose radius
            # larger than the edge is bad data, not something to smooth over.
            loop.append(vertex)
            continue

        centre = (vertex[0] + bisector[0] * centre_distance,
                  vertex[1] + bisector[1] * centre_distance)
        start = (vertex[0] + to_before[0] * tangent_distance,
                 vertex[1] + to_before[1] * tangent_distance)
        finish = (vertex[0] + to_after[0] * tangent_distance,
                  vertex[1] + to_after[1] * tangent_distance)

        start_angle = math.atan2(start[1] - centre[1], start[0] - centre[0])
        finish_angle = math.atan2(finish[1] - centre[1], finish[0] - centre[0])
        # The minor arc: the corner is convex, so the sweep is never reflex.
        sweep = (finish_angle - start_angle + math.pi) % (2 * math.pi) - math.pi

        steps = max(2, segments_per_corner)
        for step in range(steps + 1):
            angle = start_angle + sweep * step / steps
            loop.append((centre[0] + radius * math.cos(angle),
                         centre[1] + radius * math.sin(angle)))
    return loop


def circle_loop(radius, segments):
    """A circle as a closed 2D loop, for the round insert and the bore."""
    return [(radius * math.cos(2 * math.pi * i / segments),
             radius * math.sin(2 * math.pi * i / segments))
            for i in range(segments)]
