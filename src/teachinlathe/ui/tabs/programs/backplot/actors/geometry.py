"""Shapes the actors build, kept apart from the actors that draw them.

Everything here returns plain vertex lists in model space. Nothing touches GL
or the frame; an actor decides when and in what transform to draw them, which
is what keeps each actor's file about its own concern.
"""

import math

# outlines the planner draws tools with too: in the domain, used from here
from teachinlathe.tooling.model.outlines import circle_loop, rounded_polygon  # noqa: F401


def side_of(direction):
    """The other in-plane axis, so a shape opens in the XZ plane a lathe view
    looks at: across for a Z-going thing, along for an X-going one."""
    return (0.0, 0.0, 1.0) if direction[0] else (1.0, 0.0, 0.0)


def scaled(direction, length):
    """``direction`` scaled to ``length``."""
    return tuple(component * length for component in direction)


def arrow_head(direction, length, head_length, head_width):
    """The three corners of a solid arrow head, tip first.

    The tip is at ``length`` along ``direction``; the base sits one
    ``head_length`` back from it, ``head_width`` to either side.
    """
    tip = scaled(direction, length)
    base = scaled(direction, length - head_length)
    side = side_of(direction)

    def corner(sign):
        return tuple(base[i] + side[i] * head_width * sign for i in range(3))

    return [tip, corner(+1), corner(-1)]


def circle_point(radius, angle):
    """A point on a circle lying in the XZ plane.

    Angle 0 is +Z and a quarter turn is +X, so the quadrants line up with the
    axes as they are drawn: +Z to the right, +X downwards.
    """
    return (radius * math.sin(angle), 0.0, radius * math.cos(angle))


def circle_outline(radius, segments):
    """A closed circle as GL_LINES endpoint pairs."""
    points = []
    for i in range(segments):
        points.append(circle_point(radius, 2 * math.pi * i / segments))
        points.append(circle_point(radius, 2 * math.pi * (i + 1) / segments))
    return points


def circle_sector(radius, start_angle, span, segments):
    """A filled sector as GL_TRIANGLES, fanned from the centre."""
    points = []
    steps = max(2, segments)
    for i in range(steps):
        a0 = start_angle + span * i / steps
        a1 = start_angle + span * (i + 1) / steps
        points.extend([(0.0, 0.0, 0.0),
                       circle_point(radius, a0),
                       circle_point(radius, a1)])
    return points


# ── polylines and dashes ───────────────────────────────────────────────────

def polyline(points, closed=False):
    """A run of points as GL_LINES endpoint pairs.

    The vertex arrays take pairs, not strips, so a path has to be handed over
    an edge at a time; this is the one place that expansion is written.
    """
    if len(points) < 2:
        return []
    edges = []
    for i in range(len(points) - 1):
        edges.extend([points[i], points[i + 1]])
    if closed:
        edges.extend([points[-1], points[0]])
    return edges


def dashed(start, end, pattern, px_per_unit):
    """``start`` to ``end`` cut into the on-runs of ``pattern``.

    Nothing in the GL renderer dashes - upstream says as much in
    ``ProgramPart`` - so a dashed line is really this many short solid ones.
    Only an actor that builds its own vertices can do it, which is why the
    program's own rapids stay solid.

    ``pattern`` is on/off runs in pixels, as the Canvas context took them, so
    a dash keeps its size on screen as the operator zooms. ``px_per_unit`` is
    what converts it; see ``screen.pixels_per_unit``.
    """
    if not pattern or px_per_unit <= 0:
        return [start, end]

    span = tuple(end[i] - start[i] for i in range(3))
    length = math.sqrt(sum(component * component for component in span))
    if length <= 0:
        return []
    direction = tuple(component / length for component in span)

    def at(distance):
        return tuple(start[i] + direction[i] * distance for i in range(3))

    runs = [run / px_per_unit for run in pattern]
    edges = []
    position = 0.0
    index = 0
    # Even entries are the on-runs, odd the gaps - the Canvas convention the
    # patterns in ``palette`` were written for.
    while position < length:
        run = runs[index % len(runs)]
        if run <= 0:
            index += 1
            continue
        finish = min(position + run, length)
        if index % 2 == 0:
            edges.extend([at(position), at(finish)])
        position = finish
        index += 1
    return edges


# ── the insert, and other filled outlines ──────────────────────────────────

def fan_to_triangles(loop, centre=(0.0, 0.0, 0.0)):
    """A closed convex outline as GL_TRIANGLES, fanned from ``centre``.

    Every insert outline is convex - rhombic, triangular, square, trigon or
    round - and centred on the point the fan starts from, so a fan is enough
    and no tessellator is needed.
    """
    if len(loop) < 3:
        return []
    triangles = []
    for i in range(len(loop)):
        triangles.extend([centre, loop[i], loop[(i + 1) % len(loop)]])
    return triangles


# ── clipping, for the hatch ────────────────────────────────────────────────

def clip_to_rect(start, end, low, high):
    """``start``-``end`` cut down to the box ``low``-``high``, or ``None``.

    Liang-Barsky, in the two axes the lathe view uses: ``low`` and ``high`` are
    ``(x, z)`` pairs and the points are full model triples with Y ignored -
    everything on this plot lies in the Y=0 plane.

    The QML renderer had ``ctx.clip()`` for this and clipped the hatch to the
    stock with it. There is no clip in the GL renderer, so each hatch line is
    shortened to the stock before it is drawn.
    """
    origin = (start[0], start[2])
    span = (end[0] - start[0], end[2] - start[2])

    enter, leave = 0.0, 1.0
    for axis in (0, 1):
        for direction, limit in ((-1.0, -low[axis]), (1.0, high[axis])):
            p = direction * span[axis]
            q = limit - direction * origin[axis]
            if abs(p) < 1e-12:
                if q < 0:
                    return None         # parallel to this edge, and outside it
                continue
            t = q / p
            if p < 0:
                enter = max(enter, t)
            else:
                leave = min(leave, t)
            if enter > leave:
                return None

    def at(t):
        return (start[0] + (end[0] - start[0]) * t, 0.0,
                start[2] + (end[2] - start[2]) * t)

    return at(enter), at(leave)


# ── rings: a filled outline with a hole left open in it ────────────────────

def ray_hit(loop, angle):
    """Where a ray from the origin at ``angle`` leaves a closed 2D ``loop``.

    The loop must enclose the origin, which every insert outline does - it is
    centred on its inscribed circle. ``None`` if the ray somehow misses, which
    a caller treats as "skip this spoke" rather than as an error.
    """
    direction = (math.cos(angle), math.sin(angle))
    for i in range(len(loop)):
        a = loop[i]
        b = loop[(i + 1) % len(loop)]
        edge = (b[0] - a[0], b[1] - a[1])

        determinant = direction[0] * edge[1] - direction[1] * edge[0]
        if abs(determinant) < 1e-12:
            continue                    # the ray runs along this edge

        along = (a[0] * direction[1] - direction[0] * a[1]) / determinant
        if along < -1e-9 or along > 1 + 1e-9:
            continue                    # crosses the line, but off the edge

        distance = (a[0] * edge[1] - a[1] * edge[0]) / determinant
        if distance <= 0:
            continue                    # behind the origin
        return direction[0] * distance, direction[1] * distance
    return None


def _ring_spokes(loop, segments):
    """The bearings the ring is built on: every vertex of ``loop``, plus
    ``segments`` evenly spaced ones, sorted and with duplicates dropped.

    Both halves are needed and neither is enough:

    **Every vertex**, because the outline is what the fill has to reach. On
    evenly spaced bearings alone the outer boundary is a chord between two
    samples, and a chord cuts the corner off - worst exactly where the outline
    turns fastest, which on an insert is the nose radius. That is the gold
    stopping short of its own outline.

    **Evenly spaced ones**, because the vertices are not spread evenly. A
    rhombus puts all of them on its four corners and leaves the long edges
    with none, so a hole built from vertices alone would be a quadrilateral.
    """
    spokes = [(math.atan2(point[1], point[0]) % (2 * math.pi), point)
              for point in loop]
    spokes.extend(((2 * math.pi * i / segments), None)
                  for i in range(segments))
    spokes.sort(key=lambda spoke: spoke[0])

    # A generated bearing landing on a vertex is the vertex: keep the one that
    # carries the point, so the outline is followed exactly there.
    merged = []
    for angle, point in spokes:
        if merged and angle - merged[-1][0] < 1e-9:
            if point is not None:
                merged[-1] = (angle, point)
            continue
        merged.append((angle, point))
    return merged


def ring_triangles(loop, inner_radius, segments):
    """``loop`` filled as GL_TRIANGLES with a circular hole left open.

    Not a fan with a disc drawn over it: painting the hole in a second colour
    hides what is underneath, and an insert's hole is a hole - the toolpath
    and the stock behind it should show through. So the geometry itself has
    the hole in it, and nothing is drawn where it is.

    The outer boundary passes through every vertex of ``loop`` and the inner
    one is a circle; see ``_ring_spokes`` for why it is built on both the
    outline's own bearings and a set of even ones.
    """
    if len(loop) < 3 or segments < 3:
        return []
    if inner_radius <= 0:
        return fan_to_triangles(loop, centre=(0.0, 0.0))

    spokes = []
    for angle, point in _ring_spokes(loop, segments):
        outer = point if point is not None else ray_hit(loop, angle)
        if outer is None:
            continue                    # a generated bearing that missed
        if math.hypot(outer[0], outer[1]) <= inner_radius:
            # The hole is wider than the insert here: bad data, and a ring
            # built from it would turn inside out. Fall back to a solid body.
            return fan_to_triangles(loop, centre=(0.0, 0.0))
        spokes.append((outer, (inner_radius * math.cos(angle),
                               inner_radius * math.sin(angle))))

    if len(spokes) < 3:
        return fan_to_triangles(loop, centre=(0.0, 0.0))

    triangles = []
    for i in range(len(spokes)):
        (outer, inner) = spokes[i]
        (next_outer, next_inner) = spokes[(i + 1) % len(spokes)]
        triangles.extend([inner, outer, next_outer])
        triangles.extend([inner, next_outer, next_inner])
    return triangles


def annulus(radius, width, segments):
    """A ring of stroke ``width`` as GL_TRIANGLES, in the XZ plane.

    A filled band rather than a stroked circle, because a stroked one comes
    apart at this size. Upstream draws a wide line by expanding each segment
    into its own quad with butt caps - no join, no extension past the
    endpoints - so a circle tessellated finely enough to read as round is a
    ring of stubby quads that do not meet. On an 8-pixel radius at 48
    segments the chord is about a pixel and the stroke is two and a half, so
    each quad is wider than it is long and what lands on screen is a dotted,
    gappy circle: the "missing pixels" in the origin symbol.

    A band has no caps and no joints. It is also exact at any radius, which a
    stroked outline is not.
    """
    outer = radius + width / 2.0
    inner = max(0.0, radius - width / 2.0)
    triangles = []
    for i in range(segments):
        a0 = 2 * math.pi * i / segments
        a1 = 2 * math.pi * (i + 1) / segments
        outer_0, outer_1 = circle_point(outer, a0), circle_point(outer, a1)
        inner_0, inner_1 = circle_point(inner, a0), circle_point(inner, a1)
        triangles.extend([inner_0, outer_0, outer_1,
                          inner_0, outer_1, inner_1])
    return triangles
