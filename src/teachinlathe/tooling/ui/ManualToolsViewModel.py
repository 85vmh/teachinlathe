"""The tools on the Manual Turning screen: the tool holders, as LinuxCNC
knows them - holder N is tool TN.

One is the tool in the spindle; tapping another loads it (M61), unless the
machine is feeding. Nothing else is edited here: the offsets come from
touching off. After a touch-off the offset LinuxCNC worked out is read back
from its tool table into the holder, which then writes the table again
(see tool_library.tool_table_sync). A blade touched off in Z is asked
which of its points that was.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, List, Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.tooling.model.data_types import BladeTool, ToolHolder, ZOffsetPlace
from teachinlathe.tooling.store.tool_library_store import ToolLibraryStore
from teachinlathe.ui.common.images import image_url
from teachinlathe.tooling.ui.tool_library_models import (
    DataclassListModel, MountedToolViews,
)

log = logging.getLogger(__name__)

#: The title bar's toggle: on, only the recently used tools are listed.
_RECENT_ACTION = "toggle_recent"
_RECENT_ICON = image_url("recent.svg")

#: How many status polls a touch-off is waited for when the interpreter is
#: never seen busy - G10 can run inside one poll.
_TOUCH_OFF_POLLS = 4


@dataclass(frozen=True)
class ManualToolRow:
    toolNo: int          # the holder's id: LinuxCNC's T number
    toolId: int          # the mounted cutting tool's id, 0 when empty
    toolCard: str        # which thumbnail, title and figures draw it
    toolView: Any        # the view they read, or None
    toolComment: str
    xOffset: str         # as shown, or empty until touched off
    zOffset: str
    current: bool        # in the spindle
    selectable: bool     # can be loaded now


class ManualToolListModel(DataclassListModel):
    def __init__(self, parent=None):
        super().__init__(ManualToolRow, parent)


class ManualToolsViewModel(QObject):
    recentOnlyChanged = pyqtSignal()
    #: The title bar reads getHeaderState() again: the recent toggle is there.
    headerStateChanged = pyqtSignal()
    currentToolChanged = pyqtSignal()
    feedingChanged = pyqtSignal()
    #: A blade was touched off in Z: which of its points was it? (its width)
    bladePlaceRequested = pyqtSignal(float)

    def __init__(self, store: ToolLibraryStore, status=None, issue_mdi=None, parent=None):
        super().__init__(parent)
        self._store = store
        self._status = status
        self._issue_mdi = issue_mdi
        self._model = ManualToolListModel(self)
        self._views = MountedToolViews(self)
        self._touched_off_model = ManualToolListModel(self)
        self._touched_off_views = MountedToolViews(self)
        self._recent_only = False
        self._feeding = False
        self._current = 0
        self._capture: Optional[dict] = None
        self._blade_holder_id = 0

        store.add_listener(self.refresh)
        if status is not None:
            status.polled.connect(self._on_polled)
        self.refresh()

    # ── What the screen shows ───────────────────────────────────────────────

    @pyqtProperty(QObject, constant=True)
    def toolsModel(self):
        return self._model

    @pyqtProperty(QObject, constant=True)
    def touchedOffToolsModel(self):
        """Every holder with a tool and both offsets set, whatever the
        list shows: the ones a program can change to."""
        return self._touched_off_model

    @pyqtProperty(bool, notify=recentOnlyChanged)
    def recentOnly(self):
        return self._recent_only

    @recentOnly.setter
    def recentOnly(self, value):
        if bool(value) != self._recent_only:
            self._recent_only = bool(value)
            self.recentOnlyChanged.emit()
            self.headerStateChanged.emit()
            self.refresh()

    @pyqtProperty(int, notify=currentToolChanged)
    def currentToolNo(self):
        return self._current

    @pyqtProperty(bool, notify=feedingChanged)
    def feeding(self):
        return self._feeding

    # ── The title bar ───────────────────────────────────────────────────────

    def getHeaderState(self) -> dict:
        """The Manual Turning tab's title bar: the recent toggle, on the
        right. The title stays the tab's."""
        return {"right_actions": [{
            "id": _RECENT_ACTION,
            "icon": _RECENT_ICON,
            "checked": self._recent_only,
            "enabled": True,
        }]}

    def triggerHeaderAction(self, action_id: str) -> None:
        if action_id == _RECENT_ACTION:
            self.recentOnly = not self._recent_only

    # ── Edits ───────────────────────────────────────────────────────────────

    @pyqtSlot(int)
    def selectTool(self, tool_no: int) -> None:
        """Load the tool, unless it is in already, empty or the machine is
        feeding."""
        holder = self._store.find_holder(tool_no)
        if holder is None or not holder.has_tool or tool_no == self._current or self._feeding:
            return
        if self._issue_mdi is None:
            log.info("no LinuxCNC to load T%s", tool_no)
            return
        self._issue_mdi(f"M61 Q{tool_no} G43")

    def setFeeding(self, feeding) -> None:
        feeding = bool(feeding)
        if feeding != self._feeding:
            self._feeding = feeding
            self.feedingChanged.emit()
            self.refresh()

    def captureTouchOff(self, axis: str) -> None:
        """A touch-off was just sent for `axis` ("x" or "z"): once LinuxCNC
        has run it, keep the offset it worked out on the current holder."""
        holder = self._current_holder()
        if holder is None or not holder.has_tool:
            return
        self._capture = {"axis": axis, "holder": holder.tool_holder_id,
                         "busy": False, "polls": 0}

    @pyqtSlot(str)
    def setBladePlace(self, place: str) -> None:
        """Answer to bladePlaceRequested: "-1", "0" or "1"."""
        if self._blade_holder_id:
            self._store.set_z_offset_place(self._blade_holder_id, ZOffsetPlace(place))
            self._blade_holder_id = 0

    # ── The list ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._fill(self._model, self._views, self._shown_holders())
        holders = sorted(self._store.holders, key=lambda h: h.tool_holder_id)
        self._fill(self._touched_off_model, self._touched_off_views,
                   [h for h in holders if h.has_tool
                    and h.x_offset is not None and h.z_offset is not None])

    def _fill(self, model: ManualToolListModel, views: MountedToolViews,
              holders: List[ToolHolder]) -> None:
        rows = []
        views.begin()
        for holder in holders:
            tool = self._store.find_tool(holder.cutting_tool_id)
            card, view = views.view_for(tool)
            rows.append(ManualToolRow(
                toolNo=holder.tool_holder_id,
                toolId=tool.cutting_tool_id if tool else 0,
                toolCard=card,
                toolView=view,
                toolComment=tool.comment if tool else "",
                xOffset=_offset_text(holder.x_offset),
                zOffset=_offset_text(holder.z_offset),
                current=holder.tool_holder_id == self._current,
                selectable=tool is not None and not self._feeding,
            ))
        model.setRows(rows)
        views.end()

    def _shown_holders(self) -> List[ToolHolder]:
        """The holders with a tool in them: an empty one is nothing to load."""
        holders = sorted((h for h in self._store.holders if h.has_tool),
                         key=lambda h: h.tool_holder_id)
        if not self._recent_only:
            return holders
        return _recently_used(holders)

    # ── LinuxCNC ────────────────────────────────────────────────────────────

    def _on_polled(self) -> None:
        stat = self._status.stat
        try:
            in_spindle = int(stat.tool_in_spindle)
        except Exception:
            return
        if in_spindle != self._current:
            self._current = in_spindle
            if self._store.find_holder(in_spindle) is not None:
                self._store.record_loaded(in_spindle, time.time())
            self.currentToolChanged.emit()
            self.refresh()
        if self._capture is not None:
            self._poll_touch_off(stat)

    def _poll_touch_off(self, stat) -> None:
        import linuxcnc
        capture = self._capture
        capture["polls"] += 1
        if stat.interp_state != linuxcnc.INTERP_IDLE:
            capture["busy"] = True
            return
        if not capture["busy"] and capture["polls"] < _TOUCH_OFF_POLLS:
            return
        self._capture = None
        entry = next((e for e in stat.tool_table if e.id == capture["holder"]), None)
        if entry is None:
            log.error("T%s is not in LinuxCNC's tool table after touching off",
                      capture["holder"])
            return
        if capture["axis"] == "x":
            self._store.set_x_offset(capture["holder"], float(entry.xoffset))
            return
        self._store.set_z_offset(capture["holder"], float(entry.zoffset))
        tool = self._store.find_tool(self._store.find_holder(capture["holder"]).cutting_tool_id)
        if isinstance(tool, BladeTool):
            self._blade_holder_id = capture["holder"]
            self.bladePlaceRequested.emit(tool.blade_width)

    def _current_holder(self) -> Optional[ToolHolder]:
        return self._store.find_holder(self._current)


def _offset_text(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.3f}"


def _recently_used(holders: List[ToolHolder]) -> List[ToolHolder]:
    """The holders loaded today; if none was, those loaded on the last two
    days anything was."""
    loaded = [h for h in holders if h.has_tool and h.last_loaded is not None]
    if not loaded:
        return []
    days = sorted({date.fromtimestamp(h.last_loaded) for h in loaded}, reverse=True)
    today = date.today()
    shown_days = {today} if today in days else set(days[:2])
    return [h for h in loaded if date.fromtimestamp(h.last_loaded) in shown_days]
