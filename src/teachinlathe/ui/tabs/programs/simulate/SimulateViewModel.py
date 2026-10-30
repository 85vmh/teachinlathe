"""The Simulate screen's view model: a G-code file played as the machine would
run it, on its stock (programs.logic.simulate_use_case works the run out).

It is driven as the machine is: Cycle Start starts it - and goes on after an
M0, or an M1 while Break on M1 is on - Feed Hold holds it and Feed Resume
lets it go on, Cycle Stop ends it and takes it back to the start. While it
is not running, the seek bar moves it anywhere. ``speed`` plays it faster
than the machine would; so does the code (``content``): scrolled to a line
(seekToLine), the run goes to it.

What a moment looks like is the backplot's to draw: a LatheBackplot whose
``simulation`` is this view model follows ``run`` and ``moment`` as it
follows the machine (backplot.feeds.SimulatedFeed).
"""

import logging
import os

from PyQt6.QtCore import QElapsedTimer, QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.simulation.logic.program_run import MarkKind
from teachinlathe.simulation.model.moves import StopKind
from teachinlathe.ui.tabs.programs.gcode_viewer.GCodeSyntaxHighlighter import GCodeSyntaxHighlighter

LOG = logging.getLogger(__name__)

#: The run, as the screen shows it.
IDLE = "idle"           # at the start, not started
RUNNING = "running"
HELD = "held"           # Feed Hold
WAITING = "waiting"     # at an M0, or an M1 with Break on M1 on: Cycle Start goes on
FINISHED = "finished"

#: How fast it can be played, times the machine's speed.
SPEEDS = (1.0, 2.0, 5.0, 10.0, 25.0)

#: ms between two frames while it plays.
FRAME_MS = 33


class SimulateViewModel(QObject):
    fileChanged = pyqtSignal()
    loadingChanged = pyqtSignal()
    errorChanged = pyqtSignal()
    runChanged = pyqtSignal()
    momentChanged = pyqtSignal()
    stateChanged = pyqtSignal()
    speedChanged = pyqtSignal()
    optionalStopChanged = pyqtSignal()

    def __init__(self, use_case, parent=None):
        super().__init__(parent)
        self._use_case = use_case
        self._use_case.ready.connect(self._on_ready)
        self._use_case.failed.connect(self._on_failed)
        self._ngc_path = ""
        self._json_path = ""
        self._content = ""
        self._highlighter = GCodeSyntaxHighlighter(self)
        self._loading = False
        self._error = ""
        self._run = None
        self._time = 0.0
        self._state = IDLE
        self._waiting_for = ""
        self._speed = SPEEDS[0]
        self._optional_stop = False
        self._moment = None
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(FRAME_MS)
        self._timer.timeout.connect(self._on_frame)

    # ── what opens it ────────────────────────────────────────────────────

    def open(self, ngc_path: str, json_path: str = "", optional_stop: bool = False):
        """A simulation of ``ngc_path``: its stock from the conversational
        program at ``json_path``, if any, Break on M1 as on the machine."""
        self._stop_playing()
        self._ngc_path, self._json_path = ngc_path, json_path
        self._content = _read(ngc_path)
        self._optional_stop = bool(optional_stop)
        self._highlighter.set_optional_stop(self._optional_stop)
        self._run, self._moment = None, None
        self._time, self._state, self._waiting_for = 0.0, IDLE, ""
        self.fileChanged.emit()
        self.optionalStopChanged.emit()
        self.runChanged.emit()
        self.stateChanged.emit()
        self.momentChanged.emit()
        self._work_out()

    def close(self):
        """Left: nothing goes on playing."""
        self._stop_playing()

    def _work_out(self):
        self._set_error("")
        self._set_loading(True)
        self._use_case.start(self._ngc_path, self._json_path, self._optional_stop)

    def _on_ready(self, run):
        # the same program again, Break on M1 changed: where it was, kept by its line
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

    # ── the machine's buttons ────────────────────────────────────────────

    @pyqtSlot()
    def cycleStart(self):
        if self._run is None or self._state in (RUNNING, HELD):
            return
        if self._state == FINISHED:
            self._time = 0.0
        self._waiting_for = ""
        self._set_state(RUNNING)
        self._play()

    @pyqtSlot()
    def feedHold(self):
        """Feed Hold, and Feed Resume when held."""
        if self._state == RUNNING:
            self._stop_playing()
            self._set_state(HELD)
        elif self._state == HELD:
            self._set_state(RUNNING)
            self._play()

    @pyqtSlot()
    def cycleStop(self):
        """Ends the run, back at the start with the stock as it was."""
        self._stop_playing()
        self._time, self._waiting_for = 0.0, ""
        self._set_state(IDLE)
        self._show()

    @pyqtSlot(float)
    def seek(self, time):
        """The run at ``time``, while it is not running."""
        if self._run is None or self._state in (RUNNING, HELD):
            return
        self._time = min(max(float(time), 0.0), self._run.duration)
        self._waiting_for = ""
        self._set_state(FINISHED if self._time >= self._run.duration and self._run.duration > 0 else IDLE)
        self._show()

    @pyqtSlot(int)
    def seekToLine(self, line):
        """The run where line ``line`` of the program starts - the first
        thing it does from there on - while it is not running."""
        if self._run is not None and self._state not in (RUNNING, HELD):
            self.seek(self._time_of_line(line))

    @pyqtSlot(QObject)
    def attachHighlighter(self, quick_document):
        """The code's colours, as the Programs screen's: M1s greyed while
        Break on M1 is off."""
        self._highlighter.attach(quick_document)

    @pyqtSlot(float)
    def setSpeed(self, speed):
        if speed in SPEEDS and speed != self._speed:
            self._speed = speed
            self.speedChanged.emit()

    @pyqtSlot(bool)
    def setOptionalStop(self, on):
        """Break on M1: the program read again - an M1's remap takes another
        way with it on - from where it is."""
        on = bool(on)
        if on == self._optional_stop:
            return
        self._optional_stop = on
        self._highlighter.set_optional_stop(on)
        self.optionalStopChanged.emit()
        if self._run is not None and self._state not in (RUNNING, HELD):
            self._work_out()

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
            self._set_state(WAITING)
        elif after >= self._run.duration:
            self._time = after
            self._stop_playing()
            self._set_state(FINISHED)
        else:
            self._time = after
        self._show()

    def _stop_between(self, before, after):
        """The first stop the run waits at after ``before``, up to ``after``:
        an M0, an M1 with Break on M1 on."""
        for mark in self._run.marks:
            if mark.kind is not MarkKind.STOP or not before < mark.time <= after:
                continue
            if mark.label == StopKind.OPTIONAL_STOP.value and not self._optional_stop:
                continue
            return mark
        return None

    # ── the moment shown ─────────────────────────────────────────────────

    def _show(self):
        self._moment = self._run.at(self._time) if self._run is not None else None
        self.momentChanged.emit()

    def _program_line(self):
        step = self._moment.step if self._moment is not None else 0
        steps = self._run.program.steps
        return steps[min(step, len(steps) - 1)].where.program_line if steps else 0

    def _time_of_line(self, line):
        for index, step in enumerate(self._run.program.steps):
            if step.where.program_line >= line:
                return self._run.start_of(index)
        return self._run.duration

    # ── what the backplot follows ────────────────────────────────────────

    @property
    def run(self):
        """The run worked out (a ProgramRun), or None."""
        return self._run

    @property
    def moment(self):
        """The moment shown (a program_run.Moment), or None."""
        return self._moment

    @pyqtProperty(str, notify=fileChanged)
    def content(self):
        """The program's text."""
        return self._content

    @pyqtProperty(str, notify=fileChanged)
    def programFile(self):
        """The file run: what the backplot previews."""
        return self._ngc_path

    # ── what QML reads ───────────────────────────────────────────────────

    @pyqtProperty(str, notify=fileChanged)
    def fileName(self):
        return os.path.basename(self._ngc_path)

    @pyqtProperty(bool, notify=loadingChanged)
    def loading(self):
        return self._loading

    @pyqtProperty(str, notify=errorChanged)
    def error(self):
        return self._error

    @pyqtProperty(bool, notify=runChanged)
    def ready(self):
        return self._run is not None

    @pyqtProperty(float, notify=runChanged)
    def duration(self):
        return self._run.duration if self._run is not None else 0.0

    @pyqtProperty(bool, notify=runChanged)
    def timed(self):
        """Its times are the machine's estimate, not a move a second."""
        return self._run is not None and self._run.timed

    @pyqtProperty("QVariantList", notify=runChanged)
    def marks(self):
        """What the seek bar marks: {time, kind, number, label}."""
        if self._run is None:
            return []
        return [{"time": m.time, "kind": m.kind.value, "number": m.number, "label": m.label} for m in self._run.marks]

    @pyqtProperty(int, notify=momentChanged)
    def tool(self):
        """The current loaded tool's T number, 0 for none."""
        return self._moment.tool if self._moment is not None else 0

    @pyqtProperty("QVariantList", notify=runChanged)
    def collisions(self):
        """The rapids through the material: {time}."""
        if self._run is None:
            return []
        return [{"time": c.time} for c in self._run.collisions]

    @pyqtProperty(float, notify=momentChanged)
    def time(self):
        return self._time

    @pyqtProperty(str, notify=momentChanged)
    def operation(self):
        """The operation under way: "Op 3 - Profile Roughing P1", or ""."""
        if self._moment is None:
            return ""
        current = ""
        for mark in self._run.marks:
            if mark.kind is MarkKind.OPERATION and mark.step <= self._moment.step:
                current = f"Op {mark.number} - {mark.label}"
        return current

    # ── what the DRO shows (ProgramsDro, as the machine's ProgramsDroViewModel) ──

    @pyqtProperty(str, notify=momentChanged)
    def workOffsetName(self):
        """The work offset the program is in at the moment shown: "G54" ..."""
        from teachinlathe.ui.tabs.programs.ProgramsDroViewModel import WORK_OFFSETS
        offset = self._moment.work_offset if self._moment is not None else 1
        return WORK_OFFSETS.get(offset, "G54")

    def _work_position(self):
        """(x, z): the tool's tip in the program's work offset at the moment
        shown - from where its origin is then - X a diameter, mm."""
        if self._moment is None or self._moment.at is None:
            return 0.0, 0.0
        at, origin = self._moment.at, self._moment.origin
        return 2.0 * (at.r - origin.r), at.z - origin.z

    def _distance_to_go(self):
        """(x, z): what is left of the move under way, X on the diameter."""
        from teachinlathe.simulation.model.moves import Move
        if self._moment is None or self._moment.at is None:
            return 0.0, 0.0
        step = self._run.program.steps[self._moment.step] if self._moment.step < len(self._run.program.steps) else None
        if not isinstance(step, Move):
            return 0.0, 0.0
        return 2.0 * (step.end.r - self._moment.at.r), step.end.z - self._moment.at.z

    @pyqtProperty(float, notify=momentChanged)
    def xPosition(self):
        return self._work_position()[0]

    @pyqtProperty(float, notify=momentChanged)
    def zPosition(self):
        return self._work_position()[1]

    @pyqtProperty(float, notify=momentChanged)
    def xDistanceToGo(self):
        return self._distance_to_go()[0]

    @pyqtProperty(float, notify=momentChanged)
    def zDistanceToGo(self):
        return self._distance_to_go()[1]

    @pyqtProperty(int, notify=momentChanged)
    def programLine(self):
        return self._program_line() if self._moment is not None else 0

    @pyqtProperty(str, notify=stateChanged)
    def state(self):
        return self._state

    @pyqtProperty(str, notify=stateChanged)
    def waitingFor(self):
        """"M0" or "M1" while it waits there for Cycle Start, else ""."""
        return self._waiting_for

    @pyqtProperty(float, notify=speedChanged)
    def speed(self):
        return self._speed

    @pyqtProperty("QVariantList", constant=True)
    def speeds(self):
        return list(SPEEDS)

    @pyqtProperty(bool, notify=optionalStopChanged)
    def optionalStop(self):
        return self._optional_stop

    def _set_state(self, state):
        # emitted even when the state stays: waitingFor may have changed
        self._state = state
        self.stateChanged.emit()

    def _set_loading(self, loading):
        if loading != self._loading:
            self._loading = loading
            self.loadingChanged.emit()

    def _set_error(self, error):
        if error != self._error:
            self._error = error
            self.errorChanged.emit()


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError as error:
        LOG.error("simulation: could not read %s: %s", path, error)
        return ""
