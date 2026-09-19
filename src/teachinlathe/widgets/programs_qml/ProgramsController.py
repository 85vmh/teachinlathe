"""The Programs tab, without a widget under it.

This was ``ProgramsQml``, a QQuickWidget that also owned the Gremlin
QOpenGLWidget and kept it aligned with a placeholder in its own scene: every
move, resize, screen change and full-screen transition had to re-map the
widget's geometry, and a set of QPushButtons had to be moved with it.

The preview is a scene-graph item now (``LatheBackplot``), so none of that
remains. What is left is what the class was always really doing: owning the
view models, answering the app shell's header questions, and translating a
few view-model signals into preview commands.
"""

import logging
import os

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from teachinlathe.data.programs_screen import ProgramsScreen, ProgramsScreenEnum
from teachinlathe.widgets.programs_qml.filesystemview import FileSystemViewModel
from teachinlathe.widgets.programs_qml.ProgramsDroViewModel import ProgramsDroViewModel
from teachinlathe.widgets.programs_qml.ProgramsToolFeedSpeedViewModel import \
    ProgramsToolFeedSpeedViewModel
from teachinlathe.widgets.programs_qml.ProgramsViewModel import ProgramsViewModel

LOG = logging.getLogger(__name__)


class ProgramsController(QObject):
    headerStateChanged = pyqtSignal()

    def __init__(self, locations, app, parent=None, json_folder_path=''):
        super().__init__(parent)
        self._app = app
        self._backplot = None
        self._pending_fit_path = ''

        folders = [(loc.name, loc.root_path) for loc in locations]
        self.viewmodel = ProgramsViewModel(folders, self)

        self.fs_viewmodel = FileSystemViewModel(
            locations, self, json_folder_path=json_folder_path)
        self.fs_viewmodel.fileSelected.connect(
            self.viewmodel.bridge.selectFileByAbsolutePath)
        self.fs_viewmodel.fileOpenRequested.connect(
            self.viewmodel.openFileByAbsolutePath)
        self.fs_viewmodel.selectionChanged.connect(self._emit_header_state_changed)
        self.fs_viewmodel.navigationChanged.connect(self._emit_header_state_changed)

        self.dro_viewmodel = ProgramsDroViewModel(self)
        self.tool_feed_speed_viewmodel = ProgramsToolFeedSpeedViewModel(
            self.viewmodel.runtime_store, self)
        self.programs_screen_enum = ProgramsScreenEnum(self)

        self.viewmodel.programLoadRequested.connect(self._prepare_preview_for_load)
        self.viewmodel.enterRunFullScreenRequested.connect(self._enter_run_full_screen)
        self.viewmodel.exitRunFullScreenRequested.connect(self._exit_run_full_screen)
        self.viewmodel.screenIndexChanged.connect(
            lambda _index: self._emit_header_state_changed())
        self.viewmodel.currentFilePathChanged.connect(self._on_current_file_changed)
        self.viewmodel.actions.stateChanged.connect(self._emit_header_state_changed)
        self.viewmodel.gremlinZoomInRequested.connect(self._zoom_in)
        self.viewmodel.gremlinZoomOutRequested.connect(self._zoom_out)
        self.viewmodel.gremlinClearRequested.connect(self._clear_plot)
        self.viewmodel.gremlinFitRequested.connect(self._fit_to_window)
        self.viewmodel.runtime_store.machineFileChanged.connect(self._on_machine_file_changed)
        # callLevelChanged is deliberately not connected. It used to re-fit the
        # plot to the window, but the call level changes on every subroutine
        # call and return, and every conversational operation is a subroutine -
        # so the operator's zoom and pan were thrown away at each operation
        # boundary. Stepping into a subroutine does not change the geometry on
        # screen, so there is nothing to re-fit.

    # ── the preview item ────────────────────────────────────────────────────

    def _on_current_file_changed(self, path):
        if self._backplot is not None:
            self._backplot.setProgramFile(path or '')
        self._emit_header_state_changed()

    def attachBackplot(self, item):
        """Called once the QML scene is up, with the LatheBackplot item.

        The item is created by QML, so it is told here which program it is
        previewing; it reads the machine's position itself, on its own clock.
        """
        self._backplot = item
        if item is not None:
            item.setProgramFile(self.viewmodel.currentFilePath or '')

    def _zoom_in(self):
        if self._backplot is not None:
            self._backplot.zoomIn()

    def _zoom_out(self):
        if self._backplot is not None:
            self._backplot.zoomOut()

    def _clear_plot(self):
        if self._backplot is not None:
            self._backplot.clearPlot()

    def _fit_to_window(self):
        if self._backplot is not None:
            self._backplot.fitToWindow()

    def _prepare_preview_for_load(self, path):
        self._pending_fit_path = os.path.abspath(path) if path else ''
        if self._backplot is None:
            return
        # The preview follows this file from now on, not whatever the
        # interpreter happens to have open: while the program runs it dips
        # into subroutines, and a subroutine does not parse on its own.
        self._backplot.setProgramFile(path or '')
        if self._pending_fit_path:
            LOG.info('Programs: invalidating preview for %s', self._pending_fit_path)
            self._backplot.invalidatePreview(self._pending_fit_path)
            QTimer.singleShot(0, self._refresh_preview_after_load)
        else:
            self._backplot.clearPlot()

    def _refresh_preview_after_load(self):
        snapshot = self.viewmodel.runtime_store.snapshot
        if self.viewmodel.actions.isActive or snapshot.call_level > 0:
            LOG.info('Programs: skipped preview refresh while program is active')
            self._pending_fit_path = ''
            return
        if self._backplot is not None:
            self._backplot.poll()
        self._pending_fit_path = ''
        QTimer.singleShot(150, self._fit_to_window)

    def _on_machine_file_changed(self, path):
        """Fit the view when a new program reaches the machine - and only then.

        The interpreter's file also changes as it steps into subroutines, and
        re-fitting on those would move the plot under the operator mid-run.
        """
        machine_path = os.path.abspath(path) if path else ''
        if not machine_path:
            return
        program = self.viewmodel.currentFilePath or ''
        if program and machine_path != os.path.abspath(program):
            return
        if self._pending_fit_path and machine_path != self._pending_fit_path:
            return
        QTimer.singleShot(150, self._fit_to_window)
        self._pending_fit_path = ''

    # ── full screen ─────────────────────────────────────────────────────────

    def _enter_run_full_screen(self):
        if self._app is not None:
            self._app.enterProgramRunFullScreen()

    def _exit_run_full_screen(self):
        if self._app is not None:
            self._app.exitFullScreen()

    # ── the app shell's header ──────────────────────────────────────────────

    def _emit_header_state_changed(self):
        self.headerStateChanged.emit()

    def _current_program_name(self):
        path = self.viewmodel.currentFilePath or ''
        return os.path.basename(path) or 'No file loaded'

    def getHeaderState(self):
        left_actions = []
        right_actions = []
        title = 'Machine FileSystem'
        if self.viewmodel.screenIndex != ProgramsScreen.FileSystem:
            left_actions.append({"id": "back", "text": "← Back to FileSystem", "enabled": True})
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
                "enabled": bool(self.fs_viewmodel.selectedIsFile
                                and not self.fs_viewmodel.isInMountedMedia),
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
            if not json_path or self._app is None:
                return
            self._app.editConversationalProgramFromJson(json_path)
        elif action_id == "toggle_optional_stop":
            actions = self.viewmodel.actions
            actions.setOptionalStopEnabled(not actions.optionalStopAction.checked)
        elif action_id == "toggle_block_delete":
            actions = self.viewmodel.actions
            actions.setBlockDeleteEnabled(not actions.blockDeleteAction.checked)

    # ── navigation helpers the app calls ────────────────────────────────────

    def showFileInGeneratedPrograms(self, ngc_path):
        self.viewmodel.showFilesScreen()
        self.fs_viewmodel.showFileInGeneratedPrograms(os.path.abspath(ngc_path))
