"""The whole Qt Quick frame of the window, timed: what Python's own spans do
not see - the scene graph laid out, synchronised and drawn for every item on
screen, the DRO and the boxes as much as the backplot, and the swap.

From QQuickWindow's signals, on the thread that renders (the UI thread, with
the "basic" render loop the application uses):

    qsg.frame        beforeFrameBegin   -> afterFrameEnd   the whole frame
    qsg.sync         beforeSynchronizing-> afterSynchronizing  items to nodes
    qsg.render       beforeRendering    -> afterRendering  the scene drawn
                                                           (the backplot's FBO
                                                           among it)
    qsg.swap         afterRendering     -> frameSwapped    handing it over

Connected, directly, only in the "detailed" mode (``set_enabled``), and
disconnected otherwise: off, nothing is called per frame.
"""

from __future__ import annotations

import time

from PyQt6.QtCore import QObject, Qt

from teachinlathe.diagnostics.model.operations import QSG_PREFIX
from teachinlathe.diagnostics.model.spans import PROFILER, Profiler

#: The stages of a frame, each timed as ``QSG_PREFIX + stage``.
FRAME = "frame"
SYNC = "sync"
RENDER = "render"
SWAP = "swap"


class QuickFrameTimer(QObject):
    """Connected to the window's signals only while ``set_enabled(True)`` -
    the "detailed" mode - and not at all otherwise: no call per frame."""

    def __init__(self, window, profiler: Profiler = None, parent=None):
        super().__init__(parent)
        self._window = window
        self._profiler = PROFILER if profiler is None else profiler
        self._marks = {}
        self._connections = []

    @property
    def enabled(self) -> bool:
        return bool(self._connections)

    def set_enabled(self, on: bool) -> None:
        if bool(on) == self.enabled:
            return
        if not on:
            for signal, slot in self._connections:
                signal.disconnect(slot)
            self._connections = []
            self._marks = {}
            return
        window = self._window
        slots = (
            (window.beforeFrameBegin, lambda: self._begin(FRAME)),
            (window.beforeSynchronizing, lambda: self._begin(SYNC)),
            (window.beforeRendering, lambda: self._begin(RENDER)),
            (window.afterSynchronizing, lambda: self._end(SYNC)),
            (window.afterRendering, self._after_rendering),
            (window.frameSwapped, lambda: self._end(SWAP)),
            (window.afterFrameEnd, lambda: self._end(FRAME)),
        )
        for signal, slot in slots:
            signal.connect(slot, Qt.ConnectionType.DirectConnection)
        self._connections = list(slots)

    def _begin(self, mark):
        self._marks[mark] = time.perf_counter_ns()

    def _end(self, mark):
        start = self._marks.pop(mark, None)
        if start is not None:
            now = time.perf_counter_ns()
            self._profiler.record(QSG_PREFIX + mark, start, now - start)

    def _after_rendering(self):
        self._end(RENDER)
        self._marks[SWAP] = time.perf_counter_ns()
