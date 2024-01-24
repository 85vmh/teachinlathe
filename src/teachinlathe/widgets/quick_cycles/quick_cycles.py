import os
from enum import Enum
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QColor, QPalette
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.utilities import logger

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
        self.btnBack.clicked.connect(lambda: self.switchPage(Page.ROOT))

        self.turningDoc.mousePressEvent = lambda _: self.openNumPad(self.turningDoc)
        self.boringDoc.mousePressEvent = lambda _: self.openNumPad(self.boringDoc)

        self.turningFilletRadius.mousePressEvent = lambda _: self.openNumPad(self.turningFilletRadius)
        self.boringFilletRadius.mousePressEvent = lambda _: self.openNumPad(self.boringFilletRadius)

        self.turningTurnAngle.mousePressEvent = lambda _: self.openNumPad(self.turningTurnAngle)
        self.boringTurnAngle.mousePressEvent = lambda _: self.openNumPad(self.boringTurnAngle)

        self.turningTeachX.onValueCaptured.connect(self.turningXEndCaptured)
        self.boringTeachX.onValueCaptured.connect(self.boringXEndCaptured)

        self.turningTeachZ.onValueCaptured.connect(self.turningZEndCaptured)
        self.boringTeachZ.onValueCaptured.connect(self.boringZEndCaptured)

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

    def turningXEndCaptured(self, value):
        self.turningXEnd.setText(str(value))

    def boringXEndCaptured(self, value):
        self.boringXEnd.setText(str(value))

    def turningZEndCaptured(self, value):
        self.turningZEnd.setText(str(value))

    def boringZEndCaptured(self, value):
        self.boringZEnd.setText(str(value))

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
                return "facing"
            case Page.CHAMFER.index:
                return "chamfer"
            case Page.RADIUS.index:
                return "radius"
            case _:
                return ""

    def onBtnLoadClicked(self):
        self.onLoadClicked.emit(self._getSubroutineToCall())
