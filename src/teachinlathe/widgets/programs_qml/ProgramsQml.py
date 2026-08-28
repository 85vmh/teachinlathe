import os

from PyQt5.QtCore import QTimer, QUrl, pyqtSignal
from PyQt5.QtQuickWidgets import QQuickWidget

from teachinlathe.data.programs_screen import ProgramsScreen, ProgramsScreenEnum
from teachinlathe.widgets.programs_qml.filesystemview import FileSystemViewModel
from teachinlathe.widgets.programs_qml.ProgramsDroViewModel import ProgramsDroViewModel
from teachinlathe.widgets.programs_qml.ProgramsToolFeedSpeedViewModel import ProgramsToolFeedSpeedViewModel
from teachinlathe.widgets.programs_qml.toolpath_model import ToolpathModel

from teachinlathe.widgets.programs_qml.ProgramsViewModel import ProgramsViewModel


class ProgramsQml(QQuickWidget):
    headerStateChanged = pyqtSignal()

    _QML_DIR = os.path.dirname(__file__)

    def __init__(self, locations, parent=None, json_folder_path=''):
        super().__init__(parent)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)

        folders = [(loc.name, loc.root_path) for loc in locations]
        self.viewmodel = ProgramsViewModel(folders, self)
        self.toolpath_model = ToolpathModel(self.viewmodel.runtime_store, self)

        self.fs_viewmodel = FileSystemViewModel(locations, self, json_folder_path=json_folder_path)
        self.fs_viewmodel.fileSelected.connect(self.viewmodel.bridge.selectFileByAbsolutePath)
        self.fs_viewmodel.fileOpenRequested.connect(self.viewmodel.openFileByAbsolutePath)
        self.fs_viewmodel.selectionChanged.connect(self._emit_header_state_changed)
        self.fs_viewmodel.navigationChanged.connect(self._emit_header_state_changed)

        self.dro_viewmodel = ProgramsDroViewModel(self)
        self.tool_feed_speed_viewmodel = ProgramsToolFeedSpeedViewModel(self.viewmodel.runtime_store, self)

        context = self.engine().rootContext()
        self.programs_screen_enum = ProgramsScreenEnum(self)
        context.setContextProperty('programsViewModel', self.viewmodel)
        context.setContextProperty('fsViewModel', self.fs_viewmodel)
        context.setContextProperty('programsDroViewModel', self.dro_viewmodel)
        context.setContextProperty('programsToolFeedSpeedViewModel', self.tool_feed_speed_viewmodel)
        context.setContextProperty('toolpathModel', self.toolpath_model)
        context.setContextProperty('ProgramsScreen', self.programs_screen_enum)

        self.setSource(QUrl.fromLocalFile(os.path.join(self._QML_DIR, 'ProgramsTabRoot.qml')))

        self.viewmodel.programLoadRequested.connect(self.toolpath_model.loadFile)
        self.viewmodel.enterRunFullScreenRequested.connect(self._enter_run_full_screen)
        self.viewmodel.exitRunFullScreenRequested.connect(self._exit_run_full_screen)
        self.viewmodel.screenIndexChanged.connect(lambda _index: self._emit_header_state_changed())
        self.viewmodel.currentFilePathChanged.connect(lambda _path: self._emit_header_state_changed())
        self.viewmodel.actions.stateChanged.connect(self._emit_header_state_changed)

    def setAppState(self, app_state):
        context = self.engine().rootContext()
        context.setContextProperty('appState', app_state)
        context.setContextProperty('cncStore', getattr(app_state, 'cncStore', None))
        context.setContextProperty('navigationStore', getattr(app_state, 'navigationStore', None))

    def reactivate(self):
        self.show()
        self.raise_()
        self.update()
        self.repaint()

    def _emit_header_state_changed(self):
        self.headerStateChanged.emit()

    def getHeaderState(self):
        left_actions = []
        right_actions = []
        title = 'Machine FileSystem'
        if self.viewmodel.screenIndex != ProgramsScreen.FileSystem:
            left_actions.append({"id": "back", "text": "← Back to FileSystem", "enabled": True})
            # Break-on-M1 / Skip-Blocks now live in the bottom ProgramActionBar (QML).
            title = f'Loaded Program [{self._current_program_name()}]'
        else:
            if self.fs_viewmodel.isInGeneratedPrograms:
                left_actions.append({
                    "id": "edit_program",
                    "text": "Edit Program",
                    "enabled": bool(self.fs_viewmodel.canEditSelectedGeneratedProgram),
                })
            right_actions.append({
                "id": "load_program",
                "text": "Load Program",
                "enabled": bool(self.fs_viewmodel.selectedIsFile and not self.fs_viewmodel.isInMountedMedia),
            })
        return {
            "title": title,
            "left_actions": left_actions,
            "right_actions": right_actions,
        }

    def triggerHeaderAction(self, action_id):
        if action_id == "back":
            self.viewmodel.showFilesScreen()
        elif action_id == "load_program":
            self.fs_viewmodel.openSelectedFile()
        elif action_id == "edit_program":
            json_path = self.fs_viewmodel.selectedGeneratedJsonPathForEdit()
            if not json_path:
                return
            window = self.window()
            if window and hasattr(window, "editConversationalProgramFromJson"):
                window.editConversationalProgramFromJson(json_path)
        elif action_id == "toggle_optional_stop":
            actions = self.viewmodel.actions
            actions.setOptionalStopEnabled(not actions.optionalStopAction.checked)
        elif action_id == "toggle_block_delete":
            actions = self.viewmodel.actions
            actions.setBlockDeleteEnabled(not actions.blockDeleteAction.checked)

    def _current_program_name(self):
        path = self.viewmodel.currentFilePath or ''
        name = os.path.basename(path)
        return name or 'No file loaded'

    def _enter_run_full_screen(self):
        win = self.window()
        if win is None or not hasattr(win, 'enterProgramRunFullScreen'):
            return
        win.enterProgramRunFullScreen(self)

    def _exit_run_full_screen(self):
        QTimer.singleShot(0, self._exit_run_full_screen_now)

    def _exit_run_full_screen_now(self):
        win = self.window()
        if win is not None and hasattr(win, 'exitFullScreen'):
            win.exitFullScreen()
