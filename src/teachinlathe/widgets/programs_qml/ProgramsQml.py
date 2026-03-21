import os

import linuxcnc
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget, QVBoxLayout, QStackedWidget, QSplitter
from PyQt5.QtQuickWidgets import QQuickWidget
from qtpyvcp.actions import program_actions
from qtpyvcp.widgets.button_widgets.action_button import ActionButton
from qtpyvcp.widgets.input_widgets.mdientry_widget import MDIEntry

from teachinlathe.data import ProgramCallStackResolver, ProgramRuntimeStore
from teachinlathe.widgets.gremlin.gremlin_widget import GremlinWidget
from .FileSystemBridge import FileSystemBridge
from .GCodeEditorPane import GCodeEditorPane


class ProgramsQml(QWidget):
    """
    Two-screen programs panel, wired with QML.

    Screen 0 — Files:   QML (FileSystemScreen.qml)
        Left  : folder list + file list
        Right : code text viewer

    Screen 1 — Gremlin: hybrid (native Qt left, QML right)
        Left  : GremlinWidget (QOpenGLWidget)
        Right : QML code text viewer (GremlinTextViewer.qml)

    The *fsBridge* object is shared between all QML widgets, so signals
    (e.g. fileContentChanged) update whichever viewer is currently visible.
    """

    _QML_DIR = os.path.dirname(__file__)

    def __init__(self, folders, parent=None):
        super().__init__(parent)

        self.bridge = FileSystemBridge(folders, self)
        self.runtime_store = ProgramRuntimeStore(self)
        self.call_stack_resolver = ProgramCallStackResolver(self)
        self._pending_fit_path = ''

        self.bridge.screenChangeRequested.connect(self._setScreen)
        self.bridge.programLoadRequested.connect(self._prepareGremlinForLoad)
        self.runtime_store.machineFileChanged.connect(self._onMachineFileChanged)
        self.runtime_store.callLevelChanged.connect(self._onCallLevelChanged)
        self.runtime_store.snapshotChanged.connect(self._updatePauseResumeButton)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)

        self.stack.addWidget(self._buildFilesScreen())
        self.stack.addWidget(self._buildGremlinScreen())
        layout.addWidget(self._buildProgramActions())

        self._updatePauseResumeButton(self.runtime_store.snapshot)

    def _buildFilesScreen(self):
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal, container)

        browser = QQuickWidget(splitter)
        browser.setResizeMode(QQuickWidget.SizeRootObjectToView)
        browser.rootContext().setContextProperty('fsBridge', self.bridge)
        browser.setSource(QUrl.fromLocalFile(
            os.path.join(self._QML_DIR, 'FileBrowserPane.qml')))
        splitter.addWidget(browser)

        splitter.addWidget(GCodeEditorPane(
            self.bridge,
            'files',
            self.runtime_store,
            self.call_stack_resolver,
            splitter,
        ))
        splitter.setSizes([320, 880])

        layout.addWidget(splitter)
        return container

    def _buildGremlinScreen(self):
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal, container)

        gremlin_container = QWidget(splitter)
        gremlin_layout = QVBoxLayout(gremlin_container)
        gremlin_layout.setContentsMargins(0, 0, 0, 0)
        gremlin_layout.setSpacing(0)

        gremlin_toolbar = QWidget(gremlin_container)
        gremlin_toolbar.setMaximumHeight(56)
        gremlin_toolbar.setStyleSheet('background: #2d2d2d; border-bottom: 1px solid #404040;')
        gremlin_toolbar_layout = QHBoxLayout(gremlin_toolbar)
        gremlin_toolbar_layout.setContentsMargins(10, 6, 10, 6)
        gremlin_toolbar_layout.setSpacing(8)

        gremlin_title = QLabel('Gremlin View', gremlin_toolbar)
        gremlin_title.setStyleSheet('color: #d4d4d4; font: 11pt "Noto";')
        gremlin_toolbar_layout.addWidget(gremlin_title)
        gremlin_toolbar_layout.addStretch(1)

        zoom_in_button = QPushButton('Zoom In', gremlin_toolbar)
        zoom_in_button.clicked.connect(self._zoomGremlinIn)
        zoom_in_button.setMinimumHeight(40)
        zoom_in_button.setStyleSheet(
            'QPushButton {'
            'font: 11pt "Noto";'
            'color: #f0f0f0;'
            'background: #3a3a3a;'
            'border: 1px solid #6a6a6a;'
            'border-radius: 8px;'
            'padding: 6px 12px;'
            '}'
            'QPushButton:pressed { background: #4a4a4a; }'
        )
        gremlin_toolbar_layout.addWidget(zoom_in_button)

        zoom_out_button = QPushButton('Zoom Out', gremlin_toolbar)
        zoom_out_button.clicked.connect(self._zoomGremlinOut)
        zoom_out_button.setMinimumHeight(40)
        zoom_out_button.setStyleSheet(
            'QPushButton {'
            'font: 11pt "Noto";'
            'color: #f0f0f0;'
            'background: #3a3a3a;'
            'border: 1px solid #6a6a6a;'
            'border-radius: 8px;'
            'padding: 6px 12px;'
            '}'
            'QPushButton:pressed { background: #4a4a4a; }'
        )
        gremlin_toolbar_layout.addWidget(zoom_out_button)

        clear_plot_button = QPushButton('Clear Plot', gremlin_toolbar)
        clear_plot_button.clicked.connect(self._clearGremlinPlot)
        clear_plot_button.setMinimumHeight(40)
        clear_plot_button.setStyleSheet(
            'QPushButton {'
            'font: 11pt "Noto";'
            'color: #f0f0f0;'
            'background: #7a2d2d;'
            'border: 1px solid #d16969;'
            'border-radius: 8px;'
            'padding: 6px 12px;'
            '}'
            'QPushButton:pressed { background: #5f2323; }'
        )
        gremlin_toolbar_layout.addWidget(clear_plot_button)

        gremlin_layout.addWidget(gremlin_toolbar)

        self.gremlin = GremlinWidget(self.runtime_store, gremlin_container)
        gremlin_layout.addWidget(self.gremlin)
        splitter.addWidget(gremlin_container)

        splitter.addWidget(GCodeEditorPane(
            self.bridge,
            'gremlin',
            self.runtime_store,
            self.call_stack_resolver,
            splitter,
        ))

        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        return container

    def _buildProgramActions(self):
        container = QWidget(self)
        container.setFixedHeight(200)
        container.setStyleSheet('background: #252526; border-top: 1px solid #404040;')

        layout = QHBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        start_button = ActionButton(container)
        start_button.setText('Start Program')
        start_button.actionName = 'program.run'
        start_button.setMinimumHeight(64)
        start_button.setMinimumWidth(180)
        start_button.setStyleSheet(
            'QPushButton {'
            'font: 15pt "Noto";'
            'color: #f0f0f0;'
            'background: #0e639c;'
            'border: 2px solid #3794ff;'
            'border-radius: 10px;'
            'padding: 10px 18px;'
            '}'
            'QPushButton:pressed { background: #005a9e; }'
            'QPushButton:disabled { color: #808080; background: #3a3a3a; border-color: #555555; }'
        )
        layout.addWidget(start_button)

        stop_button = ActionButton(container)
        stop_button.setText('Stop Program')
        stop_button.actionName = 'program.abort'
        stop_button.setMinimumHeight(64)
        stop_button.setMinimumWidth(180)
        stop_button.setStyleSheet(
            'QPushButton {'
            'font: 15pt "Noto";'
            'color: #f0f0f0;'
            'background: #7a2d2d;'
            'border: 2px solid #d16969;'
            'border-radius: 10px;'
            'padding: 10px 18px;'
            '}'
            'QPushButton:pressed { background: #5f2323; }'
            'QPushButton:disabled { color: #808080; background: #3a3a3a; border-color: #555555; }'
        )
        layout.addWidget(stop_button)

        self.pause_resume_button = QPushButton('Pause Program', container)
        self.pause_resume_button.setMinimumHeight(64)
        self.pause_resume_button.setMinimumWidth(200)
        self.pause_resume_button.clicked.connect(self._togglePauseResume)
        self.pause_resume_button.setStyleSheet(
            'QPushButton {'
            'font: 15pt "Noto";'
            'color: #f0f0f0;'
            'background: #6b5d12;'
            'border: 2px solid #d7ba7d;'
            'border-radius: 10px;'
            'padding: 10px 18px;'
            '}'
            'QPushButton:pressed { background: #54480e; }'
            'QPushButton:disabled { color: #808080; background: #3a3a3a; border-color: #555555; }'
        )
        layout.addWidget(self.pause_resume_button)

        optional_stop_button = ActionButton(container)
        optional_stop_button.setText('Break on M1')
        optional_stop_button.actionName = 'program.optional-stop.toggle'
        optional_stop_button.setCheckable(True)
        optional_stop_button.setMinimumHeight(64)
        optional_stop_button.setMinimumWidth(180)
        optional_stop_button.setStyleSheet(
            'QPushButton {'
            'font: 14pt "Noto";'
            'color: #f0f0f0;'
            'background: #3a3a3a;'
            'border: 2px solid #6a6a6a;'
            'border-radius: 10px;'
            'padding: 10px 18px;'
            '}'
            'QPushButton:checked {'
            'background: #1f6f43;'
            'border-color: #3fb950;'
            '}'
            'QPushButton:pressed { background: #4a4a4a; }'
            'QPushButton:checked:pressed { background: #185735; }'
            'QPushButton:disabled { color: #808080; background: #3a3a3a; border-color: #555555; }'
        )
        layout.addWidget(optional_stop_button)

        block_delete_button = ActionButton(container)
        block_delete_button.setText('Skip "/" Blocks')
        block_delete_button.actionName = 'program.block-delete.toggle'
        block_delete_button.setCheckable(True)
        block_delete_button.setMinimumHeight(64)
        block_delete_button.setMinimumWidth(180)
        block_delete_button.setStyleSheet(
            'QPushButton {'
            'font: 14pt "Noto";'
            'color: #f0f0f0;'
            'background: #3a3a3a;'
            'border: 2px solid #6a6a6a;'
            'border-radius: 10px;'
            'padding: 10px 18px;'
            '}'
            'QPushButton:checked {'
            'background: #1f6f43;'
            'border-color: #3fb950;'
            '}'
            'QPushButton:pressed { background: #4a4a4a; }'
            'QPushButton:checked:pressed { background: #185735; }'
            'QPushButton:disabled { color: #808080; background: #3a3a3a; border-color: #555555; }'
        )
        layout.addWidget(block_delete_button)

        mdi_label = QLabel('MDI', container)
        mdi_label.setStyleSheet('color: #d4d4d4; font: 13pt "Noto";')
        layout.addWidget(mdi_label)

        self.mdi_entry = MDIEntry(container)
        self.mdi_entry.setObjectName('programs_qml_mdi_entry')
        self.mdi_entry.setPlaceholderText('MDI command')
        self.mdi_entry.setMinimumHeight(52)
        self.mdi_entry.setMinimumWidth(200)
        self.mdi_entry.setMaximumWidth(220)
        self.mdi_entry.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.mdi_entry.setStyleSheet(
            'QLineEdit {'
            'font: 14pt "JetBrains Mono";'
            'color: #f0f0f0;'
            'background: #1e1e1e;'
            'border: 2px solid #5a5a5a;'
            'border-radius: 8px;'
            'padding: 6px 10px;'
            '}'
            'QLineEdit:focus { border-color: #3794ff; }'
        )
        self.mdi_entry.initialize()
        layout.addWidget(self.mdi_entry)

        layout.addStretch(1)

        self.mdi_button = QPushButton('Run MDI', container)
        self.mdi_button.setMinimumHeight(52)
        self.mdi_button.setMinimumWidth(160)
        self.mdi_button.clicked.connect(self.mdi_entry.submit)
        self.mdi_button.setStyleSheet(
            'QPushButton {'
            'font: 14pt "Noto";'
            'color: #f0f0f0;'
            'background: #2d7d46;'
            'border: 2px solid #3fb950;'
            'border-radius: 8px;'
            'padding: 10px 18px;'
            '}'
            'QPushButton:pressed { background: #236437; }'
            'QPushButton:disabled { color: #808080; background: #3a3a3a; border-color: #555555; }'
        )
        layout.addWidget(self.mdi_button)

        return container

    def _prepareGremlinForLoad(self, path):
        self._pending_fit_path = os.path.abspath(path) if path else ''
        if hasattr(self, 'gremlin'):
            self.gremlin.clearLivePlot()
            self.gremlin.update()

    def _fitGremlinToWindow(self):
        if not hasattr(self, 'gremlin'):
            return
        self.gremlin.setViewXZ2()
        self.gremlin.update()

    def _zoomGremlinIn(self):
        if hasattr(self, 'gremlin'):
            self.gremlin.zoomIn()
            self.gremlin.update()

    def _zoomGremlinOut(self):
        if hasattr(self, 'gremlin'):
            self.gremlin.zoomOut()
            self.gremlin.update()

    def _clearGremlinPlot(self):
        if hasattr(self, 'gremlin'):
            self.gremlin.clearLivePlot()
            self.gremlin.update()

    def _onMachineFileChanged(self, path):
        machine_path = os.path.abspath(path) if path else ''
        if not machine_path:
            return
        if self._pending_fit_path and machine_path != self._pending_fit_path:
            return
        QTimer.singleShot(150, self._fitGremlinToWindow)
        self._pending_fit_path = ''

    def _onCallLevelChanged(self, _call_level):
        QTimer.singleShot(0, self._fitGremlinToWindow)

    def _togglePauseResume(self):
        snapshot = self.runtime_store.snapshot
        if snapshot.state == linuxcnc.RCS_EXEC and snapshot.paused:
            program_actions.resume()
        else:
            program_actions.pause()

    def _updatePauseResumeButton(self, snapshot=None):
        if not hasattr(self, 'pause_resume_button'):
            return

        snapshot = snapshot or self.runtime_store.snapshot
        is_paused = bool(snapshot.paused)
        is_running = snapshot.state == linuxcnc.RCS_EXEC

        if is_paused:
            self.pause_resume_button.setText('Resume Program')
            self.pause_resume_button.setEnabled(True)
        elif is_running:
            self.pause_resume_button.setText('Pause Program')
            self.pause_resume_button.setEnabled(True)
        else:
            self.pause_resume_button.setText('Pause Program')
            self.pause_resume_button.setEnabled(False)

    def _setScreen(self, index):
        self.stack.setCurrentIndex(index)
        if index == 1 and hasattr(self, 'gremlin'):
            self.gremlin.show()
            self.gremlin.update()
