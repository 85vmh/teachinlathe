import os

from PyQt5 import QtCore, QtWidgets
from qtpy import uic
from qtpy.QtWidgets import QWidget
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from qtpyvcp.widgets.base_widgets.dro_base_widget import Axis
from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.machine_limits import MachineLimitsHandler

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "teachin_lathe_dro.ui")


class TeachInLatheDro(QWidget):
    xPrimaryDroClicked = QtCore.pyqtSignal(float)
    zPrimaryDroClicked = QtCore.pyqtSignal(float)

    def __init__(self, parent=None):
        super(TeachInLatheDro, self).__init__(parent)
        uic.loadUi(UI_FILE, self)
        self.limitsHandler = MachineLimitsHandler()
        self.latheComponent = TeachInLatheComponent()

        self.status = getPlugin('status')
        self.pos = getPlugin('position')

        self._mm_fmt = '%10.3f'
        self._in_fmt = '%9.4f'
        self._fmt = self._in_fmt
        self.isDiameterMode = True

        self.previousMachineLimits = None
        self.currentMachineLimits = None

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

        self.xMinusLimitToggle(False)
        self.xPlusLimitToggle(False)
        self.zMinusLimitToggle(False)
        self.zPlusLimitToggle(False)
        self.xMinusLimit.stateChanged.connect(self.xMinusLimitToggle)
        self.xPlusLimit.stateChanged.connect(self.xPlusLimitToggle)
        self.zMinusLimit.stateChanged.connect(self.zMinusLimitToggle)
        self.zPlusLimit.stateChanged.connect(self.zPlusLimitToggle)

        self.xPrimaryDro.installEventFilter(self)
        self.zPrimaryDro.installEventFilter(self)

        self.status.program_units.notify(self.updateUnits, 'string')
        getattr(self.pos, 'rel').notify(self.updateValues)
        getattr(self.pos, 'abs').notify(self.positionUpdated)

        self.limitsHandler.onLimitsChanged.connect(self.onMachineLimitsChanged)
        self.limitsHandler.onDefaultLimits.connect(self.setDefaultMachineLimits)
        self.updateUnits()
        self.updateValues()

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            match source:
                case self.xPrimaryDro:
                    self.xPrimaryDroClicked.emit(float(self.xPrimaryDro.text()))
                    return True
                case self.zPrimaryDro:
                    self.zPrimaryDroClicked.emit(float(self.zPrimaryDro.text()))
                    return True

        return super().eventFilter(source, event)

    def xMinusLimitToggle(self, state):
        self.droXMinus.setEnabled(state)
        self.teachXMinus.setEnabled(state)

    def xPlusLimitToggle(self, state):
        self.droXPlus.setEnabled(state)
        self.teachXPlus.setEnabled(state)

    def zMinusLimitToggle(self, state):
        self.droZMinus.setEnabled(state)
        self.teachZMinus.setEnabled(state)

    def zPlusLimitToggle(self, state):
        self.droZPlus.setEnabled(state)
        self.teachZPlus.setEnabled(state)

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

    def onMachineLimitsChanged(self, machine_limits):
        print("Machine limits changed: ", machine_limits)
        self.currentMachineLimits = machine_limits

    def setDefaultMachineLimits(self, limits):
        print("setting default limits: ", limits)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = limits.x_min_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = limits.x_max_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = limits.z_min_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = limits.z_max_limit

    def positionUpdated(self, pos):
        if self.previousMachineLimits != self.currentMachineLimits:
            if pos is None:
                pos = getattr(self.pos, 'abs').getValue()
            x_abs = pos[Axis.X]
            z_abs = pos[Axis.Z]

            x_min_applied = False
            x_max_applied = False
            z_min_applied = False
            z_max_applied = False

            self.currentMachineLimits = self.limitsHandler.getMachineLimits()

            if x_abs > self.currentMachineLimits.x_min_limit:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = self.currentMachineLimits.x_min_limit
                x_min_applied = True
            else:
                print("Back off from X- to activate the X- virtual limit")

            if x_abs < self.currentMachineLimits.x_max_limit:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = self.currentMachineLimits.x_max_limit
                x_max_applied = True
            else:
                print("Back off from X+ to activate the X+ virtual limit")

            if z_abs > self.currentMachineLimits.z_min_limit:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = self.currentMachineLimits.z_min_limit
                z_min_applied = True
            else:
                print("Back off from Z- to activate the Z- virtual limit")

            if z_abs < self.currentMachineLimits.z_max_limit:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = self.currentMachineLimits.z_max_limit
                z_max_applied = True
            else:
                print("Back off from Z+ to activate the Z+ virtual limit")

            if x_min_applied and x_max_applied and z_min_applied and z_max_applied:
                self.previousMachineLimits = self.currentMachineLimits
                print("-----All limits applied-------")