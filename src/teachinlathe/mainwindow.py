# Setup logging
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from PyQt5.QtCore import QTimer
from qtpyvcp.widgets.form_widgets.main_window import VCPMainWindow

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.manual_lathe import ManualLathe
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog

LOG = logger.getLogger('qtpyvcp.' + __name__)

STATUS = getPlugin('status')


class MyMainWindow(VCPMainWindow):
    """Main window class for the VCP."""

    def __init__(self, *args, **kwargs):
        super(MyMainWindow, self).__init__(*args, **kwargs)
        self.manualLathe = ManualLathe()
        self.latheComponent = TeachInLatheComponent()
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleActualRpm, self.onSpindleRpmChanged)

        STATUS.spindle[0].override.signal.connect(self.onSpindleOverrideChanged)
        STATUS.feedrate.signal.connect(self.onFeedOverrideChanged)

        self.current_spindle_override = STATUS.spindle[0].override.value
        self.current_feed_override = STATUS.feedrate.value

        print("self.current_spindle_override", self.current_spindle_override)
        print("self.current_feed_override", self.current_feed_override)

        self.handle_spindle_mode(self.tabSpindleMode.currentIndex())
        self.handle_feed_mode(self.feedType.currentIndex())

        self.lastSpindleRpm = 0

        self.debounce_timer = QTimer()
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.onRpmDebounced)
        self.debounce_timer.start()

        self.feedType.addItem("mm/rev")
        self.feedType.addItem("mm/min")
        self.feedType.currentIndexChanged.connect(self.onFeedTypeChanged)

        self.openDialog.clicked.connect(self.openNumPad)
        # set the current values
        self.manualLathe.onSpindleModeChanged(self.tabSpindleMode.currentIndex())
        self.manualLathe.onFeedModeChanged(self.feedType.currentIndex())
        self.manualLathe.onInputRpmChanged(self.inputRpm.text())
        self.manualLathe.onInputCssChanged(self.inputCss.text())
        self.manualLathe.onMaxSpindleRpmChanged(self.inputMaxRpm.text())
        self.manualLathe.onStopAtActiveChanged(self.checkBoxStopAt.isChecked())
        self.manualLathe.onStopAtAngleChanged(self.inputStopAt.text())
        self.manualLathe.onInputFeedChanged(self.inputFeed.text())
        self.manualLathe.onTaperTurningChanged(self.checkBoxTaperTurning.isChecked())
        self.manualLathe.onFeedTaperAngleChanged(self.inputTaperAngle.text())

        # connect the signals
        self.tabSpindleMode.currentChanged.connect(self.manualLathe.onSpindleModeChanged)
        self.feedType.currentIndexChanged.connect(self.manualLathe.onFeedModeChanged)

        self.inputRpm.textChanged.connect(self.manualLathe.onInputRpmChanged)
        self.inputCss.textChanged.connect(self.manualLathe.onInputCssChanged)
        self.inputMaxRpm.textChanged.connect(self.manualLathe.onMaxSpindleRpmChanged)
        self.checkBoxStopAt.stateChanged.connect(self.manualLathe.onStopAtAngleChanged)
        self.inputStopAt.textChanged.connect(self.manualLathe.onStopAtAngleChanged)
        self.inputFeed.textChanged.connect(self.manualLathe.onInputFeedChanged)
        self.checkBoxTaperTurning.stateChanged.connect(self.manualLathe.onTaperTurningChanged)
        self.inputTaperAngle.textChanged.connect(self.manualLathe.onFeedTaperAngleChanged)

    def onSpindleRunningChanged(self, value):
        print("onSpindleRunningChanged", value)
        self.tabSpindleMode.setEnabled(not value)
        self.inputRpm.setEnabled(not value)
        self.inputCss.setEnabled(not value)
        self.inputMaxRpm.setEnabled(not value)
        self.inputStopAt.setEnabled(not value)
        self.checkBoxStopAt.setEnabled(not value)
        self.feedType.setEnabled(not value)
        self.inputFeed.setEnabled(not value)

    def openNumPad(self):
        self.dialog = SmartNumPadDialog(self)
        self.dialog.show()

        # self.window = QtWidgets.QDialog()
        # self.ui = SmartNumPadDialog()
        # self.ui.setupUi(self.window)
        # self.window.show()

    def onFeedTypeChanged(self, index):
        self.actualFeedType.setText(self.feedType.currentText())

    def onSpindleRpmChanged(self, value):
        self.lastSpindleRpm = int(value)
        print("non debounced value", self.lastSpindleRpm)

    def onRpmDebounced(self):
        self.actualRpm.setText(str(self.lastSpindleRpm))

    def handle_spindle_mode(self, index):
        override_factor = self.current_spindle_override
        print("sp_override", override_factor)
        print("int(self.inputCss.text()) :", int(self.inputCss.text()))
        print("result: ", str(int(int(self.inputCss.text()) * override_factor)))
        if index == 1:
            self.actualCss.setText(str(int(int(self.inputCss.text()) * override_factor)))

    def handle_feed_mode(self, index):
        override_factor = self.current_feed_override
        print("sp_override", override_factor)
        match index:
            case 0:
                self.actualFeed.setText(str(int(self.inputFeed.text()) * override_factor))
            case 1:
                self.actualFeed.setText(str(int(self.inputFeed.text()) * override_factor))

    def onSpindleOverrideChanged(self, value):
        self.current_spindle_override = value
        self.handle_spindle_mode(self.tabSpindleMode.currentIndex())

    def onFeedOverrideChanged(self, value):
        self.current_feed_override = value
        self.handle_feed_mode(self.feedType.currentIndex())
