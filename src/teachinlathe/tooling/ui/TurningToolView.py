"""A turning tool as the Tool Library shows it: the insert drawing's inputs,
its ISO designation in parts, its angles and spindle direction.

Read-only. The cutting-tool list shows one per turning tool, and the editor
(TurningToolEditorViewModel) builds on it, so the list row and the editor
cannot show the same tool two different ways.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QColor

from teachinlathe.tooling.model import insert_catalog, tool_angles
from teachinlathe.tooling.model.data_types import SpindleDirection, TurningTool
from teachinlathe.widgets.backplot.actors import palette


class TurningToolView(QObject):
    changed = pyqtSignal()

    def __init__(self, tool: TurningTool, parent=None):
        super().__init__(parent)
        self._tool = tool

    @pyqtProperty(str, constant=True)
    def toolType(self):
        """The CuttingToolType value - "turning", "boring" - so a screen can
        tell a boring bar from a turning tool."""
        return self._tool.tool_type.value

    @pyqtProperty(int, notify=changed)
    def cuttingToolId(self):
        return self._tool.cutting_tool_id

    # The ISO designation in its parts - "CCMT 06", "02", "04" - so they can
    # be coloured apart; together they read "CCMT 060204".
    @pyqtProperty(str, notify=changed)
    def familySizeCode(self):
        return f"{self._family} {self._tool.insert.size}"

    @pyqtProperty(str, notify=changed)
    def familyCode(self):
        """"CCMT" of "CCMT 06"."""
        return self._family

    @pyqtProperty(str, notify=changed)
    def sizeCode(self):
        """"06" of "CCMT 06"."""
        return self._tool.insert.size

    @pyqtProperty(str, notify=changed)
    def thicknessCode(self):
        return insert_catalog.thickness_code(self._tool.insert)

    @pyqtProperty(str, notify=changed)
    def radiusCode(self):
        if self._insert.is_round:
            return insert_catalog.ROUND_CORNER_CODE
        return self._tool.insert.radius

    @pyqtProperty(str, notify=changed)
    def isoCode(self):
        """As ISO prints it: "CCMT 060204"."""
        return f"{self.familySizeCode}{self.thicknessCode}{self.radiusCode}"

    # The drawing's inputs - TurningInsertBase's own properties.
    @pyqtProperty(str, notify=changed)
    def shapeLetter(self):
        return self._insert.shape

    @pyqtProperty(str, notify=changed)
    def insertType(self):
        return self._insert.insert_type

    @pyqtProperty(float, notify=changed)
    def ic(self):
        return self._insert.ic

    @pyqtProperty(float, notify=changed)
    def noseRadiusMm(self):
        return self._insert.nose_radius

    @pyqtProperty(float, constant=True)
    def catalogReachMm(self):
        """The reference insert's reach from its centre, so every thumbnail
        draws at the one scale that fits it."""
        return insert_catalog.scale_reach_mm()

    @pyqtProperty(float, notify=changed)
    def edgeLengthMm(self):
        """Length of the sides that meet at the cutting corner; 0 when round."""
        return 0.0 if self._insert.is_round else self._insert.edge_length()

    @pyqtProperty(float, notify=changed)
    def insertRotation(self):
        tip_x, tip_y = self._insert.active_tip()
        corner_direction = tool_angles.direction_degrees((tip_x, tip_y))
        return tool_angles.insert_rotation(self._tool.orientation, self._tool.front_angle,
                                           self._tool.back_angle, corner_direction)

    @pyqtProperty("QVariantList", notify=changed)
    def edgeDirections(self):
        """[front ray, front edge, back ray, back edge], in degrees from the
        tip, for the angle guides drawn over the insert. Empty when the
        orientation has no direction."""
        geometry = tool_angles.edge_geometry(self._tool.orientation,
                                             self._tool.front_angle, self._tool.back_angle)
        if geometry is None:
            return []
        return [geometry.front_ray, geometry.front_edge,
                geometry.back_ray, geometry.back_edge]

    # The backplot's insert colours, so the two drawings look like one tool.
    @pyqtProperty(QColor, constant=True)
    def insertBodyColor(self):
        return QColor.fromRgbF(*palette.INSERT_BODY)

    @pyqtProperty(QColor, constant=True)
    def insertEdgeColor(self):
        return QColor.fromRgbF(*palette.INSERT_EDGE)

    @pyqtProperty(int, notify=changed)
    def orientation(self):
        return self._tool.orientation

    @pyqtProperty(float, notify=changed)
    def frontAngle(self):
        return self._tool.front_angle

    @pyqtProperty(float, notify=changed)
    def backAngle(self):
        return self._tool.back_angle

    @pyqtProperty(float, notify=changed)
    def cornerAngle(self):
        """The corner's included angle; 0 on a round insert (see isRound)."""
        return self._corner or 0.0

    @pyqtProperty(bool, notify=changed)
    def isRound(self):
        return self._corner is None

    @pyqtProperty(bool, notify=changed)
    def clockwise(self):
        return self._tool.spindle_direction is SpindleDirection.M3

    # ── Internals ───────────────────────────────────────────────────────────

    @property
    def _family(self) -> str:
        return insert_catalog.family_of(self._tool.insert)

    @property
    def _insert(self):
        return insert_catalog.insert_for(self._tool.insert)

    @property
    def _corner(self) -> Optional[float]:
        return insert_catalog.corner_angle(self._tool.insert)
