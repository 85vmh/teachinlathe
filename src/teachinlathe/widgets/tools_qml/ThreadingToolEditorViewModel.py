"""The add/edit screen for a threading tool: an ER or IR laydown insert,
its size and the one pitch its full profile cuts.

Like the turning editor it works on a copy: nothing reaches the store until
`result()` is taken by a save.

A threading insert cuts square to the work, its tip along X, and has no
front or back angle to set. Which way it points goes with the insert: an
ER (external) is held at orientation 6, an IR (internal) at 8 - so choosing
one sets the other.
"""

from __future__ import annotations

import copy

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.tooling import threading_catalog
from teachinlathe.tooling.data_types import InsertSpec, SpindleDirection, ThreadingTool
from teachinlathe.widgets.tools_qml.ThreadingToolView import ThreadingToolView

#: Orientations a threading tool can be set to, in the order the picker shows.
THREADING_ORIENTATIONS = [6, 8]
assert set(THREADING_ORIENTATIONS) == set(threading_catalog.HAND_AT)


def new_threading_tool(cutting_tool_id: int) -> ThreadingTool:
    return ThreadingTool(
        cutting_tool_id=cutting_tool_id,
        insert=InsertSpec(threading_catalog.DEFAULT_HAND, threading_catalog.DEFAULT_SIZE, ""),
        orientation=threading_catalog.ORIENTATION[threading_catalog.DEFAULT_HAND],
        pitch=threading_catalog.DEFAULT_PITCH)


class ThreadingToolEditorViewModel(ThreadingToolView):
    """ThreadingToolView with the edits: it shows what the list will show."""

    # PyQt wants a property's notify signal declared in the property's own
    # class, so the editor's properties notify on this, which follows
    # ThreadingToolView.changed.
    edited = pyqtSignal()

    def __init__(self, tool: ThreadingTool, is_new: bool, parent=None):
        super().__init__(copy.deepcopy(tool), parent)
        self.changed.connect(self.edited)
        self._is_new = is_new
        self._fit_stored()

    def result(self) -> ThreadingTool:
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
    def handTexts(self):
        return [f"{hand}  ({threading_catalog.KIND[hand].lower()})"
                for hand in threading_catalog.hands()]

    @pyqtProperty(int, notify=edited)
    def handIndex(self):
        return threading_catalog.hands().index(self.hand)

    @pyqtProperty("QStringList", constant=True)
    def sizeCodes(self):
        return threading_catalog.size_codes()

    @pyqtProperty(int, notify=edited)
    def sizeIndex(self):
        return threading_catalog.size_codes().index(self.sizeCode)

    @pyqtProperty("QStringList", notify=edited)
    def pitchTexts(self):
        return [f"{threading_catalog.pitch_text(p)} mm"
                for p in threading_catalog.pitches(self.sizeCode)]

    @pyqtProperty(int, notify=edited)
    def pitchIndex(self):
        return threading_catalog.pitches(self.sizeCode).index(self.pitch)

    @pyqtProperty("QVariantList", constant=True)
    def allowedOrientations(self):
        return list(THREADING_ORIENTATIONS)

    # ── Edits ───────────────────────────────────────────────────────────────

    @pyqtSlot(int)
    def setHand(self, index):
        self._set_hand(threading_catalog.hands()[index])

    @pyqtSlot(int)
    def setSize(self, index):
        size = threading_catalog.size_codes()[index]
        self._tool.insert = InsertSpec(self.hand, size, self._tool.insert.radius)
        # Not every size has every pitch: keep the closest it has.
        self._tool.pitch = threading_catalog.nearest_pitch(size, self._tool.pitch)
        self.changed.emit()

    @pyqtSlot(int)
    def setPitch(self, index):
        self._tool.pitch = threading_catalog.pitches(self.sizeCode)[index]
        self.changed.emit()

    @pyqtSlot(int)
    def setOrientation(self, orientation):
        if orientation not in THREADING_ORIENTATIONS:
            return
        # The orientation picks the insert: 6 is an ER, 8 an IR.
        self._set_hand(threading_catalog.HAND_AT[orientation])

    @pyqtSlot(bool)
    def setClockwise(self, clockwise):
        self._tool.spindle_direction = SpindleDirection.CW if clockwise else SpindleDirection.CCW
        self.changed.emit()

    # ── Internals ───────────────────────────────────────────────────────────

    def _set_hand(self, hand):
        self._tool.insert = InsertSpec(hand, self.sizeCode, self._tool.insert.radius)
        self._tool.orientation = threading_catalog.ORIENTATION[hand]
        self.changed.emit()

    def _fit_stored(self):
        """Make a tool from the file one the screen can show: a hand, size
        and pitch from the catalogue, held the way that insert is."""
        size = threading_catalog.size_of(self._tool.insert.size)
        hand = threading_catalog.hand_of(self._tool.insert.geometry, self._tool.orientation)
        self._tool.insert = InsertSpec(hand, size, self._tool.insert.radius)
        self._tool.orientation = threading_catalog.ORIENTATION[hand]
        self._tool.pitch = threading_catalog.nearest_pitch(size, self._tool.pitch)
