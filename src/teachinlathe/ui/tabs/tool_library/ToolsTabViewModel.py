"""The Tool Library tab: tool holders on the left, cutting tools on the right,
and the screen a cutting tool is added or edited on, pushed over them."""

from __future__ import annotations

import logging
from enum import Enum

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.tooling.model.data_types import (
    BladeTool, BoringTool, CuttingToolType, DrillingTool, ReamingTool, TappingTool,
    ThreadingTool, TurningTool,
)
from teachinlathe.core.tool_library_repository import ToolLibraryRepository
from teachinlathe.ui.tabs.tool_library.tool_library_models import (
    CuttingToolCategoriesModel, ToolHolderListModel,
)
from teachinlathe.ui.tabs.tool_library.BladeToolEditorViewModel import (
    BladeToolEditorViewModel, new_blade_tool,
)
from teachinlathe.ui.tabs.tool_library.DrillingToolEditorViewModel import (
    DrillingToolEditorViewModel, new_drilling_tool,
)
from teachinlathe.ui.tabs.tool_library.ReamingToolEditorViewModel import (
    ReamingToolEditorViewModel, new_reaming_tool,
)
from teachinlathe.ui.tabs.tool_library.TappingToolEditorViewModel import (
    TappingToolEditorViewModel, new_tapping_tool,
)
from teachinlathe.ui.tabs.tool_library.ThreadingToolEditorViewModel import (
    ThreadingToolEditorViewModel, new_threading_tool,
)
from teachinlathe.ui.tabs.tool_library.TurningToolEditorViewModel import (
    TurningToolEditorViewModel, new_turning_tool,
)

log = logging.getLogger(__name__)

#: The cutting tools that have an add/edit screen: the class of each, how a
#: new one starts, and the screen's view model. A boring bar is a turning
#: tool with a body; its screen is a copy of the turning one, over the same
#: view model.
EDITABLE_TOOLS = {
    CuttingToolType.TURNING: (TurningTool, new_turning_tool,
                              TurningToolEditorViewModel),
    CuttingToolType.BORING: (BoringTool, lambda tool_id: new_turning_tool(tool_id, BoringTool),
                             TurningToolEditorViewModel),
    CuttingToolType.THREADING: (ThreadingTool, new_threading_tool,
                                ThreadingToolEditorViewModel),
    CuttingToolType.BLADE: (BladeTool, new_blade_tool, BladeToolEditorViewModel),
    CuttingToolType.DRILLING: (DrillingTool, new_drilling_tool, DrillingToolEditorViewModel),
    CuttingToolType.REAMING: (ReamingTool, new_reaming_tool, ReamingToolEditorViewModel),
    CuttingToolType.TAPPING: (TappingTool, new_tapping_tool, TappingToolEditorViewModel),
}


class HeaderAction(str, Enum):
    """The buttons this tab puts in the app's top bar."""

    BACK = "back"
    SAVE = "save"


class ToolsTabViewModel(QObject):
    editorChanged = pyqtSignal()
    # AppShellBridge listens for this to redraw the top bar.
    headerStateChanged = pyqtSignal()
    selectingHolderChanged = pyqtSignal()
    #: The tool picked to mount is in another holder: (tool, its holder, the
    #: holder it is for). The screen asks, and calls mountTool if told to.
    mountMoveRequested = pyqtSignal(int, int, int)
    #: A message for the app's toast.
    toastRequested = pyqtSignal(str)

    def __init__(self, repository: ToolLibraryRepository, parent=None):
        super().__init__(parent)
        self._repository = repository
        self._holders_model = ToolHolderListModel(repository, self)
        self._cutting_tools_model = CuttingToolCategoriesModel(repository, self)
        # Offsets come in from the Manual Turning screen's touch-offs; the
        # holder in the spindle cannot be deleted.
        repository.toolsChanged.connect(self.refresh)
        repository.currentToolChanged.connect(self.refresh)
        self._editor = None
        # The editor last closed. The screen showing it is still sliding out
        # when it closes, so it is deleted when the next one opens instead.
        self._closed_editor = None
        # The holder a cutting tool is being picked for, 0 when none is.
        self._selecting_holder_id = 0

    @pyqtProperty(QObject, constant=True)
    def holdersModel(self):
        return self._holders_model

    @pyqtProperty(QObject, constant=True)
    def cuttingToolsModel(self):
        return self._cutting_tools_model

    @pyqtProperty(QObject, notify=editorChanged)
    def editor(self):
        """The add/edit screen's view model while it is open, else null."""
        return self._editor

    @pyqtProperty(int, notify=selectingHolderChanged)
    def selectingHolderId(self):
        """The holder whose cutting tool is being picked, 0 when none is:
        while one is, tapping a cutting tool mounts it rather than editing it."""
        return self._selecting_holder_id

    # ── Mounting ────────────────────────────────────────────────────────────

    @pyqtSlot(int)
    def beginMount(self, tool_holder_id: int) -> None:
        self._set_selecting(tool_holder_id)

    @pyqtSlot()
    def cancelMount(self) -> None:
        self._set_selecting(0)

    @pyqtSlot(int)
    def cuttingToolTapped(self, cutting_tool_id: int) -> None:
        """A tool tapped in the list: mounted if a holder is waiting for one,
        otherwise opened to edit."""
        holder_id = self._selecting_holder_id
        if holder_id == 0:
            self.editCuttingTool(cutting_tool_id)
            return
        current = self._repository.holder_of(cutting_tool_id)
        if current is not None and current.tool_holder_id != holder_id:
            self.mountMoveRequested.emit(cutting_tool_id, current.tool_holder_id, holder_id)
            return
        self.mountTool(cutting_tool_id, holder_id)

    @pyqtSlot(int, int)
    def mountTool(self, cutting_tool_id: int, tool_holder_id: int) -> None:
        """Mount the tool, out of whatever holder it was in."""
        self._repository.mount(tool_holder_id, cutting_tool_id)
        self._set_selecting(0)

    @pyqtSlot(int)
    def unmountTool(self, tool_holder_id: int) -> None:
        self._repository.mount(tool_holder_id, None)

    @pyqtSlot(int)
    def deleteCuttingTool(self, cutting_tool_id: int) -> None:
        """Delete a tool, unless it is mounted in a holder."""
        if self._repository.holder_of(cutting_tool_id) is not None:
            self.toastRequested.emit("Unmount the tool from the holder before deleting")
            return
        self._repository.delete_cutting_tool(cutting_tool_id)

    @pyqtSlot(int)
    def deleteToolHolder(self, tool_holder_id: int) -> None:
        """Delete an empty holder that is not in the spindle. The screen
        offers it only for one: a holder with a tool swipes to unmount the
        tool first, and the one in the spindle does not swipe at all."""
        if tool_holder_id == self._repository.current_tool:
            self.toastRequested.emit("The holder in the spindle cannot be deleted")
            return
        try:
            self._repository.delete_holder(tool_holder_id)
        except ValueError:
            self.toastRequested.emit("Unmount the tool from the holder before deleting")

    @pyqtSlot()
    def addToolHolder(self) -> None:
        self._repository.add_holder()

    def _set_selecting(self, tool_holder_id: int) -> None:
        if tool_holder_id != self._selecting_holder_id:
            self._selecting_holder_id = tool_holder_id
            self.selectingHolderChanged.emit()

    # ── Opening the editor ──────────────────────────────────────────────────

    @pyqtSlot(str)
    def addCuttingTool(self, tool_type: str) -> None:
        tool_type = CuttingToolType(tool_type)
        editable = EDITABLE_TOOLS.get(tool_type)
        if editable is None:
            log.info("adding a %s is not implemented yet", tool_type.tool_name)
            return
        _tool_class, new_tool, editor_class = editable
        tool = new_tool(self._repository.next_cutting_tool_id())
        self._open_editor(editor_class(tool, is_new=True, parent=self))

    @pyqtSlot(int)
    def editCuttingTool(self, cutting_tool_id: int) -> None:
        tool = self._repository.find_tool(cutting_tool_id)
        editable = EDITABLE_TOOLS.get(tool.tool_type) if tool is not None else None
        # By exact class: a boring bar is a TurningTool too, but it has its
        # own screen.
        if editable is None or type(tool) is not editable[0]:
            if tool is not None:
                log.info("editing a %s is not implemented yet", tool.tool_type.tool_name)
            return
        self._open_editor(editable[2](tool, is_new=False, parent=self))

    def _open_editor(self, editor) -> None:
        if self._closed_editor is not None:
            self._closed_editor.deleteLater()
            self._closed_editor = None
        self._editor = editor
        editor.changed.connect(self.headerStateChanged)
        self.editorChanged.emit()
        self.headerStateChanged.emit()

    def _close_editor(self) -> None:
        self._closed_editor, self._editor = self._editor, None
        self.editorChanged.emit()
        self.headerStateChanged.emit()

    # ── Top bar ─────────────────────────────────────────────────────────────

    def getHeaderState(self):
        if self._editor is None:
            return {}
        return {
            "title": self._editor.title,
            "left_actions": [{"id": HeaderAction.BACK.value, "text": "← Back", "enabled": True}],
            "right_actions": [{"id": HeaderAction.SAVE.value, "text": "Save", "enabled": True}],
        }

    def triggerHeaderAction(self, action_id: str) -> None:
        if self._editor is None:
            return
        match HeaderAction(action_id):
            case HeaderAction.BACK:
                self._close_editor()
            case HeaderAction.SAVE:
                self._repository.save_cutting_tool(self._editor.result())
                self._close_editor()

    def refresh(self) -> None:
        self._holders_model.refresh()
        self._cutting_tools_model.refresh()
