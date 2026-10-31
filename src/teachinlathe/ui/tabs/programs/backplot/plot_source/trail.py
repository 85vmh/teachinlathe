"""The trail the plot draws: the points the tool's tip went through, each in
the colour of its motion, as LinuxCNC's renderer reads a position logger -
and, for each point, what made it (TrailOrigins): the tool, and the line of
the program cutting it. The blade's trail is drawn by those (actors.trail),
and the material is cut with those tools, whichever source made the trail.

Two trails: the machine's position logger (LoggerTrail), told on each poll
what the machine is doing, and a simulated run's moves (RunTrail).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Sequence

LOG = logging.getLogger(__name__)

try:
    import numpy as np
    from rs274.glcanon_bake import LOGGER_DTYPE
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot trail: preview modules unavailable: %s", exc)
    np = None

#: The position logger's colours, in the order it is given them - and its
#: index of each: the machine's motion type (EMC_MOTION_TYPE_*), 0 a jog.
COLOR_NAMES = ("backplotjog", "backplottraverse", "backplotfeed", "backplotarc",
               "backplottoolchange", "backplotprobing")
TRAVERSE, FEED, ARC, TOOL_CHANGE = 1, 2, 3, 4


def _empty_ints():
    return np.zeros(0, dtype=np.int64)


@dataclass(frozen=True)
class TrailOrigins:
    """What made each point of a trail: ``tools`` the T number, ``lines``
    the line of the program it was cutting - 0 for a line of another file (a
    tool change's subroutine). Two arrays, one entry a point."""
    tools: "np.ndarray"
    lines: "np.ndarray"

    @classmethod
    def none(cls) -> "TrailOrigins":
        return cls(_empty_ints(), _empty_ints())

    def __len__(self):
        return len(self.tools)


class Trail(ABC):
    """A trail, as LinuxCNC's renderer reads a ``linuxcnc.positionlogger``:
    ``points()``, ``npts``, ``last()``, the colours, ``clear()``. What made
    each point, ``made_by()``. ``generation`` changes when the points shown
    stop being those shown before plus new ones - cleared, read again - so
    what is worked out point by point is worked out again."""

    def __init__(self, colors: Sequence[Sequence[int]]):
        self._colors = [tuple(int(v) for v in color) for color in colors]
        self.generation = 0

    @abstractmethod
    def points(self):
        """``(bytes, npts, is_xyuv)``: the points as LOGGER_DTYPE records."""

    @property
    @abstractmethod
    def npts(self) -> int:
        """How many points there are."""

    @abstractmethod
    def last(self, _flag=True) -> Optional[tuple]:
        """The last point, (x, y, z, a, b, c), machine units; None with none."""

    @abstractmethod
    def made_by(self) -> TrailOrigins:
        """What made each of the points ``points()`` gives."""

    @abstractmethod
    def clear(self) -> None:
        """The points so far wiped, as the clear button wipes them."""

    def get_colors(self):
        return list(self._colors)

    def set_colors(self, *_args):
        pass

    def set_depth(self, *_args):
        pass

    def start(self, *_args):
        pass

    def stop(self):
        pass

    def call(self):
        pass

    def _next_generation(self):
        self.generation += 1


class LoggerTrail(Trail):
    """The machine's trail: its position logger, running on a thread of its
    own, and what made each point - noted on each poll (``observe``) for the
    points logged since, the tool in and the line run then."""

    def __init__(self, logger, colors):
        super().__init__(colors)
        self._logger = logger
        self._tools = _empty_ints() if np is not None else None
        self._lines = _empty_ints() if np is not None else None

    def points(self):
        return self._logger.points()

    @property
    def npts(self):
        return int(getattr(self._logger, "npts", 0) or 0)

    def last(self, flag=True):
        return self._logger.last(flag)

    def get_colors(self):
        return self._logger.get_colors()

    def set_colors(self, *args):
        self._logger.set_colors(*args)

    def set_depth(self, *args):
        self._logger.set_depth(*args)

    def start(self, *args):
        self._logger.start(*args)

    def stop(self):
        self._logger.stop()

    def call(self):
        self._logger.call()

    def clear(self):
        self._logger.clear()
        self._forget()

    def observe(self, tool: int, line: int) -> None:
        """The points logged since the last poll were made with ``tool`` on
        ``line``. A logger that has fewer points than it had was cleared, or
        was full and moved its points down: from the start again."""
        if np is None:
            return
        npts = self.npts
        if npts < len(self._tools):
            self._forget()
        new = npts - len(self._tools)
        if new > 0:
            self._tools = np.concatenate([self._tools, np.full(new, int(tool), dtype=np.int64)])
            self._lines = np.concatenate([self._lines, np.full(new, int(line), dtype=np.int64)])

    def made_by(self):
        if np is None:
            return None
        return TrailOrigins(self._tools, self._lines)

    def _forget(self):
        if np is not None:
            self._tools, self._lines = _empty_ints(), _empty_ints()
        self._next_generation()


class RunTrail(Trail):
    """A simulated run's trail (simulation.logic.program_run.ProgramRun): the
    points of its moves up to the moment shown, in the frame it started from,
    and what made each, as its moves say."""

    def __init__(self, colors):
        super().__init__(colors)
        self._master = None             # every point of the run, LOGGER_DTYPE
        self._ends = []                 # how many points there are once each step is done
        self._step_colors = {}          # each move's colour, by its step
        self._run = None
        self._program_file = ""
        self._frame = (0.0, 0.0, 1.0)   # the work origin's X, Z in machine units; machine units per mm
        self._made_by = TrailOrigins.none() if np is not None else None
        self._shown = np.zeros(0, dtype=LOGGER_DTYPE) if np is not None else None
        self._shown_made_by = self._made_by
        self._skip = 0

    def set_run(self, run, origin, units, program_file):
        """The trail of ``run``: ``origin`` the work origin it started from,
        (x, z) machine units; ``units`` machine units per mm; a point's line
        counts on ``program_file`` alone."""
        from teachinlathe.simulation.logic.program_run import move_points
        from teachinlathe.simulation.model.moves import Move, MoveKind

        self._run, self._skip = run, 0
        self._next_generation()
        if run is None or np is None:
            self._master, self._ends = None, []
            return
        self._frame = (origin[0], origin[1], units)
        colours = {MoveKind.RAPID: TRAVERSE, MoveKind.FEED: FEED, MoveKind.ARC: ARC,
                   MoveKind.TOOL_CHANGE: TOOL_CHANGE}
        points, colors, ends, self._step_colors = [], [], [], {}
        tools, lines = [], []
        start = run.program.start
        if start is not None:
            points.append(tuple(start))
            colors.append(TRAVERSE)
            tools.append(run.program.start_tool)
            lines.append(0)
        for step in run.program.steps:
            if isinstance(step, Move):
                self._step_colors[len(ends)] = colours[step.kind]
                drawn = move_points(step)
                line = _line(step.where, program_file)
                if not points:
                    points.append(drawn[0])
                    colors.append(colours[step.kind])
                    tools.append(step.tool)
                    lines.append(line)
                points.extend(drawn[1:])
                colors.extend([colours[step.kind]] * (len(drawn) - 1))
                tools.extend([step.tool] * (len(drawn) - 1))
                lines.extend([line] * (len(drawn) - 1))
            ends.append(len(points))
        self._master = self._points(points, colors)
        self._made_by = TrailOrigins(np.asarray(tools, dtype=np.int64), np.asarray(lines, dtype=np.int64))
        self._ends = ends
        self._program_file = program_file

    def show(self, step: Optional[int], fraction: float) -> None:
        """The trail at step ``step`` of the run, ``fraction`` of it done; none
        with no step."""
        from teachinlathe.simulation.logic.program_run import move_points
        from teachinlathe.simulation.model.moves import Move

        if np is None:
            return
        if self._master is None or step is None:
            self._shown = np.zeros(0, dtype=LOGGER_DTYPE)
            self._shown_made_by = TrailOrigins.none()
            return
        before = len(self._shown)
        done = self._ends[step - 1] if step > 0 else (1 if self._run.program.start is not None else 0)
        trail = self._master[:done]
        tools, lines = self._made_by.tools[:done], self._made_by.lines[:done]
        current = self._run.program.steps[step] if step < len(self._run.program.steps) else None
        if isinstance(current, Move) and 0.0 < fraction < 1.0:
            partial = move_points(current, fraction)[1:]
            extra = self._points(partial, [self._step_colors.get(step, FEED)] * len(partial))
            trail = np.concatenate([trail, extra])
            line = _line(current.where, self._program_file)
            tools = np.concatenate([tools, np.full(len(partial), current.tool, dtype=np.int64)])
            lines = np.concatenate([lines, np.full(len(partial), line, dtype=np.int64)])
        self._shown = trail
        self._shown_made_by = TrailOrigins(tools, lines)
        if len(trail) < before:
            # gone back: not the points shown before and new ones
            self._next_generation()

    def _points(self, points, colors):
        """(z, r) points in mm, with their colours, as logger points."""
        out = np.zeros(len(points), dtype=LOGGER_DTYPE)
        if not points:
            return out
        x0, z0, units = self._frame
        zr = np.asarray(points, dtype=float)
        out["pos"][:, 0] = zr[:, 1] * units + x0
        out["pos"][:, 2] = zr[:, 0] * units + z0
        out["c"] = np.asarray([self._colors[c] for c in colors], dtype=np.uint8)
        out["pos2"] = out["pos"]
        out["c2"] = out["c"]
        return out

    # ── what the renderer reads ──────────────────────────────────────────

    def points(self):
        shown = self._shown[self._skip:] if self._shown is not None else None
        if shown is None:
            return b"", 0, False
        return shown.tobytes(), len(shown), False

    @property
    def npts(self):
        return max(0, len(self._shown) - self._skip) if self._shown is not None else 0

    def last(self, _flag=True):
        if self._shown is None or not len(self._shown):
            return None
        x, y, z = (float(v) for v in self._shown["pos"][-1])
        return (x, y, z, 0.0, 0.0, 0.0)

    def made_by(self):
        if self._shown_made_by is None:
            return None
        return TrailOrigins(self._shown_made_by.tools[self._skip:], self._shown_made_by.lines[self._skip:])

    def clear(self):
        self._skip = len(self._shown) if self._shown is not None else 0
        self._next_generation()


def _line(where, program_file: str) -> int:
    """The line of the program a step was made on: 0 for a line of another
    file."""
    import os

    if program_file and where.file and os.path.abspath(where.file) != os.path.abspath(program_file):
        return 0
    return int(where.line)
