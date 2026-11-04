"""The add/edit screen for a turning tool, and for a boring bar - a turning
tool with a body, which this edits as it does a turning tool's and keeps the
body as it was.

It works on a copy: nothing reaches the repository until `result()` is taken by a
save, so leaving the screen any other way leaves the library as it was.

The front and back angles are kept coupled through the insert's corner (see
`tooling.tool_angles`): on orientations 1-4 setting one sets the other, and
changing the insert keeps the front angle and recomputes the back. On 6 and
8 the two are fixed, equal, by the corner alone - so arriving at a corner
orientation from one of those starts again from the default clearance.

A round insert has no corner and no direction, so the only orientation it
takes is 9; leaving it for a cornered insert goes back to orientation 2.
"""

from __future__ import annotations

import copy
from typing import Optional, Type

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.tooling.model import insert_catalog, tool_angles
from teachinlathe.tooling.model.data_types import SpindleDirection, TurningTool
from teachinlathe.ui.tabs.tool_library.TurningToolView import TurningToolView

#: Orientations a turning tool can be set to, in the order the picker shows.
TURNING_ORIENTATIONS = [2, 6, 1, 3, 8, 4]

#: The one orientation a round insert takes: centred, no direction.
ROUND_ORIENTATIONS = [9]

#: Back angle a tool in a corner orientation starts with; the front angle is
#: whatever the corner leaves of the 180 (95 for an 80 degree CCMT).
DEFAULT_BACK_ANGLE = 5.0

#: Families whose holders are usually 93 degree ones, rather than 5 degree
#: clearance at the back: the narrow corners would leave 120 (DCMT) or 140
#: (VBMT) in front.
DEFAULT_FRONT_ANGLES = {"DCMT": 93.0, "VBMT": 93.0}


def _default_front_angle(family: str, corner: Optional[float], orientation: int) -> float:
    front = DEFAULT_FRONT_ANGLES.get(family)
    if front is not None and tool_angles.max_angle(corner, orientation) is not None:
        return tool_angles.clamp_angle(front, corner, orientation)
    front = tool_angles.complementary_angle(DEFAULT_BACK_ANGLE, corner, orientation)
    return DEFAULT_BACK_ANGLE if front is None else front


def new_turning_tool(cutting_tool_id: int,
                     tool_class: Type[TurningTool] = TurningTool) -> TurningTool:
    """A new tool of `tool_class` - TurningTool or BoringTool - with the
    catalogue's first insert and the default clearance."""
    family = insert_catalog.families()[0]
    spec = insert_catalog.make_spec(family, 0, insert_catalog.nose_radii()[1])
    corner = insert_catalog.corner_angle(spec)
    front = _default_front_angle(family, corner, 2)
    back = tool_angles.complementary_angle(front, corner, 2)
    return tool_class(cutting_tool_id=cutting_tool_id, insert=spec, orientation=2,
                      front_angle=front,
                      back_angle=DEFAULT_BACK_ANGLE if back is None else back)


class TurningToolEditorViewModel(TurningToolView):
    """TurningToolView with the edits: it shows what the list will show."""

    # PyQt wants a property's notify signal declared in the property's own
    # class, so the editor's properties notify on this, which follows
    # TurningToolView.changed.
    edited = pyqtSignal()

    def __init__(self, tool: TurningTool, is_new: bool, parent=None):
        super().__init__(copy.deepcopy(tool), parent)
        self.changed.connect(self.edited)
        self._is_new = is_new
        self._fit_stored_angles()

    def result(self) -> TurningTool:
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

    @pyqtProperty("QStringList", constant=True)
    def families(self):
        return insert_catalog.families()

    @pyqtProperty(int, notify=edited)
    def familyIndex(self):
        return insert_catalog.families().index(self._family)

    @pyqtProperty("QStringList", notify=edited)
    def sizeCodes(self):
        return insert_catalog.size_codes(self._family)

    @pyqtProperty(int, notify=edited)
    def sizeIndex(self):
        return insert_catalog.size_index_of(self._tool.insert)

    @pyqtProperty("QStringList", constant=True)
    def noseRadiusCodes(self):
        return [f"{code}  (R{radius:g})" for code, radius in
                zip(insert_catalog.nose_radius_codes(), insert_catalog.nose_radii())]

    @pyqtProperty(int, notify=edited)
    def noseRadiusIndex(self):
        radii = insert_catalog.nose_radii()
        radius = insert_catalog.nose_radius_of(self._tool.insert)
        return min(range(len(radii)), key=lambda i: abs(radii[i] - radius))

    @pyqtProperty("QVariantList", notify=edited)
    def allowedOrientations(self):
        return list(self._allowed_orientations())

    @pyqtProperty(bool, notify=edited)
    def anglesCoupled(self):
        return tool_angles.max_angle(self._corner, self._tool.orientation) is not None

    @pyqtProperty(bool, notify=edited)
    def anglesEditable(self):
        """False on 6 and 8, where the corner alone sets both angles."""
        return not (self._corner is not None
                    and tool_angles.is_symmetric(self._tool.orientation))

    # ── Edits ───────────────────────────────────────────────────────────────

    @pyqtSlot(int)
    def setFamily(self, index):
        family = insert_catalog.families()[index]
        if family == self._family:
            return
        # The size list differs per family: keep the position in it, clamped.
        self._tool.insert = insert_catalog.make_spec(family, self.sizeIndex, self.noseRadiusMm)
        # Each family starts from its own usual front angle.
        self._tool.front_angle = self._default_front()
        self._recouple()

    @pyqtSlot(int)
    def setSize(self, index):
        self._set_insert(self._family, index, self.noseRadiusMm)

    @pyqtSlot(int)
    def setNoseRadius(self, index):
        self._set_insert(self._family, self.sizeIndex, insert_catalog.nose_radii()[index])

    @pyqtSlot(int)
    def setOrientation(self, orientation):
        if orientation not in self._allowed_orientations():
            return
        coming_from_fixed = not self.anglesEditable or self.isRound
        self._tool.orientation = orientation
        if coming_from_fixed:
            # The equal angles of 6 and 8 mean nothing in a corner.
            self._tool.front_angle = self._default_front()
        self._recouple()

    @pyqtSlot(float)
    def setFrontAngle(self, value):
        if not self.anglesEditable:
            return
        self._tool.front_angle = self._clamp(value)
        self._recouple()

    @pyqtSlot(float)
    def setBackAngle(self, value):
        if not self.anglesEditable:
            return
        self._tool.back_angle = self._clamp(value)
        front = tool_angles.complementary_angle(self._tool.back_angle, self._corner,
                                                self._tool.orientation)
        if front is not None:
            self._tool.front_angle = front
        self.changed.emit()

    @pyqtSlot(bool)
    def setClockwise(self, clockwise):
        self._tool.spindle_direction = SpindleDirection.M3 if clockwise else SpindleDirection.M4
        self.changed.emit()

    # ── Internals ───────────────────────────────────────────────────────────

    def _allowed_orientations(self):
        return ROUND_ORIENTATIONS if self._corner is None else TURNING_ORIENTATIONS

    def _default_front(self) -> float:
        return _default_front_angle(self._family, self._corner, self._tool.orientation)

    def _clamp(self, value) -> float:
        """An angle as typed: whole degrees, within what fits."""
        return tool_angles.clamp_angle(float(round(float(value))), self._corner,
                                       self._tool.orientation)

    def _set_insert(self, family, size_index, radius_mm):
        self._tool.insert = insert_catalog.make_spec(family, size_index, radius_mm)
        self._recouple()

    def _fit_stored_angles(self):
        """Make a tool from the file add up before it is shown.

        One written by hand, or under the earlier rule - front measured from
        the X axis, so 5 where it is now 95 - does not. The back angle is
        measured from the Z axis under both, so it is the one kept, and the
        front is made to fit it.
        """
        limit = tool_angles.max_angle(self._corner, self._tool.orientation)
        if self.anglesEditable and limit is not None:
            if self._tool.back_angle > limit:
                self._tool.back_angle = DEFAULT_BACK_ANGLE
            self._tool.front_angle = tool_angles.complementary_angle(
                self._tool.back_angle, self._corner, self._tool.orientation)
        self._recouple()

    def _recouple(self):
        """Keep the orientation and the front angle where they still fit,
        and recompute the back from the front."""
        allowed = self._allowed_orientations()
        if self._tool.orientation not in allowed:
            # Onto a round insert, or off one: the only one it takes, or the
            # usual turning one with the default clearance.
            self._tool.orientation = allowed[0]
            self._tool.front_angle = self._default_front()
        if self.anglesEditable is False:
            self._tool.front_angle = self._tool.back_angle = \
                tool_angles.symmetric_angle(self._corner)
            self.changed.emit()
            return
        limit = tool_angles.max_angle(self._corner, self._tool.orientation)
        if limit is not None and self._tool.front_angle > limit:
            # A smaller corner than the one the angle was set for: start
            # again from the default clearance rather than the limit.
            self._tool.front_angle = self._default_front()
        self._tool.front_angle = self._clamp(self._tool.front_angle)
        back = tool_angles.complementary_angle(self._tool.front_angle, self._corner,
                                               self._tool.orientation)
        if back is not None:
            self._tool.back_angle = back
        self.changed.emit()
