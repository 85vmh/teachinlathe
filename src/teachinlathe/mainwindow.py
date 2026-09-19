"""The application: one QML scene, and the machine wiring behind it.

There used to be a QMainWindow here holding a QStackedWidget of two pages, the
second holding another QStackedWidget of four QWidget tabs, each wrapping a
QQuickWidget with an engine of its own - plus a Gremlin QOpenGLWidget that had
to be positioned over a placeholder by hand. Every screen was already QML; the
widgets existed only to carry them.

They are gone. A single QQuickView loads AppRoot.qml, every screen is an item
in that one scene, and the backplot renders into the scene graph through
LatheBackplotItem. What is left in this file is what it was always for: the
view models, and the HAL pins wired to them.
"""

import logging
import os
from enum import Enum

import linuxcnc
from PyQt6.QtCore import (Q_ARG, QMetaObject, QObject, Qt, QTimer, QUrl,
                          pyqtProperty, pyqtSignal, pyqtSlot)
from PyQt6.QtGui import QColor
from PyQt6.QtQuick import QQuickItem, QQuickView

from teachinlathe.repositories.command_repository import issue_mdi
from teachinlathe.repositories.machine_repository import machine_repository
from teachinlathe.repositories.status_repository import status_repository
from teachinlathe.repositories import ini_repository

from teachinlathe.app_state import AppState
from teachinlathe.app_identity import APPLICATION_DISPLAY_NAME
from teachinlathe.dev_panel import DevPanelWindow
from teachinlathe.fixtures import LatheFixturesRepository
from teachinlathe.repositories.lathe_hal_component import TeachInLatheComponent
from teachinlathe.manual_lathe import ManualLathe
from teachinlathe.widgets.app_shell_qml import AppShellBridge
from teachinlathe.widgets.backplot import register_qml_types as register_backplot_type
from teachinlathe.widgets.conversational_qml.ConversationalQml import ConversationalQml
from teachinlathe.widgets.machine_qml.FixturesViewModel import FixturesViewModel
from teachinlathe.widgets.machine_qml.MachineViewModel import MachineViewModel
from teachinlathe.widgets.manual_qml import ManualTurningViewModel
from teachinlathe.widgets.manual_qml.TeachInLatheDroViewModel import TeachInLatheDroViewModel
from teachinlathe.widgets.touchable_input.numpad_dialog_viewmodel import NumpadDialogViewModel
from teachinlathe.widgets.programs_qml.ProgramsController import ProgramsController
from teachinlathe.widgets.tool_library.ToolLibraryViewModel import ToolLibraryViewModel

LOG = logging.getLogger(__name__)

INI = ini_repository()
STATUS = status_repository()
MACHINE = machine_repository()
LINUXCNC_CMD = linuxcnc.command()
STAT = linuxcnc.stat()
PROGRAM_PREFIX = INI.program_prefix
# Base folder for conversational outputs (user-configurable).
CONVERSATIONAL_OUTPUT_BASE = PROGRAM_PREFIX
CONVERSATIONAL_GCODE_BASE = CONVERSATIONAL_OUTPUT_BASE
CONVERSATIONAL_JSON_BASE = CONVERSATIONAL_OUTPUT_BASE

QML_DIR = os.path.join(os.path.dirname(__file__), "widgets")


class MainTabs(Enum):
    """Pages of the app content stack, in the order the shell lists them.

    There is no tools page: the shell's bottom bar offers four tabs, and the
    tool library lives inside the manual screen.
    """

    MANUAL_TURNING = 0
    CONVERSATIONAL = 1
    PROGRAMS = 2
    MACHINE_SETTINGS = 3


# The tab ids QML and AppState use, against this enum. AppRoot.qml holds the
# same order; it is the one place the two have to agree.
TAB_IDS = {
    "manual": MainTabs.MANUAL_TURNING,
    "conversational": MainTabs.CONVERSATIONAL,
    "programs": MainTabs.PROGRAMS,
    "settings": MainTabs.MACHINE_SETTINGS,
}


class ProgramTabs(Enum):
    FILE_SYSTEM = 0
    PROGRAM_LOADED = 1


class NumpadValueField(QObject):
    """Adapter that lets the QML SmartNumpadDialog drive a one-shot value
    callback (e.g. touch-off X/Z) using the same API as a QML NumpadField:
    the dialog reads ``settingName``/``description`` and calls ``commit(value)``.
    """

    def __init__(self, setting_name, description, on_commit, parent=None):
        super().__init__(parent)
        self._setting_name = setting_name
        self._description = description
        self._on_commit = on_commit

    @pyqtProperty(str, constant=True)
    def settingName(self):
        return self._setting_name

    @pyqtProperty(str, constant=True)
    def description(self):
        return self._description

    @pyqtSlot('QVariant')
    def commit(self, value):
        self._on_commit(value)

    @pyqtSlot()
    def defocus(self):
        pass


class ManualJoystickController(QObject):
    angleFeedToggled = pyqtSignal(bool)

    def __init__(self, viewmodel=None, parent=None):
        super().__init__(parent)
        self._root = None
        self._viewmodel = viewmodel

    def attach(self, root):
        self._root = root

    def setViewModel(self, viewmodel):
        self._viewmodel = viewmodel

    @pyqtSlot(bool)
    def handleAngleFeedToggled(self, enabled):
        if self._viewmodel is not None:
            self._viewmodel.setAngleFeedActive(bool(enabled))
            return
        self.angleFeedToggled.emit(bool(enabled))

    def resetAngle(self):
        if self._viewmodel is not None:
            self._viewmodel.resetAngleFeed()

    def isRotated(self):
        if self._viewmodel is not None:
            return bool(self._viewmodel.isAngleFeedActive())
        return False

    def setRapid(self, enabled: bool):
        if self._viewmodel is not None:
            self._viewmodel.setJoystickRapid(bool(enabled))

    def setJoystickState(self, state):
        if self._viewmodel is not None:
            self._viewmodel.setJoystickState(state)


class TeachInLatheApp(QObject):
    """Owns the QML scene and everything behind it."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.mainSelectedTab = MainTabs.MANUAL_TURNING
        self.lastSpindleRpm = 0
        self.isFirstGear = False
        self.xMpgLastValue = True
        self.zMpgLastValue = True
        self.current_spindle_override = 0
        self.current_feed_override = 0
        self.current_program = None
        self._fullscreen = False
        self.appRoot = None
        self.manualScreen = None
        self.devPanelWindow = None

        self.appState = AppState(self)
        self.fixture_repository = LatheFixturesRepository()
        self.manualLathe = ManualLathe()
        self.latheComponent = TeachInLatheComponent()

        # The view exists first: the view models register themselves on its
        # engine's root context as they are built.
        self._createView()
        self._buildViewModels()
        self._publishContext()
        self._loadScene()
        self._connectScreens()
        self._wireHalPins()
        self._wireStatus()

        initial_fixture = self.fixture_repository.getCurrentFixture()
        if initial_fixture:
            LOG.info("initial fixture: %s", initial_fixture.description)
            self.onChuckLimitChanged(initial_fixture.z_minus_limit)

        self.afterUIInit()

    # ── construction ────────────────────────────────────────────────────────

    def _buildViewModels(self):
        """Everything QML binds to.

        All of it exists before the scene is loaded now. It used to be spread
        over half a dozen QTimer.singleShot(0, ...) callbacks, because each
        screen had a QQuickWidget that had to be created, parented and shown
        in the right order.
        """
        self.manualTurningViewModel = ManualTurningViewModel(self.manualLathe, self)
        self.teachInLatheDroViewModel = TeachInLatheDroViewModel(self)
        self.toolLibraryViewModel = ToolLibraryViewModel(self)
        self.numpadDialogViewModel = NumpadDialogViewModel(self)

        self.manualJoystickController = ManualJoystickController(self.manualTurningViewModel, self)
        self.latheJoystick = self.manualJoystickController
        self.manualLathe.setJoystickWidget(self.manualJoystickController)
        self.manualTurningViewModel.joystickStateChanged.connect(
            self._on_manual_joystick_state_changed)

        self.machineViewModel = MachineViewModel(self)
        self.fixturesViewModel = FixturesViewModel(self)
        self.fixturesViewModel.chuckLimitChanged.connect(self.onChuckLimitChanged)

        self.programsController = self._buildProgramsController()
        self.conversationalqml = ConversationalQml(self.view.engine(), self, self)
        self.conversationalqml.setAppState(self.appState)

        self.appShellBridge = AppShellBridge(
            self.appState,
            {
                "conversational": self.conversationalqml,
                "programs": self.programsController,
            },
            self,
        )

    def _buildProgramsController(self):
        from teachinlathe.widgets.programs_qml.filesystemview import (
            FileSystemLocation, LocationType,
        )
        gcode_folder = os.path.join(CONVERSATIONAL_GCODE_BASE, "Conversational Gcode")
        json_folder = os.path.join(CONVERSATIONAL_JSON_BASE, "Conversational Json")
        usb_stick_folder = os.path.join(CONVERSATIONAL_GCODE_BASE, "USB Stick Programs")
        locations = [
            FileSystemLocation("Generated Programs", gcode_folder, LocationType.GENERATED),
            FileSystemLocation("USB Stick Programs", usb_stick_folder, LocationType.USB_STICK),
            FileSystemLocation("SyncThing Programs", os.path.expanduser("~/Sync"), LocationType.SYNCTHING),
            FileSystemLocation("Home", os.path.expanduser("~"), LocationType.HOME),
        ]
        controller = ProgramsController(locations, self, self, json_folder_path=json_folder)
        controller.viewmodel.programLoadRequested.connect(self.onProgramsQmlProgramLoadRequested)
        controller.viewmodel.ensureProgramLoadedRequested.connect(
            self.onProgramsQmlEnsureProgramLoadedRequested)
        controller.viewmodel.switchToManualRequested.connect(
            self.onProgramsQmlSwitchToManualRequested)
        # A failed file operation is reported the way the rest of the app
        # reports one: a toast, plus an entry in the events drawer.
        fs = controller.fs_viewmodel
        fs.deleteFailed.connect(lambda msg: self._show_app_toast("Delete failed: %s" % msg))
        fs.copyFailed.connect(lambda msg: self._show_app_toast("Copy failed: %s" % msg))
        return controller

    def _createView(self):
        register_backplot_type()

        self.view = QQuickView()
        self.view.setTitle(APPLICATION_DISPLAY_NAME)
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.view.setColor(QColor("#efefef"))
        self.view.setFlag(Qt.WindowType.FramelessWindowHint)

    def _publishContext(self):
        ctx = self.view.engine().rootContext()
        ctx.setContextProperty("appState", self.appState)
        ctx.setContextProperty("cncStore", self.appState.cncStore)
        ctx.setContextProperty("navigationStore", self.appState.navigationStore)
        ctx.setContextProperty("appShellBridge", self.appShellBridge)

        ctx.setContextProperty("manualViewModel", self.manualTurningViewModel)
        ctx.setContextProperty("numpadDialogViewModel", self.numpadDialogViewModel)
        ctx.setContextProperty("teachInDroViewModel", self.teachInLatheDroViewModel)
        ctx.setContextProperty("toolLibraryViewModel", self.toolLibraryViewModel)

        ctx.setContextProperty("machineViewModel", self.machineViewModel)
        ctx.setContextProperty("fixturesViewModel", self.fixturesViewModel)

        ctx.setContextProperty("programsViewModel", self.programsController.viewmodel)
        ctx.setContextProperty("fsViewModel", self.programsController.fs_viewmodel)
        ctx.setContextProperty("programsDroViewModel", self.programsController.dro_viewmodel)
        ctx.setContextProperty("programsToolFeedSpeedViewModel",
                               self.programsController.tool_feed_speed_viewmodel)
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
        self.manualScreen = self._screen("manualScreen")
        if self.manualScreen is not None:
            self.manualScreen.xToggled.connect(self.onManualQmlXHandwheelToggled)
            self.manualScreen.zToggled.connect(self.onManualQmlZHandwheelToggled)
            self.manualScreen.toastRequested.connect(self._show_app_toast)
            self.manualJoystickController.attach(self.manualScreen)

        settings_screen = self._screen("settingsScreen")
        if settings_screen is not None:
            settings_screen.setG28.connect(self.onSetG28)
            settings_screen.goToG28.connect(self.onGoToG28)
            settings_screen.setG30.connect(self.onSetG30)
            settings_screen.goToG30.connect(self.onGoToG30)

        conversational_root = self._screen("conversationalScreen")
        if conversational_root is not None:
            self.conversationalqml.attachRoot(conversational_root)

        self.programsController.attachBackplot(self._screen("latheBackplot"))

        self.teachInLatheDroViewModel.xPrimaryDroClicked.connect(self.onXPrimaryDroClicked)
        self.teachInLatheDroViewModel.zPrimaryDroClicked.connect(self.onZPrimaryDroClicked)

        # QML follows navigationStore; this is the machine-side half of it.
        self.appState.navigationStore.currentTabChanged.connect(self.onMainTabChanged)
        self.onMainTabChanged()

    # ── machine wiring ──────────────────────────────────────────────────────

    def _wireHalPins(self):
        comp = self.latheComponent.comp
        comp.addListener(TeachInLatheComponent.PinSpindleActualRpm, self.onSpindleRpmChanged)
        comp.addListener(TeachInLatheComponent.PinSpindleIsOn, self.onSpindleRunningChanged)
        comp.addListener(TeachInLatheComponent.PinSpindleCoveredOpened, self.onSpindleCoverOpenedChanged)
        comp.addListener(TeachInLatheComponent.PinSpindleResetRequired, self.onSpindleResetRequiredChanged)
        comp.addListener(TeachInLatheComponent.PinSpindleOrientation, self.onSpindleOrientationChanged)
        comp.addListener(TeachInLatheComponent.PinButtonCycleStart, self.onCycleStartPressed)
        comp.addListener(TeachInLatheComponent.PinButtonCycleStop, self.onCycleStopPressed)
        comp.addListener(TeachInLatheComponent.PinJoystickIsFeeding, self.onJoystickFeedingChanged)
        comp.addListener(TeachInLatheComponent.PinJoystickResetRequired, self.onJoystickResetRequiredChanged)
        comp.addListener(TeachInLatheComponent.PinHandwheelsJogIncrement, self.onJogIncrementChanged)
        comp.addListener(TeachInLatheComponent.PinSpindleIsFirstGear, self.onSpindleFirstGearChanged)
        comp.addListener(TeachInLatheComponent.PinHandwheelsAllowed, self.onHandwheelAllowedChanged)
        comp.addListener(TeachInLatheComponent.PinDevMode, self.onDevModeChanged)

        comp.getPin(TeachInLatheComponent.PinHandwheelsXEnable).value = True
        comp.getPin(TeachInLatheComponent.PinHandwheelsZEnable).value = True

        self.onSpindleFirstGearChanged(comp.getPin(TeachInLatheComponent.PinSpindleIsFirstGear).value)
        self.manualTurningViewModel.setSpindleRunning(
            comp.getPin(TeachInLatheComponent.PinSpindleIsOn).value)
        self.manualTurningViewModel.setSpindleCoverOpened(
            comp.getPin(TeachInLatheComponent.PinSpindleCoveredOpened).value)
        self.manualTurningViewModel.setSpindleResetRequired(
            comp.getPin(TeachInLatheComponent.PinSpindleResetRequired).value)
        self.manualTurningViewModel.setSpindleAngle(
            comp.getPin(TeachInLatheComponent.PinSpindleOrientation).value)
        self.manualTurningViewModel.setFeeding(
            comp.getPin(TeachInLatheComponent.PinJoystickIsFeeding).value)
        self.manualTurningViewModel.setJoystickResetRequired(
            comp.getPin(TeachInLatheComponent.PinJoystickResetRequired).value)
        self.onDevModeChanged(comp.getPin(TeachInLatheComponent.PinDevMode).value)

    def _wireStatus(self):
        # spindle override, initial value and updates
        self.onSpindleOverrideChanged(STATUS.spindle[0].override.value)
        STATUS.spindle[0].override.signal.connect(self.onSpindleOverrideChanged)

        # feed override, initial value and updates
        self.onFeedOverrideChanged(STATUS.feedrate.value)
        STATUS.feedrate.signal.connect(self.onFeedOverrideChanged)

        self.onTaskModeChanged(STATUS.task_mode)
        STATUS.task_mode.signal.connect(self.onTaskModeChanged)
        STATUS.state.signal.connect(self.onStateChanged)

        self.handle_spindle_mode(self.getSpindleModeIndex)

        # rpm is a float that fluctuates a lot, so debounce it
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.onRpmDebounced)
        self.debounce_timer.start()

    # ── window ──────────────────────────────────────────────────────────────

    def showMaximized(self):
        self.view.showMaximized()

    def showFullScreen(self):
        self.view.showFullScreen()

    def close(self):
        self.view.close()

    def getSpindleModeIndex(self):
        return self.manualTurningViewModel.spindleMode

    def afterUIInit(self):
        # set the current values
        self.manualLathe.onSpindleModeChanged(self.getSpindleModeIndex())
        self.manualLathe.onInputRpmChanged(self.manualTurningViewModel.inputRpm)
        self.manualLathe.onInputCssChanged(self.manualTurningViewModel.inputCss)
        self.manualLathe.onMaxSpindleRpmChanged(self.manualTurningViewModel.inputMaxRpm)
        self.manualLathe.onInputFeedChanged(self.manualTurningViewModel.inputFeed)
        self.manualTurningViewModel.setFeedOverride(self.current_feed_override)
        self.manualTurningViewModel.setSpindleOverride(self.current_spindle_override)
        self.manualTurningViewModel.setHandwheelStates(
            self.manualTurningViewModel.xHandwheelEnabled,
            self.manualTurningViewModel.zHandwheelEnabled)

    @pyqtSlot(str)
    def _show_app_toast(self, message):
        self.appShellBridge.showToast(message)

    def onChuckLimitChanged(self, z_minus_limit):
        self.teachInLatheDroViewModel.setChuckLimit(float(z_minus_limit))

    def onMainTabChanged(self):
        """The active tab changed - QML follows navigationStore, this is what
        has to happen on the HAL side when it does."""
        tab_id = self.appState.navigationStore.currentTab or "manual"
        self.mainSelectedTab = TAB_IDS.get(tab_id, MainTabs.MANUAL_TURNING)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsReadyToRunProgram).value = \
            self.mainSelectedTab == MainTabs.PROGRAMS
        self.teachInLatheDroViewModel.limitsHandler.setChuckLimitsActive(
            self.mainSelectedTab != MainTabs.MACHINE_SETTINGS)
        self.appState.cncStore.addEvent("INFO", "navigation", f"Switched to {tab_id}")

    def loadProgram(self):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = True

    def onProgramsQmlProgramLoadRequested(self, _path):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = True

    def onProgramsQmlEnsureProgramLoadedRequested(self):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = True

    def onProgramsQmlSwitchToManualRequested(self):
        self.appState.activateTab("manual")

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

    def onSpindleModeChanged(self):
        self.manualLathe.onSpindleModeChanged(self.getSpindleModeIndex())
        self.handle_spindle_mode(self.getSpindleModeIndex())

    def onCycleStartPressed(self):
        pass

    def onDevModeChanged(self, value):
        if value:
            if self.devPanelWindow is None:
                self.devPanelWindow = DevPanelWindow(self)
            self.devPanelWindow.show()
            self.devPanelWindow.raise_()
            return
        if self.devPanelWindow is not None:
            self.devPanelWindow.hide()

    def onCycleStopPressed(self, value):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = False
        if self.mainSelectedTab == MainTabs.MANUAL_TURNING:
            if self.latheJoystick.isRotated() and value:
                print("Set taper turning off when cycle stop pressed")
                self.manualTurningViewModel.resetAngleFeed()

    def angleFeedToggled(self, value):
        print("angleFeedToggled", value)
        self.manualTurningViewModel.setAngleFeedActive(bool(value))

    def _on_manual_joystick_state_changed(self):
        # Used to raise the manual QQuickWidget above its siblings; in one
        # scene there is nothing to raise.
        pass

    def onSpindleRunningChanged(self, value):
        print("onSpindleRunningChanged", value)
        self.manualTurningViewModel.setSpindleRunning(value)
        if self.latheJoystick.isRotated() and not value:
            print("Set taper turning off when stopping spindle")
            self.manualTurningViewModel.resetAngleFeed()

    def onSpindleCoverOpenedChanged(self, value):
        self.manualTurningViewModel.setSpindleCoverOpened(value)

    def onSpindleResetRequiredChanged(self, value):
        self.manualTurningViewModel.setSpindleResetRequired(value)

    def onSpindleOrientationChanged(self, value):
        self.manualTurningViewModel.setSpindleAngle(value)

    def onJoystickFeedingChanged(self, value):
        self.manualTurningViewModel.setFeeding(value)

    def onJoystickResetRequiredChanged(self, value):
        self.manualTurningViewModel.setJoystickResetRequired(value)

    def onJogIncrementChanged(self, value):
        self.manualTurningViewModel.setJogIncrement(value)

    def onSpindleFirstGearChanged(self, value):
        suffix = '1' if value else '2'
        self.manualTurningViewModel.setGearSuffix(suffix)

    def onSpindleRpmChanged(self, value):
        self.lastSpindleRpm = abs(int(value))

    def onRpmDebounced(self):
        self.manualTurningViewModel.setActualRpm(self.lastSpindleRpm)

    def handle_spindle_mode(self, index):
        self.manualTurningViewModel.setSpindleOverride(self.current_spindle_override)

    def update_actual_feed(self):
        self.manualTurningViewModel.setFeedOverride(self.current_feed_override)

    def onSpindleOverrideChanged(self, value):
        self.current_spindle_override = value
        self.handle_spindle_mode(self.getSpindleModeIndex())

    def onFeedOverrideChanged(self, value):
        self.current_feed_override = value
        self.update_actual_feed()

    def onTaskModeChanged(self, taskMode):
        match taskMode:
            case 1:
                print("----Manual mode")
                if self.current_program is not None:
                    try:
                        print("----Program finished, deleting it: ", self.current_program)
                        os.remove(self.current_program)
                    except Exception as e:
                        print("----Delete failed: ", e)
                    finally:
                        self.current_program = None

            case 2:
                print("----Auto mode")
            case 3:
                print("----MDI mode")

    def onStateChanged(self, state):
        if state == linuxcnc.RCS_DONE and self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value == True:
            print("----Loaded program has finished, NOT setting ProgramLoaded pin to false")
            #self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = False

    def onHandwheelAllowedChanged(self, allowed: bool):
        print(f"Handwheel allowed changed to: {allowed}")
        if allowed:
            x_enabled = self.xMpgLastValue
            z_enabled = self.zMpgLastValue
        else:
            x_enabled = False
            z_enabled = False
        self.manualTurningViewModel.setHandwheelsAllowed(allowed)
        self.manualTurningViewModel.setHandwheelStates(x_enabled, z_enabled)

    def toggleXMpgEnable(self):
        self.xMpgLastValue = self.manualTurningViewModel.xHandwheelEnabled
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsXEnable).value = self.xMpgLastValue

    def toggleZMpgEnable(self):
        self.zMpgLastValue = self.manualTurningViewModel.zHandwheelEnabled
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsZEnable).value = self.zMpgLastValue

    def onManualQmlXHandwheelToggled(self, enabled):
        self.xMpgLastValue = bool(enabled)
        print("toggle PinHandwheelsAppXEnable to:", self.xMpgLastValue)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsXEnable).value = self.xMpgLastValue
        self.manualTurningViewModel.setXHandwheelEnabled(self.xMpgLastValue)

    def onManualQmlZHandwheelToggled(self, enabled):
        self.zMpgLastValue = bool(enabled)
        print("toggle PinHandwheelsAppZEnable to:", self.zMpgLastValue)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsZEnable).value = self.zMpgLastValue
        self.manualTurningViewModel.setZHandwheelEnabled(self.zMpgLastValue)

    def onXPrimaryDroClicked(self, value):
        print("onXPrimaryDroClicked", value)
        self._open_qml_numpad("smart_numpad.x-offset", "Measured diameter with current tool", self.setXOffset)

    def onZPrimaryDroClicked(self, value):
        print("onZPrimaryDroClicked", value)
        self._open_qml_numpad("smart_numpad.z-offset", "Distance to Z0 with current tool", self.setZOffset)

    def _open_qml_numpad(self, setting_name, description, on_commit):
        """Open the QML SmartNumpadDialog (hosted in ManualTurningRoot) for a
        one-shot value, invoking *on_commit* with the entered value."""
        root_item = self.manualScreen
        if root_item is None:
            return
        # Keep a reference so the adapter isn't garbage-collected mid-dialog.
        self._numpad_value_field = NumpadValueField(setting_name, description, on_commit, self)
        QMetaObject.invokeMethod(
            root_item, "openNumpad", Qt.ConnectionType.DirectConnection, Q_ARG("QVariant", self._numpad_value_field)
        )

    def setXOffset(self, value):
        print("setXOffset", value)
        issue_mdi('o<touch_off_x> call [{}]'.format(value).strip())

    def setZOffset(self, value):
        print("setZOffset", value)
        issue_mdi('o<touch_off_z> call [{}]'.format(value).strip())
        try:
            if self.toolLibraryViewModel.currentToolRequiresBladeZ0Reference():
                blade_width = self.toolLibraryViewModel.currentToolBladeWidth()
                root_item = self.manualScreen
                if root_item is not None:
                    QMetaObject.invokeMethod(
                        root_item,
                        "openBladeZ0ReferenceDialog",
                        Qt.ConnectionType.DirectConnection,
                        Q_ARG("QVariant", blade_width),
                    )
        except Exception as e:
            LOG.error("openBladeZ0ReferenceDialog failed: %s", e)

    def onSetG28(self):
        issue_mdi("G28.1")

    def onGoToG28(self):
        issue_mdi("G28")

    def onSetG30(self):
        issue_mdi("G30.1")

    def onGoToG30(self):
        issue_mdi("G30")

    # ── Full-screen overlay ──────────────────────────────────────────────────────

    def enterFullScreen(self):
        """Hide the whole chrome (top bar + bottom nav)."""
        self._setFullScreen(hide_top=True, hide_bottom=True)

    def enterContentFullScreen(self):
        """Hide only the bottom nav; the AppShell title bar stays visible."""
        self._setFullScreen(hide_top=False, hide_bottom=True)

    def enterProgramRunFullScreen(self):
        """Full window (covers App Bar + bottom tab bar) for a running program."""
        self._setFullScreen(hide_top=True, hide_bottom=True)

    def _setFullScreen(self, hide_top, hide_bottom):
        # This used to carry a warning about never reparenting the page,
        # because moving a QQuickWidget - or the Gremlin QOpenGLWidget inside
        # it - tore down its render context and blocked the UI for seconds.
        # Nothing moves now: the bars are items that stop being visible, and
        # the layout gives their space back.
        self._fullscreen = True
        if self.appRoot is not None:
            self.appRoot.hideChrome(hide_top, hide_bottom)

    def exitFullScreen(self):
        """Restore the AppShell chrome (top bar + bottom nav)."""
        if not self._fullscreen:
            return
        self._fullscreen = False
        if self.appRoot is not None:
            self.appRoot.showChrome()

# The old name, so callers that predate the QWidget removal keep working.
MyMainWindow = TeachInLatheApp
