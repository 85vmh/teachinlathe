"""When the backplot records the path a program cuts, and when it polls at
all - the one place that decides it (BackplotLifecycle).

The trail is the path of a program's run and nothing else: no jog, no MDI, no
manual tool change, nothing from while no program runs. So the position logger
runs only while a program runs (Feed Hold and an M0/M1 included: the machine
stands, the logger adds nothing) and the plot is in sight; the plot's poll
timer runs only while it is in sight - showing the tool where it is while no
program runs - and not at all while hidden.

    new run (Cycle Start)  the old trail and material go, the logger starts
    Feed Hold / M1, resume nothing changes: the logger goes on
    run ended (completed)  the logger stops, the trail stays in sight
    Cycle Abort            the logger stops, the trail and material go
    another program loaded the logger stops, the trail and material go
    plot hidden            the logger and the timer stop
    plot shown again       the timer starts, the logger too while a run is on

A plot hidden in the middle of a run and shown again starts a new logger: the
part of the run it did not see is not in the trail, and nothing joins the
points before to the points after.

What carries it out is the plot (a BackplotHost), attached once it exists; till
then, and after it is detached, this only keeps the state. Every input is
idempotent: told again what it was told, nothing happens.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Optional, Protocol

from teachinlathe.diagnostics.model.units import Unit


class RunPhase(Enum):
    IDLE = "idle"               # no run since the program was loaded
    RUNNING = "running"         # Feed Hold and M0/M1 included (``paused``)
    COMPLETED = "completed"     # ended; its trail stays in sight
    ABORTED = "aborted"         # Cycle Abort; its trail went with it


class Action(StrEnum):
    """What the lifecycle did (``Transition.what``)."""
    LOGGER_START = "logger start"
    LOGGER_STOP = "logger stop"
    POLL_START = "poll start"
    POLL_STOP = "poll stop"
    RESET = "reset"
    CLEAR = "clear"
    PAUSE = "pause"
    RESUME = "resume"


class Cause(StrEnum):
    """Why it did it (``Transition.cause``, the ``last_*_cause``)."""
    PLOT_ATTACHED = "plot attached"
    ATTACHED_ELSEWHERE = "attached elsewhere"
    SHUTDOWN = "shutdown"
    PLOT_SHOWN = "plot shown"
    PLOT_HIDDEN = "plot hidden"
    PROGRAM_LOADED = "program loaded"
    CYCLE_START = "cycle start"
    RUN = "run"
    PROGRAM_COMPLETED = "program completed"
    CYCLE_ABORT = "cycle abort"
    CLEAR_PLOT = "clear plot"


class BackplotHost(Protocol):
    """What the lifecycle drives: the plot."""

    def start_logger(self) -> None: ...

    def stop_logger(self) -> None: ...

    def reset_trail(self) -> None:
        """The trail, what was noted for each of its points and the material
        cut from it, gone; the logger is stopped already."""

    def start_poll(self) -> None: ...

    def stop_poll(self) -> None: ...


@dataclass(frozen=True)
class Transition:
    """Something the lifecycle did: ``what`` (an Action), ``cause`` why (a
    Cause); ``monotonic`` and ``wall`` seconds, when."""
    what: str
    cause: str
    monotonic: float
    wall: float


#: The names the diagnostics know the backplot by: its gauges and its state
#: (``add_gauges``, ``add_state``), and the position logger's limits.
DIAGNOSTICS_NAME = "backplot"
TRAIL_LIMIT_STATE = "backplot_trail_limit"

#: The backplot's gauges: the lifecycle's state (``gauges``) ...
VISIBLE = "backplot.visible"
LOADED = "backplot.loaded"
RUNNING = "backplot.running"
PAUSED = "backplot.paused"
COMPLETED = "backplot.completed"
ABORTED = "backplot.aborted"
LOGGER_ACTIVE = "backplot.logger_active"
POLL_ACTIVE = "backplot.poll_active"
TRAIL_RETAINED = "backplot.trail_retained"
#: ... and the plot's trail (``BackplotHost.trail_stats``).
NPTS = "backplot.npts"
POINTS_LIMIT = "backplot.points_limit"
TRAIL_NATIVE_BYTES = "backplot.trail_native_bytes"
TRAIL_AUX_BYTES = "backplot.trail_aux_bytes"
FLUSHES = "backplot.flushes"
POINTS_DROPPED = "backplot.points_dropped"
LOGGERS_MADE = "backplot.loggers_made"
LOGGER_THREADS_LEFT = "backplot.logger_threads_left"
PREVIEW_RELOADS = "backplot.preview_reloads"
POLLS_PER_S = "backplot.polls_per_s"
RENDERS_PER_S = "backplot.renders_per_s"
RELOADS_PER_S = "backplot.reloads_per_s"
RENDER_ON_UI_THREAD = "backplot.render_on_ui_thread"

#: The units of the backplot's gauges, for the diagnostics.
GAUGE_UNITS = {
    VISIBLE: (Unit.FLAG, "backplot in sight"),
    LOADED: (Unit.FLAG, "program loaded"),
    RUNNING: (Unit.FLAG, "program running"),
    PAUSED: (Unit.FLAG, "program paused"),
    COMPLETED: (Unit.FLAG, "program completed"),
    ABORTED: (Unit.FLAG, "program aborted"),
    LOGGER_ACTIVE: (Unit.FLAG, "position logger on"),
    POLL_ACTIVE: (Unit.FLAG, "backplot poll timer on"),
    TRAIL_RETAINED: (Unit.FLAG, "a run's trail kept"),
    NPTS: (Unit.POINTS, "trail points"),
    POINTS_LIMIT: (Unit.POINTS, "the most a position logger holds before it flushes"),
    TRAIL_NATIVE_BYTES: (Unit.BYTES, "the position logger's buffer, estimated"),
    TRAIL_AUX_BYTES: (Unit.BYTES, "the trail's copies and what is noted per point"),
    FLUSHES: (Unit.COUNT, "position logger flushes"),
    POINTS_DROPPED: (Unit.POINTS, "points dropped by flushes"),
    LOGGERS_MADE: (Unit.COUNT, "position loggers made"),
    LOGGER_THREADS_LEFT: (Unit.COUNT, "logger threads that did not end when asked"),
    PREVIEW_RELOADS: (Unit.COUNT, "programs read for the preview"),
    POLLS_PER_S: (Unit.PER_S, "backplot polls"),
    RENDERS_PER_S: (Unit.PER_S, "backplot frames drawn"),
    RELOADS_PER_S: (Unit.PER_S, "programs read for the preview"),
    RENDER_ON_UI_THREAD: (Unit.FLAG, "the backplot drawn on the UI thread"),
}

#: The keys of ``state``.
STATE_PHASE = "phase"
STATE_PAUSED = "paused"
STATE_VISIBLE = "visible"
STATE_PROGRAM_LOADED = "program_loaded"
STATE_LOGGER_ACTIVE = "logger_active"
STATE_POLL_ACTIVE = "poll_active"
STATE_TRAIL_RETAINED = "trail_retained"
STATE_LAST_START_CAUSE = "last_start_cause"
STATE_LAST_STOP_CAUSE = "last_stop_cause"
STATE_LAST_RESET_CAUSE = "last_reset_cause"
STATE_TRANSITIONS = "transitions"
#: the keys of each of its transitions
TRANSITION_WHAT = "what"
TRANSITION_CAUSE = "cause"
TRANSITION_WALL = "wall"

#: How many transitions are kept, for diagnostics.
TRANSITIONS_KEPT = 200


class BackplotLifecycle:
    """The backplot's state - the program loaded, its run, the plot in
    sight - and, from it, whether the position logger and the poll timer run.

    ``records_trail``: False for a plot that has no logger (a simulation's):
    only its timer follows its visibility."""

    def __init__(self, records_trail: bool = True, clock=time.monotonic, wall_clock=time.time):
        self.records_trail = records_trail
        self._clock, self._wall_clock = clock, wall_clock
        self._host: Optional[BackplotHost] = None
        self.loaded_file = ""
        self.phase = RunPhase.IDLE
        self.paused = False
        self.visible = False
        self.logger_active = False
        self.poll_active = False
        #: points are in the trail from a run (ended or not) - as far as the
        #: lifecycle knows; Clear Plot may have wiped them
        self.trail_retained = False
        self.last_start_cause = ""
        self.last_stop_cause = ""
        self.last_reset_cause = ""
        self.transitions = deque(maxlen=TRANSITIONS_KEPT)

    # ── the plot ─────────────────────────────────────────────────────────

    def attach(self, host: BackplotHost) -> None:
        """The plot exists: it does what the state says from now on."""
        if host is self._host:
            return
        self.detach(Cause.ATTACHED_ELSEWHERE)
        self._host = host
        self._apply(Cause.PLOT_ATTACHED)

    def detach(self, cause: str = Cause.SHUTDOWN) -> None:
        """The plot goes: its logger and timer stop. The state is kept."""
        if self._host is None:
            return
        self._set_logger(False, cause)
        self._set_poll(False, cause)
        self._host = None

    @property
    def attached(self) -> bool:
        return self._host is not None

    # ── inputs ───────────────────────────────────────────────────────────

    def set_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if visible == self.visible:
            return
        self.visible = visible
        self._apply(Cause.PLOT_SHOWN if visible else Cause.PLOT_HIDDEN)

    def program_loaded(self, path: str) -> None:
        """A program loaded: the last one's trail and material go - the same
        file too, as its contents may be other than they were. Not while it
        runs: nothing loads one then."""
        path = path or ""
        if self.phase is RunPhase.RUNNING:
            return
        if path == self.loaded_file and self.phase is RunPhase.IDLE and not self.trail_retained:
            return
        self.loaded_file = path
        self.phase, self.paused = RunPhase.IDLE, False
        self._reset(Cause.PROGRAM_LOADED)
        self._apply(Cause.PROGRAM_LOADED)

    def run_started(self) -> None:
        """A new run of the program: Cycle Start from idle, or for another
        part after one completed."""
        if self.phase is RunPhase.RUNNING:
            return
        self.phase, self.paused = RunPhase.RUNNING, False
        self._reset(Cause.CYCLE_START)
        self._apply(Cause.CYCLE_START)

    def set_paused(self, paused: bool) -> None:
        """Feed Hold or an M0/M1, or going on from it: the logger is left as
        it is - standing, the machine adds no points."""
        paused = bool(paused) and self.phase is RunPhase.RUNNING
        if paused != self.paused:
            self.paused = paused
            self._note(Action.PAUSE if paused else Action.RESUME, Cause.RUN)

    def run_ended(self) -> None:
        """The run is over, not aborted: the trail stays in sight until the
        next run, an abort or another program."""
        if self.phase is not RunPhase.RUNNING:
            return
        self.phase, self.paused = RunPhase.COMPLETED, False
        self._apply(Cause.PROGRAM_COMPLETED)

    def run_aborted(self) -> None:
        """Cycle Abort - in a run, or leaving the Completed screen: the trail
        goes at once."""
        if self.phase is RunPhase.ABORTED and not self.trail_retained:
            return
        self.phase, self.paused = RunPhase.ABORTED, False
        self._reset(Cause.CYCLE_ABORT)
        self._apply(Cause.CYCLE_ABORT)

    def trail_cleared(self, cause: str = Cause.CLEAR_PLOT) -> None:
        """The trail was wiped by hand (Clear Plot): only noted."""
        self.trail_retained = self.logger_active
        self.last_reset_cause = cause
        self._note(Action.CLEAR, cause)

    # ── what it decides ──────────────────────────────────────────────────

    @property
    def logger_wanted(self) -> bool:
        return (self.records_trail and self._host is not None and self.visible
                and self.phase is RunPhase.RUNNING)

    @property
    def poll_wanted(self) -> bool:
        return self._host is not None and self.visible

    def _apply(self, cause: str) -> None:
        self._set_logger(self.logger_wanted, cause)
        self._set_poll(self.poll_wanted, cause)

    def _set_logger(self, on: bool, cause: str) -> None:
        if on == self.logger_active:
            return
        if on:
            self._host.start_logger()
            self.trail_retained = True
            self.last_start_cause = cause
        else:
            self._host.stop_logger()
            self.last_stop_cause = cause
        self.logger_active = on
        self._note(Action.LOGGER_START if on else Action.LOGGER_STOP, cause)

    def _set_poll(self, on: bool, cause: str) -> None:
        if on == self.poll_active:
            return
        if on:
            self._host.start_poll()
        else:
            self._host.stop_poll()
        self.poll_active = on
        self._note(Action.POLL_START if on else Action.POLL_STOP, cause)

    def _reset(self, cause: str) -> None:
        """The trail and the material gone, the logger stopped first."""
        self._set_logger(False, cause)
        if self._host is not None and self.records_trail:
            self._host.reset_trail()
        self.trail_retained = False
        self.last_reset_cause = cause
        self._note(Action.RESET, cause)

    # ── diagnostics ──────────────────────────────────────────────────────

    def gauges(self) -> dict:
        """The state as numbers (0/1), and the plot's trail as it says
        (``trail_stats``): read by the diagnostics as each bucket closes."""
        out = {VISIBLE: float(self.visible),
               LOADED: float(bool(self.loaded_file)),
               RUNNING: float(self.phase is RunPhase.RUNNING and not self.paused),
               PAUSED: float(self.paused),
               COMPLETED: float(self.phase is RunPhase.COMPLETED),
               ABORTED: float(self.phase is RunPhase.ABORTED),
               LOGGER_ACTIVE: float(self.logger_active),
               POLL_ACTIVE: float(self.poll_active),
               TRAIL_RETAINED: float(self.trail_retained)}
        stats = getattr(self._host, "trail_stats", None)
        if stats is not None:
            out.update(stats())
        return out

    def state(self) -> dict:
        """What is shown and exported as it is: the phase, the last causes,
        the transitions kept (no file names)."""
        return {STATE_PHASE: self.phase.value, STATE_PAUSED: self.paused, STATE_VISIBLE: self.visible,
                STATE_PROGRAM_LOADED: bool(self.loaded_file), STATE_LOGGER_ACTIVE: self.logger_active,
                STATE_POLL_ACTIVE: self.poll_active, STATE_TRAIL_RETAINED: self.trail_retained,
                STATE_LAST_START_CAUSE: self.last_start_cause, STATE_LAST_STOP_CAUSE: self.last_stop_cause,
                STATE_LAST_RESET_CAUSE: self.last_reset_cause,
                STATE_TRANSITIONS: [{TRANSITION_WHAT: t.what, TRANSITION_CAUSE: t.cause,
                                     TRANSITION_WALL: round(t.wall, 3)}
                                    for t in list(self.transitions)]}

    def _note(self, what: str, cause: str) -> None:
        self.transitions.append(Transition(what, cause, self._clock(), self._wall_clock()))
