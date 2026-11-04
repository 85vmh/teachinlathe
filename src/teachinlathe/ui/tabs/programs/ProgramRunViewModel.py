"""A program run as the Programs screens show it - the DRO (ProgramsDro),
the spindle, feed and tool boxes (ProgramsToolFeedSpeed), the code's line,
the timeline and the buttons - whatever runs it: the machine or a simulation
(a programs.logic.run.ProgramRunSource). The backplot is drawn from its
``plot_source()``.
"""

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.machine.model.work_offsets import work_offset_name


class ProgramRunViewModel(QObject):
    #: The state or the moment may be other than they were.
    changed = pyqtSignal()
    #: What is run may be: its duration, its marks.
    runChanged = pyqtSignal()

    def __init__(self, source, plot_source, parent=None):
        """``source``: the run (a ProgramRunSource); ``plot_source``: makes
        the backplot's PlotSource for it."""
        super().__init__(parent)
        self._source = source
        self._plot_source = plot_source
        source.changed.connect(self.changed)
        source.runChanged.connect(self.runChanged)

    def plot_source(self):
        """What the backplot draws this run from (backplot.plot_source)."""
        return self._plot_source()

    # ── the run ──────────────────────────────────────────────────────────

    @pyqtProperty(str, notify=changed)
    def state(self):
        """"idle", "running", "held", "waiting", "finished"."""
        return self._source.state.value

    @pyqtProperty(str, notify=changed)
    def waitingFor(self):
        """"M0" or "M1" while it waits there for Cycle Start, else ""."""
        return self._source.waiting_for

    @pyqtProperty(int, notify=changed)
    def programLine(self):
        return self._source.moment.program_line

    @pyqtProperty(int, notify=changed)
    def tool(self):
        """The current loaded tool's T number, 0 for none."""
        return self._source.moment.tool

    # ── the DRO ──────────────────────────────────────────────────────────

    @pyqtProperty(str, notify=changed)
    def workOffsetName(self):
        return work_offset_name(self._source.moment.work_offset)

    @pyqtProperty(float, notify=changed)
    def xPosition(self):
        return self._source.moment.x

    @pyqtProperty(float, notify=changed)
    def zPosition(self):
        return self._source.moment.z

    @pyqtProperty(float, notify=changed)
    def xDistanceToGo(self):
        return self._source.moment.x_to_go

    @pyqtProperty(float, notify=changed)
    def zDistanceToGo(self):
        return self._source.moment.z_to_go

    # ── the tool box: Current -> Next ────────────────────────────────────

    @pyqtProperty(str, notify=changed)
    def currentLoadedToolText(self):
        return f"T{self._source.moment.tool}"

    @pyqtProperty(bool, notify=changed)
    def hasNextTool(self):
        return self._source.moment.next_tool is not None

    @pyqtProperty(str, notify=changed)
    def nextToolText(self):
        next_tool = self._source.moment.next_tool
        return "" if next_tool is None else f"T{next_tool.tool}"

    @pyqtProperty(str, notify=changed)
    def nextToolTimeText(self):
        """How long until the run stops for the next tool, m:ss - "" while it
        is not running, or not timed."""
        next_tool = self._source.moment.next_tool
        if next_tool is None or next_tool.seconds is None:
            return ""
        minutes, seconds = divmod(int(round(next_tool.seconds)), 60)
        return f"{minutes}:{seconds:02d}"

    # ── the feed box ─────────────────────────────────────────────────────

    @pyqtProperty(str, notify=changed)
    def movementLetter(self):
        return "R" if self._source.moment.motion.rapid else "F"

    @pyqtProperty(str, notify=changed)
    def movementValueText(self):
        motion = self._source.moment.motion
        return f"{motion.feed:.0f}" if not motion.per_rev else f"{motion.feed:.2f}"

    @pyqtProperty(str, notify=changed)
    def movementUnitsText(self):
        return "mm/rev" if self._source.moment.motion.per_rev else "mm/min"

    @pyqtProperty(int, notify=changed)
    def movementOverridePercent(self):
        return int(round(self._source.moment.motion.feed_override * 100))

    # ── the spindle box ──────────────────────────────────────────────────

    @pyqtProperty(int, notify=changed)
    def spindleOverridePercent(self):
        return int(round(self._source.moment.motion.spindle_override * 100))

    @pyqtProperty(str, notify=changed)
    def spindleRpmText(self):
        return f"{self._source.moment.motion.rpm:.0f}"

    @pyqtProperty(bool, notify=changed)
    def spindleIsCss(self):
        return self._source.moment.motion.css is not None

    @pyqtProperty(str, notify=changed)
    def cssValueText(self):
        css = self._source.moment.motion.css
        return "0" if css is None else f"{css:.0f}"

    # ── the timeline ─────────────────────────────────────────────────────

    @pyqtProperty(float, notify=changed)
    def time(self):
        """Seconds from cycle start, 0 when not known."""
        return self._source.moment.time or 0.0

    @pyqtProperty(float, notify=runChanged)
    def duration(self):
        return self._source.duration or 0.0

    @pyqtProperty("QVariantList", notify=runChanged)
    def marks(self):
        """What the seek bar marks: {time, kind, number, label}."""
        return [{"time": m.time, "kind": m.kind, "number": m.number,
                 "label": m.label, "toolChange": m.tool_change}
                for m in self._source.marks]

    @pyqtProperty(bool, constant=True)
    def seekable(self):
        return self._source.seekable

    @pyqtProperty("QVariantList", constant=True)
    def speeds(self):
        return list(self._source.speeds)

    @pyqtProperty(float, notify=changed)
    def speed(self):
        return self._source.speed

    # ── what drives it ───────────────────────────────────────────────────

    @pyqtSlot()
    def cycleStart(self):
        self._source.cycle_start()

    @pyqtSlot()
    def feedHold(self):
        self._source.feed_hold()

    @pyqtSlot()
    def cycleStop(self):
        self._source.cycle_stop()

    @pyqtSlot(float)
    def seek(self, time):
        self._source.seek(time)

    @pyqtSlot(int)
    def seekToLine(self, line):
        self._source.seek_to_line(line)

    @pyqtSlot(float)
    def setSpeed(self, speed):
        self._source.set_speed(speed)
