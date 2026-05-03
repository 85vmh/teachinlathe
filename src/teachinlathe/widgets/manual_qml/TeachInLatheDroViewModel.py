from enum import Enum

from PyQt5 import QtCore
from PyQt5.QtCore import QMetaObject, QObject, pyqtProperty, pyqtSignal, pyqtSlot
from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities.info import Info
from qtpyvcp.widgets.base_widgets.dro_base_widget import Axis

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.machine_limits import MachineLimitsHandler
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog

INFO = Info()


class LimitStatus(Enum):
    ENABLED = 0
    DISABLED = 1
    PENDING = 2
    REACHED = 3


class TeachInLatheDroViewModel(QObject):
    xPrimaryDroClicked = pyqtSignal(float)
    zPrimaryDroClicked = pyqtSignal(float)
    droChanged = pyqtSignal()
    limitsChanged = pyqtSignal()

    LIMIT_NONE = "--none--"
    LIMIT_KEYS = ("xMinus", "xPlus", "zMinus", "zPlus", "tailstock")
    LIMIT_SETTING_NAMES = {
        "xMinus": "smart_numpad.x-minus-limit",
        "xPlus": "smart_numpad.x-plus-limit",
        "zMinus": "smart_numpad.z-minus-limit",
        "zPlus": "smart_numpad.z-plus-limit",
        "tailstock": "smart_numpad.tailstock-limit",
        "chuck": "smart_numpad.chuck-limit",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.limitsHandler = MachineLimitsHandler()
        self.latheComponent = TeachInLatheComponent()
        self.setDefaultMachineLimits(self.limitsHandler.getDefaultMachineLimits())

        self.status = getPlugin('status')
        self.pos = getPlugin('position')

        self._mm_fmt = '%10.3f'
        self._in_fmt = '%9.4f'
        self._fmt = self._mm_fmt
        self._units = "mm"
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
        self._active_numpad_field = None

        self._x_primary_value = "+0000.000"
        self._x_secondary_value = "+0000.000"
        self._x_secondary_visible = False
        self._z_primary_value = "+0000.000"
        self._z_secondary_value = "+0000.000"
        self._z_secondary_visible = False

        self.limit_status = {
            "xMinus": LimitStatus.DISABLED,
            "xPlus": LimitStatus.DISABLED,
            "zMinus": LimitStatus.DISABLED,
            "zPlus": LimitStatus.DISABLED,
            "tailstock": LimitStatus.DISABLED,
            "chuck": LimitStatus.DISABLED,
        }
        self.limit_values = {
            "xMinus": self.LIMIT_NONE,
            "xPlus": self.LIMIT_NONE,
            "zMinus": self.LIMIT_NONE,
            "zPlus": self.LIMIT_NONE,
            "tailstock": self.LIMIT_NONE,
            "chuck": self.LIMIT_NONE,
        }
        self.toggle_enabled = {key: False for key in self.LIMIT_KEYS}

        self.status.program_units.notify(self.updateUnits, 'string')
        getattr(self.pos, 'rel').notify(self.updateValues)
        getattr(self.pos, 'abs').notify(self.onAbsPositionUpdated)
        self.status.g5x_offset.signal.connect(self._updateToolRelativePos)
        self.status.g92_offset.signal.connect(self._updateToolRelativePos)
        self.status.tool_offset.signal.connect(self._updateToolRelativePos)
        self.limitsHandler.onLimitsChanged.connect(self.onMachineLimitsChanged)

        self.updateUnits()
        self.updateValues()

    @pyqtProperty(str, notify=droChanged)
    def xPrimaryValue(self):
        return self._x_primary_value

    @pyqtProperty(str, notify=droChanged)
    def xSecondaryValue(self):
        return self._x_secondary_value

    @pyqtProperty(bool, notify=droChanged)
    def xSecondaryVisible(self):
        return self._x_secondary_visible

    @pyqtProperty(str, notify=droChanged)
    def zPrimaryValue(self):
        return self._z_primary_value

    @pyqtProperty(str, notify=droChanged)
    def zSecondaryValue(self):
        return self._z_secondary_value

    @pyqtProperty(bool, notify=droChanged)
    def zSecondaryVisible(self):
        return self._z_secondary_visible

    @pyqtProperty(str, notify=droChanged)
    def units(self):
        return self._units

    def _limit_property(self, key):
        return self.limit_values[key]

    def _status_property(self, key):
        return self.limit_status[key].value

    def _toggle_text_property(self, key):
        return self._status_text(self.limit_status[key])

    def _toggle_enabled_property(self, key):
        return self.toggle_enabled[key]

    xMinusValue = pyqtProperty(str, lambda self: self._limit_property("xMinus"), notify=limitsChanged)
    xPlusValue = pyqtProperty(str, lambda self: self._limit_property("xPlus"), notify=limitsChanged)
    zMinusValue = pyqtProperty(str, lambda self: self._limit_property("zMinus"), notify=limitsChanged)
    zPlusValue = pyqtProperty(str, lambda self: self._limit_property("zPlus"), notify=limitsChanged)
    tailstockValue = pyqtProperty(str, lambda self: self._limit_property("tailstock"), notify=limitsChanged)
    chuckValue = pyqtProperty(str, lambda self: self._limit_property("chuck"), notify=limitsChanged)

    xMinusStatus = pyqtProperty(int, lambda self: self._status_property("xMinus"), notify=limitsChanged)
    xPlusStatus = pyqtProperty(int, lambda self: self._status_property("xPlus"), notify=limitsChanged)
    zMinusStatus = pyqtProperty(int, lambda self: self._status_property("zMinus"), notify=limitsChanged)
    zPlusStatus = pyqtProperty(int, lambda self: self._status_property("zPlus"), notify=limitsChanged)
    tailstockStatus = pyqtProperty(int, lambda self: self._status_property("tailstock"), notify=limitsChanged)
    chuckStatus = pyqtProperty(int, lambda self: self._status_property("chuck"), notify=limitsChanged)

    xMinusToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("xMinus"), notify=limitsChanged)
    xPlusToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("xPlus"), notify=limitsChanged)
    zMinusToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("zMinus"), notify=limitsChanged)
    zPlusToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("zPlus"), notify=limitsChanged)
    tailstockToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("tailstock"), notify=limitsChanged)

    xMinusToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("xMinus"), notify=limitsChanged)
    xPlusToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("xPlus"), notify=limitsChanged)
    zMinusToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("zMinus"), notify=limitsChanged)
    zPlusToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("zPlus"), notify=limitsChanged)
    tailstockToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("tailstock"), notify=limitsChanged)

    def setDefaultMachineLimits(self, limits):
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

    def setChuckLimit(self, value):
        self.limit_values["chuck"] = self._format_limit(value)
        self.limitsHandler.setChuckLimit(float(value))
        self.limitsChanged.emit()

    def _format_limit(self, value):
        return self._fmt % float(value)

    @pyqtSlot()
    def xPrimaryClicked(self):
        self.xPrimaryDroClicked.emit(float(self._x_primary_value))

    @pyqtSlot()
    def zPrimaryClicked(self):
        self.zPrimaryDroClicked.emit(float(self._z_primary_value))

    @pyqtSlot(str)
    def teachLimit(self, key):
        key = str(key)
        if key not in self.LIMIT_KEYS:
            return
        self.limit_values[key] = self._format_limit(self._teach_value_for_key(key))
        self.toggle_enabled[key] = True
        self.limitsChanged.emit()

    def _teach_value_for_key(self, key):
        factor = 2.0 if key.startswith("x") and self.isDiameterMode else 1.0
        if key.startswith("x"):
            return factor * self.currentXAbsValue
        if key.startswith("z") or key == "tailstock":
            return self.currentZAbsValue
        return 0

    @pyqtSlot(str, QObject)
    def openLimitField(self, key, field):
        key = str(key)
        setting_name = self.LIMIT_SETTING_NAMES.get(key, "")
        if not setting_name:
            return
        previous_field = self._active_numpad_field
        if previous_field is not None and previous_field is not field:
            self._defocus_numpad_field(previous_field)
        self._active_numpad_field = field
        dialog = SmartNumPadDialog(setting_name, True)

        def handle_value(value):
            self.limit_values[key] = self._format_limit(value)
            self._set_qml_field_value(field, self.limit_values[key])
            if key != "chuck":
                self.toggle_enabled[key] = True
            self.limitsChanged.emit()

        try:
            dialog.valueSelected.connect(handle_value)
            dialog.exec_()
        finally:
            self._defocus_numpad_field(field)
            if self._active_numpad_field is field:
                self._active_numpad_field = None

    @pyqtSlot(str, object)
    def commitLimit(self, key, value):
        key = str(key)
        if key not in self.limit_values:
            return
        self.limit_values[key] = self._format_limit(value)
        if key != "chuck":
            self.toggle_enabled[key] = True
        self.limitsChanged.emit()

    @staticmethod
    def _set_qml_field_value(field, value):
        try:
            field.setProperty("value", value)
            field.setProperty("text", str(value))
        except Exception:
            pass

    @staticmethod
    def _defocus_numpad_field(field):
        if field is None:
            return
        try:
            QMetaObject.invokeMethod(field, 'defocus', QtCore.Qt.DirectConnection)
            return
        except Exception:
            pass
        try:
            field.setProperty("numpadActive", False)
            field.setProperty("focus", False)
        except Exception:
            pass

    @pyqtSlot(str)
    def toggleLimit(self, key):
        key = str(key)
        match key:
            case "xMinus":
                self.xMinusLimitToggle()
            case "xPlus":
                self.xPlusLimitToggle()
            case "zMinus":
                self.zMinusLimitToggle()
            case "zPlus":
                self.zPlusLimitToggle()
            case "tailstock":
                self.tailstockLimitToggle()

    def _toggle_status(self, key):
        if self.limit_status[key] in (LimitStatus.ENABLED, LimitStatus.PENDING):
            self.limit_status[key] = LimitStatus.DISABLED
        elif self.limit_status[key] == LimitStatus.DISABLED:
            self.limit_status[key] = LimitStatus.PENDING
        self.limitsChanged.emit()

    def _limit_float(self, key):
        return float(str(self.limit_values[key]).strip())

    def xMinusLimitToggle(self):
        self._toggle_status("xMinus")
        self.limitsHandler.setXMinusLimit(self.tool_rel_position[0] + self._limit_float("xMinus") / 2)
        self.limitsHandler.setXMinusLimitActive(self.limit_status["xMinus"] is not LimitStatus.DISABLED)

    def xPlusLimitToggle(self):
        self._toggle_status("xPlus")
        self.limitsHandler.setXPlusLimit(self.tool_rel_position[0] + self._limit_float("xPlus") / 2)
        self.limitsHandler.setXPlusLimitActive(self.limit_status["xPlus"] is not LimitStatus.DISABLED)

    def zMinusLimitToggle(self):
        self._toggle_status("zMinus")
        self.limitsHandler.setZMinusLimit(self.tool_rel_position[2] + self._limit_float("zMinus"))
        self.limitsHandler.setZMinusLimitActive(self.limit_status["zMinus"] is not LimitStatus.DISABLED)

    def zPlusLimitToggle(self):
        self._toggle_status("zPlus")
        self.limitsHandler.setZPlusLimit(self.tool_rel_position[2] + self._limit_float("zPlus"))
        self.limitsHandler.setZPlusLimitActive(self.limit_status["zPlus"] is not LimitStatus.DISABLED)

    def tailstockLimitToggle(self):
        self._toggle_status("tailstock")
        self.limitsHandler.setTailstockLimit(self._limit_float("tailstock"))
        self.limitsHandler.setTailstockLimitActive(self.limit_status["tailstock"] is not LimitStatus.DISABLED)

    def _status_text(self, status):
        return "Disable Limit" if status in (LimitStatus.ENABLED, LimitStatus.REACHED) else "Pending..." if status == LimitStatus.PENDING else "Enable Limit"

    def updateUnits(self, units=None):
        if units is None:
            units = str(self.status.program_units)
        self._fmt = self._in_fmt if units == 'in' else self._mm_fmt
        self._units = units
        self.droChanged.emit()
        self.updateDro()

    def updateValues(self, pos=None):
        if pos is None:
            pos = getattr(self.pos, 'rel').getValue()
        self.currentXAbsValue = pos[Axis.X]
        self.currentZAbsValue = pos[Axis.Z]
        self.updateDro()

    @pyqtSlot()
    def xZeroClicked(self):
        self.isXAbs = False
        self.lastXAbsValue = self.currentXAbsValue
        self.updateDro()

    @pyqtSlot()
    def zZeroClicked(self):
        self.isZAbs = False
        self.lastZAbsValue = self.currentZAbsValue
        self.updateDro()

    @pyqtSlot()
    def xAbsRelClicked(self):
        self.isXAbs = not self.isXAbs
        if self.isXAbs:
            self.lastXAbsValue = 0
        self.updateDro()

    @pyqtSlot()
    def zAbsRelClicked(self):
        self.isZAbs = not self.isZAbs
        if self.isZAbs:
            self.lastZAbsValue = 0
        self.updateDro()

    def updateDro(self):
        factor = 2.0 if self.isDiameterMode else 1.0
        if self.isXAbs:
            self._x_primary_value = self._fmt % (factor * self.currentXAbsValue)
            self._x_secondary_visible = False
        else:
            self._x_primary_value = self._fmt % (factor * (self.currentXAbsValue - self.lastXAbsValue))
            self._x_secondary_value = self._fmt % (factor * self.currentXAbsValue)
            self._x_secondary_visible = True

        if self.isZAbs:
            self._z_primary_value = self._fmt % self.currentZAbsValue
            self._z_secondary_visible = False
        else:
            self._z_primary_value = self._fmt % (self.currentZAbsValue - self.lastZAbsValue)
            self._z_secondary_value = self._fmt % self.currentZAbsValue
            self._z_secondary_visible = True
        self.droChanged.emit()

    def onMachineLimitsChanged(self, machine_limits):
        self.currentMachineLimits = machine_limits
        self.onAbsPositionUpdated()

    def onAbsPositionUpdated(self, pos=None):
        if self.previousMachineLimits == self.currentMachineLimits:
            return
        if pos is None:
            pos = getattr(self.pos, 'abs').getValue()
        x_abs = pos[Axis.X]
        z_abs = pos[Axis.Z]
        x_min_limit = self.currentMachineLimits.x_min_limit
        x_max_limit = self.currentMachineLimits.x_max_limit
        z_min_limit = self.currentMachineLimits.z_min_limit
        z_max_limit = self.currentMachineLimits.z_max_limit
        tolerance = 0.005
        pin_written = {key: False for key in ("xMinus", "xPlus", "zMinus", "zPlus", "tailstock")}

        if x_abs >= x_min_limit and self.limit_status["xMinus"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = x_min_limit
            pin_written["xMinus"] = True
            self.limit_status["xMinus"] = LimitStatus.ENABLED
        elif self.limit_status["xMinus"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = x_min_limit
            pin_written["xMinus"] = True
        elif self.limit_status["xMinus"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["xMinus"] = LimitStatus.REACHED if abs(x_abs - x_min_limit) < tolerance else LimitStatus.ENABLED

        if x_abs <= x_max_limit and self.limit_status["xPlus"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = x_max_limit
            pin_written["xPlus"] = True
            self.limit_status["xPlus"] = LimitStatus.ENABLED
        elif self.limit_status["xPlus"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = x_max_limit
            pin_written["xPlus"] = True
        elif self.limit_status["xPlus"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["xPlus"] = LimitStatus.REACHED if abs(x_abs - x_max_limit) < tolerance else LimitStatus.ENABLED

        if z_abs >= z_min_limit and self.limit_status["zMinus"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = z_min_limit
            pin_written["zMinus"] = True
            self.limit_status["zMinus"] = LimitStatus.ENABLED
        elif self.limit_status["zMinus"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = z_min_limit
            pin_written["zMinus"] = True
        elif self.limit_status["zMinus"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["zMinus"] = LimitStatus.REACHED if abs(z_abs - z_min_limit) < tolerance else LimitStatus.ENABLED

        if z_abs <= z_max_limit and self.limit_status["zPlus"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
            pin_written["zPlus"] = True
            self.limit_status["zPlus"] = LimitStatus.ENABLED
        elif self.limit_status["zPlus"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
            pin_written["zPlus"] = True
        elif self.limit_status["zPlus"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["zPlus"] = LimitStatus.REACHED if abs(z_abs - z_max_limit) < tolerance else LimitStatus.ENABLED

        if z_abs <= z_max_limit and self.limit_status["tailstock"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
            pin_written["tailstock"] = True
            self.limit_status["tailstock"] = LimitStatus.ENABLED
        elif self.limit_status["tailstock"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
            pin_written["tailstock"] = True
        elif self.limit_status["tailstock"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["tailstock"] = LimitStatus.REACHED if abs(z_abs - z_max_limit) < tolerance else LimitStatus.ENABLED

        self.limitsChanged.emit()
        if all(pin_written.values()):
            self.previousMachineLimits = self.currentMachineLimits
