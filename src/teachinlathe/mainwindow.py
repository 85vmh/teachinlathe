# Setup logging
import os
import tempfile
from enum import Enum

import linuxcnc
from PyQt5.QtCore import QTimer, QSignalBlocker, QUrl
from PyQt5.QtCore import QItemSelectionModel
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.uic.properties import QtWidgets
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.actions.program_actions import load as loadProgram
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from qtpyvcp.utilities.info import Info
from qtpyvcp.widgets.form_widgets.main_window import VCPMainWindow

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.manual_lathe import ManualLathe
from teachinlathe.fixtures import LatheFixturesRepository
from teachinlathe.widgets.FrameAnimator import FrameAnimator
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog
from teachinlathe.widgets.tools_list_provider import ToolsListProvider
import teachinlathe_rc

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


def getProgramFooter():
    return (f"M5 (Stop the spindle)\n"
            f"M2 (Stop the program)\n"
            f"%")


class MyMainWindow(VCPMainWindow):
    """Main window class for the VCP."""

    def getSpindleModeIndex(self):
        return self.tabSpindleMode.currentIndex()

    def __init__(self, *args, **kwargs):
        super(MyMainWindow, self).__init__(*args, **kwargs)
        self.setWindowFlag(Qt.FramelessWindowHint)

        self.mainSelectedTab = MainTabs.MANUAL_TURNING
        self.lastSpindleRpm = 0
        self.isFirstGear = False
        self.xMpgLastValue = True
        self.zMpgLastValue = True
        self.current_spindle_override = 0
        self.current_feed_override = 0
        self.current_program = None

        self.fixture_repository = LatheFixturesRepository()
        self.manualLathe = ManualLathe()
        self.manualLathe.setJoystickWidget(self.latheJoystick)
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

        self.teachinlathedro.xPrimaryDroClicked.connect(self.onXPrimaryDroClicked)
        self.teachinlathedro.zPrimaryDroClicked.connect(self.onZPrimaryDroClicked)

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

        self.xMpgCheckbox.clicked.connect(self.toggleXMpgEnable)
        self.zMpgCheckbox.clicked.connect(self.toggleZMpgEnable)

        self.inputFeed.settingName = 'smart_numpad.input-feed'
        self.inputFeed.initialize()

        self.inputCss.settingName = 'smart_numpad.input-css'
        self.inputCss.initialize()

        self.latheJoystick.angleFeedToggled.connect(self.angleFeedToggled)
        self.inputRpm.mousePressEvent = lambda _: self.openNumPad(self.inputRpm, self.manualLathe.onInputRpmChanged)
        self.inputFeed.mousePressEvent = lambda _: self.openNumPad(self.inputFeed, self.manualLathe.onInputFeedChanged)
        self.inputCss.mousePressEvent = lambda _: self.openNumPad(self.inputCss, self.manualLathe.onInputCssChanged)
        self.inputMaxRpm.mousePressEvent = lambda _: self.openNumPad(self.inputMaxRpm, self.manualLathe.onMaxSpindleRpmChanged)

        self.vtk.setViewXZ2()
        self.vtk.enable_panning(True)

        # self.removableComboBox.currentDeviceEjectable.connect(self.handleUsbPresent)
        self.tabWidget.currentChanged.connect(self.onMainTabChanged)
        self.tabSpindleMode.currentChanged.connect(self.onSpindleModeChanged)

        self.addEditToolWidget.onSaved.connect(self.onToolAddEditSaved)
        self.addEditToolWidget.onCanceled.connect(self.onToolAddEditCanceled)

        self.toolsListProvider = ToolsListProvider(self)

        QTimer.singleShot(0, self.afterUIInit)
        QTimer.singleShot(0, self._initManualToolsList)
        QTimer.singleShot(0, self._syncEmbeddedQmlTabs)
        self.latheFixtures.onFixtureSelected.connect(self.onFixtureSelected)
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
        self.teachinlathedro.setChuckLimit(fixture.z_minus_limit)

    def afterUIInit(self):
        # set the current values
        self.manualLathe.onSpindleModeChanged(self.getSpindleModeIndex())
        self.manualLathe.onInputRpmChanged(self.inputRpm.text())
        self.manualLathe.onInputCssChanged(self.inputCss.text())
        self.manualLathe.onMaxSpindleRpmChanged(self.inputMaxRpm.text())
        self.manualLathe.onInputFeedChanged(self.inputFeed.text())

    def _initManualToolsList(self):
        self.manualToolsList = QQuickWidget(self.toolLibraryContainer)
        self.manualToolsList.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.manualToolsList.setGeometry(0, 0, self.toolLibraryContainer.width(), self.toolLibraryContainer.height())
        self.manualToolsList.engine().rootContext().setContextProperty("toolsProvider", self.toolsListProvider)

        qml_path = os.path.join(os.path.dirname(__file__), "widgets", "ToolListView.qml")
        self.manualToolsList.setSource(QUrl.fromLocalFile(qml_path))
        self.manualToolsList.show()

    def _syncEmbeddedQmlTabs(self):
        current_index = self.tabWidget.currentIndex()
        manual_active = current_index == MainTabs.MANUAL_TURNING.value
        conversational_active = current_index == MainTabs.CONVERSATIONAL.value

        if hasattr(self, "toolLibraryContainer"):
            self.toolLibraryContainer.setVisible(manual_active)
            self.toolLibraryContainer.update()

        if hasattr(self, "manualToolsList"):
            self.manualToolsList.setVisible(manual_active)
            self.manualToolsList.update()

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
        self.teachinlathedro.limitsHandler.setChuckLimitsActive(self.mainSelectedTab != MainTabs.MACHINE_SETTINGS)
        QTimer.singleShot(0, self._syncEmbeddedQmlTabs)

    # def handleUsbPresent(self, value):
    #     self.filesystemTabs.setCurrentIndex(ProgramTabs.FILE_SYSTEM.value if value else ProgramTabs.PROGRAM_LOADED.value)

    def loadProgram(self):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = True
        self.stackedProgramsTab.setCurrentIndex(ProgramTabs.PROGRAM_LOADED.value)
        self.vtk.clearLivePlot()

    def backToPrograms(self):
        self.stackedProgramsTab.setCurrentIndex(ProgramTabs.FILE_SYSTEM.value)

    def showGeneratedProgram(self, ngc_path: str):
        if not ngc_path:
            return
        try:
            folder = os.path.dirname(os.path.abspath(ngc_path))
            self.tabWidget.setCurrentIndex(MainTabs.PROGRAMS.value)
            self.stackedProgramsTab.setCurrentIndex(ProgramTabs.FILE_SYSTEM.value)

            table = getattr(self, "destinationFsTable", None)
            if table is not None:
                try:
                    table.setRootPath(folder)
                    idx = table.model.index(ngc_path)
                    if idx and idx.isValid():
                        table.selectionModel().select(
                            idx,
                            QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
                        )
                        table.scrollTo(idx)
                except Exception:
                    pass
        except Exception as e:
            print("showGeneratedProgram failed:", e)

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
        if value:
            self.feedAnimator.startAnimation()
        else:
            self.feedAnimator.stopAnimation()
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsAngleFeed).value = value

    def onSpindleRunningChanged(self, value):
        print("onSpindleRunningChanged", value)
        # TODO: disable input when spindle is running
        # self.tabSpindleMode.setEnabled(not value)
        # self.inputRpm.setEnabled(not value)
        # self.inputCss.setEnabled(not value)
        # self.inputMaxRpm.setEnabled(not value)
        if self.latheJoystick.isRotated() and not value:
            print("Set taper turning off when stopping spindle")
            self.angleFeedToggled(False)
            self.latheJoystick.resetAngle()

    def openNumPad(self, fake_edit_text, on_value_selected_callback=None):
        setting_name = getattr(fake_edit_text, 'settingName', None)
        dialog = SmartNumPadDialog(setting_name)

        def handle_value(value):
            self.setSelectedValue(fake_edit_text, value)
            if on_value_selected_callback:
                on_value_selected_callback(value)

        dialog.valueSelected.connect(handle_value)
        dialog.exec_()

    @staticmethod
    def setSelectedValue(fake_edit_text, value):
        fake_edit_text.setText(value)

    def onJogIncrementChanged(self, value):
        self.jogIncrement.setText(format(value, '.3f'))

    def onSpindleFirstGearChanged(self, value):
        suffix = '1' if value else '2'
        # update the settings so that the values are relevant for each type
        self.inputRpm.settingName = 'smart_numpad.input-rpm-' + suffix
        self.inputRpm.initialize()
        self.inputMaxRpm.settingName = 'smart_numpad.input-css-max-rpm-' + suffix
        self.inputMaxRpm.initialize()
        # update the values in the manual_lathe.py
        self.manualLathe.onInputRpmChanged(self.inputRpm.text())
        self.manualLathe.onMaxSpindleRpmChanged(self.inputMaxRpm.text())

    def onSpindleRpmChanged(self, value):
        self.lastSpindleRpm = abs(int(value))

    def onRpmDebounced(self):
        self.actualRpm.setText(str(self.lastSpindleRpm))
        self.actualRpmCss.setText(str(self.lastSpindleRpm))

    def handle_spindle_mode(self, index):
        override_factor = self.current_spindle_override
        input_text = self.inputCss.text()

        if input_text.isdigit() and index == 1:  # Check if input_text is a digit and index is 1
            self.actualCss.setText(str(int(input_text) * override_factor))

    def update_actual_feed(self):
        override_factor = self.current_feed_override
        calculated_feed = float(self.inputFeed.text()) * override_factor
        self.actualFeed.setText(format(calculated_feed, '.2f'))

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
        self.xMpgCheckbox.setEnabled(allowed)
        self.zMpgCheckbox.setEnabled(allowed)
        if allowed:
            # Restore last known values
            self.xMpgCheckbox.setChecked(self.xMpgLastValue)
            self.zMpgCheckbox.setChecked(self.zMpgLastValue)
        else:
            # Force disable when not allowed
            self.xMpgCheckbox.setChecked(False)
            self.zMpgCheckbox.setChecked(False)

    def toggleXMpgEnable(self):
        self.xMpgLastValue = self.xMpgCheckbox.isChecked()
        print("toggle PinHandwheelsAppXEnable to:", self.xMpgLastValue)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsXEnable).value = self.xMpgLastValue

    def toggleZMpgEnable(self):
        self.zMpgLastValue = self.xMpgCheckbox.isChecked()
        print("toggle PinHandwheelsAppZEnable to:", self.zMpgLastValue)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsZEnable).value = self.zMpgLastValue

    def onXPrimaryDroClicked(self, value):
        print("onXPrimaryDroClicked", value)
        dialog = SmartNumPadDialog("smart_numpad.x-offset", True)
        dialog.valueSelected.connect(self.setXOffset)
        dialog.exec_()

    def onZPrimaryDroClicked(self, value):
        print("onZPrimaryDroClicked", value)
        dialog = SmartNumPadDialog("smart_numpad.z-offset", True)
        dialog.valueSelected.connect(self.setZOffset)
        dialog.exec_()

    def setXOffset(self, value):
        print("setXOffset", value)
        issue_mdi('o<touch_off_x> call [{}]'.format(value).strip())

    def setZOffset(self, value):
        print("setZOffset", value)
        issue_mdi('o<touch_off_z> call [{}]'.format(value).strip())
