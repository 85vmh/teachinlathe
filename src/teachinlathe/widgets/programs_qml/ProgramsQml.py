import os

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget, QVBoxLayout, QStackedWidget, QSplitter
from PyQt5.QtQuickWidgets import QQuickWidget
from qtpyvcp.widgets.button_widgets.action_button import ActionButton
from qtpyvcp.widgets.input_widgets.mdientry_widget import MDIEntry

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
        """
        Parameters
        ----------
        folders : list of (name: str, path: str)
            Ordered pairs: display name → absolute folder path.
        """
        super().__init__(parent)

        self.bridge = FileSystemBridge(folders, self)
        self.bridge.screenChangeRequested.connect(self._setScreen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget(self)
        layout.addWidget(self.stack)

        self.stack.addWidget(self._buildFilesScreen())
        self.stack.addWidget(self._buildGremlinScreen())
        layout.addWidget(self._buildProgramActions())

    # ------------------------------------------------------------------
    # Screen builders
    # ------------------------------------------------------------------

    def _buildFilesScreen(self):
        """Screen 0: QML file browser (left) + native editor (right)."""
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

        splitter.addWidget(GCodeEditorPane(self.bridge, 'files', splitter))
        splitter.setSizes([320, 880])

        layout.addWidget(splitter)
        return container

    def _buildGremlinScreen(self):
        """Screen 1: GremlinWidget (left) + native editor (right)."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal, container)

        self.gremlin = GremlinWidget(splitter)
        splitter.addWidget(self.gremlin)

        splitter.addWidget(GCodeEditorPane(self.bridge, 'gremlin', splitter))

        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        return container

    def _buildProgramActions(self):
        container = QWidget(self)
        container.setFixedHeight(200)
        container.setStyleSheet('background: #252526; border-top: 1px solid #404040;')

        layout = QHBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(32)

        actions_column = QWidget(container)
        actions_layout = QVBoxLayout(actions_column)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(14)

        actions_title = QLabel('Program Controls', actions_column)
        actions_title.setStyleSheet('color: #d4d4d4; font: 14pt "Noto";')
        actions_layout.addWidget(actions_title)

        start_button = ActionButton(actions_column)
        start_button.setText('Start Program')
        start_button.actionName = 'program.run'
        start_button.setMinimumHeight(72)
        start_button.setMinimumWidth(220)
        start_button.setStyleSheet(
            'QPushButton {'
            'font: 16pt "Noto";'
            'color: #f0f0f0;'
            'background: #0e639c;'
            'border: 2px solid #3794ff;'
            'border-radius: 10px;'
            'padding: 12px 22px;'
            '}'
            'QPushButton:pressed { background: #005a9e; }'
            'QPushButton:disabled { color: #808080; background: #3a3a3a; border-color: #555555; }'
        )
        actions_layout.addWidget(start_button)

        stop_button = ActionButton(actions_column)
        stop_button.setText('Stop Program')
        stop_button.actionName = 'program.abort'
        stop_button.setMinimumHeight(72)
        stop_button.setMinimumWidth(220)
        stop_button.setStyleSheet(
            'QPushButton {'
            'font: 16pt "Noto";'
            'color: #f0f0f0;'
            'background: #7a2d2d;'
            'border: 2px solid #d16969;'
            'border-radius: 10px;'
            'padding: 12px 22px;'
            '}'
            'QPushButton:pressed { background: #5f2323; }'
            'QPushButton:disabled { color: #808080; background: #3a3a3a; border-color: #555555; }'
        )
        actions_layout.addWidget(stop_button)
        actions_layout.addStretch(1)
        layout.addWidget(actions_column, 0)

        mdi_column = QWidget(container)
        mdi_layout = QVBoxLayout(mdi_column)
        mdi_layout.setContentsMargins(0, 0, 0, 0)
        mdi_layout.setSpacing(14)

        mdi_title = QLabel('MDI Command', mdi_column)
        mdi_title.setStyleSheet('color: #d4d4d4; font: 14pt "Noto";')
        mdi_layout.addWidget(mdi_title)

        self.mdi_entry = MDIEntry(mdi_column)
        self.mdi_entry.setObjectName('programs_qml_mdi_entry')
        self.mdi_entry.setPlaceholderText('Enter MDI command, then press Enter')
        self.mdi_entry.setMinimumHeight(56)
        self.mdi_entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.mdi_entry.setStyleSheet(
            'QLineEdit {'
            'font: 15pt "JetBrains Mono";'
            'color: #f0f0f0;'
            'background: #1e1e1e;'
            'border: 2px solid #5a5a5a;'
            'border-radius: 8px;'
            'padding: 8px 12px;'
            '}'
            'QLineEdit:focus { border-color: #3794ff; }'
        )
        self.mdi_entry.initialize()
        mdi_layout.addWidget(self.mdi_entry)

        mdi_button = QPushButton('Run MDI', mdi_column)
        mdi_button.setMinimumHeight(56)
        mdi_button.setMinimumWidth(180)
        mdi_button.clicked.connect(self.mdi_entry.submit)
        mdi_button.setStyleSheet(
            'QPushButton {'
            'font: 14pt "Noto";'
            'color: #f0f0f0;'
            'background: #2d7d46;'
            'border: 2px solid #3fb950;'
            'border-radius: 8px;'
            'padding: 10px 20px;'
            '}'
            'QPushButton:pressed { background: #236437; }'
        )
        mdi_layout.addWidget(mdi_button)
        mdi_layout.addStretch(1)
        layout.addWidget(mdi_column, 1)

        layout.addStretch(1)
        return container

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _setScreen(self, index):
        self.stack.setCurrentIndex(index)
        if index == 1 and hasattr(self, 'gremlin'):
            self.gremlin.show()
            self.gremlin.update()
