"""The add/edit screen for a reamer.

Like the other editors it works on a copy: nothing reaches the store until
`result()` is taken by a save. What the reamer is and how it is drawn is in
ReamingToolView, which this builds on.
"""

from __future__ import annotations

import copy

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.tooling.data_types import ReamingTool, SpindleDirection
from teachinlathe.widgets.tools_qml.ReamingToolView import REAMER_ORIENTATION, ReamingToolView

DEFAULT_DIAMETER = 10.0


def new_reaming_tool(cutting_tool_id: int) -> ReamingTool:
    return ReamingTool(cutting_tool_id=cutting_tool_id, diameter=DEFAULT_DIAMETER)


class ReamingToolEditorViewModel(ReamingToolView):
    """ReamingToolView with the edits: it shows what the list will show."""

    # PyQt wants a property's notify signal declared in the property's own
    # class, so the editor's properties notify on this, which follows
    # ReamingToolView.changed.
    edited = pyqtSignal()

    def __init__(self, tool: ReamingTool, is_new: bool, parent=None):
        super().__init__(copy.deepcopy(tool), parent)
        self.changed.connect(self.edited)
        self._is_new = is_new
        if self._tool.diameter <= 0:
            self._tool.diameter = DEFAULT_DIAMETER

    def result(self) -> ReamingTool:
        return copy.deepcopy(self._tool)

    # ── What the screen shows ───────────────────────────────────────────────

    @pyqtProperty(str, notify=edited)
    def title(self):
        label = self._tool.tool_type.tool_name
        if self._is_new:
            return f"New {label}"
        return f"Edit {label} #{self._tool.cutting_tool_id}"

    @pyqtProperty(bool, constant=True)
    def isNew(self):
        return self._is_new

    @pyqtProperty("QVariantList", constant=True)
    def allowedOrientations(self):
        return [REAMER_ORIENTATION]

    # ── Edits ───────────────────────────────────────────────────────────────

    @pyqtSlot(float)
    def setDiameter(self, value):
        if value > 0:
            self._tool.diameter = float(value)
        self.changed.emit()            # puts the field back when refused

    @pyqtSlot(bool)
    def setClockwise(self, clockwise):
        self._tool.spindle_direction = SpindleDirection.CW if clockwise else SpindleDirection.CCW
        self.changed.emit()
