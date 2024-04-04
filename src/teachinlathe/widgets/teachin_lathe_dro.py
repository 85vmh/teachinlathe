import os
from enum import Enum

from PyQt5 import QtCore, QtWidgets
from qtpy import uic
from qtpyvcp.utilities.info import Info
from qtpy.QtWidgets import QWidget
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from qtpyvcp.widgets.base_widgets.dro_base_widget import Axis
from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.machine_limits import MachineLimitsHandler

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "teachin_lathe_dro.ui")
INFO = Info()


class LimitsTabs(Enum):
    MAIN = 0
    EDIT = 1


class LimitsStyle(Enum):
    ENABLED = 0
    DISABLED = 1
    PENDING = 2


class TeachInLatheDro(QWidget):
    xPrimaryDroClicked = QtCore.pyqtSignal(float)
    zPrimaryDroClicked = QtCore.pyqtSignal(float)

    limit_enabled = """
        border-style: solid;
        border-color: rgb(26, 95, 180);
        border-width: 1px;
        border-radius: 5px;
        color: white;
        background: rgb(26, 95, 180);
        font: 10pt "Noto Sans Mono";
    """

    limit_disabled = """
        border-style: solid;
        border-color: rgb(119, 118, 123);
        border-width: 1px;
        border-radius: 5px;
        color: rgb(154, 153, 150);
        background: rgb(246, 245, 244);
        font: 10pt "Noto Sans Mono";
    """

    limit_pending = """
            border-style: solid;
            border-color: rgb(26, 95, 180);
            border-width: 1px;
            border-radius: 5px;
            color: rgb(154, 153, 150);
            background: rgb(246, 245, 244);
            font: 10pt "Noto Sans Mono";
        """

    def __init__(self, parent=None):
        super(TeachInLatheDro, self).__init__(parent)
        uic.loadUi(UI_FILE, self)
        self.limitsHandler = MachineLimitsHandler()
        self.latheComponent = TeachInLatheComponent()

        self.status = getPlugin('status')
        self.pos = getPlugin('position')

        self._mm_fmt = '%10.3f'
        self._in_fmt = '%9.4f'
        self._fmt = self._mm_fmt
        self.isDiameterMode = True

        self.previousMachineLimits = None
        self.currentMachineLimits = None

        self.currentXAbsValue = 0
        self.currentZAbsValue = 0

        self.isXAbs = True
        self.lastXAbsValue = 0

        self.isZAbs = True
        self.lastZAbsValue = 0

        self.tool_rel_position = [0] * 9

        self.xZero.clicked.connect(self.xZeroClicked)
        self.zZero.clicked.connect(self.zZeroClicked)
        self.xAbsRel.clicked.connect(self.xAbsRelClicked)
        self.zAbsRel.clicked.connect(self.zAbsRelClicked)
        self.editLimits.clicked.connect(self.editLimitsClicked)
        self.saveLimits.clicked.connect(self.saveLimitsClicked)

        self.xMinusActive = False
        self.xPlusActive = False
        self.zMinusActive = False
        self.zPlusActive = False
        self.tailstockActive = False

        self.applyCurrentLimits()
        self.droXMinus.textChanged.connect(self.droXMinusChanged)
        self.droXPlus.textChanged.connect(self.droXPlusChanged)
        self.droZMinus.textChanged.connect(self.droZMinusChanged)
        self.droZPlus.textChanged.connect(self.droZPlusChanged)
        self.droTailstock.textChanged.connect(self.droTailstockChanged)

        self.xPrimaryDro.installEventFilter(self)
        self.zPrimaryDro.installEventFilter(self)
        self.xMinusLimit.installEventFilter(self)
        self.xPlusLimit.installEventFilter(self)
        self.zMinusLimit.installEventFilter(self)
        self.zPlusLimit.installEventFilter(self)
        self.tailstockLimit.installEventFilter(self)

        self.status.program_units.notify(self.updateUnits, 'string')
        getattr(self.pos, 'rel').notify(self.updateValues)
        getattr(self.pos, 'abs').notify(self.positionUpdated)

        self.status.g5x_offset.signal.connect(self._updateToolRelativePos)
        self.status.g92_offset.signal.connect(self._updateToolRelativePos)
        self.status.tool_offset.signal.connect(self._updateToolRelativePos)

        self.limitsHandler.onLimitsChanged.connect(self.onMachineLimitsChanged)
        self.limitsHandler.onDefaultLimits.connect(self.setDefaultMachineLimits)
        self.updateUnits()
        self.updateValues()

    def editLimitsClicked(self):
        self.limitsTabs.setCurrentIndex(LimitsTabs.EDIT.value)

    def saveLimitsClicked(self):
        self.limitsTabs.setCurrentIndex(LimitsTabs.MAIN.value)

    def applyCurrentLimits(self):
        self.droXMinusChanged(self.droXMinus.text())
        self.droXPlusChanged(self.droXPlus.text())
        self.droZMinusChanged(self.droZMinus.text())
        self.droZPlusChanged(self.droZPlus.text())
        self.droTailstockChanged(self.droTailstock.text())

    def _updateToolRelativePos(self):
        g5x_offset = self.status.stat.g5x_offset
        g92_offset = self.status.stat.g92_offset
        tool_offset = self.status.stat.tool_offset

        for axis in INFO.AXIS_NUMBER_LIST:
            self.tool_rel_position[axis] = g5x_offset[axis] + tool_offset[axis] + g92_offset[axis]

        print("---Tool relative position: ", self.tool_rel_position)
        self.applyCurrentLimits()

    def droXMinusChanged(self, value):
        self.xMinusLimit.setText(self._fmt % (float(value)))
        self.limitsHandler.setXMinusLimit(self.tool_rel_position[0] + float(value) / 2)

    def droXPlusChanged(self, value):
        self.xPlusLimit.setText(self._fmt % (float(value)))
        self.limitsHandler.setXPlusLimit(self.tool_rel_position[0] + float(value) / 2)

    def droZMinusChanged(self, value):
        self.zMinusLimit.setText(self._fmt % float(value))
        self.limitsHandler.setZMinusLimit(self.tool_rel_position[2] + float(value))

    def droZPlusChanged(self, value):
        self.zPlusLimit.setText(self._fmt % float(value))
        self.limitsHandler.setZPlusLimit(self.tool_rel_position[2] + float(value))

    def droTailstockChanged(self, value):
        self.tailstockLimit.setText(self._fmt % float(value))
        self.limitsHandler.setTailstockLimit(float(value))

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            match source:
                case self.xPrimaryDro:
                    self.xPrimaryDroClicked.emit(float(self.xPrimaryDro.text()))
                    return True
                case self.zPrimaryDro:
                    self.zPrimaryDroClicked.emit(float(self.zPrimaryDro.text()))
                    return True
                case self.xMinusLimit:
                    self.xMinusLimitToggle()
                    return True
                case self.xPlusLimit:
                    self.xPlusLimitToggle()
                    return True
                case self.zMinusLimit:
                    self.zMinusLimitToggle()
                    return True
                case self.zPlusLimit:
                    self.zPlusLimitToggle()
                    return True
                case self.tailstockLimit:
                    self.tailstockLimitToggle()
                    return True

        return super().eventFilter(source, event)

    def setLimitStyle(self, limit, style):
        limit.setStyleSheet({
            LimitsStyle.ENABLED: self.limit_enabled,
            LimitsStyle.DISABLED: self.limit_disabled,
            LimitsStyle.PENDING: self.limit_pending
        }[style])

    def xMinusLimitToggle(self):
        self.xMinusActive = not self.xMinusActive
        if self.xMinusActive:
            self.xMinusLimit.setStyleSheet(self.limit_enabled)
        else:
            self.xMinusLimit.setStyleSheet(self.limit_disabled)
        self.limitsHandler.setXMinusLimitActive(self.xMinusActive)

    def xPlusLimitToggle(self):
        self.xPlusActive = not self.xPlusActive
        if self.xPlusActive:
            self.xPlusLimit.setStyleSheet(self.limit_enabled)
        else:
            self.xPlusLimit.setStyleSheet(self.limit_disabled)
        self.limitsHandler.setXPlusLimitActive(self.xPlusActive)

    def zMinusLimitToggle(self):
        self.zMinusActive = not self.zMinusActive
        if self.zMinusActive:
            self.zMinusLimit.setStyleSheet(self.limit_enabled)
        else:
            self.zMinusLimit.setStyleSheet(self.limit_disabled)
        self.limitsHandler.setZMinusLimitActive(self.zMinusActive)

    def zPlusLimitToggle(self):
        self.zPlusActive = not self.zPlusActive
        if self.zPlusActive:
            self.zPlusLimit.setStyleSheet(self.limit_enabled)
        else:
            self.zPlusLimit.setStyleSheet(self.limit_disabled)
        self.limitsHandler.setZPlusLimitActive(self.zPlusActive)

    def tailstockLimitToggle(self):
        self.tailstockActive = not self.tailstockActive
        if self.tailstockActive:
            self.tailstockLimit.setStyleSheet(self.limit_enabled)
        else:
            self.tailstockLimit.setStyleSheet(self.limit_disabled)
        self.limitsHandler.setTailstockLimitActive(self.tailstockActive)

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
        print("---setting default limits: ", limits)
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
                self.latheComponent.comp.getPin(
                    TeachInLatheComponent.PinAxisLimitXMin).value = self.currentMachineLimits.x_min_limit
                x_min_applied = True
            # else:
            #     print("Back off from X- to activate the X- virtual limit")

            if x_abs < self.currentMachineLimits.x_max_limit:
                self.latheComponent.comp.getPin(
                    TeachInLatheComponent.PinAxisLimitXMax).value = self.currentMachineLimits.x_max_limit
                x_max_applied = True
            # else:
            #     print("Back off from X+ to activate the X+ virtual limit")

            if z_abs > self.currentMachineLimits.z_min_limit:
                self.latheComponent.comp.getPin(
                    TeachInLatheComponent.PinAxisLimitZMin).value = self.currentMachineLimits.z_min_limit
                z_min_applied = True
            # else:
            #     print("Back off from Z- to activate the Z- virtual limit")

            if z_abs < self.currentMachineLimits.z_max_limit:
                self.latheComponent.comp.getPin(
                    TeachInLatheComponent.PinAxisLimitZMax).value = self.currentMachineLimits.z_max_limit
                z_max_applied = True
            # else:
            #     print("Back off from Z+ to activate the Z+ virtual limit")

            if x_min_applied and x_max_applied and z_min_applied and z_max_applied:
                self.previousMachineLimits = self.currentMachineLimits
                print("-----All limits applied-------")
