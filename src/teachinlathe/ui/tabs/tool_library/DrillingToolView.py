"""A drill as the Tool Library shows it: the drawing's inputs, its diameter,
point angle, twist and spindle direction.

Read-only. The cutting-tool list shows one per drill, and the editor
(DrillingToolEditorViewModel) builds on it, so the list card and the editor
cannot show the same drill two different ways.

A drill sits on the spindle axis pointing at the work, -Z: always
orientation 7, its control point the tip of its point. How it is drawn -
point, flutes, helix - is ``ui/tabs/tool_library/shapes/Drill.qml``'s.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor

from teachinlathe.tooling.model import insert_catalog
from teachinlathe.tooling.model.data_types import DrillingTool, SpindleDirection, TwistDirection
from teachinlathe.ui.tabs.programs.backplot.actors import palette

#: Where a drill always sits: on the axis, pointing -Z.
DRILL_ORIENTATION = 7


class DrillingToolView(QObject):
    changed = pyqtSignal()

    def __init__(self, tool: DrillingTool, parent=None):
        super().__init__(parent)
        self._tool = tool

    @pyqtProperty(str, constant=True)
    def toolType(self):
        return self._tool.tool_type.value

    @pyqtProperty(int, constant=True)
    def cuttingToolId(self):
        return self._tool.cutting_tool_id

    @pyqtProperty(float, notify=changed)
    def diameter(self):
        return self._tool.diameter

    @pyqtProperty(float, notify=changed)
    def tipAngle(self):
        return self._tool.tip_angle

    @pyqtProperty(bool, notify=changed)
    def rightHand(self):
        return self._tool.twist_direction is TwistDirection.RIGHT_HAND

    @pyqtProperty(int, constant=True)
    def orientation(self):
        return DRILL_ORIENTATION

    @pyqtProperty(bool, notify=changed)
    def clockwise(self):
        return self._tool.spindle_direction is SpindleDirection.M3

    @pyqtProperty(float, constant=True)
    def catalogReachMm(self):
        """The reference insert's reach, so a drill thumbnail draws at the
        scale every insert one does."""
        return insert_catalog.scale_reach_mm()

    # The backplot's insert colours, as the other tools are drawn with.
    @pyqtProperty(QColor, constant=True)
    def bodyColor(self):
        return QColor.fromRgbF(*palette.INSERT_BODY)

    @pyqtProperty(QColor, constant=True)
    def edgeColor(self):
        return QColor.fromRgbF(*palette.INSERT_EDGE)
