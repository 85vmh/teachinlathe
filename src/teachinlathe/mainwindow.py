# Setup logging
import os
import tempfile
from enum import Enum

import linuxcnc
from PyQt5.QtCore import QTimer
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

LOG = logger.getLogger('qtpyvcp.' + __name__)
from PyQt5.QtCore import Qt

INFO = Info()
STATUS = getPlugin('status')
LINUXCNC_CMD = linuxcnc.command()
STAT = linuxcnc.stat()
PROGRAM_PREFIX = INFO.getProgramPrefix()


class MainTabs(Enum):
    MANUAL_TURNING = 0
    QUICK_CYCLES = 1
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
        self.isPowerFeeding = False
        self.isFirstGear = False
        self.xMpgEnabled = True
        self.zMpgEnabled = True
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
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinIsPowerFeeding, self.onPowerFeedingChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinHandwheelsJogIncrement, self.onJogIncrementChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleIsFirstGear, self.onSpindleFirstGearChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinHandwheelsXIsEnabled, self.onHandwheelXEnabledChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinHandwheelsZIsEnabled, self.onHandwheelZEnabledChanged)
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

        self.handle_spindle_mode(self.getSpindleModeIndex)

        # rpm is a float that fluctuates a lot, so debounce it
        self.debounce_timer = QTimer()
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.onRpmDebounced)
        self.debounce_timer.start()

        self.btnLoadProgram.clicked.connect(self.loadProgram)
        self.btnBackToPrograms.clicked.connect(self.backToPrograms)
        self.xMpgCheckbox.stateChanged.connect(self.toggleXMpgEnable)
        self.zMpgCheckbox.stateChanged.connect(self.toggleZMpgEnable)

        self.inputFeed.settingName = 'smart_numpad.input-feed'
        self.inputFeed.initialize()

        self.inputFeedAngle.settingName = 'smart_numpad.input-feed-angle'
        self.inputFeedAngle.initialize()

        self.inputCss.settingName = 'smart_numpad.input-css'
        self.inputCss.initialize()

        self.latheJoystick.angleFeedToggled.connect(self.angleFeedToggled)
        self.inputRpm.mousePressEvent = lambda _: self.openNumPad(self.inputRpm, self.manualLathe.onInputRpmChanged)
        self.inputFeed.mousePressEvent = lambda _: self.openNumPad(self.inputFeed, self.manualLathe.onInputFeedChanged)
        self.inputCss.mousePressEvent = lambda _: self.openNumPad(self.inputCss, self.manualLathe.onInputCssChanged)
        self.inputMaxRpm.mousePressEvent = lambda _: self.openNumPad(self.inputMaxRpm, self.manualLathe.onMaxSpindleRpmChanged)
        self.inputFeedAngle.mousePressEvent = lambda _: self.openNumPad(self.inputFeedAngle, self.manualLathe.onFeedAngleChanged)

        self.vtk.setViewXZ2()
        self.vtk.enable_panning(True)

        # self.removableComboBox.currentDeviceEjectable.connect(self.handleUsbPresent)
        self.quickcycles.onLoadClicked.connect(self.prepareToRunProgram)
        self.tabWidget.currentChanged.connect(self.onMainTabChanged)
        self.tabSpindleMode.currentChanged.connect(self.onSpindleModeChanged)

        QTimer.singleShot(0, self.afterUIInit)
        self.latheFixtures.onFixtureSelected.connect(self.onFixtureSelected)
        initial_fixture = self.fixture_repository.getCurrentFixture()
        if initial_fixture:
            print("Setup initial fixture: ", initial_fixture)
            self.onFixtureSelected(initial_fixture)

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
        self.manualLathe.onFeedAngleChanged(self.inputFeedAngle.text())

    def onMainTabChanged(self, index):
        self.mainSelectedTab = MainTabs(index)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsReadyToRunProgram).value = self.mainSelectedTab == MainTabs.PROGRAMS
        self.teachinlathedro.limitsHandler.setChuckLimitsActive(self.mainSelectedTab != MainTabs.MACHINE_SETTINGS)

    # def handleUsbPresent(self, value):
    #     self.filesystemTabs.setCurrentIndex(ProgramTabs.FILE_SYSTEM.value if value else ProgramTabs.PROGRAM_LOADED.value)

    def loadProgram(self):
        self.stackedProgramsTab.setCurrentIndex(ProgramTabs.PROGRAM_LOADED.value)
        self.vtk.clearLivePlot()

    def prepareToRunProgram(self, subroutine_text):
        print("subroutine_text: ", subroutine_text)
        subs_without_manual_turning_settings = ["drilling", "keyslot"]

        if any(sub.lower() in subroutine_text.lower() for sub in subs_without_manual_turning_settings):
            program_header = ''
        else:
            program_header = self.manualLathe.getProgramHeader()

        program_text = (f"(Program generated by TeachInLathe)\n\n"
                        f"{program_header}\n"
                        f"{subroutine_text}\n\n"
                        f"{getProgramFooter()}")

        print("Program text:\n", program_text)

        with tempfile.NamedTemporaryFile(dir=PROGRAM_PREFIX, suffix='.ngc', delete=False) as temp:
            temp.write(program_text.encode('utf-8'))
            temp.flush()
            print(f'Temporary file created: {temp.name}')
            loadProgram(temp.name, add_to_recents=False)
            self.current_program = temp.name

    def backToPrograms(self):
        self.stackedProgramsTab.setCurrentIndex(ProgramTabs.FILE_SYSTEM.value)

    def onSpindleModeChanged(self):
        self.manualLathe.onSpindleModeChanged(self.getSpindleModeIndex())
        self.handle_spindle_mode(self.getSpindleModeIndex())

    def onCycleStartPressed(self):
        pass

    def onCycleStopPressed(self, value):
        if self.mainSelectedTab == MainTabs.MANUAL_TURNING:
            if self.checkBoxFeedAngle.isChecked() and value:
                print("Set taper turning off when cycle stop pressed")
                self.checkBoxFeedAngle.setChecked(False)
                self.angleFeedToggled(False)

    def angleFeedToggled(self, value):
        # self.inputFeedAngle.setEnabled(value)

        if value:
            self.feedAnimator.startAnimation()
        else:
            self.feedAnimator.stopAnimation()

        print("angleFeedActive", value)
        self.manualLathe.onTaperTurningChanged(value)
        input_text = self.inputFeedAngle.text()
        if input_text.isdigit():
            self.manualLathe.onFeedAngleChanged(input_text)

    def onSpindleRunningChanged(self, value):
        print("onSpindleRunningChanged", value)
        # TODO: disable input when spindle is running
        # self.tabSpindleMode.setEnabled(not value)
        # self.inputRpm.setEnabled(not value)
        # self.inputCss.setEnabled(not value)
        # self.inputMaxRpm.setEnabled(not value)
        # self.checkBoxJogAngle.setEnabled(not value)
        # self.inputFeedAngle.setEnabled(not value and self.checkBoxFeedAngle.isChecked())
        if self.latheJoystick.isRotated() and not value:
            print("Set taper turning off when stopping spindle")
            self.latheJoystick.resetAngle()
            self.angleFeedToggled(False)

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

    def onPowerFeedingChanged(self, value):
        self.isPowerFeeding = value
        self.update_actual_feed()

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
        if self.isPowerFeeding:
            calculated_feed = float(self.inputFeed.text()) * override_factor
            self.actualFeed.setText(format(calculated_feed, '.2f'))
        else:
            self.actualFeed.setText("0.00")

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

        # if STAT.task_mode == linuxcnc.MODE_MANUAL:
        #     print("enabled")
        #     self.xMpgCheckbox.setEnabled(True)
        #     self.zMpgCheckbox.setEnabled(True)
        # else:
        #     print("disabled")
        #     self.xMpgCheckbox.setEnabled(False)
        #     self.zMpgCheckbox.setEnabled(False)

    def onHandwheelXEnabledChanged(self, value):
        print("onHandwheelXEnabledChanged from pin", value)
        self.xMpgEnabled = value
        self.xMpgCheckbox.setChecked(value)

    def onHandwheelZEnabledChanged(self, value):
        print("onHandwheelZEnabledChanged from pin", value)
        self.zMpgEnabled = value
        self.zMpgCheckbox.setChecked(value)

    def toggleXMpgEnable(self, value):
        print("toggleXMpgEnable to pin", value)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsXEnable).value = value

    def toggleZMpgEnable(self, value):
        print("toggleZMpgEnable to pin", value)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsZEnable).value = value

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

    @staticmethod
    def setXOffset(value):
        print("setXOffset", value)
        issue_mdi('o<touch_off_x> call [{}]'.format(value))

    @staticmethod
    def setZOffset(value):
        print("setZOffset", value)
        issue_mdi('o<touch_off_z> call [{}]'.format(value))
