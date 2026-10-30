"""A program run on its stock as the machine runs it (ProgramRun): the moves
the interpreter made of its G-code (simulation.model.moves) one after the
other, in time, the tool taking off the stock what it goes through.

What is cut is as material.py has it - the tool's cutting outline swept
along each feed, turned about the axis - the model the backplot cuts the
machine's own trail with too. A move synced with the spindle (G33, G33.1, G76) cuts
a thread, not all round, and takes nothing off here. A rapid - or the move
to the tool change position - that goes through the material is a collision:
it is kept (``collisions``), and takes nothing off either.

The stock is in (z, r) - r the radius - in the work coordinates of cycle
start, as the moves are. Seeking anywhere is quick: the stock is kept at
every operation's start and every few seconds of the run (KEYFRAME_SECONDS),
and from there the moves up to the moment are cut again; going forward a
little at a time - playing - goes on from the moment before. It pickles,
worked out in one process and played in another.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from shapely.geometry import Polygon

from teachinlathe.conversational.gcode.operations.profiling.shapes import _on_grid, goes_through
from teachinlathe.conversational.gcode.operations.profiling.tool_shape import ToolShape
from teachinlathe.conversational.gcode.toolpath import arc_points
from teachinlathe.simulation.logic import material as cutting
from teachinlathe.simulation.model.moves import (
    At, Dwell, Move, MoveKind, OperationStart, OriginShift, ProgramMoves, Step, Stop, StopKind, ToolChange,
)

#: Seconds of the run between two kept stocks, besides each operation's start.
KEYFRAME_SECONDS = 5.0

#: What a step takes when the program is not timed (no machine limits): the
#: run then goes a move a second.
UNTIMED_SECONDS = 1.0


class MarkKind(Enum):
    """What a mark on the run's timeline is."""
    OPERATION = "operation"         # an operation starts
    TOOL_CHANGE = "tool_change"     # a tool is loaded
    STOP = "stop"                   # M0, or M1 - it waits for cycle start there
    END = "end"                     # M2/M30


@dataclass(frozen=True)
class Mark:
    """A moment of the run a seek bar shows, and jumps to: at ``time``, the
    run's step ``step`` is ``kind`` - an operation (``number``, ``label`` its
    title), a tool change (``number`` the tool), a stop (``label`` "M0" or
    "M1")."""
    time: float
    step: int
    kind: MarkKind
    number: int = 0
    label: str = ""


@dataclass(frozen=True)
class Collision:
    """A rapid of the run - step ``step``, starting at ``time`` - that goes
    through the material there is then."""
    time: float
    step: int
    move: Move


@dataclass(frozen=True)
class Moment:
    """The run at ``time``: the tool's tip at ``at`` (None before it is
    known), ``tool`` the current loaded tool, the run in step ``step`` - the one
    under way, or the last one done - the stock, ``material``, a shapely
    shape in (z, r), and where the program has its work origin then
    (``origin``, moved from cycle start's by a G10 L20 or a G92) and in which
    work offset (``work_offset``, 1 for G54 ... 9 for G59.3)."""
    time: float
    at: Optional[At]
    tool: int
    step: int
    material: object
    origin: At = At(0.0, 0.0)
    work_offset: int = 1


@dataclass(frozen=True)
class _Kept:
    """The stock when step ``step`` starts: what the steps before it left."""
    step: int
    material: object


class ProgramRun:
    """``program`` run on ``material`` (a shapely shape in (z, r), the stock
    at cycle start), each tool cutting as ``shapes`` says: its cutting
    outline by T number (tool_shapes), none for one that cuts nothing known
    all round."""

    def __init__(self, program: ProgramMoves, material, shapes: Mapping[int, ToolShape],
                 keyframe_seconds: float = KEYFRAME_SECONDS):
        self.program = program
        self.shapes: Dict[int, ToolShape] = dict(shapes)
        self._steps: Tuple[Step, ...] = program.steps
        self._starts, self._ends = _schedule(self._steps)
        self.duration = self._ends[-1] if self._ends else 0.0
        self.marks = tuple(self._marks())
        self._origins = _origins(self._steps, program.start_work_offset)
        self.collisions: Tuple[Collision, ...] = ()
        self._kept: List[_Kept] = []
        self._run_through(_on_grid(material) if not material.is_empty else Polygon(), keyframe_seconds)
        # where the last moment asked was: playing goes on from there
        self._cursor = self._kept[0] if self._kept else _Kept(0, Polygon())

    def shape_of(self, tool: int) -> Optional[ToolShape]:
        return self.shapes.get(tool)

    @property
    def timed(self) -> bool:
        """Whether its times are the machine's (LinuxCNC's estimate), not a move a second."""
        return self.program.duration is not None

    def start_of(self, step: int) -> float:
        return self._starts[step] if step < len(self._starts) else self.duration

    # ── the run, once through ────────────────────────────────────────────

    def _run_through(self, material, keyframe_seconds: float):
        collisions, next_kept = [], 0.0
        for index, step in enumerate(self._steps):
            if isinstance(step, OperationStart) or self._starts[index] >= next_kept or index == 0:
                self._kept.append(_Kept(index, material))
                next_kept = self._starts[index] + keyframe_seconds
            if not isinstance(step, Move):
                continue
            if _cuts(step):
                material = self._cut(material, step, 1.0)
            elif self._hits(material, step):
                collisions.append(Collision(self._starts[index], index, step))
        self._kept.append(_Kept(len(self._steps), material))
        self.collisions = tuple(collisions)

    def _cut(self, material, move: Move, fraction: float):
        """``material`` less what ``move`` takes off it, up to ``fraction`` of it."""
        return cutting.cut(material, move_points(move, fraction), self.shape_of(move.tool))

    def _hits(self, material, move: Move) -> bool:
        """Whether rapid ``move`` goes through ``material``."""
        tool = self.shape_of(move.tool)
        return goes_through(material, move_points(move, 1.0), tool.outline if tool is not None else None)

    def _marks(self):
        for index, step in enumerate(self._steps):
            time = self._starts[index]
            if isinstance(step, OperationStart):
                yield Mark(time, index, MarkKind.OPERATION, step.number, step.title)
            elif isinstance(step, ToolChange):
                yield Mark(time, index, MarkKind.TOOL_CHANGE, step.tool)
            elif isinstance(step, Stop):
                kind = MarkKind.END if step.kind is StopKind.PROGRAM_END else MarkKind.STOP
                yield Mark(time, index, kind, label=step.kind.value)

    # ── a moment of it ───────────────────────────────────────────────────

    def at(self, time: float) -> Moment:
        """The run at ``time`` seconds from cycle start."""
        time = min(max(time, 0.0), self.duration)
        # the step under way: the last one started by then
        step = max(bisect.bisect_right(self._starts, time) - 1, 0)
        kept = self._cursor if self._cursor.step <= step else None
        if kept is None or self._starts_of(kept) < self._starts_of(self._kept_before(step)):
            kept = self._kept_before(step)
        material = kept.material
        for index in range(kept.step, step):
            done = self._steps[index]
            if isinstance(done, Move) and _cuts(done):
                material = self._cut(material, done, 1.0)
        self._cursor = _Kept(step, material)
        current = self._steps[step] if step < len(self._steps) else None
        fraction = self.fraction(step, time)
        if isinstance(current, Move) and _cuts(current) and fraction > 0.0:
            material = self._cut(material, current, fraction)
        origin, work_offset = (self._origins[min(step, len(self._origins) - 1)] if self._origins
                               else (At(0.0, 0.0), self.program.start_work_offset))
        return Moment(time, self._tip(step, fraction), self._tool(step), step, material, origin, work_offset)

    def _starts_of(self, kept: _Kept) -> float:
        return self.start_of(kept.step)

    def _kept_before(self, step: int) -> _Kept:
        index = bisect.bisect_right([kept.step for kept in self._kept], step) - 1
        return self._kept[max(index, 0)]

    def fraction(self, step: int, time: float) -> float:
        """How much of step ``step`` is done at ``time``, 0..1."""
        if step >= len(self._steps):
            return 1.0
        start, end = self._starts[step], self._ends[step]
        return 1.0 if end <= start else min(max((time - start) / (end - start), 0.0), 1.0)

    def _tip(self, step: int, fraction: float) -> Optional[At]:
        """Where the tip is in step ``step``, ``fraction`` of it done."""
        for index in range(min(step, len(self._steps) - 1), -1, -1):
            move = self._steps[index]
            if isinstance(move, Move):
                if index == step:
                    return At(*move_points(move, fraction)[-1])
                return move.end
        return self.program.start

    def _tool(self, step: int) -> int:
        for index in range(min(step, len(self._steps) - 1), -1, -1):
            item = self._steps[index]
            if isinstance(item, Move):
                return item.tool
            if isinstance(item, ToolChange):
                return item.tool
        return self.program.start_tool


def _cuts(move: Move) -> bool:
    """A feed that takes off all round: not a rapid, not synced with the spindle."""
    return move.kind in (MoveKind.FEED, MoveKind.ARC) and move.spindle.sync_pitch == 0.0


def _origins(steps: Sequence[Step], work_offset: int) -> List[Tuple[At, int]]:
    """Where the work origin is at each step, and in which work offset:
    cycle start's - ``work_offset`` - until an OriginShift moves it."""
    origins, origin = [], (At(0.0, 0.0), work_offset)
    for step in steps:
        if isinstance(step, OriginShift):
            origin = (step.origin, step.work_offset)
        origins.append(origin)
    return origins


def _schedule(steps: Sequence[Step]) -> Tuple[List[float], List[float]]:
    """When each step starts and ends: the estimate's times, steps with
    none - stops, operation starts - taking no time; a move a second when
    the program is not timed."""
    starts, ends, clock = [], [], 0.0
    timed = any(getattr(step, "ends_at", None) is not None for step in steps)
    for step in steps:
        starts.append(clock)
        if timed:
            ends_at = getattr(step, "ends_at", None)
            clock = max(clock, ends_at) if ends_at is not None else clock
        elif isinstance(step, (Move, Dwell, ToolChange)):
            clock += UNTIMED_SECONDS
        ends.append(clock)
    return starts, ends


def move_points(move: Move, fraction: float = 1.0) -> List[Tuple[float, float]]:
    """The (z, r) points ``move`` goes through, up to ``fraction`` of its length."""
    if move.kind is MoveKind.ARC and move.center is not None:
        inner = arc_points(move.start.z, move.start.r, move.end.z, move.end.r,
                           move.center.z, move.center.r, not move.ccw)
        points = [tuple(move.start)] + inner + [tuple(move.end)]
    else:
        points = [tuple(move.start), tuple(move.end)]
    if fraction >= 1.0:
        return points
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    left = sum(lengths) * max(fraction, 0.0)
    out = [points[0]]
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if left >= length:
            out.append(b)
            left -= length
            continue
        t = left / length if length > 0 else 0.0
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        break
    if len(out) == 1:
        out.append(points[0])
    return out


def tool_shapes(tools, program: ProgramMoves) -> Dict[int, ToolShape]:
    """What cuts of each tool ``program`` moves with - its T number, the
    holder it is in - of ``tools`` (the Tool Library, a ToolSnapshot):
    ProgramRun's shapes."""
    from teachinlathe.conversational.gcode.operations.profiling.tool_shape import cutting_shape
    from teachinlathe.tooling.model.data_types import MountedTool

    shapes = {}
    for tool in sorted({move.tool for move in program.moves if move.tool}):
        shape = cutting_shape(MountedTool.of(tools, tool))
        if shape is not None:
            shapes[tool] = shape
    return shapes
