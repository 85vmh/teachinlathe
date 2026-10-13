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
    tool = TappingTool(cutting_tool_id=cutting_tool_id, diameter=DEFAULT_DIAMETER,
                       pitch=DEFAULT_PITCH, twist_direction=TwistDirection.RIGHT_HAND)
    tool.spindle_direction = tool.twist_direction.spindle_direction
    return tool


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
        # The twist decides the spindle direction; one stored otherwise is
        # set right.
        self._tool.spindle_direction = self._tool.twist_direction.spindle_direction
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

    @pyqtProperty(str, notify=edited)
    def comment(self):
        return self._tool.comment

    @pyqtProperty(int, constant=True)
    def commentMaxLength(self):
        return self._tool.COMMENT_MAX_LENGTH

    @pyqtSlot(str)
    def setComment(self, text):
        self._tool.comment = text[:self._tool.COMMENT_MAX_LENGTH]
        self.changed.emit()

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
        self._tool.spindle_direction = self._tool.twist_direction.spindle_direction
        self.changed.emit()

    @pyqtSlot(bool)
    def setClockwise(self, clockwise):
        """Only the direction the twist cuts in: the other is disabled."""
        direction = SpindleDirection.M3 if clockwise else SpindleDirection.M4
        if direction is not self._tool.twist_direction.spindle_direction:
            return
        self._tool.spindle_direction = direction
        self.changed.emit()
