"""A blade's cuts, drawn down its middle.

The point LinuxCNC moves - the one the program's coordinates and the trail are
of - is the one the tool was touched off on: for a blade, its left corner, its
right corner or the middle of its end (the holder's ``z_offset_place``), and
the conversational programs are written for that point. The plot draws a
blade's moves down its middle: this moves the program's points, its dwell
markers and the trail's, tool by tool, from the touched-off point to there -
all of them by the same distance, so a move keeps its shape - and the profile
the blade leaves is worked out from its middle, half its width either side.

A contour is drawn along the corner it is cut with instead - its middle
moved on by half its width, toward that corner - so it lies on the profile.
Which corner that is, is not worked out from the moves - a contour down an
upright flank moves along X alone, as a plunge does - but read off the
program: the conversational G-code says it over each contour it writes
(groove_roughing.corner_comment).

The tool marker is not moved: it is drawn where the blade is, its control
point on the touched-off point, and so lands on the moved line's middle.
"""

import logging
import re

LOG = logging.getLogger(__name__)

try:
    import numpy as np
    from rs274.glcanon_bake import LOGGER_DTYPE
except ImportError:  # pragma: no cover - depends on the LinuxCNC install
    np = None


#: What the conversational G-code puts over a contour it cuts with one of a
#: blade's corners (groove_roughing.CORNER_COMMENT).
_CORNER = re.compile(r"blade (right|left) corner on the contour")


def corner_lines(filename):
    """``{line number: +1 or -1}`` for the lines of a contour the program
    says it cuts with the blade's right corner (+1) or its left (-1): every
    line after that comment up to the next comment. ``{}`` when the file
    cannot be read."""
    corners = {}
    corner = 0
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as handle:
            for number, line in enumerate(handle, start=1):
                text = line.strip().lstrip("/").strip()
                if not text:
                    continue
                found = _CORNER.search(text)
                if found:
                    corner = 1 if found.group(1) == "right" else -1
                elif text.startswith(("(", ";")):
                    corner = 0
                elif corner:
                    corners[number] = corner
    except OSError as exc:
        LOG.debug("backplot: cannot read %s for its contours: %s", filename, exc)
    return corners


def blade_offsets(description):
    """``(shift, half)`` in millimetres for a tool as ``tool_source.describe``
    gives it: how far along Z its middle is from the point it was touched off
    on, and half its width; ``(0, 0)`` for anything that is not a blade."""
    from teachinlathe.ui.tabs.programs.backplot.tool_source import BladeDrawing
    if not isinstance(description, BladeDrawing):
        return 0.0, 0.0
    half = float(description.width) / 2.0
    return -int(description.control) * half, half


def centre_program(geometry, describe, internal_per_mm, tool_in=0, corners=None):
    """Move the program's vertices along Z, blade by blade, from the point
    each was touched off on to its middle, in place, before anything draws
    them. Keeps ``geometry.blade_middle`` (the vertices at the blade's middle)
    and ``geometry.blade_half`` (half the width of the blade at each, 0 for
    any other tool), in the scene's unit, for the profile the blade cuts.
    ``tool_in``: the tool for the moves before the program changes to one -
    the one in the spindle. ``internal_per_mm``: the scene's unit, per mm.
    ``corners``: corner_lines' - a contour's vertices drawn along the corner
    it is cut with, half the blade's width on from its middle."""
    if np is None or geometry is None:
        return
    try:
        count = len(geometry.positions(0))
        tools = np.asarray(geometry.tools)
        numbers = list(getattr(geometry, "tool_numbers", None) or [])
        middle = np.array(geometry.positions(0), dtype=float)
    except (AttributeError, IndexError, TypeError) as exc:
        LOG.debug("backplot: no program to centre the blades of: %s", exc)
        return
    if count == 0:
        return
    shift = np.zeros(count)
    half = np.zeros(count)
    for index in np.unique(tools):
        index = int(index)
        number = numbers[index] if index < len(numbers) else None
        number = number or tool_in
        if not number:
            continue
        try:
            s, h = blade_offsets(describe(int(number)))
        except Exception as exc:        # bad data must not stop the plot drawing
            LOG.warning("backplot: cannot describe T%s: %s", number, exc)
            continue
        rows = tools == index
        shift[rows] = s * internal_per_mm
        half[rows] = h * internal_per_mm
    if not half.any():
        return
    middle[:, 2] += shift
    geometry.blade_middle = middle
    geometry.blade_half = half
    drawn = middle[:, 2].copy()
    if corners:
        lines = np.asarray(geometry.lines)
        corner = np.array([corners.get(int(line), 0) for line in lines], dtype=float)
        drawn += corner * half
    _move_dwells(geometry, drawn - np.asarray(geometry.positions(0)[:, 2], dtype=float))
    # the arrays the parse wrapped are read-only: each plane copied once
    planes = geometry._planes
    for p, plane in enumerate(planes):
        if not plane.flags.writeable:
            plane = plane.copy()
            planes[p] = plane
        plane["pos"][:count, 2] = drawn


def _move_dwells(geometry, shift):
    """The dwell markers moved as the vertices of their lines are moved to
    the blade's middle (``shift``, per vertex) - they are a table of their
    own, the cross drawn at each, so the vertices' move leaves them behind.
    A dwell is at the bottom of a plunge: its middle, not a corner."""
    dwells = list(getattr(geometry, "dwells", None) or [])
    if not dwells:
        return
    try:
        lines = np.asarray(geometry.lines)
    except (AttributeError, TypeError):
        return
    moved = []
    for lineno, rgba, plane_code, points in dwells:
        rows = np.nonzero(lines == lineno)[0]
        dz = float(shift[rows[-1]]) if len(rows) else 0.0
        if dz:
            points = tuple(_moved_point(point, dz) for point in points)
        moved.append((lineno, rgba, plane_code, points))
    geometry.dwells = moved


def _moved_point(point, dz):
    """``point`` (x, y, z) - a tuple or an array, as the table holds it - with
    ``dz`` on its Z."""
    if hasattr(point, "copy"):
        point = point.copy()
        point[2] += dz
        return point
    return type(point)((point[0], point[1], point[2] + dz))


def trail_shifts(origins, corners, units, offsets_of):
    """How far along Z each point of a trail is moved to be drawn as the
    program is for a blade: by the blade that made it - ``offsets_of(tool)``,
    its ``(shift, half)`` as blade_offsets gives them - and the line it was
    cutting, a contour's along the corner ``corners`` (corner_lines') says.
    ``origins``: the trail's TrailOrigins, or a slice of them; ``units``: the
    trail's unit per mm. An array, one shift a point."""
    tools, lines = np.asarray(origins.tools), np.asarray(origins.lines)
    shifts = np.zeros(len(tools))
    corner = _corner_of(lines, corners)
    for tool in np.unique(tools):
        tool = int(tool)
        if not tool:
            continue
        shift, half = offsets_of(tool)
        if not (shift or half):
            continue
        rows = tools == tool
        shifts[rows] = (shift + corner[rows] * half) * units
    return shifts


def _corner_of(lines, corners):
    """The corner (+1, -1, 0) each of ``lines`` is cut along."""
    if not corners or not len(lines):
        return np.zeros(len(lines))
    table = np.zeros(max(corners) + 1)
    for number, corner in corners.items():
        table[number] = corner
    inside = (lines >= 0) & (lines < len(table))
    corner = np.zeros(len(lines))
    corner[inside] = table[lines[inside]]
    return corner


def trail_points(raw, npts, shifts):
    """The position logger's points as ``raw`` holds them, each moved along
    Z by its own of ``shifts`` (in the logger's unit), as bytes."""
    points = np.frombuffer(raw, dtype=LOGGER_DTYPE, count=npts).copy()
    points["pos"][:, 2] += shifts[:npts]
    return points.tobytes()


def swept(starts, ends, half):
    """Moves of a blade ``half`` wide either side of the point that made them
    - its middle - as the moves of its end's edge: each moved ``half`` back and
    on along Z, and the edge across at either end. ``starts``, ``ends``:
    ``(N, 3)`` arrays, Z in the last column; ``half`` one per move, in their
    unit. A column the blade passed over then takes the radius it cut there."""
    half = np.broadcast_to(np.asarray(half, dtype=float), (len(starts),))
    wide = half > 0
    if not wide.any():
        return starts, ends
    s, e = starts[wide], ends[wide]
    along = np.zeros_like(s)
    along[:, 2] = half[wide]
    return (np.concatenate([starts[~wide], s - along, s + along, s - along, e - along]),
            np.concatenate([ends[~wide], e - along, e + along, s + along, e + along]))
