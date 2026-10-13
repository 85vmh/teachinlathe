"""The cutting tools that are not ISO turning inserts, in millimetres.

Threading inserts, blades, drills, reamers and taps, as the Tool Library
draws them - ported from ``widgets/tool_shapes/ThreadingInsert.qml``,
``Drill.qml``, ``Reamer.qml``, ``Tap.qml`` and ``tools_qml/BladeThumbnail.qml``
for the same reason ``inserts.py`` ports the turning inserts: the backplot
draws OpenGL, and a QML Canvas cannot be drawn inside it. The two have to
agree, so the numbers below are the QML's.

Everything is 2D and in the tool's own frame, as the QML lays it out with y
up: +x to the right. Each builder returns an ``Outline``; how it is turned,
mirrored and placed on the lathe's XZ plane is the actor's job.
"""

import math
from typing import List, NamedTuple, Optional, Tuple

from teachinlathe.widgets.backplot.actors import geometry

Point = Tuple[float, float]

#: Segments each rounded corner is built from, as the turning inserts'.
CORNER_SEGMENTS = 10


class Outline(NamedTuple):
    """A tool's drawing in its own frame.

    ``loop`` is the closed outline and ``fill`` the triangles that fill it.
    ``hole`` is ``(hole radius, countersink radius)`` about the origin, or
    ``None``; when there is one the fill already leaves it open. ``lines``
    are open polylines drawn on top - a drill's flutes. ``tip`` is the
    control point: the point the toolpath is programmed to.
    """

    loop: List[Point]
    fill: List[Point]
    hole: Optional[Tuple[float, float]]
    lines: List[List[Point]]
    tip: Point


# ── threading inserts ───────────────────────────────────────────────────────

#: Inscribed circle by size code - ThreadingInsert.qml's ``icTable``.
THREADING_IC = {"11": 6.35, "16": 9.525, "22": 12.7}

#: Hole and countersink diameters - its ``holeTable``.
THREADING_HOLES = {"11": (3.25, 4.80), "16": (4.00, 6.00), "22": (5.07, 7.70)}

#: The tooth by size and pitch - its ``pitchTable``: tip radius ``r``, V
#: angle ``a``, the bisector's distance ``X`` from the long side, the
#: rounded tip's distance ``Y`` along that side from the theoretical corner,
#: and the tooth's height ``h``.
THREADING_TEETH = {
    "11": {
        0.5: (0.11, 60.767, 0.7278, 0.5998, 0.414),
        0.6: (0.11, 60.767, 0.6639, 0.5998, 0.467),
        0.7: (0.11, 60.767, 0.6, 0.5998, 0.52),
        0.75: (0.11, 60.767, 0.6, 0.5998, 0.601),
        0.8: (0.12, 60.767, 0.6, 0.5998, 0.66),
        1.0: (0.15, 60.8, 0.6932, 0.65, 0.742),
        1.25: (0.16, 60.84, 0.9, 0.7992, 0.8836),
        1.5: (0.1931, 60.84, 1.0, 0.8066, 1.1193),
        1.75: (0.2262, 60.84, 1.2145, 0.814, 1.55),
        2.0: (0.2593, 60.84, 1.2483, 0.8214, 1.673),
    },
    "16": {
        0.35: (0.0448, 60.652, 0.6003, 0.5795, 0.3345),
        0.4: (0.0534, 60.691, 0.6001, 0.5825, 0.361),
        0.45: (0.062, 60.729, 0.6001, 0.5854, 0.3875),
        0.5: (0.0706, 60.767, 0.6, 0.5883, 0.414),
        0.6: (0.0878, 60.844, 0.6, 0.5941, 0.467),
        0.7: (0.105, 60.92, 0.6, 0.6, 0.52),
        0.75: (0.1003, 60.767, 0.6, 0.5929, 0.601),
        0.8: (0.1022, 60.774, 0.6382, 0.614, 0.66),
        1.0: (0.11, 60.8, 0.7008, 0.6982, 0.742),
        1.25: (0.157, 60.84, 0.9, 0.8, 0.8836),
        1.5: (0.189, 60.84, 1.15, 0.9, 1.1193),
        1.75: (0.221, 60.84, 1.2, 0.9, 1.55),
        2.0: (0.25, 60.8, 1.3, 1.0, 1.673),
        2.5: (0.3428, 60.767, 1.5, 1.1501, 1.9199),
        3.0: (0.378, 60.84, 1.6, 1.2, 2.238),
        3.5: (0.5169, 60.91, 1.5999, 1.2666, 2.629),
    },
    "22": {
        1.5: (0.1856, 61.132, 1.2111, 1.4381, 1.1193),
        1.75: (0.2199, 61.096, 1.4648, 1.4584, 1.55),
        2.0: (0.2542, 61.059, 1.5366, 1.4786, 1.673),
        2.5: (0.3228, 60.986, 1.6806, 1.5191, 1.9199),
        3.0: (0.3914, 60.913, 1.866, 1.5596, 2.238),
        3.5: (0.46, 60.84, 2.3, 1.6001, 2.629),
        4.0: (0.5286, 60.767, 2.3, 1.6406, 3.013),
        4.5: (0.5893, 60.767, 2.4, 1.7077, 3.3872),
        5.0: (0.6499, 60.767, 2.5, 1.7748, 3.7615),
        5.5: (0.7106, 60.767, 2.6448, 1.8419, 4.1357),
        6.0: (0.7712, 60.767, 2.8643, 1.909, 4.51),
    },
}

#: Segments the hole's ring is built on.
CIRCLE_SEGMENTS = 64


def threading_insert(size, pitch, mirrored=False):
    """A laydown threading insert: an equilateral body with a V tooth on
    each corner, pointing up at rotation 0 - an external thread. Mirrored
    for the internal one, as ThreadingInsert draws hand "L"."""
    ic = THREADING_IC[size]
    teeth = THREADING_TEETH[size]
    radius, angle, along, back, height = teeth[min(teeth, key=lambda p: abs(p - pitch))]

    half = math.radians(angle / 2)
    setback = radius / math.sin(half) - radius
    corner_y = ic * math.sqrt(3) / 2
    side_x = -ic / 2                                # the reference side
    apex_x = side_x + along
    apex_y = corner_y - back + setback              # the sharp apex
    chord_y = apex_y - height
    flank = height * math.tan(half)

    sector = [(side_x, chord_y), (apex_x - flank, chord_y), (apex_x, apex_y),
              (apex_x + flank, chord_y), (ic - math.sqrt(3) * chord_y, chord_y)]
    sharp = []
    for k in range(3):                              # three-fold symmetry
        turn = math.radians(-120 * k)
        cos, sin = math.cos(turn), math.sin(turn)
        sharp.extend((x * cos - y * sin, x * sin + y * cos) for x, y in sector)
    # Only the teeth are rounded; the chords' corners stay sharp.
    loop = []
    count = len(sharp)
    for i, vertex in enumerate(sharp):
        if i % len(sector) == 2:
            loop.extend(_round_corner(sharp[i - 1], vertex, sharp[(i + 1) % count], radius))
        else:
            loop.append(vertex)
    sign = -1.0 if mirrored else 1.0
    if mirrored:
        loop = [(-x, y) for x, y in reversed(loop)]

    hole, countersink = THREADING_HOLES[size]
    return Outline(loop=loop,
                   fill=geometry.ring_triangles(loop, hole / 2, CIRCLE_SEGMENTS),
                   hole=(hole / 2, countersink / 2), lines=[],
                   tip=(sign * apex_x, apex_y))


# ── blades ──────────────────────────────────────────────────────────────────

#: The drawn blade's length: 10 mm for a 1 mm blade, 20 mm for a 5 mm one -
#: BladeToolView's ``_LENGTH_AT``.
BLADE_LENGTH_AT = ((1.0, 10.0), (5.0, 20.0))


def blade_length(width):
    (w0, l0), (w1, l1) = BLADE_LENGTH_AT
    width = min(max(width, w0), w1)
    return l0 + (width - w0) * (l1 - l0) / (w1 - w0)


def blade(width, left_radius, right_radius, control=0):
    """A blade: a strip ``width`` wide, its cutting end up at rotation 0, a
    corner radius either side of it - left on -x. ``control`` is the point
    the Z offset was taken from: -1 the left corner, 1 the right, 0 the
    middle of the end."""
    half = width / 2
    length = blade_length(width)
    left = min(max(left_radius, 0.0), half)
    right = min(max(right_radius, 0.0), half)
    loop = ([(-half, -length)]
            + _round_corner((-half, -length), (-half, 0.0), (half, 0.0), left)
            + _round_corner((-half, 0.0), (half, 0.0), (half, -length), right)
            + [(half, -length)])
    return Outline(loop=loop, fill=_fan(loop), hole=None, lines=[],
                   tip=(half * control, 0.0))


# ── drills, reamers and taps: point left, body right, as at orientation 7 ──

#: Drill.qml's proportions: flutes and shank, in diameters, and the helix.
DRILL_FLUTES_D = 5.0
DRILL_SHANK_D = 2.0
DRILL_HELIX_ANGLE = 30.0
#: Points each half lead of a drill's flute edge is drawn with.
HELIX_STEPS = 24

#: How far apart the two lines of a flute edge's pair are, in pixels,
#: square to them at their middle - Drill.qml's and Reamer.qml's
#: ``helixGapPx``. Pixels, so the actor converts it at the zoom it draws at.
HELIX_GAP_PX = 3.0


def drill(diameter, tip_angle, right_hand=True, gap=0.0):
    """A twist drill from the side: a cone of ``tip_angle`` and the body,
    the flutes' edges on it and a line where the shank starts. ``gap`` is
    the pair's spacing in millimetres, square to the lines."""
    radius = diameter / 2
    point = 0.0 if tip_angle >= 179.999 else radius / math.tan(math.radians(tip_angle / 2))
    flutes_end = point + DRILL_FLUTES_D * diameter
    end = flutes_end + DRILL_SHANK_D * diameter

    top = [(0.0, 0.0), (point, radius), (end, radius)]
    bottom = [(0.0, 0.0), (point, -radius), (end, -radius)]

    def reach(x):                           # the cone, then the flutes
        if x < 0 or x > flutes_end:
            return -1.0
        return radius if x >= point or point <= 0 else radius * x / point

    # Each flute's edge is the helix seen from the side: a cosine, top to
    # bottom over half a lead - "\" for a right-hand drill. Two flutes, one
    # every half lead, each edge with its pair beside it; from half a lead
    # before the point, so the first runs into the cone, to the flutes' end.
    lines = [[(flutes_end, radius), (flutes_end, -radius)]]
    angle = math.radians(DRILL_HELIX_ANGLE)
    half_lead = math.pi * diameter / math.tan(angle) / 2
    sign = 1.0 if right_hand else -1.0
    shift = gap / math.sin(angle)           # the pair's spacing, along the axis
    start = flutes_end - half_lead * math.ceil(flutes_end / half_lead + 1)
    while start < flutes_end:
        for x0 in (start, start + shift) if gap > 0 else (start,):
            curve = [(x0 + t * half_lead, sign * radius * math.cos(math.pi * t))
                     for t in (i / HELIX_STEPS for i in range(HELIX_STEPS + 1))]
            lines.extend(_clipped(curve, reach))
        start += half_lead
    return _strip_outline(top, bottom, lines)


#: Reamer.qml's proportions and flutes.
REAMER_FLUTES_D = 4.0
REAMER_SHANK_D = 2.6
REAMER_SHANK_RATIO = 0.8
REAMER_CHAMFER_RATIO = 0.08
REAMER_MIN_CHAMFER = 0.3
REAMER_FLUTES = 6
REAMER_HELIX_ANGLE = 10.0
#: Points a reamer's flute edge is drawn with, along the fluted part.
REAMER_STEPS = 48


def reamer(diameter, gap=0.0):
    """A reamer from the side: a 45 degree lead chamfer, the fluted body,
    a 45 degree step down to a thinner shank. The flutes are a slow
    right-hand helix, seen only on the near face, each edge with its pair;
    the chamfers' edges are lines across."""
    radius = diameter / 2
    chamfer = min(radius / 4, max(REAMER_MIN_CHAMFER, REAMER_CHAMFER_RATIO * diameter))
    shank = REAMER_SHANK_RATIO * radius
    end = (REAMER_FLUTES_D + REAMER_SHANK_D) * diameter
    flutes_end = min(REAMER_FLUTES_D * diameter, 0.7 * end)
    back_end = flutes_end + (radius - shank)

    xs = [0.0, chamfer, flutes_end, back_end, end]
    rs = [radius - chamfer, radius, radius, shank, shank]

    def reach(x):                           # the fluted part's outline
        if x < 0 or x > back_end:
            return -1.0
        if x < chamfer:
            return radius - chamfer + x
        if x > flutes_end:
            return radius - (x - flutes_end)
        return radius

    angle = math.radians(REAMER_HELIX_ANGLE)
    lead = math.pi * diameter / math.tan(angle)
    gap_phase = 2 * math.pi * (gap / math.sin(angle)) / lead
    lines = [[(chamfer, radius), (chamfer, -radius)],
             [(flutes_end, radius), (flutes_end, -radius)],
             [(back_end, shank), (back_end, -shank)]]
    for i in range(REAMER_FLUTES):
        phase = 2 * math.pi * (i + 0.5) / REAMER_FLUTES
        for phase0 in (phase, phase + gap_phase) if gap > 0 else (phase,):
            # The edge is at phi on the circumference; only the near face,
            # phi up to half a turn, is seen.
            run = []
            for j in range(REAMER_STEPS + 1):
                x = back_end * j / REAMER_STEPS
                phi = (phase0 + 2 * math.pi * x / lead) % (2 * math.pi)
                if phi > math.pi:
                    if len(run) > 1:
                        lines.extend(_clipped(run, reach))
                    run = []
                    continue
                run.append((x, radius * math.cos(phi)))
            if len(run) > 1:
                lines.extend(_clipped(run, reach))

    return _strip_outline([(x, r) for x, r in zip(xs, rs)],
                          [(x, -r) for x, r in zip(xs, rs)], lines)


#: Tap.qml's proportions.
TAP_LEAD_THREADS = 3.0
TAP_THREAD_LENGTH_D = 2.0
TAP_MIN_THREADS = 8.0
TAP_SHANK_RATIO = 0.8
TAP_SHANK_D = 2.0


def tap(diameter, pitch, right_hand=True):
    """A tap from the side: 60 degree teeth on the major diameter, rising
    over a lead taper at the point, then a plain shank. The far side's teeth
    are half a pitch on; on the seen face each crest on top is joined to the
    one below half a turn later - to the right for a right-hand thread,
    "\", to the left for a left-hand one."""
    radius = diameter / 2
    pitch = max(pitch, 0.05)
    depth = pitch * math.sqrt(3) / 2
    root = max(radius - depth, radius / 3)
    lead = TAP_LEAD_THREADS * pitch
    threads = max(TAP_THREAD_LENGTH_D * diameter, TAP_MIN_THREADS * pitch)
    end = threads + TAP_SHANK_D * diameter
    shank = min(radius, max(root, TAP_SHANK_RATIO * radius))

    def crest(x):
        return radius if x >= lead else root + (radius - root) * max(0.0, x) / lead

    def profile(x, phase):
        u = ((x - phase) / pitch) % 1.0
        tooth = 1.0 - abs(2.0 * u - 1.0)            # 0 at the root, 1 at the crest
        return min(root + tooth * (radius - root), crest(x))

    # Every crest and root of both sides, and the taper's ends: the profile
    # is straight between them, so the outline is exact on them.
    stations = {0.0, lead, threads}
    k = 0
    while k * pitch / 2 <= threads:
        stations.add(k * pitch / 2)
        k += 1
    xs = sorted(x for x in stations if 0.0 <= x <= threads)

    top = [(x, profile(x, 0.0)) for x in xs] + [(threads, shank), (end, shank)]
    bottom = [(x, -profile(x, pitch / 2)) for x in xs] + [(threads, -shank), (end, -shank)]

    lines = []
    way = 1.0 if right_hand else -1.0
    n = 0
    while n * pitch <= threads:
        on_top = n * pitch + pitch / 2              # a crest on top
        below = on_top + way * pitch / 2            # the next one below
        if on_top <= threads and 0.0 <= below <= threads:
            lines.append([(on_top, crest(on_top)), (below, -crest(below))])
        n += 1
    return _strip_outline(top, bottom, lines)


def _clipped(curve, reach):
    """The parts of ``curve`` inside ``|y| <= reach(x)``, as runs; each
    crossing found along the segment it falls in, so a run ends on the
    outline rather than a step short of it. ``reach`` is negative where
    nothing is inside."""
    def inside(point):
        return reach(point[0]) - abs(point[1])

    runs, run = [], []
    for i, point in enumerate(curve):
        if inside(point) >= 0:
            if not run and i > 0:
                run.append(_crossing(curve[i - 1], point, inside))
            run.append(point)
        elif run:
            run.append(_crossing(run[-1], point, inside))
            runs.append(run)
            run = []
    if run:
        runs.append(run)
    return [r for r in runs if len(r) > 1]


def _crossing(a, b, inside):
    """Where the segment ``a``-``b`` crosses the outline, by bisection."""
    lo, hi = (a, b) if inside(a) >= 0 else (b, a)
    for _ in range(30):
        mid = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2)
        if inside(mid) >= 0:
            lo = mid
        else:
            hi = mid
    return lo


# ── shared ──────────────────────────────────────────────────────────────────

def _strip_outline(top, bottom, lines):
    """An outline that is one top and one bottom edge over the same x's,
    filled strip by strip - the shape of anything turned seen from the side,
    which a fan from one point cannot fill. Tipped at the origin."""
    fill = []
    for i in range(len(top) - 1):
        fill.extend([top[i], bottom[i], top[i + 1]])
        fill.extend([bottom[i], bottom[i + 1], top[i + 1]])
    loop = list(top) + list(reversed(bottom))
    return Outline(loop=_dedupe(loop), fill=fill, hole=None, lines=lines, tip=(0.0, 0.0))


def _fan(loop):
    """A convex loop as triangles, fanned from its centroid."""
    cx = sum(x for x, _ in loop) / len(loop)
    cy = sum(y for _, y in loop) / len(loop)
    fill = []
    for i in range(len(loop)):
        fill.extend([(cx, cy), loop[i], loop[(i + 1) % len(loop)]])
    return fill


def _round_corner(before, vertex, after, radius):
    """The corner at ``vertex`` rounded to ``radius``, as points - the arc
    ``geometry.rounded_polygon`` builds, for one corner of a loop whose
    other corners stay sharp. The vertex itself when there is no radius."""
    if radius <= 1e-9:
        return [vertex]
    to_before = _unit(before[0] - vertex[0], before[1] - vertex[1])
    to_after = _unit(after[0] - vertex[0], after[1] - vertex[1])
    dot = max(-1.0, min(1.0, to_before[0] * to_after[0] + to_before[1] * to_after[1]))
    half_angle = math.acos(dot) / 2.0
    bisector = _unit(to_before[0] + to_after[0], to_before[1] + to_after[1])
    if half_angle < 1e-6 or bisector == (0.0, 0.0):
        return [vertex]
    centre_distance = radius / math.sin(half_angle)
    tangent_distance = radius / math.tan(half_angle)
    centre = (vertex[0] + bisector[0] * centre_distance,
              vertex[1] + bisector[1] * centre_distance)
    start = (vertex[0] + to_before[0] * tangent_distance,
             vertex[1] + to_before[1] * tangent_distance)
    finish = (vertex[0] + to_after[0] * tangent_distance,
              vertex[1] + to_after[1] * tangent_distance)
    start_angle = math.atan2(start[1] - centre[1], start[0] - centre[0])
    finish_angle = math.atan2(finish[1] - centre[1], finish[0] - centre[0])
    sweep = (finish_angle - start_angle + math.pi) % (2 * math.pi) - math.pi
    return [(centre[0] + radius * math.cos(start_angle + sweep * i / CORNER_SEGMENTS),
             centre[1] + radius * math.sin(start_angle + sweep * i / CORNER_SEGMENTS))
            for i in range(CORNER_SEGMENTS + 1)]


def _unit(x, y):
    length = math.hypot(x, y)
    if length < 1e-12:
        return 0.0, 0.0
    return x / length, y / length


def _dedupe(loop):
    out = []
    for point in loop:
        if not out or math.hypot(point[0] - out[-1][0], point[1] - out[-1][1]) > 1e-9:
            out.append(point)
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= 1e-9:
        out.pop()
    return out
