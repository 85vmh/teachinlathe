"""A plan's G-code (profiling.plan.RoughingPlan): the comments that say what
it was planned for and could not do, then its moves as the machine makes them,
the contour's runs of chords written back as the arcs they lie on. Profile
Roughing and Profile Contour write their plans with this."""

import math

from ...config import fmt
from ...helpers.m1 import inspect_position_int


def write_plan(lines, plan, prefix, stock, m1_params=None, spindle_direction=0, title=None):
    """``plan``'s G-code onto ``lines``: the tool it was planned for, its
    warnings, ``title`` (a comment line, as it is) and its moves (emit_moves)."""
    if plan.tool is not None and plan.tool.known:
        lines.append(comment(f"Planned for {plan.tool.label}, nose R{fmt(plan.tool.nose_radius)}"))
    for warning in plan.warnings:
        lines.append(comment(warning))
    if title:
        lines.append(title)
    emit_moves(lines, plan.moves, prefix, stock, m1_params, spindle_direction)


def comment(text):
    """``text`` as a G-code comment. LinuxCNC refuses a comment with another
    one in it, so the brackets ``text`` may have are made square."""
    return "( " + str(text).replace("(", "[").replace(")", "]") + " )"


def emit_moves(lines, moves, prefix, stock, m1_params=None, spindle_direction=0):
    """``moves`` as G0 / G1, the contour's runs of short chords fitted back
    into G2 / G3 arcs where they lie on one; ``stock`` (radial, axial) is the
    stock to leave the contour's comment names. With ``m1_params`` an
    optional stop after each pass, as they ask."""
    include_m1 = bool(m1_params.get("include_m1", False)) if m1_params else False
    position = None
    contour = []                    # (z, r) points of the contour run under way

    def flush_contour():
        if len(contour) > 1:
            for gcode in _fit_arcs(contour):
                lines.append(f"{prefix}{gcode}")
        contour.clear()

    in_contour = False
    for move in moves:
        if move.contour and move.feed:
            if not in_contour:
                lines.append(f"( Contour with StockToLeave[radial={fmt(stock[0])} "
                             f"axial={fmt(stock[1])}] )")
                in_contour = True
            if not contour:
                if position != (move.z0, move.r0):
                    lines.append(f"{prefix}G0 X{fmt(2 * move.r0)} Z{fmt(move.z0)}")
                contour.append((move.z0, move.r0))
            contour.append((move.z1, move.r1))
            position = (move.z1, move.r1)
            continue
        flush_contour()
        if (move.z0, move.r0) == (move.z1, move.r1):
            if position is None:                    # the start position
                lines.append(f"{prefix}G0 X{fmt(2 * move.r1)} Z{fmt(move.z1)}")
                position = (move.z1, move.r1)
            continue
        if position != (move.z0, move.r0):
            lines.append(f"{prefix}G0 X{fmt(2 * move.r0)} Z{fmt(move.z0)}")
        word = "G1" if move.feed else "G0"
        lines.append(f"{prefix}{word} X{fmt(2 * move.r1)} Z{fmt(move.z1)}")
        position = (move.z1, move.r1)
        if move.pass_end:
            if include_m1:
                lines.append(
                    f"{prefix}o<m1_handling> call "
                    f"[{inspect_position_int(m1_params)}] "
                    f"[{fmt(2 * move.r1)}] "
                    f"[{fmt(move.z1)}] "
                    f"[{spindle_direction}]"
                )
            lines.append("")
    flush_contour()
    lines.append("")


#: How far a chord of the contour may be from the arc it is written as, in mm.
ARC_FIT_TOLERANCE = 0.003


def _fit_arcs(points):
    """G1 / G2 / G3 words along ``points`` [(z, r)]: each longest run of
    four or more points on one circle - within ARC_FIT_TOLERANCE, turning
    one way - as an arc, the rest as lines. X as a diameter, I and K as
    radial and axial distances from the arc's start to its centre."""

    words = []
    i, n = 0, len(points)
    while i < n - 1:
        best = None
        j = i + 3
        while j < n:
            arc = _circle(points[i], points[(i + j) // 2], points[j])
            if arc is None or not _on_arc(points[i:j + 1], arc):
                break
            best = (j, arc)
            j += 1
        if best is not None and _straight(points[i:best[0] + 1]):
            # on a line as much as on a circle - a radius of tens of mm
            # through chords barely bent: a line it is
            j = best[0]
            z1, r1 = points[j]
            words.append(f"G1 X{fmt(2 * r1)} Z{fmt(z1)}")
            i = j
        elif best is not None:
            j, (cz, cr, radius, clockwise) = best
            z0, r0 = points[i]
            z1, r1 = points[j]
            word = "G2" if clockwise else "G3"
            words.append(f"{word} X{fmt(2 * r1)} Z{fmt(z1)} I{fmt(cr - r0)} K{fmt(cz - z0)}")
            i = j
        else:
            z1, r1 = points[i + 1]
            words.append(f"G1 X{fmt(2 * r1)} Z{fmt(z1)}")
            i += 1
    return words


def _straight(points):
    """Whether every point lies on the line from the first to the last,
    within ARC_FIT_TOLERANCE."""
    (az, ar), (bz, br) = points[0], points[-1]
    length = math.hypot(bz - az, br - ar)
    if length < 1e-12:
        return False
    return all(abs((z - az) * (br - ar) - (r - ar) * (bz - az)) / length <= ARC_FIT_TOLERANCE
               for z, r in points)


def _circle(a, b, c):
    """The circle through three (z, r) points as (cz, cr, radius, clockwise),
    clockwise as seen with Z to the right and X up; None when they are in a
    line or the circle is too big to be worth an arc."""
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    radius = math.hypot(ax - ux, ay - uy)
    if radius > 500.0:
        return None
    cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
    return ux, uy, radius, cross < 0


def _on_arc(points, arc):
    """Whether every point, and every chord's middle, is on ``arc`` within
    the tolerance, the points going round it one way only."""
    cz, cr, radius, clockwise = arc
    previous = None
    for k, (z, r) in enumerate(points):
        if abs(math.hypot(z - cz, r - cr) - radius) > ARC_FIT_TOLERANCE:
            return False
        if k:
            pz, pr = points[k - 1]
            mz, mr = (z + pz) / 2, (r + pr) / 2
            if abs(math.hypot(mz - cz, mr - cr) - radius) > ARC_FIT_TOLERANCE:
                return False
            turn = math.atan2(r - cr, z - cz) - math.atan2(pr - cr, pz - cz)
            turn = (turn + math.pi) % (2 * math.pi) - math.pi
            if (turn < 0) != clockwise or abs(turn) > math.pi / 2:
                return False
            if previous is not None and abs(turn) < 1e-9:
                return False
            previous = turn
    return True
