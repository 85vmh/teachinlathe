import linuxcnc
from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent


class ProgramsToolFeedSpeedViewModel(QObject):
    valuesChanged = pyqtSignal()

    MODE_RPM = 0
    MODE_CSS = 1

    def __init__(self, runtime_store, tool_changes, parent=None):
        """``tool_changes``: the program loaded's next tool
        (programs.logic.tool_changes_use_case.ToolChangesUseCase)."""
        super().__init__(parent)
        self._runtime_store = runtime_store
        self._tool_changes = tool_changes
        self._snapshot = runtime_store.snapshot
        self._actual_rpm = 0.0

        self._lathe_component = TeachInLatheComponent()
        self._lathe_component.comp.addListener(
            TeachInLatheComponent.PinSpindleActualRpm,
            self._on_actual_rpm_changed,
        )

        self._runtime_store.snapshotChanged.connect(self._on_runtime_snapshot_changed)
        self._tool_changes.changed.connect(self.valuesChanged)

    def _on_runtime_snapshot_changed(self, snapshot):
        self._snapshot = snapshot
        self.valuesChanged.emit()

    def _on_actual_rpm_changed(self, value):
        try:
            next_rpm = abs(float(value or 0.0))
        except Exception:
            next_rpm = 0.0
        if int(round(next_rpm)) == int(round(self._actual_rpm)):
            return
        self._actual_rpm = next_rpm
        self.valuesChanged.emit()

    def _percent(self, value):
        try:
            numeric = float(value)
        except Exception:
            return 100
        if numeric <= 0:
            return 100
        return int(round(numeric * 100))

    def _motion_is_feed(self):
        motion_type = int(getattr(self._snapshot, 'motion_type', 0) or 0)
        return motion_type in (linuxcnc.MOTION_TYPE_FEED, linuxcnc.MOTION_TYPE_ARC)

    def _motion_is_traverse(self):
        motion_type = int(getattr(self._snapshot, 'motion_type', 0) or 0)
        return motion_type == linuxcnc.MOTION_TYPE_TRAVERSE

    def _movement_value(self):
        if self._motion_is_feed():
            live_value = self._live_mm_per_rev()
            if live_value > 0:
                return live_value
        if self._motion_is_traverse():
            return self._live_mm_per_min()
        return self._active_feed_value()

    def _live_mm_per_rev(self):
        rpm = self._actual_rpm
        if rpm <= 0:
            return 0.0
        current_vel = float(getattr(self._snapshot, 'current_vel', 0.0) or 0.0)
        return (current_vel * 60.0) / rpm

    def _live_mm_per_min(self):
        current_vel = float(getattr(self._snapshot, 'current_vel', 0.0) or 0.0)
        return current_vel * 60.0

    def _active_feed_value(self):
        settings = tuple(getattr(self._snapshot, 'interpreter_settings', ()) or ())
        if len(settings) <= 1:
            return 0.0
        try:
            return float(settings[1] or 0.0)
        except Exception:
            return 0.0

    def _current_loaded_tool(self):
        return int(getattr(self._snapshot, 'current_loaded_tool', 0) or 0)

    def _next_tool(self):
        return self._tool_changes.next_tool(self._current_loaded_tool())

    @pyqtProperty(str, notify=valuesChanged)
    def currentLoadedToolText(self):
        return f"T{self._current_loaded_tool()}"

    @pyqtProperty(bool, notify=valuesChanged)
    def hasNextTool(self):
        return self._next_tool() is not None

    @pyqtProperty(str, notify=valuesChanged)
    def nextToolText(self):
        next_tool = self._next_tool()
        return "" if next_tool is None else f"T{next_tool.tool}"

    @pyqtProperty(str, notify=valuesChanged)
    def nextToolTimeText(self):
        """How long until the machine stops for the next tool, m:ss - "" while
        the program is not running, or not timed."""
        next_tool = self._next_tool()
        if next_tool is None or next_tool.seconds is None:
            return ""
        minutes, seconds = divmod(int(round(next_tool.seconds)), 60)
        return f"{minutes}:{seconds:02d}"

    @pyqtProperty(str, notify=valuesChanged)
    def movementLetter(self):
        if self._motion_is_traverse():
            return "R"
        return "F"

    @pyqtProperty(str, notify=valuesChanged)
    def movementValueText(self):
        if self._motion_is_traverse():
            return f"{self._movement_value():.0f}"
        return f"{self._movement_value():.2f}"

    @pyqtProperty(str, notify=valuesChanged)
    def movementUnitsText(self):
        if self._motion_is_traverse():
            return "mm/min"
        return "mm/rev"

    @pyqtProperty(int, notify=valuesChanged)
    def movementOverridePercent(self):
        if self._motion_is_traverse():
            return self._percent(getattr(self._snapshot, 'rapidrate', 0.0))
        return self._percent(getattr(self._snapshot, 'feedrate', 0.0))

    @pyqtProperty(int, notify=valuesChanged)
    def spindleOverridePercent(self):
        return self._percent(getattr(self._snapshot, 'spindle_override', 0.0))

    @pyqtProperty(str, notify=valuesChanged)
    def spindleRpmText(self):
        return f"{self._actual_rpm:.0f}"

    @pyqtProperty(int, notify=valuesChanged)
    def spindleMode(self):
        return self.MODE_RPM

    @pyqtProperty(bool, notify=valuesChanged)
    def spindleIsCss(self):
        return self.spindleMode == self.MODE_CSS

    @pyqtProperty(str, notify=valuesChanged)
    def cssValueText(self):
        return "0"
