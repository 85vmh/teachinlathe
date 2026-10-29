"""A plan's G-code (profiling.plan.RoughingPlan): the comments that say what
it was planned for and could not do, then its moves as the machine makes them,
the contour's runs of chords written back as the arcs they lie on. Profile
Roughing and Profile Contour write their plans with this."""

import math
from dataclasses import dataclass

from ...config import fmt
from ...toolpath import GcodeEmitter, comment
from .geometry import DEGENERATE, ROUNDING


def write_plan(path: GcodeEmitter, plan, stock, m1_params=None, title=None):
    """``plan``'s G-code onto ``path``: the tool it was planned for, its
    warnings, ``title`` (a comment line, as it is) and its moves (emit_moves)."""
    if plan.tool is not None and plan.tool.known:
        path.note(comment(f"Planned for {plan.tool.label}, nose R{fmt(plan.tool.nose_radius)}"))
    for warning in plan.warnings:
        path.note(comment(warning))
    if title:
        path.note(title)
    if any(move.contour and move.feed for move in plan.moves):
        path.note(comment(f"Contour with StockToLeave[radial={fmt(stock[0])} "
                          f"axial={fmt(stock[1])}]"))
    emit_moves(path, plan.moves, stock, m1_params)


def emit_moves(path: GcodeEmitter, moves, stock, m1_params=None):
    """``moves`` onto ``path`` as G0 / G1, the contour's runs of short chords
    fitted back into G2 / G3 arcs where they lie on one; ``stock`` (radial,
    axial) is the stock to leave the contour's comment names. With
    ``m1_params`` (M1Parameters) asking for it, a Pause to Inspect after each
    pass."""
    include_m1 = m1_params is not None and m1_params.include_m1
    contour = []                    # (z, r) points of the contour run under way

    def flush_contour():
        if len(contour) > 1:
            for segment in fit_arcs(contour):
                segment.write(path)
        contour.clear()

    for move in moves:
        path.pass_no = move.pass_no
        if move.contour and move.feed:
            if not contour:
                path.rapid(2 * move.r0, move.z0)
                contour.append((move.z0, move.r0))
            contour.append((move.z1, move.r1))
            continue
        flush_contour()
        if (move.z0, move.r0) == (move.z1, move.r1):
            # the start position: there, when it is not known where it is
            if path.x is None or path.z is None:
                path.rapid(2 * move.r1, move.z1)
            continue
        path.rapid(2 * move.r0, move.z0)
        if move.feed:
            path.feed(2 * move.r1, move.z1)
        else:
            path.rapid(2 * move.r1, move.z1)
        if move.pass_end:
            if include_m1:
                path.inspect_stop(m1_params)
            path.blank()
    flush_contour()
    path.blank()


@dataclass(frozen=True)
class _Line:
    """A G1 along the contour to (z, r)."""
    z: float
    r: float

    def write(self, path: GcodeEmitter):
        path.feed(2 * self.r, self.z)


@dataclass(frozen=True)
class _Arc:
    """A G2 / G3 along the contour to (z, r), round the centre ``i`` (on the
    radius) and ``k`` from where it starts."""
    z: float
    r: float
    i: float
    k: float
    clockwise: bool

    def write(self, path: GcodeEmitter):
        path.arc(2 * self.r, self.z, self.i, self.k, self.clockwise)


#: How far a chord of the contour may be from the arc it is written as, in mm.
ARC_FIT_TOLERANCE = 0.003

#: mm: chords on a circle wider than this are taken as the straight line
#: they nearly are, not fitted with an arc.
MAX_ARC_RADIUS = 500.0


def fit_arcs(points, tolerance=ARC_FIT_TOLERANCE):
    """The contour along ``points`` [(z, r)] as segments - _Arc, _Line: each
    longest run of four or more points on one circle - within ``tolerance``
    (ARC_FIT_TOLERANCE), turning one way - as an arc, the rest as lines; I
    and K the radial and axial distances from the arc's start to its centre."""

    words = []
    i, n = 0, len(points)
    while i < n - 1:
        best = None
        j = i + 3
        while j < n:
            arc = _circle(points[i], points[(i + j) // 2], points[j])
            if arc is None or not _on_arc(points[i:j + 1], arc, tolerance):
                break
            best = (j, arc)
            j += 1
        if best is not None and _straight(points[i:best[0] + 1], tolerance):
            # on a line as much as on a circle - a radius of tens of mm
            # through chords barely bent: a line it is
            j = best[0]
            z1, r1 = points[j]
            words.append(_Line(z1, r1))
            i = j
        elif best is not None:
            j, (cz, cr, radius, clockwise) = best
            z0, r0 = points[i]
            z1, r1 = points[j]
            words.append(_Arc(z1, r1, cr - r0, cz - z0, clockwise))
            i = j
        else:
            z1, r1 = points[i + 1]
            words.append(_Line(z1, r1))
            i += 1
    return words


def _straight(points, tolerance):
    """Whether every point lies on the line from the first to the last,
    within ``tolerance``."""
    (az, ar), (bz, br) = points[0], points[-1]
    length = math.hypot(bz - az, br - ar)
    if length < DEGENERATE:
        return False
    return all(abs((z - az) * (br - ar) - (r - ar) * (bz - az)) / length <= tolerance
               for z, r in points)


def _circle(a, b, c):
    """The circle through three (z, r) points as (cz, cr, radius, clockwise),
    clockwise as seen with Z to the right and X up; None when they are in a
    line or the circle is too big to be worth an arc."""
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < DEGENERATE:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    radius = math.hypot(ax - ux, ay - uy)
    if radius > MAX_ARC_RADIUS:
        return None
    cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
    return ux, uy, radius, cross < 0


def _on_arc(points, arc, tolerance):
    """Whether every point, and every chord's middle, is on ``arc`` within
    ``tolerance``, the points going round it one way only."""
    cz, cr, radius, clockwise = arc
    previous = None
    for k, (z, r) in enumerate(points):
        if abs(math.hypot(z - cz, r - cr) - radius) > tolerance:
            return False
        if k:
            pz, pr = points[k - 1]
            mz, mr = (z + pz) / 2, (r + pr) / 2
            if abs(math.hypot(mz - cz, mr - cr) - radius) > tolerance:
                return False
            turn = math.atan2(r - cr, z - cz) - math.atan2(pr - cr, pz - cz)
            turn = (turn + math.pi) % (2 * math.pi) - math.pi
            if (turn < 0) != clockwise or abs(turn) > math.pi / 2:
                return False
            if previous is not None and abs(turn) < ROUNDING:
                return False
            previous = turn
    return True
