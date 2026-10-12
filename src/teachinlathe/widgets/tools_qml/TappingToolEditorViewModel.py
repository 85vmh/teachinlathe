"""The add/edit screen for a tap.

Like the other editors it works on a copy: nothing reaches the store until
`result()` is taken by a save. What the tap is and how it is drawn is in
TappingToolView, which this builds on.
"""

from __future__ import annotations

import copy

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.tooling.data_types import SpindleDirection, TappingTool, TwistDirection
from teachinlathe.widgets.tools_qml.TappingToolView import TappingToolView

DEFAULT_DIAMETER = 10.0
DEFAULT_PITCH = 1.5


def new_tapping_tool(cutting_tool_id: int) -> TappingTool:
    return TappingTool(cutting_tool_id=cutting_tool_id, diameter=DEFAULT_DIAMETER,
                       pitch=DEFAULT_PITCH, twist_direction=TwistDirection.RIGHT_HAND)


class TappingToolEditorViewModel(TappingToolView):
    """TappingToolView with the edits: it shows what the list will show."""

    # PyQt wants a property's notify signal declared in the property's own
    # class, so the editor's properties notify on this, which follows
    # TappingToolView.changed.
    edited = pyqtSignal()

    def __init__(self, tool: TappingTool, is_new: bool, parent=None):
        super().__init__(copy.deepcopy(tool), parent)
        self.changed.connect(self.edited)
        self._is_new = is_new
        if self._tool.diameter <= 0:
            self._tool.diameter = DEFAULT_DIAMETER
        if self._tool.pitch <= 0:
            self._tool.pitch = DEFAULT_PITCH

    def result(self) -> TappingTool:
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

    # ── Edits ───────────────────────────────────────────────────────────────

    @pyqtSlot(float)
    def setDiameter(self, value):
        if value > 0:
            self._tool.diameter = float(value)
        self.changed.emit()            # puts the field back when refused

    @pyqtSlot(float)
    def setPitch(self, value):
        if value > 0:
            self._tool.pitch = float(value)
        self.changed.emit()

    @pyqtSlot(bool)
    def setRightHand(self, right_hand):
        self._tool.twist_direction = (TwistDirection.RIGHT_HAND if right_hand
                                      else TwistDirection.LEFT_HAND)
        self.changed.emit()

    @pyqtSlot(bool)
    def setClockwise(self, clockwise):
        self._tool.spindle_direction = SpindleDirection.CW if clockwise else SpindleDirection.CCW
        self.changed.emit()
