"""The Performance Diagnostics panel's view model: the mode, the window of
history shown, the summary of the last bucket, the slow operations, Reset
History and Export - over the DiagnosticsService the Application made.

The panel is told whether it is in sight (``setPanelVisible``): while it is,
each bucket closed - every 5 s - brings the summary, the list and the charts
up to date (``revision``, which the charts follow); while it is not, nothing
is read and nothing redrawn, and the history is read once it is again. The
charts (DiagnosticsChart) read the store themselves: no series is handed to
QML.
"""

from __future__ import annotations

import logging
import os
import threading
import time

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe import __version__
from teachinlathe.diagnostics.model import collectors as metric
from teachinlathe.diagnostics.model import event_loop as loop
from teachinlathe.diagnostics.model import export
from teachinlathe.diagnostics.model.collectors import system_info
from teachinlathe.diagnostics.model.formatting import fixed as _fmt
from teachinlathe.diagnostics.model.modes import SETTING, ProfilingMode
from teachinlathe.diagnostics.model.units import Unit
from teachinlathe.programs.model import backplot_lifecycle as backplot

LOG = logging.getLogger(__name__)

#: The windows of history the charts can show, seconds, and their labels.
WINDOWS = (300, 900, 1800, 3600, 14400)
WINDOW_LABELS = ("5 min", "15 min", "30 min", "1 h", "4 h")
#: How many slow operations the panel lists, the newest first.
SLOW_SHOWN = 30
#: The thread an export is written on.
EXPORT_THREAD = "diagnostics-export"

#: The panel's charts, top to bottom: a title, a height (px) and the series,
#: by name - those of one unit share a band (DiagnosticsChart).
CHARTS = (
    {"title": "Performance", "height": 260,
     "series": [metric.PROC_CPU_CORE_PCT, metric.SYS_CPU_PCT, loop.LOOP_P95_MS, loop.LOOP_MAX_MS]},
    {"title": "Temperature, load and frequency", "height": 420,
     "series": [metric.TEMP_MAX_C, metric.PROC_CPU_CORE_PCT, metric.SYS_CPU_PCT, metric.SYS_LOAD1,
                metric.SYS_CPU_MHZ_AVG]},
    {"title": "Memory and backplot", "height": 330,
     "series": [metric.PROC_RSS_MIB, metric.SYS_MEM_USED_MIB, backplot.NPTS,
                backplot.TRAIL_NATIVE_BYTES, backplot.TRAIL_AUX_BYTES]},
)

#: What a series is called on the panel.
LABELS = {
    metric.PROC_CPU_CORE_PCT: "Process CPU (of one core)",
    metric.PROC_CPU_TOTAL_PCT: "Process CPU (of all cores)",
    metric.SYS_CPU_PCT: "System CPU",
    metric.SYS_LOAD1: "Load 1 min",
    metric.SYS_CPU_MHZ_AVG: "CPU frequency (average)",
    loop.LOOP_P95_MS: "Event loop p95",
    loop.LOOP_MAX_MS: "Event loop max",
    metric.TEMP_MAX_C: "CPU max temperature",
    metric.PROC_RSS_MIB: "Process RSS",
    metric.SYS_MEM_USED_MIB: "System memory used",
    backplot.NPTS: "Backplot points",
    backplot.TRAIL_NATIVE_BYTES: "Trail memory (logger)",
    backplot.TRAIL_AUX_BYTES: "Trail memory (copies)",
}


class DiagnosticsViewModel(QObject):
    modeChanged = pyqtSignal()
    windowChanged = pyqtSignal()
    #: the history shown is other than it was: the charts draw again
    revisionChanged = pyqtSignal()
    summaryChanged = pyqtSignal()
    slowOperationsChanged = pyqtSignal()
    exportStatusChanged = pyqtSignal()
    cursorChanged = pyqtSignal()

    def __init__(self, service, settings=None, export_dir: str = "", parent=None):
        super().__init__(parent)
        self.service = service
        self._settings = settings
        self._export_dir = export_dir
        self._window = WINDOWS[1]
        self._visible = False
        self._stale = True
        self._revision = 0
        self._summary = []
        self._slow = []
        self._export_status = ""
        self._cursor = -1.0
        service.bucketClosed.connect(self._on_bucket)
        service.modeChanged.connect(lambda _mode: self.modeChanged.emit())
        self._exported.connect(self._on_exported)

    # ── what the charts read ─────────────────────────────────────────────

    @property
    def store(self):
        return self.service.store

    def label_of(self, name: str) -> str:
        return LABELS.get(name, name)

    @pyqtProperty(list, constant=True)
    def charts(self):
        """[{title, height, series}]: the charts the panel shows."""
        return [dict(chart) for chart in CHARTS]

    # ── the mode ─────────────────────────────────────────────────────────

    @pyqtProperty(list, constant=True)
    def modes(self):
        return [m.value for m in ProfilingMode]

    @pyqtProperty(list, constant=True)
    def modeLabels(self):
        return ["Off", "Basic", "Detailed"]

    @pyqtProperty(int, notify=modeChanged)
    def modeIndex(self):
        return [m for m in ProfilingMode].index(self.service.mode)

    @pyqtSlot(int)
    def setModeIndex(self, index):
        modes = list(ProfilingMode)
        if 0 <= index < len(modes):
            self.service.set_mode(modes[index])
            if self._settings is not None:
                self._settings.set(SETTING, modes[index].value)

    # ── the window shown ─────────────────────────────────────────────────

    @pyqtProperty(list, constant=True)
    def windowLabels(self):
        return list(WINDOW_LABELS)

    @pyqtProperty(int, notify=windowChanged)
    def windowIndex(self):
        return WINDOWS.index(self._window)

    @property
    def window_seconds(self) -> int:
        return self._window

    @pyqtSlot(int)
    def setWindowIndex(self, index):
        if 0 <= index < len(WINDOWS) and WINDOWS[index] != self._window:
            self._window = WINDOWS[index]
            self.windowChanged.emit()
            self._bump()

    # ── the moment looked at, across the charts ──────────────────────────

    @pyqtProperty(float, notify=cursorChanged)
    def cursorTime(self):
        """The wall time picked on a chart, every chart showing its values
        then; -1 for none: the newest."""
        return self._cursor

    @pyqtSlot(float)
    def setCursorTime(self, wall):
        wall = float(wall)
        if wall != self._cursor:
            self._cursor = wall
            self.cursorChanged.emit()

    # ── in sight or not ──────────────────────────────────────────────────

    @pyqtSlot(bool)
    def setPanelVisible(self, visible):
        self._visible = bool(visible)
        if self._visible and self._stale:
            self._refresh()

    @pyqtProperty(int, notify=revisionChanged)
    def revision(self):
        return self._revision

    def _on_bucket(self, _seq):
        if self._visible:
            self._refresh()
        else:
            self._stale = True

    def _bump(self):
        self._revision += 1
        self.revisionChanged.emit()

    def _refresh(self):
        self._stale = False
        self._summary = self._read_summary()
        self.summaryChanged.emit()
        self._slow = self._read_slow()
        self.slowOperationsChanged.emit()
        self._bump()

    # ── the summary and the slow ones ────────────────────────────────────

    @pyqtProperty(list, notify=summaryChanged)
    def summary(self):
        """[{label, value}] of the last bucket."""
        return self._summary

    @pyqtProperty(list, notify=slowOperationsChanged)
    def slowOperations(self):
        """[{time, name, duration, ok, status, meta}], the newest first."""
        return self._slow

    def _read_summary(self):
        row = self.store.last_row()
        get = row.get
        states = self.service.states().get(backplot.DIAGNOSTICS_NAME, {})
        cores = os.cpu_count() or 1
        return [
            {"label": "Process CPU", "value": "%s of one core  (%s of %d cores)" % (
                _fmt(get(metric.PROC_CPU_CORE_PCT), 1, Unit.PERCENT),
                _fmt(get(metric.PROC_CPU_TOTAL_PCT), 1, Unit.PERCENT), cores)},
            {"label": "System CPU", "value": _fmt(get(metric.SYS_CPU_PCT), 1, Unit.PERCENT)},
            {"label": "Load average", "value": "%s / %s / %s" % (
                _fmt(get(metric.SYS_LOAD1), 2), _fmt(get(metric.SYS_LOAD5), 2), _fmt(get(metric.SYS_LOAD15), 2))},
            {"label": "CPU max temperature", "value": _fmt(get(metric.TEMP_MAX_C), 0, Unit.CELSIUS)},
            {"label": "CPU frequency", "value": "avg %s, max %s" % (
                _fmt(get(metric.SYS_CPU_MHZ_AVG), 0, Unit.MHZ), _fmt(get(metric.SYS_CPU_MHZ_MAX), 0, Unit.MHZ))},
            {"label": "Power", "value": {1.0: "mains", 0.0: "battery"}.get(get(metric.SYS_ON_AC), "–")},
            {"label": "Process RSS", "value": _fmt(get(metric.PROC_RSS_MIB), 0, Unit.MIB)},
            {"label": "System memory used", "value": "%s  (%s)" % (
                _fmt(get(metric.SYS_MEM_USED_MIB), 0, Unit.MIB),
                _fmt(get(metric.SYS_MEM_USED_PCT), 0, Unit.PERCENT))},
            {"label": "Threads", "value": _fmt(get(metric.PROC_THREADS), 0)},
            {"label": "Event loop lag", "value": "now %s, p95 %s, max %s" % (
                _fmt(get(loop.LOOP_LAST_MS), 1, Unit.MS), _fmt(get(loop.LOOP_P95_MS), 1, Unit.MS),
                _fmt(get(loop.LOOP_MAX_MS), 0, Unit.MS))},
            {"label": "Backplot points", "value": "%s of %s" % (
                _fmt(get(backplot.NPTS), 0), _fmt(get(backplot.POINTS_LIMIT), 0))},
            {"label": "Position logger", "value": "on" if states.get(backplot.STATE_LOGGER_ACTIVE) else "off"},
            {"label": "Backplot poll timer", "value": "on" if states.get(backplot.STATE_POLL_ACTIVE) else "off"},
        ]

    def _read_slow(self):
        out = []
        for slow in reversed(list(self.service.profiler.slow)[-SLOW_SHOWN:]):
            meta = ", ".join("%s=%s" % (k, v) for k, v in sorted(slow.meta.items()))
            out.append({"time": time.strftime("%H:%M:%S", time.localtime(slow.wall)),
                        "name": slow.name, "duration": "%.0f ms" % slow.duration_ms,
                        "ok": slow.ok, "status": "ok" if slow.ok else "failed", "meta": meta})
        return out

    # ── Reset History, Export ────────────────────────────────────────────

    @pyqtSlot()
    def resetHistory(self):
        self.service.reset_history()
        self._refresh()

    @pyqtProperty(str, notify=exportStatusChanged)
    def exportStatus(self):
        return self._export_status

    @pyqtSlot()
    def exportHistory(self):
        """The window shown, as JSON in the diagnostics folder. Only the states
        are read here - on the thread that owns what they read; the report,
        the machine's settings and the file are made off the UI thread."""
        service = self.service
        states = service.states()
        mode, unavailable, seconds = service.mode.value, list(service.unavailable), self._window
        directory = self._export_dir or os.path.expanduser(export.FALLBACK_DIRECTORY)
        self._set_export_status("Exporting…")

        def write():
            try:
                data = export.report(service.store, service.profiler, __version__, mode, unavailable,
                                     states, seconds=seconds, system=system_info())
                path = export.write(data, directory)
                self._exported.emit(path, "")
            except (OSError, ValueError) as exc:
                self._exported.emit("", str(exc))

        threading.Thread(target=write, name=EXPORT_THREAD, daemon=True).start()

    #: from the export's thread: (path, error)
    _exported = pyqtSignal(str, str)

    def _set_export_status(self, text):
        if text != self._export_status:
            self._export_status = text
            self.exportStatusChanged.emit()

    def _on_exported(self, path, error):
        self._set_export_status("Exported to %s" % path if path else "Export failed: %s" % error)
