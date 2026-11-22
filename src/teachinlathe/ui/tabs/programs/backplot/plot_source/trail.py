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

from teachinlathe.ui.tabs.programs.backplot.plot_source.growing_array import GrowingArray

LOG = logging.getLogger(__name__)

#: The fields of a LOGGER_DTYPE point (rs274.glcanon_bake): where the segment
#: starts and its colour, where it ends and its colour.
POS = "pos"
COLOR = "c"
POS2 = "pos2"
COLOR2 = "c2"
#: The fields of a SYNC_DTYPE record.
SYNC_MODE = "mode"
SYNC_PITCH = "pitch"
SYNC_ANGLE = "angle"
#: The position logger's thread.
LOGGER_THREAD = "positionlogger"

try:
    import numpy as np
    from rs274.glcanon_bake import LOGGER_DTYPE
    #: A point's sync with the spindle, as ``positionlogger.sync_points()``
    #: has it: the mode (linuxcnc.SPINDLE_SYNC_*), the pitch (machine units a
    #: turn), the angle from the index the synced motion started at.
    SYNC_DTYPE = np.dtype([(SYNC_MODE, "u1"), ("pad", "u1", 3), (SYNC_PITCH, "f4"), (SYNC_ANGLE, "f4")])
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot trail: preview modules unavailable: %s", exc)
    np = None

try:
    from linuxcnc import SPINDLE_SYNC_POSITION
except ImportError:  # a LinuxCNC without spindle-sync-info: no line is synced as far as is known
    SPINDLE_SYNC_POSITION = None

#: The position logger's colours, in the order it is given them - and its
#: index of each: the machine's motion type (EMC_MOTION_TYPE_*), 0 a jog.
COLOR_NAMES = ("backplotjog", "backplottraverse", "backplotfeed", "backplotarc",
               "backplottoolchange", "backplotprobing")
TRAVERSE, FEED, ARC, TOOL_CHANGE = 1, 2, 3, 4

#: What a line not drawn is coloured: a thread's pass, which the threading
#: tooth's Vs stand for (actors.stock, actors.trail). Fully transparent, so
#: the line is there to the trail, and not to the eye.
HIDDEN_COLOR = (0, 0, 0, 0)


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

    #: Whether the points, once read, stay as they were - only the last moving
    #: on along its line - so that what is worked out point by point is worked
    #: out for the new ones alone. A simulated run's are made again each time.
    appends_only = False

    def __init__(self, colors: Sequence[Sequence[int]]):
        self._colors = [tuple(int(v) for v in color) for color in colors]
        self.generation = 0
        #: points dropped from the front since ``generation`` changed: what is
        #: worked out point by point drops as many, and goes on
        self.dropped = 0

    def sync_points(self):
        """For each point, how the line ending there was synced with the
        spindle: a SYNC_DTYPE array - or None when the trail does not know."""
        return None

    def synced(self, npts: int):
        """For each of the first ``npts`` points, whether the line ending
        there was synced with the spindle on position - a bool array; None
        when none was, or that is not known."""
        return None

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


#: How often the position logger reads the machine's status, seconds.
LOGGER_INTERVAL_S = 0.01
#: How long stopping waits for the logger's thread to end: it ends after one
#: more interval.
LOGGER_JOIN_TIMEOUT_S = 1.0
#: How many of its oldest points a full position logger drops: MAX_POINTS / 10
#: in emcmodule.cc. It holds up to about 131 000 (its buffer doubles from 2
#: until it is past MAX_POINTS, 100 000), then moves its points down by this
#: many - a window sliding along the run.
LOGGER_FLUSH_POINTS = 10000
#: How many points a position logger holds before it flushes: its buffer,
#: 2 at first, doubles (2n + 2) until it is past MAX_POINTS.
LOGGER_CAPACITY_POINTS = 131070
#: What a point takes in the logger: a logger_point and, made with sync=True,
#: a logger_sync - bytes.
LOGGER_POINT_BYTES = 32 + 12


class LoggerTrail(Trail):
    """The machine's trail: its position logger, running on a thread of its
    own while a program runs (``start_logging`` / ``stop_logging``, as the
    BackplotLifecycle says), read once a poll (``refresh``) - the points, how
    each was synced with the spindle, and what made the points logged since:
    the tool in and the line run then. Everything that reads the trail till
    the next poll reads that one copy.

    A ``linuxcnc.positionlogger``'s ``start`` is the thread's loop: it sets the
    point count to 0 and runs until ``stop``, which only asks it to end - it
    ends after one more interval. Started again before it has, the old loop
    sees the request withdrawn and goes on: two threads on one buffer. So
    each start makes a new logger (``make_logger``) and stopping waits for
    the thread to end; a stopped logger is kept, its points still drawn,
    until the trail is reset or cleared.

    A full logger drops its oldest LOGGER_FLUSH_POINTS points: what is noted
    for each point drops them too, and ``dropped`` - the points dropped since
    the trail started (``generation``) - tells whoever works point by point
    to drop as many of theirs, not to start over.

    The tool's tip, ``last()``, is the logger's last point while it runs - the
    marker where the trail ends - and the machine's position (``position``,
    as the logger works it out) while it does not."""

    #: the points read once stay as they were; only the last one may move on
    #: along its line
    appends_only = True

    def __init__(self, make_logger, colors, position=None):
        super().__init__(colors)
        self._make_logger = make_logger
        self._position = position
        self._logger = None
        self._thread = None
        self._depth = None
        self._tools = GrowingArray(np.int64) if np is not None else None
        self._lines = GrowingArray(np.int64) if np is not None else None
        self._synced = GrowingArray(bool) if np is not None else None
        self._any_synced = False
        self._empty()
        #: points dropped from the front since the trail started
        self.dropped = 0
        #: for diagnostics: loggers made, threads that did not end when asked,
        #: the logger's flushes and the points they dropped, all told
        self.loggers_made = 0
        self.threads_left_running = 0
        self.flushes = 0
        self.points_dropped = 0

    # ── its logger ───────────────────────────────────────────────────────

    @property
    def logging(self) -> bool:
        return self._thread is not None

    def start_logging(self) -> None:
        """A new logger, logging from now - the points before it gone.
        Logging already: nothing."""
        import threading

        if self._thread is not None:
            return
        logger = self._make_logger()
        if self._depth is not None:
            logger.set_depth(*self._depth)
        self._logger = logger
        self._empty()
        self._forget()
        self.loggers_made += 1
        self._thread = threading.Thread(target=logger.start, args=(LOGGER_INTERVAL_S,),
                                        name=LOGGER_THREAD, daemon=True)
        self._thread.start()

    def stop_logging(self) -> None:
        """The logger stopped, its thread ended; its points stay. Not logging:
        nothing."""
        thread, self._thread = self._thread, None
        if thread is None:
            return
        self._logger.stop()
        thread.join(LOGGER_JOIN_TIMEOUT_S)
        if thread.is_alive():
            # it is never started again, so it ends on its own once it can
            self.threads_left_running += 1
            LOG.warning("backplot: the position logger's thread did not end in %.1f s",
                        LOGGER_JOIN_TIMEOUT_S)

    def reset(self) -> None:
        """No logger, no points: the trail of the run before is gone."""
        self.stop_logging()
        self._logger = None
        self._empty()
        self._forget()

    def clear(self):
        """Clear Plot: the points wiped. While it logs, a new logger goes on
        from here - the old one is stopped first, so that nothing it logs
        after the clear is mistaken for what it had; a stopped one is let go."""
        logging = self._thread is not None
        self.reset()
        if logging:
            self.start_logging()

    def refresh(self, tool: int, line: int) -> None:
        """The logger's points as they are now, read once for everything that
        reads the trail till the next poll; those logged since the last were
        made with ``tool`` on ``line``."""
        if self._logger is None or np is None:
            return
        raw, npts, _is_xyuv = self._logger.points()
        sync = self._read_sync()
        if sync is not None:
            # read one after the other, the logger adding points between
            npts = min(npts, len(sync))
        points = np.frombuffer(raw, dtype=LOGGER_DTYPE, count=npts)
        dropped = self._dropped_since(points)
        if dropped is None:
            self._forget()
        elif dropped:
            self._drop(dropped)
        self._raw, self._npts, self._points, self._sync = raw, npts, points, sync
        self._note_made_by(npts, tool, line)
        self._note_synced(npts, sync)

    def _read_sync(self):
        # a logger made with sync=True (LinuxCNC's spindle-sync-info) has them
        read = getattr(self._logger, "sync_points", None)
        found = read() if read is not None else None
        if found is None:
            return None
        raw, count = found
        return np.frombuffer(raw, dtype=SYNC_DTYPE, count=int(count))

    def _dropped_since(self, points):
        """How many of the points read before are not at the front of
        ``points`` - dropped by a full logger: 0, a multiple of
        LOGGER_FLUSH_POINTS, or None when they are not the same points."""
        before = self._points
        had = len(before) if before is not None else 0
        if not had:
            return 0
        if not len(points):
            return None
        first = points[:1].tobytes()
        if before[:1].tobytes() == first:
            # the first point never moves: the same points, or others
            return 0 if len(points) >= had else None
        for at in range(LOGGER_FLUSH_POINTS, had, LOGGER_FLUSH_POINTS):
            if before[at:at + 1].tobytes() == first:
                return at
        return None

    def _drop(self, count):
        self._tools.drop_front(count)
        self._lines.drop_front(count)
        self._synced.drop_front(count)
        self.dropped += count
        self.flushes += 1
        self.points_dropped += count

    def _note_made_by(self, npts, tool, line):
        had = self._tools.n
        if npts < had:
            self._tools.resize(npts)
            self._lines.resize(npts)
        elif npts > had:
            self._tools.resize(npts)[had:] = int(tool)
            self._lines.resize(npts)[had:] = int(line)

    def _note_synced(self, npts, sync):
        # from the last point read before: it may have moved on along its line
        start = max(0, min(self._synced.n, npts) - 1)
        mask = self._synced.resize(npts)
        if sync is not None and SPINDLE_SYNC_POSITION is not None:
            mask[start:] = sync[SYNC_MODE][start:npts] == SPINDLE_SYNC_POSITION
        else:
            mask[start:] = False
        self._any_synced = bool(mask.any())

    def _empty(self):
        self._raw, self._npts, self._points, self._sync = b"", 0, None, None

    # ── what the renderer reads ──────────────────────────────────────────

    def points(self):
        return self._raw, self._npts, False

    def sync_points(self):
        return self._sync

    def synced(self, npts):
        if not self._any_synced:
            return None
        return self._synced.view()[:npts]

    @property
    def npts(self):
        return self._npts

    def last(self, flag=True):
        if self._thread is not None:
            found = self._logger.last(flag)
            if found is not None:
                return found
        return self._position() if self._position is not None else None

    def get_colors(self):
        if self._logger is None:
            return list(self._colors)
        return self._logger.get_colors()

    def set_colors(self, *args):
        if self._logger is not None:
            self._logger.set_colors(*args)

    def set_depth(self, *args):
        # kept for the loggers made later
        self._depth = args
        if self._logger is not None:
            self._logger.set_depth(*args)

    # upstream's names for the logger's thread: driven by start_logging and
    # stop_logging, never by the renderer
    def start(self, *_args):
        pass

    def stop(self):
        pass

    def call(self):
        pass

    def made_by(self):
        if np is None:
            return None
        return TrailOrigins(self._tools.view(), self._lines.view())

    @property
    def nbytes(self) -> int:
        """What the copy of the logger's points read, and what is noted for
        each, take - bytes (diagnostics)."""
        if np is None:
            return 0
        own = len(self._raw) + (self._sync.nbytes if self._sync is not None else 0)
        return own + self._tools.nbytes + self._lines.nbytes + self._synced.nbytes

    def _forget(self):
        if np is not None:
            self._tools.clear()
            self._lines.clear()
            self._synced.clear()
            self._any_synced = False
        self.dropped = 0
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
        # by point: whether the line ending there is synced with the spindle
        self._master_synced = self._shown_synced = np.zeros(0, dtype=bool) if np is not None else None

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
        tools, lines, synced = [], [], []
        start = run.program.start
        if start is not None:
            points.append(tuple(start))
            synced.append(False)
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
                    synced.append(False)
                    colors.append(colours[step.kind])
                    tools.append(step.tool)
                    lines.append(line)
                points.extend(drawn[1:])
                colors.extend([colours[step.kind]] * (len(drawn) - 1))
                synced.extend([step.sync is not None] * (len(drawn) - 1))
                tools.extend([step.tool] * (len(drawn) - 1))
                lines.extend([line] * (len(drawn) - 1))
            ends.append(len(points))
        self._master = self._points(points, colors)
        self._master_synced = np.asarray(synced, dtype=bool)
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
            self._shown_synced = np.zeros(0, dtype=bool)
            self._shown_made_by = TrailOrigins.none()
            return
        before = len(self._shown)
        done = self._ends[step - 1] if step > 0 else (1 if self._run.program.start is not None else 0)
        trail = self._master[:done]
        synced = self._master_synced[:done]
        tools, lines = self._made_by.tools[:done], self._made_by.lines[:done]
        current = self._run.program.steps[step] if step < len(self._run.program.steps) else None
        if isinstance(current, Move) and 0.0 < fraction < 1.0:
            partial = move_points(current, fraction)[1:]
            extra = self._points(partial, [self._step_colors.get(step, FEED)] * len(partial))
            trail = np.concatenate([trail, extra])
            synced = np.concatenate([synced, np.full(len(partial), current.sync is not None)])
            line = _line(current.where, self._program_file)
            tools = np.concatenate([tools, np.full(len(partial), current.tool, dtype=np.int64)])
            lines = np.concatenate([lines, np.full(len(partial), line, dtype=np.int64)])
        self._shown = trail
        self._shown_synced = synced
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
        out[POS][:, 0] = zr[:, 1] * units + x0
        out[POS][:, 2] = zr[:, 0] * units + z0
        out[COLOR] = np.asarray([self._colors[c] for c in colors], dtype=np.uint8)
        out[POS2] = out[POS]
        out[COLOR2] = out[COLOR]
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
        x, y, z = (float(v) for v in self._shown[POS][-1])
        return (x, y, z, 0.0, 0.0, 0.0)

    def synced(self, npts):
        if self._shown_synced is None:
            return None
        mask = self._shown_synced[self._skip:self._skip + npts]
        return mask if mask.any() else None

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
