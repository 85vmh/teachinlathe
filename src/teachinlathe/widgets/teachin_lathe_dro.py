import os

from PyQt5 import QtCore, QtWidgets
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from qtpyvcp.widgets.base_widgets.dro_base_widget import Axis

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "teachin_lathe_dro.ui")


class TeachInLatheDro(QWidget):
    xPrimaryDroClicked = QtCore.pyqtSignal(float)
    zPrimaryDroClicked = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        super(TeachInLatheDro, self).__init__(parent)
        uic.loadUi(UI_FILE, self)
        self.status = getPlugin('status')
        self.pos = getPlugin('position')

        self._mm_fmt = '%10.3f'
        self._in_fmt = '%9.4f'
        self._fmt = self._in_fmt
        self.isDiameterMode = True

        self.currentXAbsValue = 0
        self.currentZAbsValue = 0

        self.isXAbs = True
        self.lastXAbsValue = 0

        self.isZAbs = True
        self.lastZAbsValue = 0

        self.xZero.clicked.connect(self.xZeroClicked)
        self.zZero.clicked.connect(self.zZeroClicked)
        self.xAbsRel.clicked.connect(self.xAbsRelClicked)
        self.zAbsRel.clicked.connect(self.zAbsRelClicked)

        self.xPrimaryDro.installEventFilter(self)
        self.zPrimaryDro.installEventFilter(self)

        self.status.program_units.notify(self.updateUnits, 'string')
        getattr(self.pos, 'rel').notify(self.updateValues)
        self.updateUnits()
        self.updateValues()

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            match source:
                case self.xPrimaryDro:
                    # Handle the mouse press event
                    print("Label x clicked")
                    self.xPrimaryDroClicked.emit(float(self.xPrimaryDro.text()))
                    return True
                case self.zPrimaryDro:
                    # Handle the mouse press event
                    print("Label z clicked")
                    self.zPrimaryDroClicked.emit(float(self.zPrimaryDro.text()))
                    return True

        return super().eventFilter(source, event)

    def updateUnits(self, units=None):
        if units is None:
            units = str(self.status.program_units)

        if units == 'in':
            self._fmt = self._in_fmt
        else:
            self._fmt = self._mm_fmt

        self.xUnit.setText(units)
        self.zUnit.setText(units)

        self.updateDro()

    def updateValues(self, pos=None):
        if pos is None:
            pos = getattr(self.pos, 'rel').getValue()

        self.currentXAbsValue = pos[Axis.X]
        self.currentZAbsValue = pos[Axis.Z]
        self.updateDro()

    def xZeroClicked(self):
        self.isXAbs = False
        self.lastXAbsValue = self.currentXAbsValue
        self.updateDro()

    def zZeroClicked(self):
        self.isZAbs = False
        self.lastZAbsValue = self.currentZAbsValue
        self.updateDro()

    def xAbsRelClicked(self):
        self.isXAbs = not self.isXAbs
        if self.isXAbs:
            self.lastXAbsValue = 0
        self.updateDro()

    def zAbsRelClicked(self):
        self.isZAbs = not self.isZAbs
        if self.isZAbs:
            self.lastZAbsValue = 0
        self.updateDro()

    def updateDro(self):
        factor = 2.0 if self.isDiameterMode else 1.0

        if self.isXAbs:
            self.xPrimaryDro.setText(self._fmt % (factor * self.currentXAbsValue))
            self.xSecondaryDro.hide()
        else:
            self.xPrimaryDro.setText(self._fmt % (factor * (self.currentXAbsValue - self.lastXAbsValue)))
            self.xSecondaryDro.setText(self._fmt % (factor * self.currentXAbsValue))
            self.xSecondaryDro.show()

        if self.isZAbs:
            self.zPrimaryDro.setText(self._fmt % self.currentZAbsValue)
            self.zSecondaryDro.hide()
        else:
            self.zPrimaryDro.setText(self._fmt % (self.currentZAbsValue - self.lastZAbsValue))
            self.zSecondaryDro.setText(self._fmt % self.currentZAbsValue)
            self.zSecondaryDro.show()
