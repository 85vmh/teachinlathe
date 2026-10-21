"""The application window: one QML scene, and what it is built from.

A single QQuickView loads AppRoot.qml, every screen is an item in that one
scene, and the backplot renders into the scene graph through
LatheBackplotItem. What this file does is compose: build the view models QML
binds to, publish them, load the scene and connect the tabs to each other.
The machine itself is behind the view models, in each feature's use case.
"""

import logging
import os

from PyQt6.QtCore import QObject, Qt, QUrl
from PyQt6.QtGui import QColor
from PyQt6.QtQml import qmlRegisterSingletonInstance
from PyQt6.QtQuick import QQuickView

from teachinlathe.app.application import Application
from teachinlathe.app.app_state import AppState
from teachinlathe.app.app_identity import APPLICATION_DISPLAY_NAME
from teachinlathe.app.dev_panel import DevPanelWindow
from teachinlathe.app.touch_feedback import TouchFeedback
from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.app.app_shell_qml import AppShellBridge
from teachinlathe.ui.tabs.programs.backplot import register_qml_types as register_backplot_type
from teachinlathe.ui.tabs.conversational.ConversationalViewModel import ConversationalViewModel
from teachinlathe.ui.tabs.machine_settings.FixturesViewModel import FixturesViewModel
from teachinlathe.ui.tabs.machine_settings.MachineViewModel import MachineViewModel
from teachinlathe.ui.tabs.manual_turning.ManualTabViewModel import ManualTabViewModel
from teachinlathe.ui.common.touchable_input.numpad_dialog_viewmodel import NumpadDialogViewModel
from teachinlathe.app import APP_QML_IMPORT_DIR
from teachinlathe.ui import QML_IMPORT_DIR
from teachinlathe.ui.tabs.programs.ProgramsViewModel import ProgramsViewModel
from teachinlathe.ui.tabs.tool_library.ToolsTabViewModel import ToolsTabViewModel

LOG = logging.getLogger(__name__)

QML_DIR = os.path.dirname(os.path.abspath(__file__))

#: The QML module the view models are singletons of.
QML_MODULE = "TeachInLathe"


class AppWindow(QObject):
    """Owns the QML scene and everything behind it."""

    def __init__(self, application: Application, parent=None):
        super().__init__(parent)
        self.application = application

        self.appRoot = None
        self.devPanelWindow = None

        self.appState = AppState(self)
        self.fixture_repository = application.fixtures
        self.latheComponent = application.hal

        # The view exists first: the view models register themselves on its
        # engine's root context as they are built.
        self._createView()
        self._buildViewModels()
        self._registerSingletons()
        self._loadScene()
        self._connectScreens()

        self.latheComponent.comp.addListener(TeachInLatheComponent.PinDevMode, self.onDevModeChanged)
        self.onDevModeChanged(self.latheComponent.comp.getPin(TeachInLatheComponent.PinDevMode).value)

        initial_fixture = self.fixture_repository.getCurrentFixture()
        if initial_fixture:
            LOG.info("initial fixture: %s", initial_fixture.description)
            self.onChuckLimitChanged(initial_fixture.z_minus_limit)

    # ── construction ────────────────────────────────────────────────────────

    def _buildViewModels(self):
        """Everything QML binds to, built before the scene is loaded."""
        # First: the tabs are handed it, for full screen, toasts and tab switches.
        self.appShellBridge = AppShellBridge(self.appState, parent=self)

        self.manualTabViewModel = ManualTabViewModel(self)
        self.toolsTabViewModel = ToolsTabViewModel(self.appShellBridge, self)
        # The numpad the Manual and Tool Library screens open: it remembers
        # the last value entered for each setting.
        self.numpadDialogViewModel = NumpadDialogViewModel(self)

        self.machineViewModel = MachineViewModel(self)
        self.fixturesViewModel = FixturesViewModel(self)
        self.fixturesViewModel.chuckLimitChanged.connect(self.onChuckLimitChanged)

        self.programsViewModel = ProgramsViewModel(self.appShellBridge, self.appState.navigationStore, self)
        self.conversationalViewModel = ConversationalViewModel(self.appShellBridge, self)

        # The two tabs hand programs to each other.
        self.conversationalViewModel.gcodeGenerated.connect(self.showGeneratedProgram)
        self.programsViewModel.editConversationalProgramRequested.connect(
            self.editConversationalProgramFromJson)

        for tab_id, controller in (
            ("manual", self.manualTabViewModel),
            ("tools", self.toolsTabViewModel),
            ("conversational", self.conversationalViewModel),
            ("programs", self.programsViewModel),
        ):
            self.appShellBridge.addFeatureController(tab_id, controller)

    def _createView(self):
        register_backplot_type()

        self.view = QQuickView()
        self.view.setTitle(APPLICATION_DISPLAY_NAME)
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.view.setColor(QColor("#efefef"))
        self.view.setFlag(Qt.WindowType.FramelessWindowHint)
        self.touchFeedback = TouchFeedback(self.view, parent=self)

        # Every QML directory is a module named after its path from one of
        # these - `import theme`, `import tabs.conversational`,
        # `import app_shell_qml` - whatever directory the importing file is in.
        self.view.engine().addImportPath(QML_IMPORT_DIR)
        self.view.engine().addImportPath(APP_QML_IMPORT_DIR)

    def _registerSingletons(self):
        """What the screens bind to, as singletons of the TeachInLathe module:
        `import TeachInLathe`, then `ProgramsViewModel.running`, say."""
        for name, instance in (
            ("TouchFeedback", self.touchFeedback),
            ("NavigationStore", self.appState.navigationStore),
            ("AppShellBridge", self.appShellBridge),
            ("ManualTabViewModel", self.manualTabViewModel),
            ("ToolsTabViewModel", self.toolsTabViewModel),
            ("ConversationalViewModel", self.conversationalViewModel),
            ("ProgramsViewModel", self.programsViewModel),
            ("MachineViewModel", self.machineViewModel),
            ("FixturesViewModel", self.fixturesViewModel),
            # Used by more than one tab: the numpad the Manual and Tool Library
            # screens open, and the machine's position for the Teach buttons.
            ("NumpadDialogViewModel", self.numpadDialogViewModel),
            ("PositionsBridge", self.conversationalViewModel.positionsBridge),
        ):
            qmlRegisterSingletonInstance(QML_MODULE, 1, 0, name, instance)

    def _loadScene(self):
        self.view.setSource(QUrl.fromLocalFile(os.path.join(QML_DIR, "AppRoot.qml")))
        for error in self.view.errors():
            LOG.error("QML error: %s", error.toString())

        self.appRoot = self.view.rootObject()
        if self.appRoot is None:
            raise RuntimeError("AppRoot.qml failed to load")

    def _connectScreens(self):
        # QML follows navigationStore; this is what else has to follow it.
        self.appState.navigationStore.currentTabChanged.connect(self.onMainTabChanged)
        self.onMainTabChanged()

    # ── window ──────────────────────────────────────────────────────────────

    def showMaximized(self):
        self.view.showMaximized()

    def showFullScreen(self):
        self.view.showFullScreen()

    def close(self):
        self.view.close()

    def onChuckLimitChanged(self, z_minus_limit):
        self.manualTabViewModel.dro.setChuckLimit(float(z_minus_limit))

    def onMainTabChanged(self):
        """The active tab changed - QML follows navigationStore, this is what
        has to happen on the machine side when it does."""
        tab_id = self.appState.navigationStore.currentTab or "manual"
        self.manualTabViewModel.dro.limitsHandler.setChuckLimitsActive(tab_id != "settings")
        self.appState.cncStore.addEvent("INFO", "navigation", f"Switched to {tab_id}")

    def showGeneratedProgram(self, ngc_path: str):
        if not ngc_path:
            return
        try:
            self.appState.activateTab("programs")
            self.programsViewModel.showFileInGeneratedPrograms(ngc_path)
        except Exception as e:
            LOG.error("showGeneratedProgram failed: %s", e)

    def editConversationalProgramFromJson(self, json_path: str):
        if not json_path or not os.path.isfile(json_path):
            return
        try:
            self.appState.activateTab("conversational")
            self.conversationalViewModel.openProgramFile(os.path.abspath(json_path))
        except Exception as e:
            LOG.error("editConversationalProgramFromJson failed: %s", e)

    def onDevModeChanged(self, value):
        if value:
            if self.devPanelWindow is None:
                self.devPanelWindow = DevPanelWindow(self)
            self.devPanelWindow.show()
            self.devPanelWindow.raise_()
            return
        if self.devPanelWindow is not None:
            self.devPanelWindow.hide()
