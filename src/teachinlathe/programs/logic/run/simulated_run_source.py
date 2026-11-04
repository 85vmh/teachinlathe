"""A G-code file played as the machine would run it, as a ProgramRunSource.

The run is worked out off the GUI thread (SimulateUseCase: LinuxCNC's own
interpreter, the program's stock) and played on a clock of its own: Cycle
Start starts it - and goes on after an M0, or an M1 while Optional Stop is
on - Feed Hold holds it and Feed Resume lets it go on, Cycle Stop ends it
and takes it back to the start. While it is not running, it is moved
anywhere (``seek``, ``seek_to_line``); it plays faster than the machine
would at a ``speed`` of more than 1.

The plot reads it as a RunPlayback (backplot.plot_source.SimulationSource):
``run``, ``played`` and ``program_file``.
"""

from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtCore import QElapsedTimer, QTimer, pyqtSignal

from teachinlathe.programs.logic.run.run_source import ProgramRunSource
from teachinlathe.programs.model.run_moment import MotionReadout, RunMark, RunMoment, RunState
from teachinlathe.programs.model.tool_changes import NextTool
from teachinlathe.simulation.logic.program_run import MarkKind
from teachinlathe.simulation.model.moves import Move, MoveKind, StopKind

#: How fast it can be played, times the machine's speed.
SPEEDS = (1.0, 2.0, 5.0, 10.0, 25.0)
#: ms between two frames while it plays.
FRAME_MS = 33
#: X is a radius in the run, a diameter on a lathe's DRO.
DIAMETER = 2.0


class SimulatedRunSource(ProgramRunSource):
    #: Reading the program, or not.
    loadingChanged = pyqtSignal()
    #: Why there is no run, or why it stops short ("" with nothing to say).
    errorChanged = pyqtSignal()

    seekable = True
    speeds = SPEEDS

    def __init__(self, use_case, parent=None):
        """``use_case``: what works the run out (SimulateUseCase)."""
        super().__init__(parent)
        self._use_case = use_case
        use_case.ready.connect(self._on_ready)
        use_case.failed.connect(self._on_failed)
        self._ngc_path = ""
        self._json_path = ""
        self._optional_stop = False
        self._block_delete = False
        self._loading = False
        self._error = ""
        self._run = None
        self._time = 0.0
        self._state = RunState.IDLE
        self._waiting_for = ""
        self._speed = SPEEDS[0]
        self._played = None             # the run's own moment (program_run.Moment), for the plot
        self._moment: Optional[RunMoment] = None
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._on_frame)

    # ── what it plays ────────────────────────────────────────────────────

    def open(self, ngc_path: str, json_path: str = "", optional_stop: bool = False,
             block_delete: bool = False) -> None:
        """A simulation of ``ngc_path``: its stock from the conversational
        program at ``json_path``, if any, Optional Stop as on the machine."""
        self._stop_playing()
        self._ngc_path, self._json_path = ngc_path, json_path
        self._optional_stop = bool(optional_stop)
        self._block_delete = bool(block_delete)
        self._run, self._played = None, None
        self._time, self._state, self._waiting_for = 0.0, RunState.IDLE, ""
        self.runChanged.emit()
        self._show()
        self._work_out()

    def close(self) -> None:
        """Left: nothing goes on playing."""
        self._stop_playing()

    def set_optional_stop(self, on: bool) -> None:
        """Optional Stop: the program read again - an M1's remap takes another
        way with it on - from where it is."""
        on = bool(on)
        if on == self._optional_stop:
            return
        self._optional_stop = on
        if self._run is not None and self._state not in (RunState.RUNNING, RunState.HELD):
            self._work_out()

    def set_block_delete(self, on: bool) -> None:
        """Skip ``/`` blocks and work the run out again."""
        on = bool(on)
        if on == self._block_delete:
            return
        self._block_delete = on
        if self._run is not None and self._state not in (RunState.RUNNING, RunState.HELD):
            self._work_out()

    @property
    def optional_stop(self) -> bool:
        return self._optional_stop

    @property
    def block_delete(self) -> bool:
        return self._block_delete

    @property
    def loading(self) -> bool:
        return self._loading

    @property
    def error(self) -> str:
        return self._error

    # ── what the plot reads (a RunPlayback) ──────────────────────────────

    @property
    def run(self):
        """The run worked out (a ProgramRun), or None."""
        return self._run

    @property
    def played(self):
        """The moment shown as the run has it (a program_run.Moment), or None."""
        return self._played

    @property
    def program_file(self) -> str:
        return self._ngc_path

    # ── the run, as a ProgramRunSource ───────────────────────────────────

    @property
    def state(self):
        return self._state

    @property
    def moment(self):
        if self._moment is None:
            self._moment = self._read_moment()
        return self._moment

    @property
    def duration(self):
        return self._run.duration if self._run is not None else None

    @property
    def marks(self):
        if self._run is None:
            return ()
        marks = self._run.marks
        shown = []
        for index, mark in enumerate(marks):
            if mark.kind is MarkKind.TOOL_CHANGE:
                # Represented by the owning operation's filled circle, never
                # as a separate mark on the seek bar.
                continue
            if (mark.kind is MarkKind.STOP and mark.label == StopKind.PROGRAM_STOP.value
                    and index > 0 and marks[index - 1].kind is MarkKind.TOOL_CHANGE
                    and marks[index - 1].time == mark.time):
                # The M6 remap waits with an M0 immediately after loading the
                # tool. The filled operation circle already communicates that
                # event; keep the wait in playback, but not as a yellow line.
                continue
            changes_tool = False
            if mark.kind is MarkKind.OPERATION:
                for following in marks[index + 1:]:
                    if following.kind is MarkKind.OPERATION:
                        break
                    if following.kind is MarkKind.TOOL_CHANGE:
                        changes_tool = True
                        break
            shown.append(RunMark(mark.time, mark.kind.value, mark.number,
                                 mark.label, changes_tool))
        return tuple(shown)

    @property
    def waiting_for(self):
        return self._waiting_for

    @property
    def time(self) -> float:
        return self._time

    def cycle_start(self):
        if self._run is None or self._state in (RunState.RUNNING, RunState.HELD):
            return
        if self._state is RunState.FINISHED:
            self._time = 0.0
        self._waiting_for = ""
        self._set_state(RunState.RUNNING)
        self._play()

    def feed_hold(self):
        if self._state is RunState.RUNNING:
            self._stop_playing()
            self._set_state(RunState.HELD)
        elif self._state is RunState.HELD:
            self._set_state(RunState.RUNNING)
            self._play()

    def cycle_stop(self):
        """Ends the run, back at the start with the stock as it was."""
        self._stop_playing()
        self._time, self._waiting_for = 0.0, ""
        self._set_state(RunState.IDLE)
        self._show()

    @property
    def speed(self):
        return self._speed

    def set_speed(self, speed):
        if speed in SPEEDS and speed != self._speed:
            self._speed = speed
            self.changed.emit()

    def seek(self, time):
        """Show the run at ``time``. Seeking an active run puts it in Feed
        Hold; Feed Resume then continues from the requested moment."""
        if self._run is None:
            return
        active = self._state in (RunState.RUNNING, RunState.HELD, RunState.WAITING)
        if self._state is RunState.RUNNING:
            self._stop_playing()
        self._time = min(max(float(time), 0.0), self._run.duration)
        self._waiting_for = ""
        if active:
            self._state = RunState.HELD
        else:
            finished = self._time >= self._run.duration and self._run.duration > 0
            self._state = RunState.FINISHED if finished else RunState.IDLE
        self._show()

    def seek_to_line(self, line):
        """The run where line ``line`` of the program starts - the first
        thing it does from there on. An active run is held there."""
        if self._run is not None:
            self.seek(self._time_of_line(line))

    # ── working it out ───────────────────────────────────────────────────

    def _work_out(self):
        self._set_error("")
        self._set_loading(True)
        self._use_case.start(
            self._ngc_path, self._json_path, self._optional_stop, self._block_delete)

    def _on_ready(self, run):
        # the same program again, Optional Stop changed: where it was, kept by its line
        line = self._program_line() if self._run is not None else None
        self._run = run
        self._set_loading(False)
        self._set_error(run.program.error and f"The interpreter stopped: {run.program.error}")
        self._time = self._time_of_line(line) if line is not None else 0.0
        self.runChanged.emit()
        self._show()

    def _on_failed(self, message):
        self._set_loading(False)
        self._set_error(message)

    # ── playing ──────────────────────────────────────────────────────────

    def _play(self):
        self._clock.start()
        self._timer.start()

    def _stop_playing(self):
        self._timer.stop()

    def _on_frame(self):
        elapsed = self._clock.restart() / 1000.0
        before, after = self._time, min(self._time + elapsed * self._speed, self._run.duration)
        stop = self._stop_between(before, after)
        if stop is not None:
            self._time = stop.time
            self._waiting_for = stop.label
            self._stop_playing()
            self._state = RunState.WAITING
        elif after >= self._run.duration:
            self._time = after
            self._stop_playing()
            self._state = RunState.FINISHED
        else:
            self._time = after
        self._show()

    def _stop_between(self, before, after):
        """The first stop the run waits at after ``before``, up to ``after``:
        an M0, an M1 with Optional Stop on."""
        for mark in self._run.marks:
            if mark.kind is not MarkKind.STOP or not before < mark.time <= after:
                continue
            if mark.label == StopKind.OPTIONAL_STOP.value and not self._optional_stop:
                continue
            return mark
        return None

    # ── the moment shown ─────────────────────────────────────────────────

    def _show(self):
        self._played = self._run.at(self._time) if self._run is not None else None
        self._moment = None
        self.changed.emit()

    def _set_state(self, state):
        self._state = state
        self._show()

    def _program_line(self):
        step = self._played.step if self._played is not None else 0
        steps = self._run.program.steps
        return steps[min(step, len(steps) - 1)].where.program_line if steps else 0

    def _time_of_line(self, line):
        for index, step in enumerate(self._run.program.steps):
            if step.where.program_line >= line:
                return self._run.start_of(index)
        return self._run.duration

    def _read_moment(self) -> RunMoment:
        moment = self._played
        if moment is None or moment.at is None:
            return RunMoment(work_offset=moment.work_offset if moment is not None else 1, time=self._time)
        at, origin = moment.at, moment.origin
        step = self._step()
        x_to_go = z_to_go = 0.0
        if isinstance(step, Move):
            x_to_go, z_to_go = DIAMETER * (step.end.r - at.r), step.end.z - at.z
        return RunMoment(x=DIAMETER * (at.r - origin.r), z=at.z - origin.z, x_to_go=x_to_go, z_to_go=z_to_go,
                         work_offset=moment.work_offset, program_line=self._program_line(), tool=moment.tool,
                         next_tool=self._next_tool(moment.tool), motion=self._motion(step, at.r - origin.r),
                         time=self._time)

    def _step(self):
        steps = self._run.program.steps if self._run is not None else ()
        index = self._played.step if self._played is not None else 0
        return steps[index] if index < len(steps) else None

    def _next_tool(self, tool) -> Optional[NextTool]:
        """The first tool other than ``tool`` the run loads from now on, and in
        how many seconds of the run - "now" while not playing: the next tool
        shows; its time only while it runs, as the machine's does."""
        for mark in self._run.marks:
            if mark.kind is MarkKind.TOOL_CHANGE and mark.time >= self._time and mark.number != tool:
                playing = self._state in (RunState.RUNNING, RunState.HELD, RunState.WAITING)
                return NextTool(mark.number, mark.time - self._time if playing else None)
        return None

    def _motion(self, step, radius) -> MotionReadout:
        """The feed and the spindle of ``step``, the tool ``radius`` mm from
        the axis: a rapid at its average speed; the spindle's rpm from its
        surface speed under G96, capped at its D."""
        if not isinstance(step, Move):
            return MotionReadout()
        spindle = step.spindle
        rpm, css = spindle.speed, None
        if spindle.css_max:
            css = spindle.speed
            rpm = css * 1000.0 / (2.0 * math.pi * abs(radius)) if radius else math.inf
            rpm = min(rpm, spindle.css_max)
        if not spindle.turning:
            rpm = 0.0
        if step.kind in (MoveKind.RAPID, MoveKind.TOOL_CHANGE):
            return MotionReadout(rapid=True, feed=self._rapid_speed(step), per_rev=False, rpm=rpm, css=css)
        return MotionReadout(feed=spindle.feed, per_rev=spindle.per_rev, rpm=rpm, css=css)

    def _rapid_speed(self, step) -> float:
        """mm/min a rapid goes at, on average."""
        index = self._played.step
        seconds = self._run.start_of(index + 1) - self._run.start_of(index)
        if seconds <= 0:
            return 0.0
        return math.hypot(step.end.z - step.start.z, step.end.r - step.start.r) / seconds * 60.0

    def _set_loading(self, loading):
        if loading != self._loading:
            self._loading = loading
            self.loadingChanged.emit()

    def _set_error(self, error):
        if error != self._error:
            self._error = error
            self.errorChanged.emit()
