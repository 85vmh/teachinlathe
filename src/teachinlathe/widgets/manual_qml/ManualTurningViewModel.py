from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from qtpyvcp import SETTINGS
from qtpyvcp.utilities.settings import setSetting

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.data_source.numpad_settings import NumpadSettings


class ManualTurningViewModel(QObject):
    spindleModeChanged = pyqtSignal()
    spindleValuesChanged = pyqtSignal()
    feedValuesChanged = pyqtSignal()
    rapidOverrideChanged = pyqtSignal()
    handwheelValuesChanged = pyqtSignal()
    joystickStateChanged = pyqtSignal()

    def __init__(self, manual_lathe, parent=None):
        super().__init__(parent)
        self._manual_lathe = manual_lathe
        self._lathe_component = TeachInLatheComponent()
        self._numpad_settings = NumpadSettings.instance()
        self._spindle_mode = 0
        self._gear_suffix = "2"
        self._rpm_setting_name = ""
        self._max_rpm_setting_name = ""
        self._css_setting_name = "spindle.css"
        self._feed_setting_name = "turning.feed_rate"
        self._input_rpm = "1000"
        self._input_css = "200"
        self._input_max_rpm = "1500"
        self._input_feed = "0.10"
        self._actual_rpm = "0"
        self._actual_css = "0"
        self._actual_feed = "0.00"
        self._spindle_override = 1.0
        self._feed_override = 1.0
        self._rapid_override = int(self._setting_value("rapid_speeds.percentage", 50))
        self._jog_increment = "0.001"
        self._handwheels_allowed = True
        self._x_handwheel_enabled = True
        self._z_handwheel_enabled = True
        self._joystick_state = 0
        self._joystick_rapid = False
        self._angle_feed_active = False
        self._allows_joystick_touch = True
        self.setGearSuffix(self._gear_suffix)
        self._set_setting_backed_value("_input_css", self._css_setting_name, self._input_css)
        self._set_setting_backed_value("_input_feed", self._feed_setting_name, self._input_feed)

    def _setting_value(self, setting_name: str, default):
        try:
            setting = SETTINGS.get(setting_name)
            if setting is not None:
                return setting.getValue()
        except Exception:
            pass
        return default

    def _set_setting_backed_value(self, attr_name: str, setting_name: str, default):
        # RPM / feed / CSS / max-RPM are populated from numpad_settings.json
        # (the persisted last_value), not from qtpyvcp anymore.
        value = self._numpad_settings.current_value(setting_name)
        if value is None:
            value = default
        setattr(self, attr_name, str(value))

    def _store_setting(self, setting_name: str, value):
        if not setting_name:
            return
        try:
            setSetting(setting_name, value)
        except Exception:
            pass

    def _to_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return float(default)

    def _update_actual_css(self):
        css = int(self._to_float(self._input_css, 0) * self._spindle_override)
        self._actual_css = str(css)

    def _update_actual_feed(self):
        feed = self._to_float(self._input_feed, 0.0) * self._feed_override
        self._actual_feed = f"{feed:.2f}"

    @pyqtProperty(int, notify=spindleModeChanged)
    def spindleMode(self):
        return self._spindle_mode

    @pyqtProperty(str, notify=spindleValuesChanged)
    def rpmSettingName(self):
        return self._rpm_setting_name

    @pyqtProperty(str, notify=spindleValuesChanged)
    def maxRpmSettingName(self):
        return self._max_rpm_setting_name

    @pyqtProperty(str, constant=True)
    def cssSettingName(self):
        return self._css_setting_name

    @pyqtProperty(str, constant=True)
    def feedSettingName(self):
        return self._feed_setting_name

    @pyqtProperty(str, notify=spindleValuesChanged)
    def inputRpm(self):
        return self._input_rpm

    @pyqtProperty(str, notify=spindleValuesChanged)
    def inputCss(self):
        return self._input_css

    @pyqtProperty(str, notify=spindleValuesChanged)
    def inputMaxRpm(self):
        return self._input_max_rpm

    @pyqtProperty(str, notify=spindleValuesChanged)
    def actualRpm(self):
        return self._actual_rpm

    @pyqtProperty(str, notify=spindleValuesChanged)
    def actualCss(self):
        return self._actual_css

    @pyqtProperty(str, notify=feedValuesChanged)
    def inputFeed(self):
        return self._input_feed

    @pyqtProperty(str, notify=feedValuesChanged)
    def actualFeed(self):
        return self._actual_feed

    @pyqtProperty(int, notify=rapidOverrideChanged)
    def rapidOverride(self):
        return self._rapid_override

    @pyqtProperty(str, notify=handwheelValuesChanged)
    def jogIncrement(self):
        return self._jog_increment

    @pyqtProperty(bool, notify=handwheelValuesChanged)
    def handwheelsAllowed(self):
        return self._handwheels_allowed

    @pyqtProperty(bool, notify=handwheelValuesChanged)
    def xHandwheelEnabled(self):
        return self._x_handwheel_enabled

    @pyqtProperty(bool, notify=handwheelValuesChanged)
    def zHandwheelEnabled(self):
        return self._z_handwheel_enabled

    @pyqtProperty(int, notify=joystickStateChanged)
    def joystickState(self):
        return self._joystick_state

    @pyqtProperty(bool, notify=joystickStateChanged)
    def joystickRapid(self):
        return self._joystick_rapid

    @pyqtProperty(bool, notify=joystickStateChanged)
    def angleFeedActive(self):
        return self._angle_feed_active

    @pyqtProperty(bool, notify=joystickStateChanged)
    def allowsJoystickTouch(self):
        return self._allows_joystick_touch

    @pyqtProperty(float, notify=joystickStateChanged)
    def joystickRotationTarget(self):
        return 45.0 if self._angle_feed_active else 0.0

    @pyqtSlot(int)
    def setSpindleMode(self, mode):
        mode = int(mode or 0)
        if self._spindle_mode == mode:
            return
        self._spindle_mode = mode
        self._manual_lathe.onSpindleModeChanged(mode)
        self.spindleModeChanged.emit()

    @pyqtSlot(str)
    def setGearSuffix(self, suffix):
        suffix = str(suffix or "2")
        if suffix not in ("1", "2"):
            suffix = "2"
        self._gear_suffix = suffix
        self._rpm_setting_name = f"spindle.rpm_{suffix}"
        self._max_rpm_setting_name = f"spindle.css_max_rpm_{suffix}"
        self._set_setting_backed_value("_input_rpm", self._rpm_setting_name, self._input_rpm)
        self._set_setting_backed_value("_input_max_rpm", self._max_rpm_setting_name, self._input_max_rpm)
        self._manual_lathe.onInputRpmChanged(self._input_rpm)
        self._manual_lathe.onMaxSpindleRpmChanged(self._input_max_rpm)
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setInputRpm(self, value):
        # Persistence of the chosen value is handled by NumpadDialogViewModel
        # (writes last_value into numpad_settings.json).
        self._input_rpm = str(value)
        self._manual_lathe.onInputRpmChanged(self._input_rpm)
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setInputCss(self, value):
        self._input_css = str(value)
        self._manual_lathe.onInputCssChanged(self._input_css)
        self._update_actual_css()
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setInputMaxRpm(self, value):
        self._input_max_rpm = str(value)
        self._manual_lathe.onMaxSpindleRpmChanged(self._input_max_rpm)
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setInputFeed(self, value):
        self._input_feed = str(value)
        self._manual_lathe.onInputFeedChanged(self._input_feed)
        self._update_actual_feed()
        self.feedValuesChanged.emit()

    @pyqtSlot(int)
    def setRapidOverride(self, value):
        self._rapid_override = int(value or 0)
        self._store_setting("machine.jog.linear-speed-percentage", self._rapid_override)
        self._store_setting("rapid_speeds.percentage", self._rapid_override)
        self.rapidOverrideChanged.emit()

    @pyqtSlot(bool)
    def setXHandwheelEnabled(self, enabled):
        enabled = bool(enabled)
        if self._x_handwheel_enabled == enabled:
            return
        self._x_handwheel_enabled = enabled
        self.handwheelValuesChanged.emit()

    @pyqtSlot(bool)
    def setZHandwheelEnabled(self, enabled):
        enabled = bool(enabled)
        if self._z_handwheel_enabled == enabled:
            return
        self._z_handwheel_enabled = enabled
        self.handwheelValuesChanged.emit()

    def setActualRpm(self, value):
        self._actual_rpm = str(abs(int(value or 0)))
        self.spindleValuesChanged.emit()

    @pyqtProperty(int, notify=spindleValuesChanged)
    def spindleOverridePercent(self):
        return int(round(self._spindle_override * 100))

    @pyqtProperty(int, notify=feedValuesChanged)
    def feedOverridePercent(self):
        return int(round(self._feed_override * 100))

    def setSpindleOverride(self, value):
        self._spindle_override = self._to_float(value, 1.0)
        self._update_actual_css()
        self.spindleValuesChanged.emit()

    def setFeedOverride(self, value):
        self._feed_override = self._to_float(value, 1.0)
        self._update_actual_feed()
        self.feedValuesChanged.emit()

    def setJogIncrement(self, value):
        try:
            self._jog_increment = f"{float(value):.3f}"
        except Exception:
            self._jog_increment = str(value)
        self.handwheelValuesChanged.emit()

    def setHandwheelsAllowed(self, allowed):
        self._handwheels_allowed = bool(allowed)
        self.handwheelValuesChanged.emit()

    def setHandwheelStates(self, x_enabled, z_enabled):
        self._x_handwheel_enabled = bool(x_enabled)
        self._z_handwheel_enabled = bool(z_enabled)
        self.handwheelValuesChanged.emit()

    def _set_angle_feed_active(self, enabled):
        enabled = bool(enabled)
        if self._angle_feed_active == enabled:
            return
        self._angle_feed_active = enabled
        self._manual_lathe.onTaperTurningChanged(enabled)
        try:
            self._lathe_component.comp.getPin(TeachInLatheComponent.PinIsAngleFeed).value = enabled
        except Exception:
            pass
        self.joystickStateChanged.emit()

    @pyqtSlot()
    def toggleAngleFeedFromJoystick(self):
        if not self._allows_joystick_touch:
            return
        self._set_angle_feed_active(not self._angle_feed_active)

    @pyqtSlot(bool)
    def setAngleFeedActive(self, enabled):
        self._set_angle_feed_active(enabled)

    @pyqtSlot()
    def resetAngleFeed(self):
        self._set_angle_feed_active(False)

    def isAngleFeedActive(self):
        return self._angle_feed_active

    def setJoystickState(self, state):
        value = state.value if hasattr(state, "value") else int(state or 0)
        if self._joystick_state == value and self._allows_joystick_touch == (value == 0):
            return
        self._joystick_state = value
        self._allows_joystick_touch = value == 0
        self.joystickStateChanged.emit()

    def setJoystickRapid(self, enabled):
        enabled = bool(enabled)
        if self._joystick_rapid == enabled:
            return
        self._joystick_rapid = enabled
        self.joystickStateChanged.emit()
