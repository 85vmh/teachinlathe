import os
from enum import Enum
from PyQt5 import QtCore
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
import tempfile

from qtpyvcp.widgets.display_widgets.dro_widget import Axis

from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "quick_cycles.ui")
STATUS = getPlugin('status')


class Page(Enum):
    def __init__(self, index, title, next_btn_text="Load"):
        self.index = index
        self.title = title
        self.next_btn_text = next_btn_text

    ROOT = (0, "Quick Cycles")
    TURNING = (1, "Turning")
    BORING = (2, "Boring")
    FACING = (3, "Facing")
    CHAMFER = (4, "Chamfer")
    RADIUS = (5, "Radius")
    DRILLING = (6, "Drilling")
    KEY_SLOT = (7, "Key Slot")
    THREADING_1 = (8, "Threading (step 1)", "Next")
    THREADING_2 = (9, "Threading (step 2)", "Next")
    THREADING_3 = (10, "Threading (step 3)", "Load")
    THREADING_4 = (11, "Threading (step 4)", None)
    THREADING_5 = (12, "Threading (step 5)", "Load")


class QuickCycles(QWidget):
    onLoadClicked = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(QuickCycles, self).__init__(parent)
        uic.loadUi(UI_FILE, self)

        self.currentXValue = 0
        self.currentZValue = 0

        self.last_thread_x_start = None
        self.last_thread_z_start = None
        self.last_thread_x_end = None

        self.pos = getPlugin('position')
        getattr(self.pos, 'rel').notify(self.updateValues)
        STATUS.task_mode.signal.connect(self.onTaskModeChanged)

        self.isExternalThread = True
        self.switchPage(Page.ROOT)
        self.btnTurning.clicked.connect(lambda: self.switchPage(Page.TURNING))
        self.btnBoring.clicked.connect(lambda: self.switchPage(Page.BORING))
        self.btnFacing.clicked.connect(lambda: self.switchPage(Page.FACING))
        self.btnChamfer.clicked.connect(lambda: self.switchPage(Page.CHAMFER))
        self.btnRadius.clicked.connect(lambda: self.switchPage(Page.RADIUS))
        self.btnThreading.clicked.connect(lambda: self.switchPage(Page.THREADING_1))
        self.btnDrilling.clicked.connect(lambda: self.switchPage(Page.DRILLING))
        self.btnKeySlot.clicked.connect(lambda: self.switchPage(Page.KEY_SLOT))
        self.btnBack.clicked.connect(self.btnOnBackClicked)
        self.btnThreadingFinished.clicked.connect(self.onThreadingFinished)
        self.btnThreadingGoDeeper.clicked.connect(self.onThreadingGoDeeper)

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
        self.newXEnd.mousePressEvent = lambda _: self.openNumPad(self.newXEnd)
        self.threadingZEnd.mousePressEvent = lambda _: self.openNumPad(self.threadingZEnd)
        self.threadingCompute.clicked.connect(self.computeThreadDepth)
        self.threadingCompAngle.mousePressEvent = lambda _: self.openNumPad(self.threadingCompAngle)
        self.handleInternalExternalThread()

        self.keyslotDoc.mousePressEvent = lambda _: self.openNumPad(self.keyslotDoc)
        self.keyslotDoc.mousePressEvent = lambda _: self.openNumPad(self.keyslotDoc)
        self.keyslotFeed.mousePressEvent = lambda _: self.openNumPad(self.keyslotFeed)

        self.btnNext.clicked.connect(self.onBtnNextClicked)
        self.btnMoveToPosX.clicked.connect(self.moveToPosX)
        self.btnMoveToPosZ.clicked.connect(self.moveToPosZ)

    def updateValues(self, pos=None):
        if self.stackedWidget.currentIndex() is not Page.THREADING_3.index:
            return
        if pos is None:
            pos = getattr(self.pos, 'rel').getValue()

        self.currentXValue = pos[Axis.X] * 2
        self.currentZValue = pos[Axis.Z]

        self.last_thread_x_start = self.currentXValue
        self.last_thread_z_start = self.currentZValue

        if self.isExternalThread:
            self.labelRetract.setText(str(round(self.currentXValue - float(self.labelMajorDiameter.text()), 1)))
        else:
            self.labelRetract.setText(str(round(float(self.labelMinorDiameter.text() - self.currentXValue), 1)))

        if self.labelZEnd.text() is not None:
            self.labelThreadLength.setText(str(round(abs(float(self.labelZEnd.text()) - self.currentZValue), 1)))

    def onTaskModeChanged(self, mode):
        print("----quick cycles Task mode changed----")
        print(f"Mode: {mode}")
        print(f"Current index: {self.stackedWidget.currentIndex()}")
        if (self.stackedWidget.currentIndex() in [Page.THREADING_3.index, Page.THREADING_5.index]) and mode == 1:
            print("----Threading finished----")
            self.switchPage(Page.THREADING_4)

    def switchPage(self, page: Page):
        self.stackedWidget.setCurrentIndex(page.index)
        self.title.setText(page.title)
        self.btnBack.setVisible(page != Page.ROOT)
        self.btnNext.setVisible(page != Page.ROOT and page.next_btn_text is not None)
        if page.next_btn_text is not None:
            self.btnNext.setText(page.next_btn_text)

        if page == Page.THREADING_3:
            pitch = self.threadingPitch.text()
            starts = self.threadingStarts.currentText()
            x_start = self.threadingXStart.text()
            x_end = self.threadingXEnd.text()
            infeed_angle = self.threadingCompAngle.text()

            self.labelThreadType.setText(f"External, [{pitch}]mm, [{starts} starts]"
                                         if self.isExternalThread
                                         else f"Internal, [{pitch}]mm, [{starts} starts]")
            self.labelMajorDiameter.setText(x_start if self.isExternalThread else x_end)
            self.labelMinorDiameter.setText(x_end if self.isExternalThread else x_start)
            self.labelZEnd.setText(self.threadingZEnd.text())
            self.labelDepthDegression.setText(self.threadingDepthDegression.currentText())
            self.labelFirstPassDoc.setText(self.threadingFirstPass.text())
            self.labelTaperLocation.setText(self.threadingTaper.currentText())
            self.labelSpringPasses.setText(self.threadingSpringPasses.currentText())
            self.updateValues()
        if page == Page.THREADING_5:
            self.currentThreadXStart.setText(str(round(self.last_thread_x_start, 3)))
            self.currentThreadZStart.setText(str(round(self.last_thread_z_start, 3)))
            self.lastXEnd.setText(str(self.last_thread_x_end))

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
            case Page.THREADING_3.index:
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

                self.last_thread_x_end = x_end
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
            case Page.THREADING_5.index:
                pitch = self.threadingPitch.text()
                starts = self.threadingStarts.currentText()
                z_end = self.threadingZEnd.text()
                x_start = self.threadingXStart.text()
                x_end = self.newXEnd.text()
                first_pass = abs(float(x_start) - float(self.last_thread_x_end))
                depth_degression = self.threadingDepthDegression.currentText()
                infeed_angle = self.threadingCompAngle.text()
                taper = self.threadingTaper.currentIndex()
                spring_passes = self.threadingNewSpringPasses.currentText()

                self.last_thread_x_end = x_end
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

    def onThreadingFinished(self):
        self.switchPage(Page.ROOT)
        self.last_thread_x_start = None
        self.last_thread_z_start = None

    def onThreadingGoDeeper(self):
        self.switchPage(Page.THREADING_5)

    def btnOnBackClicked(self):
        match self.stackedWidget.currentIndex():
            case Page.THREADING_2.index:
                self.switchPage(Page.THREADING_1)
            case Page.THREADING_3.index:
                self.switchPage(Page.THREADING_2)
            case _:
                self.switchPage(Page.ROOT)

    def onForceStep4(self):
        print("Force step 4")
        self.switchPage(Page.THREADING_4)

    def onBtnNextClicked(self):
        match self.stackedWidget.currentIndex():
            case Page.THREADING_1.index:
                self.switchPage(Page.THREADING_2)
            case Page.THREADING_2.index:
                self.switchPage(Page.THREADING_3)
            case _:
                self.onLoadClicked.emit(self._getSubroutineToCall())

    def moveToPosX(self):
        if self.last_thread_x_start is None:
            return
        issue_mdi(f"G0 X{self.last_thread_x_start}")

    def moveToPosZ(self):
        if self.last_thread_z_start is None:
            return
        issue_mdi(f"G0 Z{self.last_thread_z_start}")
