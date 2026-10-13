"""A threading tool as the Tool Library shows it: the insert drawing's
inputs, its designation in parts, its pitch and spindle direction.

Read-only. The cutting-tool list shows one per threading tool, and the
editor (ThreadingToolEditorViewModel) builds on it, so the list card and the
editor cannot show the same tool two different ways.

A tool from the file is shown as the catalogue reads it: an insert it does
not know (an EL from before there was IR) by the orientation it is held at,
and a pitch the drawing has no tooth for as the closest one it has.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor

from teachinlathe.tooling import insert_catalog, threading_catalog
from teachinlathe.tooling.data_types import SpindleDirection, ThreadingTool
from teachinlathe.widgets.backplot.actors import palette

#: How far ThreadingInsert.qml is turned for each orientation. At 0 its tip
#: points up (+X), which is orientation 6's: the body below, the tip up.
_ROTATION = {6: 0.0, 8: 180.0}


class ThreadingToolView(QObject):
    changed = pyqtSignal()

    def __init__(self, tool: ThreadingTool, parent=None):
        super().__init__(parent)
        self._tool = tool

    @pyqtProperty(str, constant=True)
    def toolType(self):
        return self._tool.tool_type.value

    @pyqtProperty(int, constant=True)
    def cuttingToolId(self):
        return self._tool.cutting_tool_id

    # The designation in its parts - "16", "ER", "1.5" - so they can be
    # coloured apart; together they read "16ER 1.5".
    @pyqtProperty(str, notify=changed)
    def sizeCode(self):
        return threading_catalog.size_of(self._tool.insert.size)

    @pyqtProperty(str, notify=changed)
    def hand(self):
        """"ER" or "IR"."""
        return threading_catalog.hand_of(self._tool.insert.geometry, self._tool.orientation)

    @pyqtProperty(str, notify=changed)
    def pitchText(self):
        return threading_catalog.pitch_text(self.pitch)

    @pyqtProperty(str, notify=changed)
    def isoCode(self):
        """As the makers print it: "16ER 1.5"."""
        return f"{self.sizeCode}{self.hand} {self.pitchText}"

    @pyqtProperty(str, notify=changed)
    def kind(self):
        """"External" or "Internal"."""
        return threading_catalog.KIND[self.hand]

    @pyqtProperty(float, notify=changed)
    def pitch(self):
        return threading_catalog.nearest_pitch(self.sizeCode, self._tool.pitch)

    # The drawing's inputs - ThreadingInsert's own properties.
    @pyqtProperty(str, notify=changed)
    def drawnHand(self):
        """ThreadingInsert's `hand`: an IR is drawn mirrored."""
        return threading_catalog.DRAWN_HAND[self.hand]

    @pyqtProperty(float, notify=changed)
    def ic(self):
        return threading_catalog.SIZES[self.sizeCode]

    @pyqtProperty(int, notify=changed)
    def orientation(self):
        """The one the insert is held at: 6 for an ER, 8 for an IR."""
        return threading_catalog.ORIENTATION[self.hand]

    @pyqtProperty(float, notify=changed)
    def insertRotation(self):
        return _ROTATION[self.orientation]

    @pyqtProperty(float, constant=True)
    def catalogReachMm(self):
        """The reference insert's reach, so a threading thumbnail draws at
        the scale every turning one does."""
        return insert_catalog.scale_reach_mm()

    # The backplot's insert colours, as the turning tools are drawn with.
    @pyqtProperty(QColor, constant=True)
    def insertBodyColor(self):
        return QColor.fromRgbF(*palette.INSERT_BODY)

    @pyqtProperty(QColor, constant=True)
    def insertEdgeColor(self):
        return QColor.fromRgbF(*palette.INSERT_EDGE)

    @pyqtProperty(bool, notify=changed)
    def clockwise(self):
        return self._tool.spindle_direction is SpindleDirection.M3
