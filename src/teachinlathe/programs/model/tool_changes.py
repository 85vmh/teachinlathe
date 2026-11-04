"""The tool changes of a program and when they come, for the Programs
screen's tool box: the current loaded tool, the next one and how long until
the machine stops for it.

A ToolChangePlan is made from the program's moves as the interpreter reads
them (core.gcode_moves.read_moves, in the planning worker) and kept small,
to come back through the pipe: for each move, the line it comes from and
when it starts and ends; for each tool change, the tool and when the machine
gets to it. While the program runs, ``locate`` finds the move the machine is
making from the line linuxcnc.stat() reports and where the tool is.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import NamedTuple, Optional, Tuple

from teachinlathe.simulation.model.moves import Move, ProgramMoves, ToolChange, Where

#: How far, mm, the tool may be off a move and still be on it: what decides,
#: of the moves a single line makes (a canned cycle), which one is being made.
ON_MOVE_MM = 0.05


class LineKey(NamedTuple):
    """A line of the G-code as linuxcnc.stat() reports the one being run:
    ``depth`` calls deep, ``program_line`` the program's own line (the
    call's, inside a subroutine) and ``line`` the line of the file it is in."""
    depth: int
    program_line: int
    line: int

    @classmethod
    def of(cls, where: Where) -> "LineKey":
        return cls(where.depth, where.program_line, where.line)


@dataclass(frozen=True)
class Segment:
    """A move: where it comes from, the points of the work (z, r) in mm it
    goes through - ``center`` and ``ccw`` for an arc - and when it starts
    and ends, seconds from cycle start (None, not timed)."""
    key: LineKey
    start: Tuple[float, float]
    end: Tuple[float, float]
    starts_at: Optional[float]
    ends_at: Optional[float]
    center: Optional[Tuple[float, float]] = None
    ccw: bool = False

    def distance_and_fraction(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """How far ``point`` is off the move, mm, and how much of it, 0..1,
        lies before the nearest point on it."""
        if self.center is not None:
            return self._arc(point)
        (z0, r0), (z1, r1) = self.start, self.end
        dz, dr = z1 - z0, r1 - r0
        length2 = dz * dz + dr * dr
        if length2 <= 0.0:
            return math.hypot(point[0] - z0, point[1] - r0), 1.0
        fraction = min(1.0, max(0.0, ((point[0] - z0) * dz + (point[1] - r0) * dr) / length2))
        return math.hypot(point[0] - (z0 + fraction * dz), point[1] - (r0 + fraction * dr)), fraction

    def _arc(self, point):
        cz, cr = self.center
        radius = math.hypot(self.start[0] - cz, self.start[1] - cr)
        a0 = math.atan2(self.start[1] - cr, self.start[0] - cz)
        a1 = math.atan2(self.end[1] - cr, self.end[0] - cz)
        at = math.atan2(point[1] - cr, point[0] - cz)
        sweep = _turn(a0, a1, self.ccw) or 2.0 * math.pi
        fraction = min(1.0, _turn(a0, at, self.ccw) / sweep)
        return abs(math.hypot(point[0] - cz, point[1] - cr) - radius), fraction


def _turn(a_from: float, a_to: float, ccw: bool) -> float:
    """The angle, 0..2pi, turned from ``a_from`` to ``a_to`` in the arc's sense."""
    turn = (a_to - a_from) if ccw else (a_from - a_to)
    return turn % (2.0 * math.pi)


@dataclass(frozen=True)
class Change:
    """Tool ``tool`` is put in after move ``after`` (the index of the last
    move before it; -1, before any), the machine there at ``at`` seconds
    from cycle start (None, not timed)."""
    tool: int
    after: int
    at: Optional[float]


@dataclass(frozen=True)
class NextTool:
    """The tool that comes next and in how many seconds the machine stops for
    it (None while the program is not running, or not timed)."""
    tool: int
    seconds: Optional[float]


@dataclass(frozen=True)
class ToolChangePlan:
    """A program's moves, as Segments, and its tool changes, in order;
    how long it runs (``duration``, seconds; None, not timed)."""
    segments: Tuple[Segment, ...]
    changes: Tuple[Change, ...]
    duration: Optional[float] = None

    @classmethod
    def of(cls, moves: ProgramMoves) -> "ToolChangePlan":
        segments, changes = [], []
        ended_at = 0.0 if moves.duration is not None else None
        for step in moves.steps:
            if isinstance(step, Move):
                starts_at = ended_at
                ended_at = step.ends_at if step.ends_at is not None else ended_at
                segments.append(Segment(LineKey.of(step.where), tuple(step.start), tuple(step.end), starts_at,
                                        ended_at, tuple(step.center) if step.center is not None else None,
                                        step.ccw))
            elif isinstance(step, ToolChange):
                # the machine is at the tool change when the move there ends
                changes.append(Change(int(step.tool), len(segments) - 1, ended_at))
                ended_at = step.ends_at if step.ends_at is not None else ended_at
            elif getattr(step, "ends_at", None) is not None:
                ended_at = step.ends_at
        return cls(tuple(segments), tuple(changes), moves.duration)

    def next_tool(self, current_tool: int, after: int = -1) -> Optional[int]:
        """The first tool other than ``current_tool`` put in after move
        ``after`` or later (-1: from the start), None with none."""
        change = self._next_change(current_tool, after)
        return None if change is None else change.tool

    def next_tool_at(self, current_tool: int, index: int, point: Tuple[float, float]) -> Optional[NextTool]:
        """The next tool once the machine is ``point`` (z, r, mm) on move
        ``index``, and in how many seconds it gets to its change."""
        change = self._next_change(current_tool, index)
        if change is None:
            return None
        now = self.time_at(index, point)
        seconds = None if now is None or change.at is None else max(0.0, change.at - now)
        return NextTool(change.tool, seconds)

    def _next_change(self, current_tool, after):
        for change in self.changes:
            if change.after >= after and change.tool != current_tool:
                return change
        return None

    def time_at(self, index: int, point: Tuple[float, float]) -> Optional[float]:
        """Seconds from cycle start with the tool at ``point`` on move ``index``."""
        if not 0 <= index < len(self.segments):
            return None
        segment = self.segments[index]
        if segment.starts_at is None or segment.ends_at is None:
            return None
        _distance, fraction = segment.distance_and_fraction(point)
        return segment.starts_at + fraction * (segment.ends_at - segment.starts_at)

    def locate(self, key: LineKey, point: Tuple[float, float], from_index: int = 0) -> Optional[int]:
        """The move made from line ``key`` with the tool at ``point``, the
        first from move ``from_index`` on - the machine goes forward, and a
        line in a loop or a subroutine called again is run more than once.
        Of the moves one line makes, the first the tool is on; none on, the
        nearest. With no move from that line, the first move from the same
        program line; None, with none of those either."""
        from_index = max(0, from_index)
        segments = self.segments
        first = next((i for i in range(from_index, len(segments)) if segments[i].key == key), None)
        if first is None:
            return next((i for i in range(from_index, len(segments))
                         if segments[i].key.program_line == key.program_line), None)
        best, best_distance = first, math.inf
        index = first
        while index < len(segments) and segments[index].key == key:
            distance, _fraction = segments[index].distance_and_fraction(point)
            if distance <= ON_MOVE_MM:
                return index
            if distance < best_distance:
                best, best_distance = index, distance
            index += 1
        return best
