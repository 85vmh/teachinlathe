import os
from enum import Enum

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QVariantAnimation, QEasingCurve, QPropertyAnimation
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsColorizeEffect
from qtpy import uic
from qtpyvcp.utilities.info import Info
from qtpy.QtWidgets import QWidget
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities import logger
from qtpyvcp.widgets.base_widgets.dro_base_widget import Axis
from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.machine_limits import MachineLimitsHandler
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog

LOG = logger.getLogger(__name__)

UI_FILE = os.path.join(os.path.dirname(__file__), "teachin_lathe_dro.ui")
INFO = Info()


class LimitStatus(Enum):
    ENABLED = 0
    DISABLED = 1
    PENDING = 2,
    REACHED = 3


BOX_STYLE_TEMPLATE = """
    QWidget#{name} {{
        border-style: solid;
        border-width: {border}px;
        border-radius: 8px;
        border-color: rgb({r}, {g}, {b});
        color: rgb(10, 10, 10);
    }}
"""

LABEL_STYLE_TEMPLATE = """
    QLabel#{name} {{
        font: 75 14pt "Noto Mono";
        color: rgb({r}, {g}, {b});
    }}
"""

DISABLED_COLOR = QColor(50, 50, 50)
ENABLED_COLOR = QColor(26, 95, 180)
ON_LIMIT_COLOR = QColor(255, 0, 0)
PENDING_COLOR = QColor(255, 140, 0)


class TeachInLatheDro(QWidget):
    xPrimaryDroClicked = QtCore.pyqtSignal(float)
    zPrimaryDroClicked = QtCore.pyqtSignal(float)

    @staticmethod
    def set_box_border_color(widget: QWidget, color: QColor, border=1):
        widget.setStyleSheet(BOX_STYLE_TEMPLATE.format(
            name=widget.objectName(),
            border=border,
            r=color.red(), g=color.green(), b=color.blue()
        ))

    @staticmethod
    def set_label_color(widget: QWidget, color: QColor):
        widget.setStyleSheet(LABEL_STYLE_TEMPLATE.format(
            name=widget.objectName(),
            r=color.red(), g=color.green(), b=color.blue()
        ))

    def __init__(self, parent=None):
        super(TeachInLatheDro, self).__init__(parent)
        uic.loadUi(UI_FILE, self)
        print("-----TeachInLatheDro.__init__")
        self.limitsHandler = MachineLimitsHandler()
        print("limits handler created")
        self.latheComponent = TeachInLatheComponent()

        self.setDefaultMachineLimits(self.limitsHandler.getDefaultMachineLimits())

        self.status = getPlugin('status')
        self.pos = getPlugin('position')

        self._mm_fmt = '%10.3f'
        self._in_fmt = '%9.4f'
        self._fmt = self._mm_fmt
        self.isDiameterMode = True
        self.LIMIT_NONE = "--none--"

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

        self.teachXMinus.clicked.connect(lambda: self.xMinusToggle.setEnabled(True))
        self.teachXPlus.clicked.connect(lambda: self.xPlusToggle.setEnabled(True))
        self.teachZMinus.clicked.connect(lambda: self.zMinusToggle.setEnabled(True))
        self.teachZPlus.clicked.connect(lambda: self.zPlusToggle.setEnabled(True))
        self.teachTailstock.clicked.connect(lambda: self.tailstockToggle.setEnabled(True))

        self.xMinusToggle.clicked.connect(self.xMinusLimitToggle)
        self.xPlusToggle.clicked.connect(self.xPlusLimitToggle)
        self.zMinusToggle.clicked.connect(self.zMinusLimitToggle)
        self.zPlusToggle.clicked.connect(self.zPlusLimitToggle)
        self.tailstockToggle.clicked.connect(self.tailstockLimitToggle)

        self.xMinusLimitStatus = LimitStatus.DISABLED
        self.xPlusLimitStatus = LimitStatus.DISABLED
        self.zMinusLimitStatus = LimitStatus.DISABLED
        self.zPlusLimitStatus = LimitStatus.DISABLED
        self.tailstockLimitStatus = LimitStatus.DISABLED
        self.chuckLimitStatus = LimitStatus.DISABLED

        self.droLabelZMinus.setText(self.LIMIT_NONE)
        self.droLabelZPlus.setText(self.LIMIT_NONE)
        self.droLabelXMinus.setText(self.LIMIT_NONE)
        self.droLabelXPlus.setText(self.LIMIT_NONE)
        self.droLabelTailstock.setText(self.LIMIT_NONE)

        self.xPrimaryDro.installEventFilter(self)
        self.zPrimaryDro.installEventFilter(self)
        self.droLabelXMinus.installEventFilter(self)
        self.droLabelXPlus.installEventFilter(self)
        self.droLabelZMinus.installEventFilter(self)
        self.droLabelZPlus.installEventFilter(self)
        self.droLabelTailstock.installEventFilter(self)

        self.status.program_units.notify(self.updateUnits, 'string')
        getattr(self.pos, 'rel').notify(self.updateValues)
        getattr(self.pos, 'abs').notify(self.onAbsPositionUpdated)

        self.status.g5x_offset.signal.connect(self._updateToolRelativePos)
        self.status.g92_offset.signal.connect(self._updateToolRelativePos)
        self.status.tool_offset.signal.connect(self._updateToolRelativePos)

        self.limitsHandler.onLimitsChanged.connect(self.onMachineLimitsChanged)
        self.updateUnits()
        self.updateValues()

    def setDefaultMachineLimits(self, limits):
        print("---Setting default limits: ", limits)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = limits.x_min_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = limits.x_max_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = limits.z_min_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = limits.z_max_limit

    def _updateToolRelativePos(self):
        g5x_offset = self.status.stat.g5x_offset
        g92_offset = self.status.stat.g92_offset
        tool_offset = self.status.stat.tool_offset

        for axis in INFO.AXIS_NUMBER_LIST:
            self.tool_rel_position[axis] = g5x_offset[axis] + tool_offset[axis] + g92_offset[axis]

        print("---Tool relative position: ", self.tool_rel_position)
        # self.applyCurrentLimits()

    def setChuckLimit(self, value):
        self.droChuckLimit.setText(self._fmt % float(value))
        self.limitsHandler.setChuckLimit(float(value))

    def eventFilter(self, source, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            match source:
                case self.xPrimaryDro:
                    self.xPrimaryDroClicked.emit(float(self.xPrimaryDro.text()))
                    return True
                case self.zPrimaryDro:
                    self.zPrimaryDroClicked.emit(float(self.zPrimaryDro.text()))
                    return True
                case self.droLabelXMinus:
                    if self.xMinusLimitStatus == LimitStatus.DISABLED:
                        dialog = SmartNumPadDialog("smart_numpad.x-minus-limit", True)
                        dialog.valueSelected.connect(lambda val: (
                            self.droLabelXMinus.setText(f"{float(val):.3f}"),
                            self.xMinusToggle.setEnabled(True)
                        ))
                        dialog.exec_()
                    return True
                case self.droLabelXPlus:
                    if self.xPlusLimitStatus == LimitStatus.DISABLED:
                        dialog = SmartNumPadDialog("smart_numpad.x-plus-limit", True)
                        dialog.valueSelected.connect(lambda val: (
                            self.droLabelXPlus.setText(f"{float(val):.3f}"),
                            self.xPlusToggle.setEnabled(True)
                        ))
                        dialog.exec_()
                    return True
                case self.droLabelZMinus:
                    if self.zMinusLimitStatus == LimitStatus.DISABLED:
                        dialog = SmartNumPadDialog("smart_numpad.z-minus-limit", True)
                        dialog.valueSelected.connect(lambda val: (
                            self.droLabelZMinus.setText(f"{float(val):.3f}"),
                            self.zMinusToggle.setEnabled(True)
                        ))
                        dialog.exec_()
                    return True
                case self.droLabelZPlus:
                    if self.zPlusLimitStatus == LimitStatus.DISABLED:
                        dialog = SmartNumPadDialog("smart_numpad.z-plus-limit", True)
                        dialog.valueSelected.connect(lambda val: (
                            self.droLabelZPlus.setText(f"{float(val):.3f}"),
                            self.zPlusToggle.setEnabled(True)
                        ))
                        dialog.exec_()
                    return True
                case self.droLabelTailstock:
                    if self.tailstockLimitStatus == LimitStatus.DISABLED:
                        dialog = SmartNumPadDialog("smart_numpad.tailstock-limit", True)
                        dialog.valueSelected.connect(lambda val: (
                            self.droLabelTailstock.setText(f"{float(val):.3f}"),
                            self.tailstockToggle.setEnabled(True)
                        ))
                        dialog.exec_()
                    return True

        return super().eventFilter(source, event)

    def setStyleForLimitStatus(self, box, title_label, toggle_button, limit_status):
        match limit_status:
            case LimitStatus.DISABLED:
                self.set_box_border_color(box, DISABLED_COLOR)
                self.set_label_color(title_label, DISABLED_COLOR)
                toggle_button.setText("Enable Limit")
            case LimitStatus.PENDING:
                self.set_box_border_color(box, PENDING_COLOR, 2)
                self.set_label_color(title_label, PENDING_COLOR)
                toggle_button.setText("Pending...")
            case LimitStatus.ENABLED:
                self.set_box_border_color(box, ENABLED_COLOR, 3)
                self.set_label_color(title_label, ENABLED_COLOR)
                toggle_button.setText("Disable Limit")
            case LimitStatus.REACHED:
                self.set_box_border_color(box, ON_LIMIT_COLOR, 3)
                self.set_label_color(title_label, ON_LIMIT_COLOR)

    def xMinusLimitToggle(self):
        match self.xMinusLimitStatus:
            case LimitStatus.ENABLED | LimitStatus.PENDING:
                self.xMinusLimitStatus = LimitStatus.DISABLED
            case LimitStatus.DISABLED:
                self.xMinusLimitStatus = LimitStatus.PENDING
        self.setStyleForLimitStatus(self.boxXMinusLimit, self.labelXMinusLimit, self.sender(), self.xMinusLimitStatus)

        self.limitsHandler.setXMinusLimit(self.tool_rel_position[0] + float(self.droLabelXMinus.text()) / 2)
        self.limitsHandler.setXMinusLimitActive(self.xMinusLimitStatus is not LimitStatus.DISABLED)

    def xPlusLimitToggle(self):
        match self.xPlusLimitStatus:
            case LimitStatus.ENABLED | LimitStatus.PENDING:
                self.xPlusLimitStatus = LimitStatus.DISABLED
            case LimitStatus.DISABLED:
                self.xPlusLimitStatus = LimitStatus.PENDING
        self.setStyleForLimitStatus(self.boxXPlusLimit, self.labelXPlusLimit, self.sender(), self.xPlusLimitStatus)

        self.limitsHandler.setXPlusLimit(self.tool_rel_position[0] + float(self.droLabelXPlus.text()) / 2)
        self.limitsHandler.setXPlusLimitActive(self.xPlusLimitStatus is not LimitStatus.DISABLED)

    def zMinusLimitToggle(self):
        match self.zMinusLimitStatus:
            case LimitStatus.ENABLED | LimitStatus.PENDING:
                self.zMinusLimitStatus = LimitStatus.DISABLED
            case LimitStatus.DISABLED:
                self.zMinusLimitStatus = LimitStatus.PENDING
        self.setStyleForLimitStatus(self.boxZMinusLimit, self.labelZMinusLimit, self.sender(), self.zMinusLimitStatus)

        self.limitsHandler.setZMinusLimit(self.tool_rel_position[2] + float(self.droLabelZMinus.text()))
        self.limitsHandler.setZMinusLimitActive(self.zMinusLimitStatus is not LimitStatus.DISABLED)

    def zPlusLimitToggle(self):
        match self.zPlusLimitStatus:
            case LimitStatus.ENABLED | LimitStatus.PENDING:
                self.zPlusLimitStatus = LimitStatus.DISABLED
            case LimitStatus.DISABLED:
                self.zPlusLimitStatus = LimitStatus.PENDING
        self.setStyleForLimitStatus(self.boxZPlusLimit, self.labelZPlusLimit, self.sender(), self.zPlusLimitStatus)

        self.limitsHandler.setZPlusLimit(self.tool_rel_position[2] + float(self.droLabelZPlus.text()))
        self.limitsHandler.setZPlusLimitActive(self.zPlusLimitStatus is not LimitStatus.DISABLED)

    def tailstockLimitToggle(self):
        match self.tailstockLimitStatus:
            case LimitStatus.ENABLED | LimitStatus.PENDING:
                self.tailstockLimitStatus = LimitStatus.DISABLED
            case LimitStatus.DISABLED:
                self.tailstockLimitStatus = LimitStatus.PENDING
        self.setStyleForLimitStatus(self.boxTailstockLimit, self.labelTailstockLimit, self.sender(), self.tailstockLimitStatus)

        self.limitsHandler.setTailstockLimit(float(self.droLabelTailstock.text()))
        self.limitsHandler.setTailstockLimitActive(self.tailstockLimitStatus is not LimitStatus.DISABLED)

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
        print("---Machine limits changed: ", machine_limits)
        self.currentMachineLimits = machine_limits
        self.onAbsPositionUpdated()

    def onAbsPositionUpdated(self, pos=None):
        if self.previousMachineLimits != self.currentMachineLimits:
            if pos is None:
                pos = getattr(self.pos, 'abs').getValue()
            x_abs = pos[Axis.X]
            z_abs = pos[Axis.Z]

            x_minus_pin_written = False
            x_plus_pin_written = False
            z_minus_pin_written = False
            z_plus_pin_written = False
            tailstock_pin_written = False

            x_min_limit = self.currentMachineLimits.x_min_limit
            x_max_limit = self.currentMachineLimits.x_max_limit
            z_min_limit = self.currentMachineLimits.z_min_limit
            z_max_limit = self.currentMachineLimits.z_max_limit
            limit_reached_tolerance = 0.005

            # --- X MINUS ---
            if x_abs >= x_min_limit and self.xMinusLimitStatus == LimitStatus.PENDING:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = x_min_limit
                x_minus_pin_written = True
                self.xMinusLimitStatus = LimitStatus.ENABLED
            elif self.xMinusLimitStatus == LimitStatus.DISABLED:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = x_min_limit
                x_minus_pin_written = True
            elif self.xMinusLimitStatus in (LimitStatus.ENABLED, LimitStatus.REACHED):
                if abs(x_abs - x_min_limit) < limit_reached_tolerance:
                    self.xMinusLimitStatus = LimitStatus.REACHED
                else:
                    self.xMinusLimitStatus = LimitStatus.ENABLED

            # --- X PLUS ---
            if x_abs <= x_max_limit and self.xPlusLimitStatus == LimitStatus.PENDING:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = x_max_limit
                x_plus_pin_written = True
                self.xPlusLimitStatus = LimitStatus.ENABLED
            elif self.xPlusLimitStatus == LimitStatus.DISABLED:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = x_max_limit
                x_plus_pin_written = True
            elif self.xPlusLimitStatus in (LimitStatus.ENABLED, LimitStatus.REACHED):
                if abs(x_abs - x_max_limit) < limit_reached_tolerance:
                    self.xPlusLimitStatus = LimitStatus.REACHED
                else:
                    self.xPlusLimitStatus = LimitStatus.ENABLED

            # --- Z MINUS ---
            if z_abs >= z_min_limit and self.zMinusLimitStatus == LimitStatus.PENDING:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = z_min_limit
                z_minus_pin_written = True
                self.zMinusLimitStatus = LimitStatus.ENABLED
            elif self.zMinusLimitStatus == LimitStatus.DISABLED:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = z_min_limit
                z_minus_pin_written = True
            elif self.zMinusLimitStatus in (LimitStatus.ENABLED, LimitStatus.REACHED):
                if abs(z_abs - z_min_limit) < limit_reached_tolerance:
                    self.zMinusLimitStatus = LimitStatus.REACHED
                else:
                    self.zMinusLimitStatus = LimitStatus.ENABLED

            # --- Z PLUS ---
            if z_abs <= z_max_limit and self.zPlusLimitStatus == LimitStatus.PENDING:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
                z_plus_pin_written = True
                self.zPlusLimitStatus = LimitStatus.ENABLED
            elif self.zPlusLimitStatus == LimitStatus.DISABLED:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
                z_plus_pin_written = True
            elif self.zPlusLimitStatus in (LimitStatus.ENABLED, LimitStatus.REACHED):
                if abs(z_abs - z_max_limit) < limit_reached_tolerance:
                    self.zPlusLimitStatus = LimitStatus.REACHED
                else:
                    self.zPlusLimitStatus = LimitStatus.ENABLED

            # --- TAILSTOCK Z MAX LIMIT ---
            if z_abs <= z_max_limit and self.tailstockLimitStatus == LimitStatus.PENDING:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
                tailstock_pin_written = True
                self.tailstockLimitStatus = LimitStatus.ENABLED
            elif self.tailstockLimitStatus == LimitStatus.DISABLED:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
                tailstock_pin_written = True
            elif self.tailstockLimitStatus in (LimitStatus.ENABLED, LimitStatus.REACHED):
                if abs(z_abs - z_max_limit) < limit_reached_tolerance:
                    self.tailstockLimitStatus = LimitStatus.REACHED
                else:
                    self.tailstockLimitStatus = LimitStatus.ENABLED

            self.setStyleForLimitStatus(self.boxXMinusLimit, self.labelXMinusLimit, self.xMinusToggle, self.xMinusLimitStatus)
            self.setStyleForLimitStatus(self.boxXPlusLimit, self.labelXPlusLimit, self.xPlusToggle, self.xPlusLimitStatus)
            self.setStyleForLimitStatus(self.boxZMinusLimit, self.labelZMinusLimit, self.zMinusToggle, self.zMinusLimitStatus)
            self.setStyleForLimitStatus(self.boxZPlusLimit, self.labelZPlusLimit, self.zPlusToggle, self.zPlusLimitStatus)
            # self.setStyleForLimitStatus(self.boxChuckLimit, self.labelChuckLimit, self.changeChuck, self.chuckLimitStatus)
            self.setStyleForLimitStatus(self.boxTailstockLimit, self.labelTailstockLimit, self.tailstockToggle, self.tailstockLimitStatus)

            if x_minus_pin_written and x_plus_pin_written and z_minus_pin_written and z_plus_pin_written and tailstock_pin_written:
                self.previousMachineLimits = self.currentMachineLimits
                print("-----All limits applied-------")
