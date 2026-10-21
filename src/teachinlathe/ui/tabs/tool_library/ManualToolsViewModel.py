"""The tools on the Manual Turning screen: the tool holders, as LinuxCNC
knows them - holder N is tool TN.

One is the current loaded tool; tapping another loads it (M61), unless the
machine is feeding. Nothing else is edited here: the offsets come from
touching off, which the tool library repository runs. A blade touched off
in Z is asked which of its points that was.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, List

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.core.tool_library_repository import ToolLibraryRepository, tool_library_repository
from teachinlathe.tooling.model.data_types import BladeTool, ToolHolder, ZOffsetPlace
from teachinlathe.ui.common.images import image_url
from teachinlathe.ui.tabs.tool_library.tool_library_models import (
    DataclassListModel, MountedToolViews, offset_text,
)

log = logging.getLogger(__name__)

#: The title bar's toggle: on, only the recently used tools are listed.
_RECENT_ACTION = "toggle_recent"
_RECENT_ICON = image_url("recent.svg")


@dataclass(frozen=True)
class ManualToolRow:
    toolNo: int          # the holder's id: LinuxCNC's T number
    toolId: int          # the mounted cutting tool's id, 0 when empty
    toolCard: str        # which thumbnail, title and figures draw it
    toolView: Any        # the view they read, or None
    toolComment: str
    xOffset: str         # as shown, or empty until touched off
    zOffset: str
    isCurrentLoadedTool: bool
    selectable: bool     # can be loaded now


class ManualToolListModel(DataclassListModel):
    def __init__(self, parent=None):
        super().__init__(ManualToolRow, parent)


def fill_tool_rows(repository: ToolLibraryRepository, model: ManualToolListModel,
                   views: MountedToolViews, holders: List[ToolHolder], feeding: bool = False) -> None:
    """One row per holder, with the tool in it drawn as its card shows it."""
    rows = []
    current = repository.current_loaded_tool
    views.begin()
    for holder in holders:
        tool = repository.find_tool(holder.cutting_tool_id)
        card, view = views.view_for(tool)
        rows.append(ManualToolRow(
            toolNo=holder.tool_holder_id,
            toolId=tool.cutting_tool_id if tool else 0,
            toolCard=card,
            toolView=view,
            toolComment=tool.comment if tool else "",
            xOffset=offset_text(holder, "x"),
            zOffset=offset_text(holder, "z"),
            isCurrentLoadedTool=holder.tool_holder_id == current,
            selectable=tool is not None and not feeding,
        ))
    model.setRows(rows)
    views.end()


class TouchedOffToolsModel(ManualToolListModel):
    """Every holder with a tool and both offsets set: the ones a program can
    change to. For the conversational editors' tool pickers."""

    def __init__(self, repository: ToolLibraryRepository = None, parent=None):
        super().__init__(parent)
        self._repository = tool_library_repository() if repository is None else repository
        self._views = MountedToolViews(self)
        self._repository.toolsChanged.connect(self.refresh)
        self._repository.currentLoadedToolChanged.connect(self.refresh)
        self.refresh()

    def refresh(self, *_args) -> None:
        holders = sorted(self._repository.holders, key=lambda h: h.tool_holder_id)
        fill_tool_rows(self._repository, self, self._views, [h for h in holders if h.is_ready])


class ManualToolsViewModel(QObject):
    recentOnlyChanged = pyqtSignal()
    #: The title bar reads getHeaderState() again: the recent toggle is there.
    headerStateChanged = pyqtSignal()
    currentLoadedToolChanged = pyqtSignal()
    #: The current loaded tool moved in the list, or the list was refilled.
    currentLoadedToolRowChanged = pyqtSignal()
    feedingChanged = pyqtSignal()
    #: A blade was touched off in Z: which of its points was it? (its width)
    bladePlaceRequested = pyqtSignal(float)

    def __init__(self, parent=None, repository: ToolLibraryRepository = None, hal=None):
        super().__init__(parent)
        self._repository = tool_library_repository() if repository is None else repository
        repository = self._repository
        self._model = ManualToolListModel(self)
        self._views = MountedToolViews(self)
        self._recent_only = False
        self._feeding = False
        self._blade_holder_id = 0
        self._current_loaded_tool_row = -1
        self._row_count = 0

        repository.toolsChanged.connect(self.refresh)
        repository.currentLoadedToolChanged.connect(self._on_current_loaded_tool_changed)
        repository.touchedOff.connect(self._on_touched_off)

        # No tool change while the joystick is feeding.
        comp = (TeachInLatheComponent() if hal is None else hal).comp
        comp.addListener(TeachInLatheComponent.PinJoystickIsFeeding, self.setFeeding)
        self._feeding = bool(comp.getPin(TeachInLatheComponent.PinJoystickIsFeeding).value)
        self.refresh()

    # ── What the screen shows ───────────────────────────────────────────────

    @pyqtProperty(QObject, constant=True)
    def toolsModel(self):
        return self._model

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

    @pyqtProperty(int, notify=currentLoadedToolChanged)
    def currentLoadedToolNo(self):
        return self._repository.current_loaded_tool

    @pyqtProperty(int, notify=currentLoadedToolRowChanged)
    def currentLoadedToolRow(self):
        """The row the current loaded tool is on, -1 when it is not listed:
        the list keeps it in view."""
        return self._current_loaded_tool_row

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
        holder = self._repository.find_holder(tool_no)
        if holder is None or not holder.has_tool or self._feeding \
                or tool_no == self._repository.current_loaded_tool:
            return
        self._repository.load_tool(tool_no)

    def setFeeding(self, feeding) -> None:
        feeding = bool(feeding)
        if feeding != self._feeding:
            self._feeding = feeding
            self.feedingChanged.emit()
            self.refresh()

    @pyqtSlot(str)
    def setBladePlace(self, place: str) -> None:
        """Answer to bladePlaceRequested: "-1", "0" or "1"."""
        if self._blade_holder_id:
            self._repository.set_z_offset_place(self._blade_holder_id, ZOffsetPlace(place))
            self._blade_holder_id = 0

    # ── The list ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        holders = self._shown_holders()
        fill_tool_rows(self._repository, self._model, self._views, holders, self._feeding)
        current = self._repository.current_loaded_tool
        row = next((i for i, h in enumerate(holders) if h.tool_holder_id == current), -1)
        if row != self._current_loaded_tool_row or len(holders) != self._row_count:
            self._current_loaded_tool_row = row
            self._row_count = len(holders)
            self.currentLoadedToolRowChanged.emit()

    def _shown_holders(self) -> List[ToolHolder]:
        """The holders with a tool in them: an empty one is nothing to load."""
        holders = sorted((h for h in self._repository.holders if h.has_tool),
                         key=lambda h: h.tool_holder_id)
        if not self._recent_only:
            return holders
        return _recently_used(holders)

    # ── The repository ──────────────────────────────────────────────────────

    def _on_current_loaded_tool_changed(self, _tool_no: int) -> None:
        self.currentLoadedToolChanged.emit()
        self.refresh()

    def _on_touched_off(self, tool_holder_id: int, axis: str) -> None:
        if axis != "z":
            return
        tool = self._repository.tool_in(tool_holder_id)
        if isinstance(tool, BladeTool):
            self._blade_holder_id = tool_holder_id
            self.bladePlaceRequested.emit(tool.blade_width)


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
