"""A reamer as the Tool Library shows it: the drawing's inputs, its diameter
and spindle direction.

Read-only; the editor (ReamingToolEditorViewModel) builds on it, so a list
card made from it cannot show a reamer differently from the editor.

A reamer sits on the spindle axis pointing at the work, -Z, as a drill does:
always orientation 7, its control point the middle of its end. How it is
drawn - chamfers, flutes, shank - is ``tooling/ui/shapes/Reamer.qml``'s.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor

from teachinlathe.tooling.model import insert_catalog
from teachinlathe.tooling.model.data_types import ReamingTool, SpindleDirection
from teachinlathe.widgets.backplot.actors import palette

#: Where a reamer always sits: on the axis, pointing -Z.
REAMER_ORIENTATION = 7

#: The helix a reamer is drawn with, in degrees from the axis: its flutes
#: are always a small right-hand helix.
REAMER_HELIX_ANGLE = 10.0


class ReamingToolView(QObject):
    changed = pyqtSignal()

    def __init__(self, tool: ReamingTool, parent=None):
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

    @pyqtProperty(float, constant=True)
    def helixAngle(self):
        return REAMER_HELIX_ANGLE

    @pyqtProperty(int, constant=True)
    def orientation(self):
        return REAMER_ORIENTATION

    @pyqtProperty(bool, notify=changed)
    def clockwise(self):
        return self._tool.spindle_direction is SpindleDirection.M3

    @pyqtProperty(float, constant=True)
    def catalogReachMm(self):
        """The reference insert's reach, so a reamer thumbnail draws at the
        scale every insert one does."""
        return insert_catalog.scale_reach_mm()

    # The backplot's insert colours, as the other tools are drawn with.
    @pyqtProperty(QColor, constant=True)
    def bodyColor(self):
        return QColor.fromRgbF(*palette.INSERT_BODY)

    @pyqtProperty(QColor, constant=True)
    def edgeColor(self):
        return QColor.fromRgbF(*palette.INSERT_EDGE)
