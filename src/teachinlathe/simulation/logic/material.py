"""What a tool takes off a turned part: the one model of it, for a simulation
(program_run.ProgramRun) and for the machine's own trail as it runs
(MaterialLeft, which the backplot keeps).

The part (Part) is shapely shapes in (z, r) - r the radius. What a tool
takes off going along a move is its cutting outline (tool_shape.cutting_shape)
swept along it, turned about the axis (shapes.turned): what it cuts on one
side it cuts all round. Whether a rapid goes through the part is
shapes.goes_through, as the conversational G-code checks it.

A move synced with the spindle (G33, G76's passes) cuts a thread instead: the
spindle turns as the tool goes along, so a section of the part through the
axis is under the tool only once a turn, and there the tooth (its outline)
leaves its V - one every turn, a pitch apart, along the move. A Part keeps
two such sections, the two halves a plot shows: the one the tool is drawn on
(``TOOL_SIDE``, at 0 degrees from the spindle's index) and the one across the
axis from it (``FAR_SIDE``, 180 degrees). On a single start thread the Vs of
one are half a pitch along from the other's, as on the part. Each section is
cut on its own once there is a thread - a V is taken out of it, a cut all
round out of both and what is turned; ``trace`` is the outline of each V
where it went into the material, on the tool's side: one V inside the next,
pass after pass.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from teachinlathe.conversational.gcode.operations.profiling.shapes import (
    MIN_AREA, _difference, _on_grid, sweeps, turned)
from teachinlathe.conversational.gcode.operations.profiling.tool_shape import ToolShape
from teachinlathe.simulation.model.moves import SpindleSync

Point = Tuple[float, float]

#: The two sections of the part a plot shows: where the tool is drawn, and
#: across the axis from it - in degrees from the spindle's index.
TOOL_SIDE, FAR_SIDE = 0, 1
SECTION_ANGLES = (0.0, 180.0)

_EMPTY = Polygon()


class Part:
    """A turned part, as it is cut: ``turned``, the shape that is the same
    all round, and - once a thread is cut in it - its two sections
    (``sections``, by TOOL_SIDE / FAR_SIDE; None before), and on the tool's
    side the ``trace`` of the threading tooth: the outline of each V where it
    went into the material, a tuple of shapely lines, in the order cut. It
    does not change: a cut makes a new one. Two are the same only when they
    are one."""

    def __init__(self, turned_shape=_EMPTY, sections=None, trace=()):
        self.turned = turned_shape
        self.sections = tuple(sections) if sections is not None else None
        self.trace = tuple(trace)

    @property
    def is_empty(self) -> bool:
        return self.turned.is_empty

    @property
    def threaded(self) -> bool:
        return self.sections is not None

    def section(self, side: int):
        """The part through the axis on ``side`` (TOOL_SIDE, FAR_SIDE): what
        is turned, less the thread cut there; a shapely shape in (z, r)."""
        return self.sections[side] if self.sections is not None else self.turned


def part_of(material) -> Part:
    """``material`` - a Part, or a shapely shape in (z, r), the stock (None
    for none) - as a Part."""
    if isinstance(material, Part):
        return material
    if material is None or material.is_empty:
        return Part()
    return Part(_on_grid(material))


def cut(part: Part, points: Sequence[Point], tool: Optional[ToolShape], sync: Optional[SpindleSync] = None) -> Part:
    """``part`` less what ``tool`` going through ``points`` - (z, r), in
    order - takes off it: turned about the axis, or with ``sync`` - the move
    synced with the spindle - a thread. ``part`` itself when it takes
    nothing off, or there is no tool."""
    if tool is None or part.is_empty or len(points) < 2:
        return part
    if sync is not None and sync.pitch > 0.0:
        return _thread_cut(part, points, tool, sync)
    swept = _on_grid(turned(unary_union(sweeps(tool.outline, points))))
    after = _turned_cut(part.turned, swept)
    if after is part.turned:
        return part
    sections = tuple(_turned_cut(section, swept) for section in part.sections) if part.threaded else None
    return Part(after, sections, part.trace)


def _turned_cut(shape, swept):
    return _difference(shape, swept) if swept.intersects(shape) else shape


def _thread_cut(part: Part, points: Sequence[Point], tool: ToolShape, sync: SpindleSync) -> Part:
    """``part`` with the Vs the tooth ``tool`` leaves in each section going
    through ``points`` turning with the spindle as ``sync`` says. A V that
    takes nothing off - in the air, a spring pass, the same line read again -
    is left out, of the section and of the trace."""
    sections = [part.section(side) for side in (TOOL_SIDE, FAR_SIDE)]
    trace, changed = part.trace, False
    for side, angle in enumerate(SECTION_ANGLES):
        stamps = [_placed(tool.outline, at) for at in _under_tool(points, sync, angle)]
        if not stamps:
            continue
        before = sections[side]
        # what of the section is round them: each V is weighed against that
        bounds = [stamp.bounds for stamp in stamps]
        near = before.intersection(box(min(b[0] for b in bounds), min(b[1] for b in bounds),
                                       max(b[2] for b in bounds), max(b[3] for b in bounds)))
        cutting = [stamp for stamp in stamps if stamp.intersection(near).area > MIN_AREA]
        if not cutting:
            continue
        if side == TOOL_SIDE:
            lines = (stamp.exterior.intersection(near) for stamp in cutting)
            trace += tuple(line for line in lines if not line.is_empty)
        sections[side] = _difference(before, _on_grid(unary_union(cutting)))
        changed = True
    return Part(part.turned, sections, trace) if changed else part


def _under_tool(points: Sequence[Point], sync: SpindleSync, angle: float):
    """Where along ``points`` the tool is when the spindle is at ``angle``
    degrees from its index: the section at that angle under it, once a turn."""
    turn = sync.pitch
    done = 0.0
    for a, b in zip(points, points[1:]):
        length = math.dist(a, b)
        if length <= 0.0:
            continue
        # how far along the move the spindle next comes to the angle
        first = ((angle - sync.angle_after(done)) / 360.0) % 1.0 * turn
        s = first
        while s <= length + 1e-9:
            t = s / length
            yield a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            s += turn
        done += length


def _placed(outline, at: Point) -> Polygon:
    return Polygon([(at[0] + z, at[1] + r) for z, r in outline])


class MaterialLeft:
    """A part as it is being cut: ``material``, a Part, from ``stock`` on,
    less what each cut takes off it (cut). ``version`` counts the cuts that
    changed it, for whatever draws it to know when to draw it again."""

    def __init__(self, stock=None):
        self.material = part_of(stock)
        self.version = 0

    def cut(self, points: Sequence[Point], tool: Optional[ToolShape], sync: Optional[SpindleSync] = None) -> bool:
        """``tool`` through ``points`` (synced with the spindle as ``sync``
        says, if it is): whether it took anything off."""
        after = cut(self.material, points, tool, sync)
        if after is self.material:
            return False
        self.material = after
        self.version += 1
        return True
