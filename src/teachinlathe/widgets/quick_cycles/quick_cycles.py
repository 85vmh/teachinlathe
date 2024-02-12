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
        self.isExternalThread = True
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

        self.turningXEnd.mousePressEvent = lambda _: self.openNumPad(self.turningXEnd)
        self.turningZEnd.mousePressEvent = lambda _: self.openNumPad(self.turningZEnd)
        self.turningDoc.mousePressEvent = lambda _: self.openNumPad(self.turningDoc)
        self.turningTurnAngle.mousePressEvent = lambda _: self.openNumPad(self.turningTurnAngle)
        self.turningFilletRadius.mousePressEvent = lambda _: self.openNumPad(self.turningFilletRadius)

        self.boringXEnd.mousePressEvent = lambda _: self.openNumPad(self.boringXEnd)
        self.boringZEnd.mousePressEvent = lambda _: self.openNumPad(self.boringZEnd)
        self.boringDoc.mousePressEvent = lambda _: self.openNumPad(self.boringDoc)
        self.boringTurnAngle.mousePressEvent = lambda _: self.openNumPad(self.boringTurnAngle)
        self.boringFilletRadius.mousePressEvent = lambda _: self.openNumPad(self.boringFilletRadius)

        self.facingXEnd.mousePressEvent = lambda _: self.openNumPad(self.facingXEnd)
        self.facingZEnd.mousePressEvent = lambda _: self.openNumPad(self.facingZEnd)
        self.facingDoc.mousePressEvent = lambda _: self.openNumPad(self.facingDoc)

        self.chamferCornerX.mousePressEvent = lambda _: self.openNumPad(self.chamferCornerX)
        self.chamferCornerZ.mousePressEvent = lambda _: self.openNumPad(self.chamferCornerZ)
        self.chamferWidth.mousePressEvent = lambda _: self.openNumPad(self.chamferWidth)
        self.chamferDoc.mousePressEvent = lambda _: self.openNumPad(self.chamferDoc)

        self.radiusCornerX.mousePressEvent = lambda _: self.openNumPad(self.radiusCornerX)
        self.radiusCornerZ.mousePressEvent = lambda _: self.openNumPad(self.radiusCornerZ)
        self.radiusValue.mousePressEvent = lambda _: self.openNumPad(self.radiusValue)
        self.radiusDoc.mousePressEvent = lambda _: self.openNumPad(self.radiusDoc)

        self.drillingZEnd.mousePressEvent = lambda _: self.openNumPad(self.drillingZEnd)
        self.drillingZRetract.mousePressEvent = lambda _: self.openNumPad(self.drillingZRetract)
        self.drillingFeed.mousePressEvent = lambda _: self.openNumPad(self.drillingFeed)
        self.drillingPeckDepth.mousePressEvent = lambda _: self.openNumPad(self.drillingPeckDepth)
        self.drillingRpm.mousePressEvent = lambda _: self.openNumPad(self.drillingRpm)

        self.threadLocationGroup.buttonClicked.connect(self.handleInternalExternalThread)
        self.threadingPitch.mousePressEvent = lambda _: self.openNumPad(self.threadingPitch)
        self.threadingFirstPass.mousePressEvent = lambda _: self.openNumPad(self.threadingFirstPass)
        self.threadingXStart.mousePressEvent = lambda _: self.openNumPad(self.threadingXStart)
        self.threadingXEnd.mousePressEvent = lambda _: self.openNumPad(self.threadingXEnd)
        self.threadingZEnd.mousePressEvent = lambda _: self.openNumPad(self.threadingZEnd)
        self.threadingCompute.clicked.connect(self.computeThreadDepth)
        self.threadingCompAngle.mousePressEvent = lambda _: self.openNumPad(self.threadingCompAngle)
        self.handleInternalExternalThread()

        self.keyslotDoc.mousePressEvent = lambda _: self.openNumPad(self.keyslotDoc)
        self.keyslotDoc.mousePressEvent = lambda _: self.openNumPad(self.keyslotDoc)
        self.keyslotFeed.mousePressEvent = lambda _: self.openNumPad(self.keyslotFeed)

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

    def handleInternalExternalThread(self):
        if self.threadLocationGroup.checkedButton().text() == "External":
            self.threadLabelXStart.setText("Major Diam.")
            self.threadLabelXEnd.setText("Minor Diam.")
            self.isExternalThread = True
        else:
            self.threadLabelXStart.setText("Minor Diam.")
            self.threadLabelXEnd.setText("Major Diam.")
            self.isExternalThread = False

    def computeThreadDepth(self):
        pitch = self.threadingPitch.text()
        x_start = self.threadingXStart.text()
        external_height = float(pitch) * 0.61344
        internal_height = float(pitch) * 0.54127

        if self.isExternalThread:
            x_end = float(x_start) - external_height * 2
        else:
            x_end = float(x_start) + internal_height * 2

        self.threadingXEnd.setText(str(round(x_end, 3)))

    def _getSubroutineToCall(self):
        match self.stackedWidget.currentIndex():
            case Page.TURNING.index:
                x_end = self.turningXEnd.text()
                z_end = self.turningZEnd.text()
                doc = self.turningDoc.text()
                t_angle = self.turningTurnAngle.text()
                f_radius = self.turningFilletRadius.text()
                return f"o<turning> call [#<_x> * 2] [#<_z>] [{x_end}] [{z_end}] [{doc}] [{t_angle}] [{f_radius}]"
            case Page.BORING.index:
                x_end = self.boringXEnd.text()
                z_end = self.boringZEnd.text()
                doc = self.boringDoc.text()
                t_angle = self.boringTurnAngle.text()
                f_radius = self.boringFilletRadius.text()
                return f"o<boring> call [#<_x> * 2] [#<_z>] [{x_end}] [{z_end}] [{doc}] [{t_angle}] [{f_radius}]"
            case Page.FACING.index:
                x_end = self.facingXEnd.text()
                z_end = self.facingZEnd.text()
                doc = self.facingDoc.text()
                return f"o<facing> call [#<_x> * 2] [#<_z>] [{x_end}] [{z_end}] [{doc}]"
            case Page.CHAMFER.index:
                corner_x = self.chamferCornerX.text()
                corner_z = self.chamferCornerZ.text()
                chamfer = self.chamferWidth.text()
                doc = self.radiusDoc.text()
                location = self.radiusLocation.currentIndex()
                return f"o<chamfer> call [#<_x> * 2] [#<_z>] [{corner_x}] [{corner_z}] [{chamfer}] [{doc}] [{location}]"
            case Page.RADIUS.index:
                corner_x = self.radiusCornerX.text()
                corner_z = self.radiusCornerZ.text()
                radius = self.radiusValue.text()
                doc = self.radiusDoc.text()
                location = self.radiusLocation.currentIndex()
                return f"o<radius> call [#<_x> * 2] [#<_z>] [{corner_x}] [{corner_z}] [{radius}] [{doc}] [{location}]"
            case Page.THREADING.index:
                pitch = self.threadingPitch.text()
                starts = self.threadingStarts.currentText()
                z_end = self.threadingZEnd.text()
                x_start = self.threadingXStart.text()
                x_end = self.threadingXEnd.text()
                first_pass = self.threadingFirstPass.text()
                depth_degression = self.threadingDepthDegression.currentText()
                infeed_angle = self.threadingCompAngle.text()
                taper = self.threadingTaper.currentIndex()
                spring_passes = self.threadingSpringPasses.currentText()
                return (f"o<threading> call "
                        f"[{x_start}] "
                        f"[#<_z>] "
                        f"[{x_end}] "
                        f"[{z_end}] "
                        f"[{pitch}] "
                        f"[{starts}] "
                        f"[{first_pass}] "
                        f"[{depth_degression}] "
                        f"[{infeed_angle}] "
                        f"[{taper}] "
                        f"[{45}] "
                        f"[{spring_passes}]")
            case Page.DRILLING.index:
                z_end = self.drillingZEnd.text()
                retract = self.drillingZRetract.text()
                peck_depth = self.drillingPeckDepth.text()
                rpm = self.drillingRpm.text()
                feed = self.drillingFeed.text()
                return f"o<drilling> call [#<_x> * 2] [#<_z>] [{z_end}] [{retract}] [{peck_depth}] [{rpm}] [{feed}]"
            case Page.KEY_SLOT.index:
                x_end = self.keyslotXEnd.text()
                z_end = self.keyslotZEnd.text()
                doc = self.keyslotDoc.text()
                feed = self.keyslotFeed.text()
                return f"o<keyslot> call [#<_x>] [#<_z>] [{x_end}] [{z_end}] [{doc}] [{feed}]"
            case _:
                return ""

    def onBtnLoadClicked(self):
        self.onLoadClicked.emit(self._getSubroutineToCall())
