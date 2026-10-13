"""A tap as the Tool Library shows it: the drawing's inputs, its diameter,
pitch, hand and spindle direction.

Read-only; the editor (TappingToolEditorViewModel) builds on it, so a list
card made from it cannot show a tap differently from the editor.

A tap sits on the spindle axis pointing at the work, -Z, as a drill does:
always orientation 7, its control point the middle of its end. How it is
drawn - lead, teeth, helix - is ``widgets/tool_shapes/Tap.qml``'s.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor

from teachinlathe.tooling import insert_catalog
from teachinlathe.tooling.data_types import SpindleDirection, TappingTool, TwistDirection
from teachinlathe.widgets.backplot.actors import palette

#: Where a tap always sits: on the axis, pointing -Z.
TAP_ORIENTATION = 7


class TappingToolView(QObject):
    changed = pyqtSignal()

    def __init__(self, tool: TappingTool, parent=None):
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
    def pitch(self):
        return self._tool.pitch

    @pyqtProperty(str, notify=changed)
    def designation(self):
        """As a metric thread is called: "M10x1.5"."""
        return f"M{self._tool.diameter:g}x{self._tool.pitch:g}"

    @pyqtProperty(bool, notify=changed)
    def rightHand(self):
        return self._tool.twist_direction is TwistDirection.RIGHT_HAND

    @pyqtProperty(int, constant=True)
    def orientation(self):
        return TAP_ORIENTATION

    @pyqtProperty(bool, notify=changed)
    def clockwise(self):
        return self._tool.spindle_direction is SpindleDirection.M3

    @pyqtProperty(float, constant=True)
    def catalogReachMm(self):
        """The reference insert's reach, so a tap thumbnail draws at the
        scale every insert one does."""
        return insert_catalog.scale_reach_mm()

    # The backplot's insert colours, as the other tools are drawn with.
    @pyqtProperty(QColor, constant=True)
    def bodyColor(self):
        return QColor.fromRgbF(*palette.INSERT_BODY)

    @pyqtProperty(QColor, constant=True)
    def edgeColor(self):
        return QColor.fromRgbF(*palette.INSERT_EDGE)
