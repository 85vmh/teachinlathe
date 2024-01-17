# Setup logging
from PyQt5.QtCore import QTimer
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from qtpyvcp.widgets.form_widgets.main_window import VCPMainWindow

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.manual_lathe import ManualLathe
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog

LOG = logger.getLogger('qtpyvcp.' + __name__)
from PyQt5.QtCore import Qt

STATUS = getPlugin('status')

from resources import resources_rc


class MyMainWindow(VCPMainWindow):
    """Main window class for the VCP."""

    def getSpindleModeIndex(self):
        if self.radioRpm.isChecked():
            return 0
        else:
            return 1

    def __init__(self, *args, **kwargs):
        super(MyMainWindow, self).__init__(*args, **kwargs)
        self.setWindowFlag(Qt.FramelessWindowHint)

        self.manualLathe = ManualLathe()
        self.latheComponent = TeachInLatheComponent()
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleActualRpm, self.onSpindleRpmChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinButtonCycleStop, self.onCycleStopPressed)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinIsSpindleStarted, self.onSpindleRunningChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinIsPowerFeeding, self.onPowerFeedingChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinHandwheelsJogIncrement, self.onJogIncrementChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleIsFirstGear, self.onSpindleFirstGearChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinHandwheelsXIsEnabled, self.onHandwheelXEnabledChanged)
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinHandwheelsZIsEnabled, self.onHandwheelZEnabledChanged)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsXEnable).value = True
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsZEnable).value = True
        self.isFirstGear = self.latheComponent.comp.getPin(TeachInLatheComponent.PinSpindleIsFirstGear).value

        self.teachinlathedro.xPrimaryDroClicked.connect(self.onXPrimaryDroClicked)
        self.teachinlathedro.zPrimaryDroClicked.connect(self.onZPrimaryDroClicked)

        STATUS.spindle[0].override.signal.connect(self.onSpindleOverrideChanged)
        STATUS.feedrate.signal.connect(self.onFeedOverrideChanged)

        self.lastSpindleRpm = 0
        self.isPowerFeeding = False
        self.isFirstGear = False
        self.xMpgEnabled = True
        self.zMpgEnabled = True

        # get the initial values
        self.current_spindle_override = STATUS.spindle[0].override.value
        self.current_feed_override = STATUS.feedrate.value

        self.handle_spindle_mode(self.getSpindleModeIndex)

        self.debounce_timer = QTimer()
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.onRpmDebounced)
        self.debounce_timer.start()

        self.setZDatumBtn.clicked.connect(self.setZDatum)
        self.btnLoadProgram.clicked.connect(self.loadProgram)
        self.btnBackToPrograms.clicked.connect(self.backToPrograms)
        self.xMpgCheckbox.stateChanged.connect(self.toggleXMpgEnable)
        self.zMpgCheckbox.stateChanged.connect(self.toggleZMpgEnable)

        # set the current values
        self.manualLathe.onSpindleModeChanged(self.getSpindleModeIndex())
        self.manualLathe.onInputRpmChanged(self.inputRpm.text())
        self.manualLathe.onInputCssChanged(self.inputCss.text())
        self.manualLathe.onMaxSpindleRpmChanged(self.inputMaxRpm.text())
        self.manualLathe.onInputFeedChanged(self.inputFeed.text())
        self.manualLathe.onFeedAngleChanged(self.inputFeedAngle.text())

        # connect the signals
        self.radioRpm.toggled.connect(self.onRadioButtonToggled)
        self.radioCss.toggled.connect(self.onRadioButtonToggled)

        self.inputRpm.textChanged.connect(self.manualLathe.onInputRpmChanged)
        self.inputCss.textChanged.connect(self.manualLathe.onInputCssChanged)
        self.inputMaxRpm.textChanged.connect(self.manualLathe.onMaxSpindleRpmChanged)
        self.inputFeed.textChanged.connect(self.manualLathe.onInputFeedChanged)
        self.inputFeedAngle.textChanged.connect(self.manualLathe.onFeedAngleChanged)
        self.checkBoxFeedAngle.stateChanged.connect(self.checkBoxFeedAngleChanged)
        self.checkBoxJogAngle.stateChanged.connect(self.checkBoxJogAngleChanged)

        self.inputRpm.mousePressEvent = lambda _: self.openNumPad(self.inputRpm, True)
        self.inputFeed.mousePressEvent = lambda _: self.openNumPad(self.inputFeed)
        self.inputCss.mousePressEvent = lambda _: self.openNumPad(self.inputCss)
        self.inputMaxRpm.mousePressEvent = lambda _: self.openNumPad(self.inputMaxRpm, True)
        self.inputFeedAngle.mousePressEvent = lambda _: self.openNumPad(self.inputFeedAngle)

        self.vtk.setViewXZ2()
        self.vtk.enable_panning(True)

        self.removableComboBox.currentDeviceEjectable.connect(self.handleUsbPresent)

    def handleUsbPresent(self, value):
        self.filesystemTabs.setCurrentIndex(0 if value else 1)

    def loadProgram(self):
        self.stackedProgramsTab.setCurrentIndex(1)
        self.vtk.clearLivePlot()

    def backToPrograms(self):
        self.stackedProgramsTab.setCurrentIndex(0)

    def onRadioButtonToggled(self):
        self.manualLathe.onSpindleModeChanged(self.getSpindleModeIndex())
        self.handle_spindle_mode(self.getSpindleModeIndex())
        self.spindleModeWidget.setCurrentIndex(self.getSpindleModeIndex())

    def onCycleStopPressed(self, value):
        if self.checkBoxFeedAngle.isChecked() and value:
            print("Set taper turning off when cycle stop pressed")
            self.checkBoxFeedAngle.setChecked(False)
            self.checkBoxFeedAngleChanged(False)

    def checkBoxFeedAngleChanged(self, value):
        self.inputFeedAngle.setEnabled(value)
        self.manualLathe.onTaperTurningChanged(value)
        input_text = self.inputFeedAngle.text()
        if input_text.isdigit():
            self.manualLathe.onFeedAngleChanged(input_text)

    def checkBoxJogAngleChanged(self, value):
        self.inputJogAngle.setEnabled(value)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsAngleJogEnable).value = value
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinHandwheelsAngleJogValue).value = float(self.inputJogAngle.text())

    def onSpindleRunningChanged(self, value):
        print("onSpindleRunningChanged", value)
        self.radioRpm.setEnabled(not value)
        self.radioCss.setEnabled(not value)
        self.inputRpm.setEnabled(not value)
        self.inputCss.setEnabled(not value)
        self.inputMaxRpm.setEnabled(not value)
        self.inputFeed.setEnabled(not value)
        self.checkBoxFeedAngle.setEnabled(not value)
        self.checkBoxJogAngle.setEnabled(not value)
        self.inputFeedAngle.setEnabled(not value and self.checkBoxFeedAngle.isChecked())
        self.inputJogAngle.setEnabled(not value and self.checkBoxJogAngle.isChecked())
        if self.checkBoxFeedAngle.isChecked() and not value:
            print("Set taper turning off when stopping spindle")
            self.checkBoxFeedAngle.setChecked(False)
            self.checkBoxFeedAngleChanged(False)

    def openNumPad(self, line_edit, spindle_related=False):
        if spindle_related:
            suffix = '-1' if self.isFirstGear else '-2'
        else:
            suffix = ''

        setting_name = getattr(line_edit, 'settingName', None)
        dialog = SmartNumPadDialog(setting_name + suffix)
        dialog.valueSelected.connect(lambda value: line_edit.setText(value))
        line_edit.clearFocus()
        dialog.exec_()

    def onPowerFeedingChanged(self, value):
        self.isPowerFeeding = value
        self.update_actual_feed()

    def onJogIncrementChanged(self, value):
        self.jogIncrement.setText(format(value, '.3f') + ' mm/div')

    def onSpindleFirstGearChanged(self, value):
        self.isFirstGear = value
        # close spindle dialog if open

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
        print("feed_override", override_factor)
        if self.isPowerFeeding:
            calculated_feed = float(self.inputFeed.text()) * override_factor
            self.actualFeed.setText(format(calculated_feed, '.3f'))
        else:
            self.actualFeed.setText("0.000")

    def onSpindleOverrideChanged(self, value):
        self.current_spindle_override = value
        self.handle_spindle_mode(self.getSpindleModeIndex())

    def onFeedOverrideChanged(self, value):
        self.current_feed_override = value
        self.update_actual_feed()

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

    @staticmethod
    def setZDatum():
        issue_mdi('G10 L20 P0 Z0')
