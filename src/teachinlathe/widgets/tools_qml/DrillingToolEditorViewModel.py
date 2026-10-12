"""The add/edit screen for a drill.

Like the other editors it works on a copy: nothing reaches the store until
`result()` is taken by a save. What the drill is and how it is drawn is in
DrillingToolView, which this builds on.

The point angle is picked from the usual ones, spot drill to flat bottom;
one from the file that is not among them is offered too, so opening a drill
never changes it.
"""

from __future__ import annotations

import copy

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.tooling.data_types import DrillingTool, SpindleDirection, TwistDirection
from teachinlathe.widgets.tools_qml.DrillingToolView import DRILL_ORIENTATION, DrillingToolView

#: The usual point angles, and what each is: spot drills at 90, through the
#: twist drills, to the flat bottom of a U drill.
TIP_ANGLES = [
    (90.0, "spot drill"),
    (118.0, "HSS"),
    (120.0, ""),
    (130.0, ""),
    (135.0, "split point"),
    (140.0, "carbide"),
    (145.0, ""),
    (180.0, "flat, U drill"),
]

DEFAULT_DIAMETER = 10.0
DEFAULT_TIP_ANGLE = 118.0


def new_drilling_tool(cutting_tool_id: int) -> DrillingTool:
    return DrillingTool(cutting_tool_id=cutting_tool_id, diameter=DEFAULT_DIAMETER,
                        tip_angle=DEFAULT_TIP_ANGLE,
                        twist_direction=TwistDirection.RIGHT_HAND)


class DrillingToolEditorViewModel(DrillingToolView):
    """DrillingToolView with the edits: it shows what the list will show."""

    # PyQt wants a property's notify signal declared in the property's own
    # class, so the editor's properties notify on this, which follows
    # DrillingToolView.changed.
    edited = pyqtSignal()

    def __init__(self, tool: DrillingTool, is_new: bool, parent=None):
        super().__init__(copy.deepcopy(tool), parent)
        self.changed.connect(self.edited)
        self._is_new = is_new
        if self._tool.diameter <= 0:
            self._tool.diameter = DEFAULT_DIAMETER
        if not 0 < self._tool.tip_angle <= 180:
            self._tool.tip_angle = DEFAULT_TIP_ANGLE

    def result(self) -> DrillingTool:
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

    @pyqtProperty("QStringList", notify=edited)
    def tipAngleTexts(self):
        return [f"{angle:g}°  ({what})" if what else f"{angle:g}°"
                for angle, what in self._tip_angles()]

    @pyqtProperty(int, notify=edited)
    def tipAngleIndex(self):
        return [angle for angle, _ in self._tip_angles()].index(self._tool.tip_angle)

    @pyqtProperty("QVariantList", constant=True)
    def allowedOrientations(self):
        return [DRILL_ORIENTATION]

    # ── Edits ───────────────────────────────────────────────────────────────

    @pyqtSlot(float)
    def setDiameter(self, value):
        if value > 0:
            self._tool.diameter = float(value)
        self.changed.emit()            # puts the field back when refused

    @pyqtSlot(int)
    def setTipAngle(self, index):
        self._tool.tip_angle = self._tip_angles()[index][0]
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

    # ── Internals ───────────────────────────────────────────────────────────

    def _tip_angles(self):
        """The usual angles, and the drill's own among them if it is not."""
        angles = list(TIP_ANGLES)
        if all(angle != self._tool.tip_angle for angle, _ in angles):
            angles.append((self._tool.tip_angle, "this drill's"))
            angles.sort()
        return angles
