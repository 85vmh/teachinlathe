"""A blade - parting, grooving, trepanning - as the Tool Library shows it:
the drawing's inputs, its width and corner radii, its spindle direction.

Read-only. The cutting-tool list shows one per blade, and the editor
(BladeToolEditorViewModel) builds on it, so the list card and the editor
cannot show the same blade two different ways.

A blade is a strip `bladeWidth` wide with a rounded corner either side of
its cutting end. Its control point is the middle of that end, and it points
along X (orientations 6 and 8, parting and grooving) or along Z (5 and 7,
face grooving and trepanning).

Left and right are the blade's corners as seen held at orientation 6,
cutting end up - left on the -Z side. Held at 8, cutting end down, left
stays on the -Z side: the drawing is mirrored, not turned over. At 5 and 7
the blade is turned a quarter either way, and its corners with it.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor

# the drawn length - 3:1 to the width - the backplot's, so every drawing agrees
from teachinlathe.ui.tabs.programs.backplot.actors.tool_outlines import blade_length
from teachinlathe.tooling.model import insert_catalog
from teachinlathe.tooling.model.data_types import BladeTool, SpindleDirection
from teachinlathe.ui.tabs.programs.backplot.actors import palette
from teachinlathe.ui.tabs.tool_library.tool_title_parts import title_parts

#: How the drawing is placed for each orientation: degrees turned
#: counter-clockwise, and whether it is mirrored top to bottom first. At 0,
#: unmirrored, the cutting end points up (+X), orientation 6's; 5 points it
#: along +Z, 7 along -Z, 8 down - as the orientation pictures have them.
_PLACEMENT = {6: (0.0, False), 5: (-90.0, False), 8: (0.0, True), 7: (90.0, False)}


class BladeToolView(QObject):
    changed = pyqtSignal()

    def __init__(self, tool: BladeTool, parent=None):
        super().__init__(parent)
        self._tool = tool

    @pyqtProperty("QVariantMap", notify=changed)
    def titleParts(self):
        """Its card's and its list's titles, in parts (tool_title_parts)."""
        return title_parts(self._tool)

    @pyqtProperty(str, constant=True)
    def toolType(self):
        return self._tool.tool_type.value

    @pyqtProperty(int, constant=True)
    def cuttingToolId(self):
        return self._tool.cutting_tool_id

    @pyqtProperty(float, notify=changed)
    def bladeWidth(self):
        return self._tool.blade_width

    @pyqtProperty(float, notify=changed)
    def leftRadius(self):
        return self._tool.left_radius

    @pyqtProperty(float, notify=changed)
    def rightRadius(self):
        return self._tool.right_radius

    @pyqtProperty(float, notify=changed)
    def maxRadius(self):
        return self._tool.blade_width / 2

    @pyqtProperty(float, notify=changed)
    def bladeLength(self):
        return blade_length(self._tool.blade_width)

    @pyqtProperty(int, notify=changed)
    def orientation(self):
        return self._tool.orientation

    @pyqtProperty(float, notify=changed)
    def bladeRotation(self):
        return _PLACEMENT.get(self._tool.orientation, _PLACEMENT[6])[0]

    @pyqtProperty(bool, notify=changed)
    def bladeMirrored(self):
        """Mirrored top to bottom before it is turned: at 8, so left stays
        on the -Z side."""
        return _PLACEMENT.get(self._tool.orientation, _PLACEMENT[6])[1]

    @pyqtProperty(bool, notify=changed)
    def clockwise(self):
        return self._tool.spindle_direction is SpindleDirection.M3

    @pyqtProperty(float, constant=True)
    def catalogReachMm(self):
        """The reference insert's reach, so a blade thumbnail draws at the
        scale every insert one does."""
        return insert_catalog.scale_reach_mm()

    # The backplot's insert colours, as the other tools are drawn with.
    @pyqtProperty(QColor, constant=True)
    def bodyColor(self):
        return QColor.fromRgbF(*palette.INSERT_BODY)

    @pyqtProperty(QColor, constant=True)
    def edgeColor(self):
        return QColor.fromRgbF(*palette.INSERT_EDGE)
