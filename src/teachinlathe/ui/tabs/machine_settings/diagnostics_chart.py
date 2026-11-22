"""A chart of diagnostics series over the window of history shown, drawn in
Python from the store (DiagnosticsChart): no series is handed to QML.

Series of one unit share a band with its own scale - from 0, or the lowest
value when it is below 0, to the highest - and the bands are stacked over one
time axis: the CPU, the temperature and the event loop's lag of one moment
are one above the other, each in its own real values. A bucket without data
breaks its line. The moment picked (``cursorTime``, the view model's, one for
every chart) is a line across, each series' value then in its legend.

It draws again only when told (``revision``, which the view model raises as
a bucket closes while the panel is in sight) or resized.
"""

from __future__ import annotations

import math
import time

import numpy as np
from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtQml import qmlRegisterType
from PyQt6.QtQuick import QQuickPaintedItem

from teachinlathe.diagnostics.model.export import unit_of
from teachinlathe.diagnostics.model.formatting import short as _short
from teachinlathe.diagnostics.model.series import BUCKET_SECONDS
from teachinlathe.diagnostics.model.units import Unit

COLORS = ("#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b")
AXIS = QColor("#9e9e9e")
GRID = QColor("#eeeeee")
TEXT = QColor("#424242")
CURSOR = QColor("#ff6f00")
LEFT, RIGHT, TOP, BOTTOM = 64, 12, 8, 22
#: How wide a column of the line is, px: the buckets that fall in one are
#: drawn as their lowest and highest.
COLUMN_PX = 2
BAND_GAP = 10
LEGEND_HEIGHT = 16


def _scaled(value, unit):
    """Bytes shown as MiB: the series stay in bytes."""
    if unit == Unit.BYTES:
        return value / 2 ** 20, Unit.MIB
    return value, unit


class DiagnosticsChart(QQuickPaintedItem):
    viewModelChanged = pyqtSignal()
    seriesChanged = pyqtSignal()
    revisionChanged = pyqtSignal()
    cursorTimeChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm = None
        self._series = []
        self._revision = 0
        self._cursor = -1.0
        # the time axis last drawn: (first wall, last wall) - for timeAt
        self._span = (0.0, 0.0)
        self.paints = 0
        self.setAntialiasing(True)

    # ── properties ───────────────────────────────────────────────────────

    def _get_vm(self):
        return self._vm

    def _set_vm(self, vm):
        if vm is not self._vm:
            self._vm = vm
            self.viewModelChanged.emit()
            self.update()

    viewModel = pyqtProperty(QObject, _get_vm, _set_vm, notify=viewModelChanged)

    def _get_series(self):
        return list(self._series)

    def _set_series(self, series):
        series = [str(s) for s in (series or [])]
        if series != self._series:
            self._series = series
            self.seriesChanged.emit()
            self.update()

    #: the series drawn, by name
    series = pyqtProperty(list, _get_series, _set_series, notify=seriesChanged)

    def _get_revision(self):
        return self._revision

    def _set_revision(self, revision):
        if revision != self._revision:
            self._revision = revision
            self.revisionChanged.emit()
            self.update()

    revision = pyqtProperty(int, _get_revision, _set_revision, notify=revisionChanged)

    def _get_cursor(self):
        return self._cursor

    def _set_cursor(self, wall):
        if wall != self._cursor:
            self._cursor = float(wall)
            self.cursorTimeChanged.emit()
            self.update()

    cursorTime = pyqtProperty(float, _get_cursor, _set_cursor, notify=cursorTimeChanged)

    @pyqtSlot(float, result=float)
    def timeAt(self, x):
        """The wall time at ``x`` on the time axis; -1 off it."""
        first, last = self._span
        width = self.width() - LEFT - RIGHT
        if last <= first or width <= 0 or x < LEFT:
            return -1.0
        return first + (min(x, LEFT + width) - LEFT) / width * (last - first)

    # ── drawing ──────────────────────────────────────────────────────────

    def paint(self, painter: QPainter):
        self.paints += 1
        vm = self._vm
        if vm is None or not self._series:
            return
        store = vm.store
        buckets = int(vm.window_seconds / BUCKET_SECONDS)
        rows = store.rows_since(store.next_seq - buckets - 1, self._series)
        width, height = self.width(), self.height()
        plot_w = width - LEFT - RIGHT
        if plot_w <= 10:
            return
        last_wall = float(rows.wall[-1]) if len(rows) else time.time()
        first_wall = last_wall - vm.window_seconds
        self._span = (first_wall, last_wall)
        font = QFont()
        font.setPixelSize(11)
        painter.setFont(font)

        bands = {}
        for name in self._series:
            bands.setdefault(_scaled(1.0, unit_of(store, name))[1], []).append(name)
        count = max(1, len(bands))
        band_h = (height - TOP - BOTTOM - BAND_GAP * (count - 1)) / count

        def x_of(wall):
            return LEFT + (wall - first_wall) / max(1e-9, last_wall - first_wall) * plot_w

        cursor_at = None
        if self._cursor >= 0 and len(rows):
            cursor_at = int(np.argmin(np.abs(rows.wall - self._cursor)))
        color_at = 0
        for band, (unit, names) in enumerate(bands.items()):
            top = TOP + band * (band_h + BAND_GAP)
            area = QRectF(LEFT, top + LEGEND_HEIGHT, plot_w, max(4.0, band_h - LEGEND_HEIGHT))
            values = {n: _scaled(rows.values[n], unit_of(store, n))[0] for n in names if n in rows.values}
            finite = [v[np.isfinite(v)] for v in values.values()]
            finite = np.concatenate(finite) if finite else np.zeros(0)
            low = min(0.0, float(finite.min())) if len(finite) else 0.0
            high = float(finite.max()) if len(finite) else 1.0
            if high <= low:
                high = low + 1.0
            high *= 1.05 if high > 0 else 1.0

            painter.setPen(QPen(GRID, 1))
            for k in range(5):
                y = area.top() + area.height() * k / 4
                painter.drawLine(QPointF(area.left(), y), QPointF(area.right(), y))
            painter.setPen(QPen(AXIS, 1))
            painter.drawRect(area)
            painter.setPen(TEXT)
            right = Qt.AlignmentFlag.AlignRight
            painter.drawText(QRectF(0, area.top() - 6, LEFT - 6, 14), right, _short(high))
            painter.drawText(QRectF(0, area.center().y() - 7, LEFT - 6, 14), right, unit)
            painter.drawText(QRectF(0, area.bottom() - 8, LEFT - 6, 14), right, _short(low))

            legend_x = LEFT
            for name in names:
                color = QColor(COLORS[color_at % len(COLORS)])
                color_at += 1
                series = values.get(name)
                if series is None:
                    series = np.full(len(rows), math.nan)
                xs = LEFT + (rows.wall - first_wall) / max(1e-9, last_wall - first_wall) * plot_w
                ys = area.bottom() - (series - low) / (high - low) * area.height()
                # not antialiased: on the software painter a line of two
                # thousand points costs three times as much smoothed
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
                painter.setPen(QPen(color, 1.5))
                for line in _polylines(xs, ys):
                    painter.drawPolyline(line)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                at = cursor_at if cursor_at is not None else len(series) - 1
                shown = series[at] if 0 <= at < len(series) else math.nan
                text = "%s: %s" % (self._vm.label_of(name), _short(shown) if math.isfinite(shown) else "–")
                painter.setPen(color)
                painter.drawText(QPointF(legend_x, top + 12), text)
                legend_x += painter.fontMetrics().horizontalAdvance(text) + 16

        # the time axis, shared
        painter.setPen(TEXT)
        for k in range(5):
            wall = first_wall + (last_wall - first_wall) * k / 4
            x = x_of(wall)
            label = time.strftime("%H:%M", time.localtime(wall))
            box, align = QRectF(x - 30, height - BOTTOM + 4, 60, 14), Qt.AlignmentFlag.AlignHCenter
            if k == 4:
                box, align = QRectF(x - 60, height - BOTTOM + 4, 60, 14), Qt.AlignmentFlag.AlignRight
            painter.drawText(box, align, label)
        if cursor_at is not None:
            x = x_of(float(rows.wall[cursor_at]))
            painter.setPen(QPen(CURSOR, 1, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(x, TOP), QPointF(x, height - BOTTOM))
            painter.drawText(QRectF(x - 40, height - BOTTOM + 4, 80, 14), Qt.AlignmentFlag.AlignHCenter,
                             time.strftime("%H:%M:%S", time.localtime(float(rows.wall[cursor_at]))))


def _polylines(xs: np.ndarray, ys: np.ndarray):
    """The line through points ``xs``, ``ys`` (pixels; NaN where there was no
    data), as QPolygonFs - one for each stretch without a gap - with no more
    than two points a pixel column: where several buckets share a column,
    their lowest and highest, so a spike narrower than a pixel still shows.
    Worked out with numpy, not point by point: four hours are 2880 points a
    series."""
    if not len(xs):
        return []
    columns = (np.floor(xs / COLUMN_PX) * COLUMN_PX).astype(np.int64)
    starts = np.flatnonzero(np.r_[True, columns[1:] != columns[:-1]])
    if len(starts) < len(xs):
        # several points a column: its lowest and its highest (NaN only when
        # every point in it is)
        low = np.fmin.reduceat(ys, starts)
        high = np.fmax.reduceat(ys, starts)
        x = columns[starts].astype(float) + COLUMN_PX / 2
        xs = np.repeat(x, 2)
        ys = np.column_stack([low, high]).ravel()
    finite = np.isfinite(ys)
    lines = []
    # stretches between the gaps
    edges = np.flatnonzero(np.diff(np.r_[False, finite, False].astype(np.int8)))
    for begin, end in zip(edges[::2], edges[1::2]):
        if end - begin >= 1:
            lines.append(QPolygonF(list(map(QPointF, xs[begin:end].tolist(), ys[begin:end].tolist()))))
    return lines


def register_qml_types():
    qmlRegisterType(DiagnosticsChart, "TeachInLathe.Diagnostics", 1, 0, "DiagnosticsChart")
