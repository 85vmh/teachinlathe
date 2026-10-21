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
from PyQt6.QtQuick import QQuickItem, QQuickView

from teachinlathe.app.application import Application
from teachinlathe.app.app_state import AppState
from teachinlathe.app.app_identity import APPLICATION_DISPLAY_NAME
from teachinlathe.app.dev_panel import DevPanelWindow
from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.manual.logic.manual_turning_use_case import ManualTurningUseCase
from teachinlathe.app.app_shell_qml import AppShellBridge
from teachinlathe.ui.tabs.programs.backplot import register_qml_types as register_backplot_type
from teachinlathe.ui.tabs.conversational.ConversationalQml import ConversationalQml
from teachinlathe.ui.tabs.machine_settings.FixturesViewModel import FixturesViewModel
from teachinlathe.ui.tabs.machine_settings.MachineViewModel import MachineViewModel
from teachinlathe.ui.tabs.manual_turning import ManualTurningViewModel
from teachinlathe.ui.tabs.manual_turning.TeachInLatheDroViewModel import TeachInLatheDroViewModel
from teachinlathe.ui.common.touchable_input.numpad_dialog_viewmodel import NumpadDialogViewModel
from teachinlathe.ui import QML_IMPORT_DIR
from teachinlathe.ui.tabs.programs.ProgramsController import ProgramsController
from teachinlathe.ui.tabs.tool_library.ManualToolsViewModel import ManualToolsViewModel
from teachinlathe.ui.tabs.tool_library.ToolsTabViewModel import ToolsTabViewModel

LOG = logging.getLogger(__name__)

QML_DIR = os.path.dirname(os.path.abspath(__file__))


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
        self._publishContext()
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

        self.manualTurningUseCase = ManualTurningUseCase(
            self.application.hal, self.application.status, self)
        self.manualTurningViewModel = ManualTurningViewModel(self.manualTurningUseCase, self)
        self.teachInLatheDroViewModel = TeachInLatheDroViewModel(self, self.application.tool_library)
        tool_library = self.application.tool_library
        self.toolsTabViewModel = ToolsTabViewModel(tool_library, self)
        self.toolsTabViewModel.toastRequested.connect(self.appShellBridge.showToast)
        self.manualToolsViewModel = ManualToolsViewModel(tool_library, self, self.application.hal)
        self.numpadDialogViewModel = NumpadDialogViewModel(self)

        self.machineViewModel = MachineViewModel(self)
        self.fixturesViewModel = FixturesViewModel(self)
        self.fixturesViewModel.chuckLimitChanged.connect(self.onChuckLimitChanged)

        self.programsController = ProgramsController(
            self.appShellBridge, self.appState.navigationStore, self)
        self.conversationalqml = ConversationalQml(self.view.engine(), self.appShellBridge, self)
        self.conversationalqml.setAppState(self.appState)

        # The two tabs hand programs to each other.
        self.conversationalqml.gcodeGenerated.connect(self.showGeneratedProgram)
        self.programsController.editConversationalProgramRequested.connect(
            self.editConversationalProgramFromJson)

        for tab_id, controller in (
            ("manual", self.manualToolsViewModel),
            ("tools", self.toolsTabViewModel),
            ("conversational", self.conversationalqml),
            ("programs", self.programsController),
        ):
            self.appShellBridge.addFeatureController(tab_id, controller)

    def _createView(self):
        register_backplot_type()

        self.view = QQuickView()
        self.view.setTitle(APPLICATION_DISPLAY_NAME)
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.view.setColor(QColor("#efefef"))
        self.view.setFlag(Qt.WindowType.FramelessWindowHint)

        # So every screen can say `import theme 1.0` whatever directory it is
        # in, rather than counting ".." back to it.
        self.view.engine().addImportPath(QML_IMPORT_DIR)

    def _publishContext(self):
        ctx = self.view.engine().rootContext()
        ctx.setContextProperty("appState", self.appState)
        ctx.setContextProperty("cncStore", self.appState.cncStore)
        ctx.setContextProperty("navigationStore", self.appState.navigationStore)
        ctx.setContextProperty("appShellBridge", self.appShellBridge)

        ctx.setContextProperty("manualViewModel", self.manualTurningViewModel)
        ctx.setContextProperty("numpadDialogViewModel", self.numpadDialogViewModel)
        ctx.setContextProperty("teachInDroViewModel", self.teachInLatheDroViewModel)
        ctx.setContextProperty("manualToolsViewModel", self.manualToolsViewModel)
        ctx.setContextProperty("toolsTabViewModel", self.toolsTabViewModel)

        ctx.setContextProperty("machineViewModel", self.machineViewModel)
        ctx.setContextProperty("fixturesViewModel", self.fixturesViewModel)

        ctx.setContextProperty("programsViewModel", self.programsController.viewmodel)
        ctx.setContextProperty("fsViewModel", self.programsController.fs_viewmodel)
        ctx.setContextProperty("programsDroViewModel", self.programsController.dro_viewmodel)
        ctx.setContextProperty("programsToolFeedSpeedViewModel", self.programsController.tool_feed_speed_viewmodel)
        ctx.setContextProperty("ProgramsScreen", self.programsController.programs_screen_enum)

    def _loadScene(self):
        self.view.setSource(QUrl.fromLocalFile(os.path.join(QML_DIR, "AppRoot.qml")))
        for error in self.view.errors():
            LOG.error("QML error: %s", error.toString())

        self.appRoot = self.view.rootObject()
        if self.appRoot is None:
            raise RuntimeError("AppRoot.qml failed to load")

    def _screen(self, object_name):
        item = self.appRoot.findChild(QQuickItem, object_name)
        if item is None:
            LOG.error("QML item %r not found", object_name)
        return item

    def _connectScreens(self):
        conversational_root = self._screen("conversationalScreen")
        if conversational_root is not None:
            self.conversationalqml.attachRoot(conversational_root)

        self.programsController.attachBackplot(self._screen("latheBackplot"))

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
        self.teachInLatheDroViewModel.setChuckLimit(float(z_minus_limit))

    def onMainTabChanged(self):
        """The active tab changed - QML follows navigationStore, this is what
        has to happen on the machine side when it does."""
        tab_id = self.appState.navigationStore.currentTab or "manual"
        self.teachInLatheDroViewModel.limitsHandler.setChuckLimitsActive(tab_id != "settings")
        self.appState.cncStore.addEvent("INFO", "navigation", f"Switched to {tab_id}")

    def showGeneratedProgram(self, ngc_path: str):
        if not ngc_path:
            return
        try:
            self.appState.activateTab("programs")
            self.programsController.showFileInGeneratedPrograms(ngc_path)
        except Exception as e:
            LOG.error("showGeneratedProgram failed: %s", e)

    def editConversationalProgramFromJson(self, json_path: str):
        if not json_path or not os.path.isfile(json_path):
            return
        try:
            self.appState.activateTab("conversational")
            self.conversationalqml.openProgramFile(os.path.abspath(json_path))
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
