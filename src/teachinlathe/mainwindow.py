# Setup logging
import os
from enum import Enum

import linuxcnc
from PyQt5.QtCore import Q_ARG, QMetaObject, QObject, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtWidgets import QApplication
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from qtpyvcp.utilities.info import Info
from qtpyvcp.widgets.form_widgets.main_window import VCPMainWindow

from teachinlathe.app_state import AppState
from teachinlathe.app_identity import APPLICATION_DISPLAY_NAME, APPLICATION_ID
from teachinlathe.fixtures import LatheFixturesRepository
from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.manual_lathe import ManualLathe
from teachinlathe.widgets.FrameAnimator import FrameAnimator
from teachinlathe.widgets.app_shell_widget import AppShellWidget
from teachinlathe.widgets.manual_qml import ManualTurningViewModel
from teachinlathe.widgets.manual_qml.TeachInLatheDroViewModel import TeachInLatheDroViewModel
from teachinlathe.widgets.touchable_input.numpad_dialog_viewmodel import NumpadDialogViewModel
from teachinlathe.widgets.programs_qml.ProgramsQml import ProgramsQml
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog
from teachinlathe.widgets.tool_library.ToolLibraryViewModel import ToolLibraryViewModel

LOG = logger.getLogger('qtpyvcp.' + __name__)
from PyQt5.QtCore import Qt

INFO = Info()
STATUS = getPlugin('status')
TOOLTABLE = getPlugin('tooltable')
LINUXCNC_CMD = linuxcnc.command()
STAT = linuxcnc.stat()
PROGRAM_PREFIX = INFO.getProgramPrefix()
# Base folder for conversational outputs (user-configurable).
CONVERSATIONAL_OUTPUT_BASE = PROGRAM_PREFIX
CONVERSATIONAL_GCODE_BASE = CONVERSATIONAL_OUTPUT_BASE
CONVERSATIONAL_JSON_BASE = CONVERSATIONAL_OUTPUT_BASE


class MainTabs(Enum):
    MANUAL_TURNING = 0
    CONVERSATIONAL = 1
    PROGRAMS = 2
    TOOLS_OFFSETS = 3
    MACHINE_SETTINGS = 4


class ProgramTabs(Enum):
    FILE_SYSTEM = 0
    PROGRAM_LOADED = 1


class ManualInputBridge(QObject):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self._window = window

    @pyqtSlot(QObject)
    def openField(self, field):
        self._window.openNumPad(field)


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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._root = None

    def attach(self, root):
        self._root = root

    @pyqtSlot(bool)
    def handleAngleFeedToggled(self, enabled):
        self.angleFeedToggled.emit(bool(enabled))

    def setTouchEnabled(self, enabled: bool):
        if self._root is not None:
            self._root.setProperty("allowsTouchInteraction", bool(enabled))

    def resetAngle(self):
        if self._root is not None:
            QMetaObject.invokeMethod(self._root, "resetAngle")

    def isRotated(self):
        if self._root is None:
            return False
        return bool(self._root.property("currentRotation"))

    def setRapid(self, enabled: bool):
        if self._root is not None:
            self._root.setProperty("rapidMode", bool(enabled))

    def setJoystickState(self, state):
        if self._root is None:
            return
        value = state.value if hasattr(state, "value") else int(state)
        self._root.setProperty("joystickState", int(value))
        self.setTouchEnabled(int(value) == 0)


def getProgramFooter():
    return (f"M5 (Stop the spindle)\n"
            f"M2 (Stop the program)\n"
            f"%")


class MyMainWindow(VCPMainWindow):
    """Main window class for the VCP."""

    def getSpindleModeIndex(self):
        if hasattr(self, "manualTurningViewModel"):
            return self.manualTurningViewModel.spindleMode
        return 0

    def __init__(self, *args, **kwargs):
        super(MyMainWindow, self).__init__(*args, **kwargs)
        app = QApplication.instance()
        if app is not None:
            app.setApplicationName(APPLICATION_DISPLAY_NAME)
            app.setApplicationDisplayName(APPLICATION_DISPLAY_NAME)
            app.setDesktopFileName(APPLICATION_ID)
        self.setWindowTitle(APPLICATION_DISPLAY_NAME)
        self.setWindowFlag(Qt.FramelessWindowHint)

        self.mainSelectedTab = MainTabs.MANUAL_TURNING
        self.lastSpindleRpm = 0
        self.isFirstGear = False
        self.xMpgLastValue = True
        self.zMpgLastValue = True
        self.current_spindle_override = 0
        self.current_feed_override = 0
        self.current_program = None
        self.appState = AppState(self)

        self.fixture_repository = LatheFixturesRepository()
        self.manualLathe = ManualLathe()
        self.manualTurningViewModel = ManualTurningViewModel(self.manualLathe, self)
        self.teachInLatheDroViewModel = TeachInLatheDroViewModel(self)
        self.manualJoystickController = ManualJoystickController(self)
        self.latheJoystick = self.manualJoystickController
        self.manualLathe.setJoystickWidget(self.manualJoystickController)
        self.manualJoystickController.angleFeedToggled.connect(self.angleFeedToggled)
        self.feedAnimator = FrameAnimator(self.feedFrame)

        self.latheComponent = TeachInLatheComponent()

        self.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleActualRpm, self.onSpindleRpmChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinButtonCycleStart, self.onCycleStartPressed)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinButtonCycleStop, self.onCycleStopPressed)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinIsSpindleStarted, self.onSpindleRunningChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinHandwheelsJogIncrement, self.onJogIncrementChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleIsFirstGear, self.onSpindleFirstGearChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinHandwheelsAllowed, self.onHandwheelAllowedChanged)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsXEnable).value = True
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsZEnable).value = True
        self.onSpindleFirstGearChanged(self.latheComponent.comp.getPin(TeachInLatheComponent.PinSpindleIsFirstGear).value)

        self.teachInLatheDroViewModel.xPrimaryDroClicked.connect(self.onXPrimaryDroClicked)
        self.teachInLatheDroViewModel.zPrimaryDroClicked.connect(self.onZPrimaryDroClicked)

        # spindle override, initial value and updates
        self.onSpindleOverrideChanged(STATUS.spindle[0].override.value)
        STATUS.spindle[0].override.signal.connect(self.onSpindleOverrideChanged)

        # feed override, initial value and updates
        self.onFeedOverrideChanged(STATUS.feedrate.value)
        STATUS.feedrate.signal.connect(self.onFeedOverrideChanged)

        self.onTaskModeChanged(STATUS.task_mode)
        STATUS.task_mode.signal.connect(self.onTaskModeChanged)
        STATUS.state.signal.connect(self.onStateChanged)

        self.latheToolTable.toolEditClicked.connect(self.onToolEditClicked)
        self.latheToolTable.toolAddClicked.connect(self.onToolAddClicked)

        self.handle_spindle_mode(self.getSpindleModeIndex)

        # rpm is a float that fluctuates a lot, so debounce it
        self.debounce_timer = QTimer()
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.onRpmDebounced)
        self.debounce_timer.start()

        self.btnLoadProgram.clicked.connect(self.loadProgram)
        self.btnBackToPrograms.clicked.connect(self.backToPrograms)

        self.btnSetG28.clicked.connect(self.onSetG28)
        self.btnGoToG28.clicked.connect(self.onGoToG28)
        self.btnSetG30.clicked.connect(self.onSetG30)
        self.btnGoToG30.clicked.connect(self.onGoToG30)

        self.vtk.setViewXZ2()
        self.vtk.enable_panning(True)

        # self.removableComboBox.currentDeviceEjectable.connect(self.handleUsbPresent)
        self.tabWidget.currentChanged.connect(self.onMainTabChanged)

        self.addEditToolWidget.onSaved.connect(self.onToolAddEditSaved)
        self.addEditToolWidget.onCanceled.connect(self.onToolAddEditCanceled)

        self.toolLibraryViewModel = ToolLibraryViewModel(self)

        QTimer.singleShot(0, self._initManualTurningRoot)
        QTimer.singleShot(0, self.afterUIInit)
        QTimer.singleShot(0, self._initProgramsQml)
        QTimer.singleShot(0, self._syncEmbeddedQmlTabs)
        QTimer.singleShot(0, self._initAppShell)
        self.latheFixtures.onFixtureSelected.connect(self.onFixtureSelected)
        try:
            self.conversationalqml.setAppState(self.appState)
        except Exception as e:
            print("Failed to inject app state into conversational:", e)

        initial_fixture = self.fixture_repository.getCurrentFixture()
        if initial_fixture:
            print("Setup initial fixture: ", initial_fixture)
            self.onFixtureSelected(initial_fixture)

    def onToolAddEditSaved(self):
        print("onToolAddEditSaved")
        self.innerToolsAndOffsets.setCurrentIndex(0)  # Switch to the offsets tab
        self.latheToolTable.finishEditingTool()

    def onToolAddEditCanceled(self):
        print("onToolAddEditCanceled")
        self.innerToolsAndOffsets.setCurrentIndex(0)  # Switch to the offsets tab
        self.latheToolTable.finishEditingTool()

    def onToolEditClicked(self, tool_data, tool_model, tool_no):
        print("onToolEditClicked:", tool_no)
        self.innerToolsAndOffsets.setCurrentIndex(1)  # Switch to the tool add/edit tab
        self.addEditToolWidget.setEditToolData(tool_data, tool_model, tool_no)

    def onToolAddClicked(self, tool_data, tool_model):
        print("onToolAddClicked")
        self.innerToolsAndOffsets.setCurrentIndex(1)
        self.addEditToolWidget.setAddToolData(tool_data, tool_model)

    def onFixtureSelected(self, fixture):
        print("---Fixture selected: ", fixture)
        self.teachInLatheDroViewModel.setChuckLimit(fixture.z_minus_limit)

    def afterUIInit(self):
        # set the current values
        self.manualLathe.onSpindleModeChanged(self.getSpindleModeIndex())
        self.manualLathe.onInputRpmChanged(self.manualTurningViewModel.inputRpm)
        self.manualLathe.onInputCssChanged(self.manualTurningViewModel.inputCss)
        self.manualLathe.onMaxSpindleRpmChanged(self.manualTurningViewModel.inputMaxRpm)
        self.manualLathe.onInputFeedChanged(self.manualTurningViewModel.inputFeed)

    def _initManualTurningRoot(self):
        if hasattr(self, "manualTurningRootQml"):
            return

        self.manualInputBridge = ManualInputBridge(self, self)
        self.numpadDialogViewModel = NumpadDialogViewModel(self)
        self._active_numpad_field = None

        tab = self.manualTurningTab
        self.manualTurningRootQml = QQuickWidget(tab)
        self.manualTurningRootQml.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.manualTurningRootQml.setClearColor(QColor("#efefef"))
        self.manualTurningRootQml.setGeometry(0, 0, tab.width(), tab.height())
        self.manualTurningRootQml.setFocusPolicy(Qt.StrongFocus)
        self.manualTurningRootQml.setMouseTracking(True)

        ctx = self.manualTurningRootQml.engine().rootContext()
        ctx.setContextProperty("manualViewModel",     self.manualTurningViewModel)
        ctx.setContextProperty("manualInputBridge",   self.manualInputBridge)
        ctx.setContextProperty("numpadDialogViewModel", self.numpadDialogViewModel)
        ctx.setContextProperty("teachInDroViewModel", self.teachInLatheDroViewModel)
        ctx.setContextProperty("toolLibraryViewModel", self.toolLibraryViewModel)
        ctx.setContextProperty("appState",            self.appState)
        ctx.setContextProperty("cncStore",            self.appState.cncStore)
        ctx.setContextProperty("navigationStore",     self.appState.navigationStore)

        self.manualTurningRootQml.statusChanged.connect(self._on_manual_root_status_changed)

        qml_path = os.path.join(os.path.dirname(__file__), "widgets", "manual_qml", "ManualTurningRoot.qml")
        self.manualTurningRootQml.setSource(QUrl.fromLocalFile(qml_path))
        self.manualTurningRootQml.show()
        self.manualTurningRootQml.raise_()

        # Hide legacy widgets now superseded by the QML root
        if hasattr(self, "toolLibraryContainer"):
            self.toolLibraryContainer.setVisible(False)

        # Restore persisted state into ViewModel
        self.onSpindleFirstGearChanged(self.latheComponent.comp.getPin(TeachInLatheComponent.PinSpindleIsFirstGear).value)
        spindle_mode           = self.manualTurningViewModel.spindleMode
        jog_increment          = self.manualTurningViewModel.jogIncrement
        x_handwheel_enabled    = self.manualTurningViewModel.xHandwheelEnabled
        z_handwheel_enabled    = self.manualTurningViewModel.zHandwheelEnabled
        self.manualTurningViewModel.setSpindleMode(spindle_mode)
        self.manualTurningViewModel.setFeedOverride(self.current_feed_override)
        self.manualTurningViewModel.setSpindleOverride(self.current_spindle_override)
        self.manualTurningViewModel.setJogIncrement(jog_increment)
        self.manualTurningViewModel.setHandwheelStates(x_handwheel_enabled, z_handwheel_enabled)
        self.manualLathe.onInputCssChanged(self.manualTurningViewModel.inputCss)
        self.manualLathe.onInputFeedChanged(self.manualTurningViewModel.inputFeed)

    def _on_manual_root_status_changed(self, status):
        if status != QQuickWidget.Ready:
            return
        root = self.manualTurningRootQml.rootObject()
        if root is None:
            return
        root.openNumPadRequested.connect(lambda field: self.openNumPad(field))
        root.xToggled.connect(self.onManualQmlXHandwheelToggled)
        root.zToggled.connect(self.onManualQmlZHandwheelToggled)
        root.angleFeedToggled.connect(self.manualJoystickController.handleAngleFeedToggled)
        self.manualJoystickController.attach(root)
        self.latheJoystick = self.manualJoystickController
        self.manualLathe.setJoystickWidget(self.manualJoystickController)

    def _initManualToolsList(self):
        self.manualToolsList = QQuickWidget(self.toolLibraryContainer)
        self.manualToolsList.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.manualToolsList.setGeometry(0, 0, self.toolLibraryContainer.width(), self.toolLibraryContainer.height())
        self.manualToolsList.engine().rootContext().setContextProperty("toolLibraryViewModel", self.toolLibraryViewModel)
        self.manualToolsList.engine().rootContext().setContextProperty("appState", self.appState)
        self.manualToolsList.engine().rootContext().setContextProperty("cncStore", self.appState.cncStore)
        self.manualToolsList.engine().rootContext().setContextProperty("navigationStore", self.appState.navigationStore)

        qml_path = os.path.join(os.path.dirname(__file__), "widgets", "tool_library", "ToolLibraryView.qml")
        self.manualToolsList.setSource(QUrl.fromLocalFile(qml_path))
        self.manualToolsList.show()

    def _initTeachInLatheDroQml(self):
        if hasattr(self, "teachInLatheDroQml"):
            return
        self.teachInLatheDroQml = QQuickWidget(self.manualTurningTab)
        self.teachInLatheDroQml.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.teachInLatheDroQml.setClearColor(QColor("#efefef"))
        self.teachInLatheDroQml.setGeometry(0, 0, 1311, 696)
        self.teachInLatheDroQml.engine().rootContext().setContextProperty(
            "teachInDroViewModel",
            self.teachInLatheDroViewModel,
        )
        qml_path = os.path.join(os.path.dirname(__file__), "widgets", "manual_qml", "TeachInLatheDroRoot.qml")
        self.teachInLatheDroQml.setSource(QUrl.fromLocalFile(qml_path))
        self.teachInLatheDroQml.show()
        self.teachInLatheDroQml.raise_()

    def _initManualTurningQml(self):
        if hasattr(self, "manualSpindleQml"):
            return

        self.manualInputBridge = ManualInputBridge(self, self)
        self._active_numpad_field = None

        spindle_mode = self.manualTurningViewModel.spindleMode
        jog_increment = self.manualTurningViewModel.jogIncrement
        x_handwheel_enabled = self.manualTurningViewModel.xHandwheelEnabled
        z_handwheel_enabled = self.manualTurningViewModel.zHandwheelEnabled

        self.manualJoystickQml = self._create_manual_qml_widget(
            self.feedFrame,
            "ManualJoystickPanel.qml",
            5,
            5,
            260,
            230,
        )
        self.manualSpindleQml = self._create_manual_qml_widget(
            self.spindleFrame,
            "ManualSpindlePanel.qml",
            5,
            5,
            286,
            231,
        )
        self.manualFeedQml = self._create_manual_qml_widget(
            self.feedFrame,
            "ManualFeedPanel.qml",
            270,
            5,
            276,
            230,
        )
        self.manualHandwheelsQml = self._create_manual_qml_widget(
            self.handwheelsFrame,
            "ManualHandwheelsPanel.qml",
            0,
            0,
            216,
            241,
        )
        self._raise_manual_qml_widgets()

        self.onSpindleFirstGearChanged(self.latheComponent.comp.getPin(TeachInLatheComponent.PinSpindleIsFirstGear).value)
        self.manualTurningViewModel.setSpindleMode(spindle_mode)
        self.manualTurningViewModel.setFeedOverride(self.current_feed_override)
        self.manualTurningViewModel.setSpindleOverride(self.current_spindle_override)
        self.manualTurningViewModel.setJogIncrement(jog_increment)
        self.manualTurningViewModel.setHandwheelStates(x_handwheel_enabled, z_handwheel_enabled)
        self.manualLathe.onInputCssChanged(self.manualTurningViewModel.inputCss)
        self.manualLathe.onInputFeedChanged(self.manualTurningViewModel.inputFeed)
        self.latheJoystick = self.manualJoystickController
        self.manualLathe.setJoystickWidget(self.manualJoystickController)

    def _create_manual_qml_widget(self, parent, qml_name, x, y, width, height):
        widget = QQuickWidget(parent)
        widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        widget.setClearColor(QColor("transparent"))
        widget.setGeometry(x, y, width, height)
        widget.setFocusPolicy(Qt.StrongFocus)
        widget.setMouseTracking(True)
        widget.engine().rootContext().setContextProperty("manualViewModel", self.manualTurningViewModel)
        widget.engine().rootContext().setContextProperty("manualInputBridge", self.manualInputBridge)
        widget.statusChanged.connect(lambda status, qml_widget=widget: self._on_manual_qml_status_changed(status, qml_widget))
        qml_path = os.path.join(os.path.dirname(__file__), "widgets", "manual_qml", qml_name)
        widget.setSource(QUrl.fromLocalFile(qml_path))
        widget.show()
        widget.raise_()
        return widget

    def _raise_manual_qml_widgets(self):
        widget = getattr(self, "manualTurningRootQml", None)
        if widget is not None:
            widget.raise_()

    def _on_manual_qml_status_changed(self, status, widget):
        if status != QQuickWidget.Ready:
            return
        root = widget.rootObject()
        if root is None:
            return
        root.setProperty("viewModel", self.manualTurningViewModel)
        try:
            root.openNumPadRequested.connect(lambda field: self.openNumPad(field))
        except Exception:
            pass
        try:
            root.xToggled.connect(self.onManualQmlXHandwheelToggled)
            root.zToggled.connect(self.onManualQmlZHandwheelToggled)
        except Exception:
            pass
        if root.objectName() == "manualJoystickPanel":
            self.manualJoystickController.attach(root)
            try:
                root.angleFeedToggled.connect(self.manualJoystickController.handleAngleFeedToggled)
            except Exception as e:
                print("Manual QML joystick hook failed:", e)

    def _initProgramsQml(self):
        from PyQt5.QtWidgets import QWidget, QVBoxLayout
        from teachinlathe.widgets.programs_qml.filesystemview import (
            FileSystemLocation, LocationType,
        )
        gcode_folder     = os.path.join(CONVERSATIONAL_GCODE_BASE, "Conversational Gcode")
        json_folder      = os.path.join(CONVERSATIONAL_JSON_BASE, "Conversational Json")
        usb_stick_folder = os.path.join(CONVERSATIONAL_GCODE_BASE, "USB Stick Programs")
        locations = [
            FileSystemLocation("Generated Programs", gcode_folder,                         LocationType.GENERATED),
            FileSystemLocation("USB Stick Programs",  usb_stick_folder,                    LocationType.USB_STICK),
            FileSystemLocation("SyncThing Programs",  os.path.expanduser("~/Sync"),        LocationType.SYNCTHING),
            FileSystemLocation("Home",                os.path.expanduser("~"),             LocationType.HOME),
        ]
        # Replace the legacy Programs tab (index 2) with the new Programs QML widget.
        self.tabWidget.removeTab(MainTabs.PROGRAMS.value)
        self.programsQmlTab = QWidget()
        self.tabWidget.insertTab(MainTabs.PROGRAMS.value, self.programsQmlTab, "Programs")

        tab_layout = QVBoxLayout(self.programsQmlTab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self.programsQmlWidget = ProgramsQml(locations, self.programsQmlTab, json_folder_path=json_folder)
        self.programsQmlWidget.setAppState(self.appState)
        self.programsQmlWidget.viewmodel.programLoadRequested.connect(self.onProgramsQmlProgramLoadRequested)
        tab_layout.addWidget(self.programsQmlWidget)

    def _initAppShell(self):
        if hasattr(self, "appShellWidget") and self.appShellWidget is not None:
            return

        from PyQt5.QtWidgets import QVBoxLayout

        self.tabWidget.setTabBarAutoHide(True)
        self.tabWidget.tabBar().hide()

        if self.pageReady.layout() is None:
            layout = QVBoxLayout(self.pageReady)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        else:
            layout = self.pageReady.layout()

        feature_controllers = {
            "conversational": getattr(self, "conversationalqml", None),
            "programs": getattr(self, "programsQmlWidget", None),
        }
        self.appShellWidget = AppShellWidget(self.tabWidget, self.appState, self.pageReady, feature_controllers=feature_controllers)
        layout.addWidget(self.appShellWidget)

        tab_id = {
            MainTabs.MANUAL_TURNING.value: "manual",
            MainTabs.CONVERSATIONAL.value: "conversational",
            MainTabs.PROGRAMS.value: "programs",
            MainTabs.TOOLS_OFFSETS.value: "tools",
            MainTabs.MACHINE_SETTINGS.value: "settings",
        }.get(self.tabWidget.currentIndex(), "manual")
        self.appState.activateTab(tab_id)

    def _syncEmbeddedQmlTabs(self):
        current_index = self.tabWidget.currentIndex()
        manual_active = current_index == MainTabs.MANUAL_TURNING.value
        conversational_active = current_index == MainTabs.CONVERSATIONAL.value

        if hasattr(self, "manualTurningRootQml"):
            self.manualTurningRootQml.setVisible(manual_active)
            if manual_active:
                self.manualTurningRootQml.raise_()

        if hasattr(self, "conversationalqml"):
            self.conversationalqml.setVisible(conversational_active)
            self.conversationalqml.update()

        current_widget = self.tabWidget.currentWidget()
        if current_widget is not None:
            current_widget.raise_()
            current_widget.update()
            current_widget.repaint()
        self.tabWidget.update()

    def onMainTabChanged(self, index):
        self.mainSelectedTab = MainTabs(index)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsReadyToRunProgram).value = self.mainSelectedTab == MainTabs.PROGRAMS
        self.teachInLatheDroViewModel.limitsHandler.setChuckLimitsActive(self.mainSelectedTab != MainTabs.MACHINE_SETTINGS)

        tab_id = {
            MainTabs.MANUAL_TURNING.value: "manual",
            MainTabs.CONVERSATIONAL.value: "conversational",
            MainTabs.PROGRAMS.value: "programs",
            MainTabs.TOOLS_OFFSETS.value: "tools",
            MainTabs.MACHINE_SETTINGS.value: "settings",
        }.get(index, "manual")
        self.appState.activateTab(tab_id)
        self.appState.cncStore.addEvent("INFO", "navigation", f"Switched to {tab_id}")
        QTimer.singleShot(0, self._syncEmbeddedQmlTabs)
        QTimer.singleShot(0, self._initAppShell)

    # def handleUsbPresent(self, value):
    #     self.filesystemTabs.setCurrentIndex(ProgramTabs.FILE_SYSTEM.value if value else ProgramTabs.PROGRAM_LOADED.value)

    def loadProgram(self):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = True
        self.stackedProgramsTab.setCurrentIndex(ProgramTabs.PROGRAM_LOADED.value)
        self.vtk.clearLivePlot()

    def onProgramsQmlProgramLoadRequested(self, _path):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = True

    def backToPrograms(self):
        self.stackedProgramsTab.setCurrentIndex(ProgramTabs.FILE_SYSTEM.value)

    def showGeneratedProgram(self, ngc_path: str):
        if not ngc_path:
            return
        try:
            self.tabWidget.setCurrentIndex(MainTabs.PROGRAMS.value)
            self.programsQmlWidget.viewmodel.showFilesScreen()
            self.programsQmlWidget.fs_viewmodel.showFileInGeneratedPrograms(
                os.path.abspath(ngc_path)
            )
            self.programsQmlWidget.reactivate()
            QTimer.singleShot(0, self.programsQmlWidget.reactivate)
            QTimer.singleShot(100, self.programsQmlWidget.reactivate)
        except Exception as e:
            print("showGeneratedProgram failed:", e)

    def editConversationalProgramFromJson(self, json_path: str):
        if not json_path or not os.path.isfile(json_path):
            return
        try:
            self.tabWidget.setCurrentIndex(MainTabs.CONVERSATIONAL.value)
            if hasattr(self, "conversationalqml"):
                self.conversationalqml.openProgramFile(os.path.abspath(json_path))
        except Exception as e:
            print("editConversationalProgramFromJson failed:", e)

    def onSpindleModeChanged(self):
        self.manualLathe.onSpindleModeChanged(self.getSpindleModeIndex())
        self.handle_spindle_mode(self.getSpindleModeIndex())

    def onCycleStartPressed(self):
        pass

    def onCycleStopPressed(self, value):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = False
        if self.mainSelectedTab == MainTabs.MANUAL_TURNING:
            if self.latheJoystick.isRotated() and value:
                print("Set taper turning off when cycle stop pressed")
                self.angleFeedToggled(False)
                self.latheJoystick.resetAngle()

    def angleFeedToggled(self, value):
        print("angleFeedToggled", value)
        self.manualLathe.onTaperTurningChanged(value)
        self._raise_manual_qml_widgets()
        if value:
            self.feedAnimator.startAnimation()
        else:
            self.feedAnimator.stopAnimation()
        QTimer.singleShot(0, self._raise_manual_qml_widgets)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsAngleFeed).value = value

    def onSpindleRunningChanged(self, value):
        print("onSpindleRunningChanged", value)
        if self.latheJoystick.isRotated() and not value:
            print("Set taper turning off when stopping spindle")
            self.angleFeedToggled(False)
            self.latheJoystick.resetAngle()

    def openNumPad(self, fake_edit_text, on_value_selected_callback=None):
        setting_name = getattr(fake_edit_text, 'settingName', None)
        if setting_name is None:
            try:
                setting_name = fake_edit_text.property("settingName")
            except Exception:
                setting_name = None
        if not setting_name:
            self._defocus_numpad_field(fake_edit_text)
            return
        previous_field = getattr(self, "_active_numpad_field", None)
        if previous_field is not None and previous_field is not fake_edit_text:
            self._defocus_numpad_field(previous_field)
        self._active_numpad_field = fake_edit_text
        dialog = SmartNumPadDialog(setting_name)

        def handle_value(value):
            self._handle_manual_numpad_value(setting_name, value)
            self.setSelectedValue(fake_edit_text, value)
            if on_value_selected_callback:
                on_value_selected_callback(value)

        try:
            dialog.valueSelected.connect(handle_value)
            dialog.exec_()
        finally:
            self._defocus_numpad_field(fake_edit_text)
            if getattr(self, "_active_numpad_field", None) is fake_edit_text:
                self._active_numpad_field = None

    @staticmethod
    def setSelectedValue(fake_edit_text, value):
        try:
            fake_edit_text.setProperty("value", value)
            fake_edit_text.setProperty("text", str(value))
            return
        except Exception:
            pass
        try:
            if hasattr(fake_edit_text, 'commit'):
                fake_edit_text.commit(value)
                return
        except Exception:
            pass
        try:
            QMetaObject.invokeMethod(fake_edit_text, 'commit', Qt.DirectConnection, Q_ARG('QVariant', value))
            return
        except Exception:
            pass
        try:
            fake_edit_text.setText(value)
            return
        except Exception:
            pass
        try:
            fake_edit_text.setProperty("text", str(value))
        except Exception as e:
            print("setSelectedValue failed:", e)

    def _handle_manual_numpad_value(self, setting_name, value):
        if not hasattr(self, "manualTurningViewModel"):
            return
        if setting_name == self.manualTurningViewModel.feedSettingName:
            self.manualTurningViewModel.setInputFeed(str(value))
        elif setting_name == self.manualTurningViewModel.cssSettingName:
            self.manualTurningViewModel.setInputCss(str(value))
        elif setting_name == self.manualTurningViewModel.rpmSettingName:
            self.manualTurningViewModel.setInputRpm(str(value))
        elif setting_name == self.manualTurningViewModel.maxRpmSettingName:
            self.manualTurningViewModel.setInputMaxRpm(str(value))

    @staticmethod
    def _defocus_numpad_field(field):
        if field is None:
            return
        try:
            QMetaObject.invokeMethod(field, 'defocus', Qt.DirectConnection)
            return
        except Exception:
            pass
        try:
            field.setProperty("numpadActive", False)
            field.setProperty("focus", False)
        except Exception:
            pass

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
            print("----Loaded program has finished")
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = False

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
        root = getattr(self, "manualTurningRootQml", None)
        root_item = root.rootObject() if root is not None else None
        if root_item is None:
            return
        # Keep a reference so the adapter isn't garbage-collected mid-dialog.
        self._numpad_value_field = NumpadValueField(setting_name, description, on_commit, self)
        QMetaObject.invokeMethod(
            root_item, "openNumpad", Qt.DirectConnection, Q_ARG("QVariant", self._numpad_value_field)
        )

    def setXOffset(self, value):
        print("setXOffset", value)
        issue_mdi('o<touch_off_x> call [{}]'.format(value).strip())

    def setZOffset(self, value):
        print("setZOffset", value)
        issue_mdi('o<touch_off_z> call [{}]'.format(value).strip())

    def onSetG28(self):
        issue_mdi("G28.1")

    def onGoToG28(self):
        issue_mdi("G28")

    def onSetG30(self):
        issue_mdi("G30.1")

    def onGoToG30(self):
        issue_mdi("G30")

    # ── Full-screen overlay ──────────────────────────────────────────────────────

    def enterFullScreen(self, widget):
        """Re-parent widget to the main window and stretch it to cover everything."""
        self._enterFullScreenAt(widget, y_offset=0)

    def enterContentFullScreen(self, widget):
        """Re-parent widget below the AppShell title bar, leaving it visible."""
        from PyQt5.QtCore import QPoint
        shell = getattr(self, "appShellWidget", None)
        title_bar = getattr(shell, "title_bar", None) if shell else None
        y_offset = 0
        if title_bar is not None:
            try:
                y_offset = shell.mapTo(self, QPoint(0, title_bar.height())).y()
            except Exception:
                y_offset = title_bar.height()
        self._enterFullScreenAt(widget, y_offset=y_offset)

    def enterProgramRunFullScreen(self, widget):
        """Full window (covers App Bar + bottom tab bar) for a running program."""
        self._enterFullScreenAt(widget, y_offset=0)

    def _enterFullScreenAt(self, widget, y_offset=0):
        if getattr(self, "_fullscreen_widget", None) is widget:
            return
        widget._fs_saved_parent   = widget.parent()
        widget._fs_saved_geometry = widget.geometry()
        widget.setParent(self)
        widget.setGeometry(0, y_offset, self.width(), self.height() - y_offset)
        widget.show()
        widget.raise_()
        self._fullscreen_widget  = widget
        self._fullscreen_y_offset = y_offset

    def exitFullScreen(self):
        """Restore the full-screen widget back to its original place."""
        widget = getattr(self, "_fullscreen_widget", None)
        if widget is None:
            return
        self._fullscreen_widget  = None
        self._fullscreen_y_offset = 0
        saved_parent = getattr(widget, "_fs_saved_parent", None)
        saved_geom   = getattr(widget, "_fs_saved_geometry", None)
        if saved_parent is not None:
            widget.setParent(saved_parent)
        if saved_geom is not None:
            widget.setGeometry(saved_geom)
        widget.show()
        widget.raise_()
        widget.update()
        widget.repaint()
        if hasattr(widget, "reactivate"):
            QTimer.singleShot(0, widget.reactivate)
            QTimer.singleShot(100, widget.reactivate)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        widget = getattr(self, "_fullscreen_widget", None)
        if widget is not None:
            y = getattr(self, "_fullscreen_y_offset", 0)
            widget.setGeometry(0, y, self.width(), self.height() - y)
