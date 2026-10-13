"""The add/edit screen for a blade: parting, grooving, trepanning.

Like the other editors it works on a copy: nothing reaches the store until
`result()` is taken by a save. What the blade is - its shape, its corners,
how it is held - is in BladeToolView, which this builds on. A corner can be
no rounder than half the width, where the two meet in a full round tip.
"""

from __future__ import annotations

import copy

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.tooling.data_types import BladeTool, SpindleDirection
from teachinlathe.widgets.tools_qml.BladeToolView import BladeToolView

#: Orientations a blade can be set to.
BLADE_ORIENTATIONS = [5, 6, 7, 8]
DEFAULT_ORIENTATION = 6

DEFAULT_WIDTH = 1.5
DEFAULT_RADIUS = 0.2


def new_blade_tool(cutting_tool_id: int) -> BladeTool:
    return BladeTool(cutting_tool_id=cutting_tool_id, blade_width=DEFAULT_WIDTH,
                     left_radius=DEFAULT_RADIUS, right_radius=DEFAULT_RADIUS,
                     orientation=DEFAULT_ORIENTATION)


class BladeToolEditorViewModel(BladeToolView):
    """BladeToolView with the edits: it shows what the list will show."""

    # PyQt wants a property's notify signal declared in the property's own
    # class, so the editor's properties notify on this, which follows
    # BladeToolView.changed.
    edited = pyqtSignal()

    def __init__(self, tool: BladeTool, is_new: bool, parent=None):
        super().__init__(copy.deepcopy(tool), parent)
        self.changed.connect(self.edited)
        self._is_new = is_new
        self._fit_stored()

    def result(self) -> BladeTool:
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

    @pyqtProperty("QVariantList", constant=True)
    def allowedOrientations(self):
        return list(BLADE_ORIENTATIONS)

    # ── Edits ───────────────────────────────────────────────────────────────

    @pyqtSlot(float)
    def setBladeWidth(self, value):
        if value <= 0:
            self.changed.emit()        # puts the field back
            return
        self._tool.blade_width = float(value)
        # A narrower blade can leave a corner rounder than it can be.
        self._tool.left_radius = self._clamp_radius(self._tool.left_radius)
        self._tool.right_radius = self._clamp_radius(self._tool.right_radius)
        self.changed.emit()

    @pyqtSlot(float)
    def setLeftRadius(self, value):
        self._tool.left_radius = self._clamp_radius(value)
        self.changed.emit()

    @pyqtSlot(float)
    def setRightRadius(self, value):
        self._tool.right_radius = self._clamp_radius(value)
        self.changed.emit()

    @pyqtSlot()
    def copyLeftToRight(self):
        self._tool.right_radius = self._tool.left_radius
        self.changed.emit()

    @pyqtSlot()
    def copyRightToLeft(self):
        self._tool.left_radius = self._tool.right_radius
        self.changed.emit()

    @pyqtSlot()
    def roundTip(self):
        """Both corners half the width: a full round end."""
        self._tool.left_radius = self._tool.right_radius = self.maxRadius
        self.changed.emit()

    @pyqtSlot(int)
    def setOrientation(self, orientation):
        if orientation not in BLADE_ORIENTATIONS:
            return
        self._tool.orientation = orientation
        self.changed.emit()

    @pyqtSlot(bool)
    def setClockwise(self, clockwise):
        self._tool.spindle_direction = SpindleDirection.M3 if clockwise else SpindleDirection.M4
        self.changed.emit()

    # ── Internals ───────────────────────────────────────────────────────────

    def _clamp_radius(self, value) -> float:
        return min(max(float(value), 0.0), self.maxRadius)

    def _fit_stored(self):
        """Make a blade from the file one the screen can show."""
        if self._tool.blade_width <= 0:
            self._tool.blade_width = DEFAULT_WIDTH
        self._tool.left_radius = self._clamp_radius(self._tool.left_radius)
        self._tool.right_radius = self._clamp_radius(self._tool.right_radius)
        if self._tool.orientation not in BLADE_ORIENTATIONS:
            self._tool.orientation = DEFAULT_ORIENTATION
