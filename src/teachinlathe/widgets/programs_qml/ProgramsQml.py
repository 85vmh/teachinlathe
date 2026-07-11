import os

from PyQt5.QtCore import QPoint, QPointF, QTimer, QUrl, pyqtSignal, Qt
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QWidget

from teachinlathe.data.programs_screen import ProgramsScreen, ProgramsScreenEnum
from teachinlathe.widgets.gremlin.gremlin_widget import GremlinWidget
from teachinlathe.widgets.programs_qml.filesystemview import FileSystemViewModel
from teachinlathe.widgets.programs_qml.ProgramsDroViewModel import ProgramsDroViewModel
from teachinlathe.widgets.programs_qml.ProgramsToolFeedSpeedViewModel import ProgramsToolFeedSpeedViewModel
from qtpyvcp.utilities import logger

from teachinlathe.widgets.programs_qml.ProgramsViewModel import ProgramsViewModel

LOG = logger.getLogger('qtpyvcp.' + __name__)


class ProgramsQml(QQuickWidget):
    headerStateChanged = pyqtSignal()

    _QML_DIR = os.path.dirname(__file__)

    def __init__(self, locations, parent=None, json_folder_path=''):
        super().__init__(parent)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)

        folders = [(loc.name, loc.root_path) for loc in locations]
        self.viewmodel = ProgramsViewModel(folders, self)
        gremlin_parent = parent if parent is not None else self
        self.gremlin = GremlinWidget(self.viewmodel.runtime_store, gremlin_parent)
        self.gremlin.enable_panning(True)
        self.gremlin.enable_dro = False
        self.gremlin.show_overlay = False
        self.gremlin.hide()

        self._pending_fit_path = ''
        self._gremlin_placeholder = None
        self._program_loaded_item = None
        self._root_item = None
        self._complete_dialog = None

        self._overlay_host = gremlin_parent
        self._top_left_controls = QWidget(self._overlay_host)
        self._top_left_controls.setStyleSheet('background: transparent;')
        self._top_left_layout = QHBoxLayout(self._top_left_controls)
        self._top_left_layout.setContentsMargins(0, 0, 0, 0)
        self._top_left_layout.setSpacing(12)
        self._clear_plot_button = QPushButton('Clear Plot', self._overlay_host)
        self._overlay_buttons = []
        self._create_gremlin_overlay_controls()
        self._hide_gremlin_overlay_controls()

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
        context.setContextProperty('ProgramsScreen', self.programs_screen_enum)

        self.statusChanged.connect(self._on_status_changed)
        self.setSource(QUrl.fromLocalFile(os.path.join(self._QML_DIR, 'ProgramsTabRoot.qml')))

        self.viewmodel.programLoadRequested.connect(self._prepareGremlinForLoad)
        self.viewmodel.enterRunFullScreenRequested.connect(self._enter_run_full_screen)
        self.viewmodel.exitRunFullScreenRequested.connect(self._exit_run_full_screen)
        self.viewmodel.programCompleted.connect(self._on_program_completed)
        self.viewmodel.screenIndexChanged.connect(lambda _index: QTimer.singleShot(0, self._sync_gremlin_widget))
        self.viewmodel.screenIndexChanged.connect(lambda _index: self._emit_header_state_changed())
        self.viewmodel.currentFilePathChanged.connect(lambda _path: self._emit_header_state_changed())
        self.viewmodel.actions.stateChanged.connect(self._emit_header_state_changed)
        self.viewmodel.gremlinZoomInRequested.connect(self._zoom_gremlin_in)
        self.viewmodel.gremlinZoomOutRequested.connect(self._zoom_gremlin_out)
        self.viewmodel.gremlinClearRequested.connect(self._clear_gremlin_plot)
        self.viewmodel.gremlinFitRequested.connect(self._fit_gremlin_to_window)
        self.viewmodel.runtime_store.machineFileChanged.connect(self._on_machine_file_changed)
        self.viewmodel.runtime_store.callLevelChanged.connect(self._on_call_level_changed)

    def _create_gremlin_overlay_controls(self):
        button_style = (
            'QPushButton { background: #2d7d46; color: white; border: 1px solid #3fb950; '
            'padding: 10px 16px; font: 12pt "Noto Sans"; border-radius: 6px; }'
            'QPushButton:hover { background: #25673a; }'
            'QPushButton:disabled { color: #d9e7de; background: #8ea99a; border-color: #8ea99a; }'
        )
        clear_style = (
            'QPushButton { background: #7a2d2d; color: white; border: 1px solid #d16969; '
            'padding: 10px 16px; font: 12pt "Noto Sans"; border-radius: 6px; }'
            'QPushButton:hover { background: #652424; }'
        )

        for label, handler in (
            ('Zoom In', self._zoom_gremlin_in),
            ('Zoom Out', self._zoom_gremlin_out),
            ('Fit To Screen', self._fit_gremlin_to_window),
        ):
            button = QPushButton(label, self._top_left_controls)
            button.setStyleSheet(button_style)
            button.setFocusPolicy(Qt.NoFocus)
            button.clicked.connect(handler)
            self._top_left_layout.addWidget(button)
            self._overlay_buttons.append(button)

        self._clear_plot_button.setStyleSheet(clear_style)
        self._clear_plot_button.setFocusPolicy(Qt.NoFocus)
        self._clear_plot_button.clicked.connect(self._clear_gremlin_plot)

    def _hide_gremlin_overlay_controls(self):
        self._top_left_controls.hide()
        self._clear_plot_button.hide()

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
        self._schedule_gremlin_sync()
        QTimer.singleShot(50, self._sync_gremlin_widget)

    def _emit_header_state_changed(self):
        self.headerStateChanged.emit()

    def getHeaderState(self):
        left_actions = []
        right_actions = []
        title = 'Machine FileSystem'
        if self.viewmodel.screenIndex != ProgramsScreen.FileSystem:
            left_actions.append({"id": "back", "text": "Back to FileSystem", "enabled": True})
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

    def _on_status_changed(self, status):
        if status != QQuickWidget.Ready:
            return

        self._root_item = self.rootObject()
        if not self._root_item:
            return

        self._complete_dialog = self._root_item.findChild(QQuickItem, 'programCompleteDialog')
        self._program_loaded_item = self._root_item.findChild(QQuickItem, 'programLoadedScreen')

        self._gremlin_placeholder = self._root_item.findChild(QQuickItem, 'gremlinViewport')
        if self._gremlin_placeholder is not None:
            for signal_name in ('xChanged', 'yChanged', 'widthChanged', 'heightChanged', 'visibleChanged'):
                try:
                    getattr(self._gremlin_placeholder, signal_name).connect(self._schedule_gremlin_sync)
                except Exception:
                    pass
        if self._program_loaded_item is not None:
            for signal_name in ('visibleChanged', 'xChanged', 'yChanged', 'widthChanged', 'heightChanged'):
                try:
                    getattr(self._program_loaded_item, signal_name).connect(self._schedule_gremlin_sync)
                except Exception:
                    pass
        self._schedule_gremlin_sync()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_gremlin_sync()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_gremlin_sync()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.gremlin.hide()
        self._hide_gremlin_overlay_controls()

    def _enter_run_full_screen(self):
        self._hide_program_complete_dialog()
        win = self.window()
        if win is None or not hasattr(win, 'enterProgramRunFullScreen'):
            return
        win.enterProgramRunFullScreen(self)
        # The gremlin overlay + controls are siblings of this widget under the
        # tab; move them onto the full-screen host so they stay on top.
        self.gremlin.setParent(win)
        self._top_left_controls.setParent(win)
        self._clear_plot_button.setParent(win)
        self._schedule_gremlin_sync()

    def _hide_program_complete_dialog(self):
        dlg = getattr(self, '_complete_dialog', None)
        if dlg is None and self._root_item is not None:
            dlg = self._root_item.findChild(QQuickItem, 'programCompleteDialog')
            self._complete_dialog = dlg
        if dlg is not None:
            dlg.setProperty('visible', False)

    def _on_program_completed(self, name, movement, toolchange, total):
        # The gremlin is a native widget overlaid on top of the QQuickWidget, so
        # hide it while the QML completion dialog is shown. It is re-shown by the
        # gremlin sync when re-running (Run Again) or leaving full screen (Done).
        self.gremlin.hide()
        self._hide_gremlin_overlay_controls()
        dlg = getattr(self, '_complete_dialog', None)
        if dlg is None and self._root_item is not None:
            dlg = self._root_item.findChild(QQuickItem, 'programCompleteDialog')
            self._complete_dialog = dlg
        if dlg is not None:
            dlg.setProperty('programName', name)
            dlg.setProperty('movement', movement)
            dlg.setProperty('toolchange', toolchange)
            dlg.setProperty('total', total)
            dlg.setProperty('visible', True)  # open()

    def _exit_run_full_screen(self):
        QTimer.singleShot(0, self._exit_run_full_screen_now)

    def _exit_run_full_screen_now(self):
        self._hide_program_complete_dialog()
        win = self.window()
        self.gremlin.hide()
        self._hide_gremlin_overlay_controls()
        if win is not None and hasattr(win, 'exitFullScreen'):
            win.exitFullScreen()
        QTimer.singleShot(100, self._restore_gremlin_overlay_after_full_screen)
        QTimer.singleShot(250, self._sync_gremlin_widget)

    def _restore_gremlin_overlay_after_full_screen(self):
        self.gremlin.hide()
        self._hide_gremlin_overlay_controls()
        self.gremlin.setParent(self._overlay_host)
        self._top_left_controls.setParent(self._overlay_host)
        self._clear_plot_button.setParent(self._overlay_host)
        self._schedule_gremlin_sync()

    def _schedule_gremlin_sync(self):
        QTimer.singleShot(0, self._sync_gremlin_widget)

    def _sync_gremlin_widget(self):
        if self.viewmodel.screenIndex not in (ProgramsScreen.ProgramLoaded, ProgramsScreen.ProgramRunning) \
                or self._gremlin_placeholder is None:
            self.gremlin.hide()
            self._hide_gremlin_overlay_controls()
            return

        item = self._gremlin_placeholder
        if self._program_loaded_item is not None and not self._program_loaded_item.isVisible():
            self.gremlin.hide()
            self._hide_gremlin_overlay_controls()
            return
        if item.width() <= 0 or item.height() <= 0 or not item.isVisible():
            self.gremlin.hide()
            self._hide_gremlin_overlay_controls()
            return

        scene_pos = item.mapToScene(QPointF(0, 0))
        top_left = self.mapTo(self.gremlin.parentWidget(), QPoint(int(scene_pos.x()), int(scene_pos.y())))
        width = int(item.width())
        height = int(item.height())
        left = int(top_left.x())
        top = int(top_left.y())
        parent = self.gremlin.parentWidget()
        if parent is None or width <= 0 or height <= 0 or left < 0 or top < 0 \
                or left + width > parent.width() or top + height > parent.height():
            self.gremlin.hide()
            self._hide_gremlin_overlay_controls()
            return

        self.gremlin.setGeometry(left, top, width, height)
        self.gremlin.show()
        self.gremlin.raise_()
        self.gremlin.update()

        self._top_left_controls.adjustSize()
        self._top_left_controls.move(left + 16, top + 16)
        self._top_left_controls.raise_()
        self._top_left_controls.show()

        self._clear_plot_button.adjustSize()
        self._clear_plot_button.move(left + width - self._clear_plot_button.width() - 16, top + 16)
        self._clear_plot_button.raise_()
        self._clear_plot_button.show()

    def _prepareGremlinForLoad(self, path):
        self._pending_fit_path = os.path.abspath(path) if path else ''
        self._clear_gremlin_plot()

    def _fit_gremlin_to_window(self):
        LOG.info('ProgramsQml: fit-to-screen requested')
        self._sync_gremlin_widget()
        self.gremlin.setViewXZ2()
        self.gremlin.update()

    def _zoom_gremlin_in(self):
        LOG.info('ProgramsQml: zoom-in requested')
        self.gremlin.zoomIn()
        self.gremlin.update()

    def _zoom_gremlin_out(self):
        LOG.info('ProgramsQml: zoom-out requested')
        self.gremlin.zoomOut()
        self.gremlin.update()

    def _clear_gremlin_plot(self):
        LOG.info('ProgramsQml: clear-plot requested')
        self.gremlin.clearLivePlot()
        self.gremlin.update()

    def _on_machine_file_changed(self, path):
        machine_path = os.path.abspath(path) if path else ''
        if not machine_path:
            return
        if self._pending_fit_path and machine_path != self._pending_fit_path:
            return
        QTimer.singleShot(150, self._fit_gremlin_to_window)
        self._pending_fit_path = ''

    def _on_call_level_changed(self, _call_level):
        QTimer.singleShot(0, self._fit_gremlin_to_window)
