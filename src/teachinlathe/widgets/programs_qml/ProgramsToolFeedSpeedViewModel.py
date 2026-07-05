import linuxcnc
from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from teachinlathe.lathe_hal_component import TeachInLatheComponent


class ProgramsToolFeedSpeedViewModel(QObject):
    valuesChanged = pyqtSignal()

    MODE_RPM = 0
    MODE_CSS = 1

    def __init__(self, runtime_store, parent=None):
        super().__init__(parent)
        self._runtime_store = runtime_store
        self._snapshot = runtime_store.snapshot
        self._actual_rpm = 0.0
        self._last_debug_signature = None

        self._lathe_component = TeachInLatheComponent()
        self._lathe_component.comp.addListener(
            TeachInLatheComponent.PinSpindleActualRpm,
            self._on_actual_rpm_changed,
        )

        self._runtime_store.snapshotChanged.connect(self._on_runtime_snapshot_changed)

    def _on_runtime_snapshot_changed(self, snapshot):
        self._snapshot = snapshot
        self._debug_runtime_values("snapshot")
        self.valuesChanged.emit()

    def _on_actual_rpm_changed(self, value):
        try:
            next_rpm = abs(float(value or 0.0))
        except Exception:
            next_rpm = 0.0
        if int(round(next_rpm)) == int(round(self._actual_rpm)):
            return
        self._actual_rpm = next_rpm
        self._debug_runtime_values("rpm")
        self.valuesChanged.emit()

    def _debug_runtime_values(self, source):
        motion_type = int(getattr(self._snapshot, 'motion_type', 0) or 0)
        current_vel = float(getattr(self._snapshot, 'current_vel', 0.0) or 0.0)
        feedrate = float(getattr(self._snapshot, 'feedrate', 0.0) or 0.0)
        rapidrate = float(getattr(self._snapshot, 'rapidrate', 0.0) or 0.0)
        spindle_override = float(getattr(self._snapshot, 'spindle_override', 0.0) or 0.0)
        settings = tuple(getattr(self._snapshot, 'interpreter_settings', ()) or ())
        signature = (
            motion_type,
            round(current_vel, 6),
            round(feedrate, 6),
            round(rapidrate, 6),
            round(spindle_override, 6),
            tuple(round(float(v or 0.0), 6) for v in settings[:5]),
            int(round(self._actual_rpm)),
            self.movementLetter,
            self.movementUnitsText,
            self.movementValueText,
            self.movementOverridePercent,
        )
        if signature == self._last_debug_signature:
            return
        self._last_debug_signature = signature
        # print(
        #     "[ProgramsToolFeedSpeed]",
        #     source,
        #     f"motion_type={motion_type}",
        #     f"current_vel={current_vel}",
        #     f"feedrate={feedrate}",
        #     f"rapidrate={rapidrate}",
        #     f"spindle_override={spindle_override}",
        #     f"settings={settings}",
        #     f"actual_rpm={self._actual_rpm}",
        #     f"movementLetter={self.movementLetter}",
        #     f"movementUnits={self.movementUnitsText}",
        #     f"movementValue={self.movementValueText}",
        #     f"movementOverride={self.movementOverridePercent}",
        # )

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

    @pyqtProperty(str, notify=valuesChanged)
    def currentToolText(self):
        tool = int(getattr(self._snapshot, 'tool_in_spindle', 0) or 0)
        return f"T{tool}"

    @pyqtProperty(str, notify=valuesChanged)
    def nextToolText(self):
        return "T-"

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
