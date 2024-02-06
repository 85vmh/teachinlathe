import os
from enum import Enum
from PyQt5 import QtCore
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.utilities import logger
import tempfile

from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "quick_cycles.ui")


class Page(Enum):
    def __init__(self, index, title):
        self.index = index
        self.title = title

    ROOT = (0, "Quick Cycles")
    TURNING = (1, "Turning")
    BORING = (2, "Boring")
    FACING = (3, "Facing")
    CHAMFER = (4, "Chamfer")
    RADIUS = (5, "Radius")
    DRILLING = (6, "Drilling")
    THREADING = (7, "Threading")
    KEY_SLOT = (8, "Key Slot")


class QuickCycles(QWidget):
    onLoadClicked = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(QuickCycles, self).__init__(parent)
        uic.loadUi(UI_FILE, self)
        self.switchPage(Page.ROOT)
        self.btnTurning.clicked.connect(lambda: self.switchPage(Page.TURNING))
        self.btnBoring.clicked.connect(lambda: self.switchPage(Page.BORING))
        self.btnFacing.clicked.connect(lambda: self.switchPage(Page.FACING))
        self.btnChamfer.clicked.connect(lambda: self.switchPage(Page.CHAMFER))
        self.btnRadius.clicked.connect(lambda: self.switchPage(Page.RADIUS))
        self.btnThreading.clicked.connect(lambda: self.switchPage(Page.THREADING))
        self.btnDrilling.clicked.connect(lambda: self.switchPage(Page.DRILLING))
        self.btnKeySlot.clicked.connect(lambda: self.switchPage(Page.KEY_SLOT))
        self.btnBack.clicked.connect(lambda: self.switchPage(Page.ROOT))

        self.turningDoc.mousePressEvent = lambda _: self.openNumPad(self.turningDoc)
        self.boringDoc.mousePressEvent = lambda _: self.openNumPad(self.boringDoc)
        self.facingDoc.mousePressEvent = lambda _: self.openNumPad(self.facingDoc)
        self.keyslotDoc.mousePressEvent = lambda _: self.openNumPad(self.keyslotDoc)
        self.drillingFeed.mousePressEvent = lambda _: self.openNumPad(self.drillingFeed)
        self.keyslotFeed.mousePressEvent = lambda _: self.openNumPad(self.keyslotFeed)
        self.threadingPitch.mousePressEvent = lambda _: self.openNumPad(self.threadingPitch)
        self.threadingFirstPass.mousePressEvent = lambda _: self.openNumPad(self.threadingFirstPass)
        self.threadingCompAngle.mousePressEvent = lambda _: self.openNumPad(self.threadingCompAngle)
        self.radiusValue.mousePressEvent = lambda _: self.openNumPad(self.radiusValue)
        self.radiusDoc.mousePressEvent = lambda _: self.openNumPad(self.radiusDoc)

        self.turningFilletRadius.mousePressEvent = lambda _: self.openNumPad(self.turningFilletRadius)
        self.boringFilletRadius.mousePressEvent = lambda _: self.openNumPad(self.boringFilletRadius)

        self.turningTurnAngle.mousePressEvent = lambda _: self.openNumPad(self.turningTurnAngle)
        self.boringTurnAngle.mousePressEvent = lambda _: self.openNumPad(self.boringTurnAngle)

        self.btnLoad.clicked.connect(self.onBtnLoadClicked)

    def switchPage(self, page: Page):
        self.stackedWidget.setCurrentIndex(page.index)
        self.title.setText(page.title)
        self.btnBack.setVisible(page != Page.ROOT)
        self.btnLoad.setVisible(page != Page.ROOT)

    def openNumPad(self, line_edit):
        setting_name = getattr(line_edit, 'settingName', None)
        dialog = SmartNumPadDialog(setting_name)
        dialog.valueSelected.connect(lambda value: self.setSelectedValue(line_edit, value))
        dialog.exec_()

    @staticmethod
    def setSelectedValue(line_edit, value):
        line_edit.setText(value)
        line_edit.editingFinished.emit()
        line_edit.clearFocus()

    def _getSubroutineToCall(self):
        match self.stackedWidget.currentIndex():
            case Page.TURNING.index:
                x_end = self.turningXEnd.text()
                z_end = self.turningZEnd.text()
                doc = self.turningDoc.text()
                t_angle = self.turningTurnAngle.text()
                f_radius = self.turningFilletRadius.text()
                return f"o<turning> call [{x_end}] [{z_end}] [{doc}] [{t_angle}] [{f_radius}]"
            case Page.BORING.index:
                x_end = self.boringXEnd.text()
                z_end = self.boringZEnd.text()
                doc = self.boringDoc.text()
                t_angle = self.boringTurnAngle.text()
                f_radius = self.boringFilletRadius.text()
                return f"o<boring> call [{x_end}] [{z_end}] [{doc}] [{t_angle}] [{f_radius}]"
            case Page.FACING.index:
                x_end = self.facingXEnd.text()
                z_end = self.facingZEnd.text()
                doc = self.facingDoc.text()
                return f"o<facing> call [{x_end}] [{z_end}] [{doc}]"
            case Page.CHAMFER.index:
                return "chamfer"
            case Page.RADIUS.index:
                x_end = self.radiusXEnd.text()
                z_end = self.radiusZEnd.text()
                radius = self.radiusValue.text()
                doc = self.radiusDoc.text()
                location = self.radiusLocation.currentIndex()
                return f"o<radius> call [{x_end}] [{z_end}] [{radius}] [{doc}] [{location}]"
            case Page.THREADING.index:
                '''
                val pitch = parameters.pitch.stripZeros()
                val zEnd = parameters.zEnd.stripZeros()
                val startDiameter =
                    when {
                        parameters.isExternal -> parameters.majorDiameter.stripZeros()
                        else -> parameters.minorDiameter.stripZeros()
                    }
                val firstPassDoc = parameters.firstPassDepth.stripZeros()
                val finalDepth = parameters.finalDepth.stripZeros()
                val depthDegression = 1
                val infeedAngle = 30
                val taper = 0
                val springPasses = 0'''

                pitch = self.threadingPitch.text()
                starts = self.threadingStarts.text()
                zEnd = self.threadingZEnd.text()
                xStart = self.threadingXStart.text()
                xEnd = self.threadingFinalDepth.text()
                firstPass = self.threadingFirstPass.text()
                depthDegression = self.threadingDepthDegression.text()

                return f"o<threading> call [{pitch}] [{zEnd}] [{xStart}] [{firstPass}] [{xEnd}] [{depthDegression}] [$infeedAngle] [2] [45] [$springPasses]"
            case Page.DRILLING.index:
                z_end = self.drillingZEnd.text()
                retract = self.drillingRetract.text()
                peck_depth = self.drillingPeckDepth.text()
                feed = self.turningTurnAngle.text()
                return f"o<drilling> call [{z_end}] [{retract}] [{peck_depth}] [{feed}]"
            case Page.KEY_SLOT.index:
                x_end = self.keyslotXEnd.text()
                z_end = self.keyslotZEnd.text()
                doc = self.keyslotDoc.text()
                feed = self.keyslotFeed.text()
                return f"o<keyslot> call [{x_end}] [{z_end}] [{doc}] [{feed}]"
            case _:
                return ""

    def onBtnLoadClicked(self):
        self.onLoadClicked.emit(self._getSubroutineToCall())
