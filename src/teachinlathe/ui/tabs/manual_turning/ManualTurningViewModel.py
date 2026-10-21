from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from teachinlathe.core.settings_repository import settings_repository

from teachinlathe.manual.logic.manual_turning_use_case import ManualTurningUseCase
from teachinlathe.ui.common.touchable_input.numpad_settings import NumpadSettings


class ManualTurningViewModel(QObject):
    spindleModeChanged = pyqtSignal()
    spindleValuesChanged = pyqtSignal()
    feedValuesChanged = pyqtSignal()
    rapidOverrideChanged = pyqtSignal()
    handwheelValuesChanged = pyqtSignal()
    joystickStateChanged = pyqtSignal()

    def __init__(self, parent=None, use_case: ManualTurningUseCase = None):
        super().__init__(parent)
        self._use_case = ManualTurningUseCase(parent=self) if use_case is None else use_case
        self._numpad_settings = NumpadSettings.instance()
        self._spindle_mode = 0
        self._gear_suffix = "2"
        self._spindle_gear_number = 0
        self._rpm_setting_name = ""
        self._max_rpm_setting_name = ""
        self._css_setting_name = "spindle.css"
        self._feed_setting_name = "turning.feed_rate"
        self._input_rpm = "1000"
        self._input_css = "200"
        self._input_max_rpm = "1500"
        self._input_feed = "0.1"
        self._actual_rpm = "0"
        self._actual_css = "0"
        self._spindle_angle = 0.0
        self._spindle_running = False
        self._spindle_cover_opened = False
        self._spindle_reset_required = False
        self._feeding = False
        self._joystick_reset_required = False
        self._actual_feed = "0.0"
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
        self._input_feed = self._format_feed_value(self._input_feed)
        self._update_actual_feed()
        self._follow_machine()

    def _follow_machine(self):
        """Show what the machine is doing, and tell it what the screen holds."""
        uc = self._use_case
        uc.spindleRunningChanged.connect(self.setSpindleRunning)
        uc.spindleCoverOpenedChanged.connect(self.setSpindleCoverOpened)
        uc.spindleResetRequiredChanged.connect(self.setSpindleResetRequired)
        uc.spindleAngleChanged.connect(self.setSpindleAngle)
        uc.actualRpmChanged.connect(self.setActualRpm)
        uc.gearChanged.connect(lambda gear: self.setGearSuffix(str(gear)))
        uc.spindleOverrideChanged.connect(self.setSpindleOverride)
        uc.feedOverrideChanged.connect(self.setFeedOverride)
        uc.feedingChanged.connect(self.setFeeding)
        uc.joystickResetRequiredChanged.connect(self.setJoystickResetRequired)
        uc.joystickStateChanged.connect(self.setJoystickState)
        uc.joystickRapidChanged.connect(self.setJoystickRapid)
        uc.angleFeedChanged.connect(self._on_angle_feed_changed)
        uc.jogIncrementChanged.connect(self.setJogIncrement)
        uc.handwheelsChanged.connect(self._on_handwheels_changed)

        self.setGearSuffix(str(uc.gear))
        self.setSpindleRunning(uc.spindle_running)
        self.setSpindleCoverOpened(uc.spindle_cover_opened)
        self.setSpindleResetRequired(uc.spindle_reset_required)
        self.setSpindleAngle(uc.spindle_angle)
        self.setSpindleOverride(uc.spindle_override)
        self.setFeedOverride(uc.feed_override)
        self.setFeeding(uc.feeding)
        self.setJoystickResetRequired(uc.joystick_reset_required)
        self._on_handwheels_changed()

        uc.set_spindle_mode(self._spindle_mode)
        uc.set_spindle_rpm(self._input_rpm)
        uc.set_spindle_css(self._input_css)
        uc.set_max_spindle_rpm(self._input_max_rpm)
        uc.set_feed_per_rev(self._input_feed)

    def _setting_value(self, setting_name: str, default):
        return settings_repository().get(setting_name, default)

    def _set_setting_backed_value(self, attr_name: str, setting_name: str, default):
        # RPM / feed / CSS / max-RPM are populated from numpad_settings.json
        # (the persisted last_value), not from the settings file.
        value = self._numpad_settings.current_value(setting_name)
        if value is None:
            value = default
        setattr(self, attr_name, str(value))

    def _store_setting(self, setting_name: str, value):
        if not setting_name:
            return
        settings_repository().set(setting_name, value)

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
        self._actual_feed = self._format_feed_value(feed)

    def _format_feed_value(self, value):
        try:
            number = float(value)
        except Exception:
            return str(value)
        text = f"{number:.2f}".rstrip("0").rstrip(".")
        if "." not in text:
            text += ".0"
        return text

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

    @pyqtProperty(str, notify=spindleValuesChanged)
    def spindleAngleText(self):
        return f"{self._spindle_angle:.1f}°"

    @pyqtProperty(bool, notify=spindleValuesChanged)
    def spindleRunning(self):
        return self._spindle_running

    @pyqtProperty(bool, notify=spindleValuesChanged)
    def spindleCoverOpened(self):
        return self._spindle_cover_opened

    @pyqtProperty(bool, notify=spindleValuesChanged)
    def spindleResetRequired(self):
        return self._spindle_reset_required

    @pyqtProperty(str, notify=spindleValuesChanged)
    def spindlePanelMode(self):
        if not self._spindle_running:
            return "Editable"
        if self._spindle_cover_opened:
            return "CoverOpened"
        if self._spindle_reset_required:
            return "ResetRequired"
        return "ReadOnly"

    @pyqtProperty(str, notify=spindleValuesChanged)
    def spindlePanelMessageTitle(self):
        if self.spindlePanelMode == "CoverOpened":
            return "Spindle cover opened!"
        if self.spindlePanelMode == "ResetRequired":
            return "Spindle reset required!"
        return ""

    @pyqtProperty(str, notify=spindleValuesChanged)
    def spindlePanelMessageBody(self):
        if self.spindlePanelMode == "CoverOpened":
            return "Close the spindle cover to continue."
        if self.spindlePanelMode == "ResetRequired":
            return "Return the spindle lever to neutral position."
        return ""

    @pyqtProperty(str, notify=spindleValuesChanged)
    def spindleModeLabel(self):
        return "CSS" if self._spindle_mode == 1 else "RPM"

    @pyqtProperty(int, notify=spindleValuesChanged)
    def spindleGearNumber(self):
        return self._spindle_gear_number

    @pyqtProperty(str, notify=spindleValuesChanged)
    def spindleTitle(self):
        if self._spindle_gear_number == 0:
            return "Spindle"
        return f"Spindle [{self._spindle_gear_number}]"

    @pyqtProperty(str, notify=feedValuesChanged)
    def inputFeed(self):
        return self._input_feed

    @pyqtProperty(str, notify=feedValuesChanged)
    def actualFeed(self):
        return self._actual_feed

    @pyqtProperty(bool, notify=feedValuesChanged)
    def feeding(self):
        return self._feeding

    @pyqtProperty(bool, notify=feedValuesChanged)
    def joystickResetRequired(self):
        return self._joystick_reset_required

    @pyqtProperty(str, notify=feedValuesChanged)
    def feedPanelMode(self):
        if self._joystick_reset_required:
            return "ResetRequired"
        return "ReadOnly" if self._feeding else "Editable"

    @pyqtProperty(str, notify=feedValuesChanged)
    def feedPanelMessageTitle(self):
        if self.feedPanelMode == "ResetRequired":
            return "Joystick reset required!"
        return ""

    @pyqtProperty(str, notify=feedValuesChanged)
    def feedPanelMessageBody(self):
        if self.feedPanelMode == "ResetRequired":
            return "Return the joystick to neutral position."
        return ""

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
        self._use_case.set_spindle_mode(mode)
        self.spindleModeChanged.emit()
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setGearSuffix(self, suffix):
        suffix = str(suffix or "2")
        if suffix not in ("1", "2"):
            suffix = "2"
        self._gear_suffix = suffix
        self._spindle_gear_number = int(suffix)
        self._rpm_setting_name = f"spindle.rpm_{suffix}"
        self._max_rpm_setting_name = f"spindle.css_max_rpm_{suffix}"
        self._set_setting_backed_value("_input_rpm", self._rpm_setting_name, self._input_rpm)
        self._set_setting_backed_value("_input_max_rpm", self._max_rpm_setting_name, self._input_max_rpm)
        self._use_case.set_spindle_rpm(self._input_rpm)
        self._use_case.set_max_spindle_rpm(self._input_max_rpm)
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setInputRpm(self, value):
        # Persistence of the chosen value is handled by NumpadDialogViewModel
        # (writes last_value into numpad_settings.json).
        self._input_rpm = str(value)
        self._use_case.set_spindle_rpm(self._input_rpm)
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setInputCss(self, value):
        self._input_css = str(value)
        self._use_case.set_spindle_css(self._input_css)
        self._update_actual_css()
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setInputMaxRpm(self, value):
        self._input_max_rpm = str(value)
        self._use_case.set_max_spindle_rpm(self._input_max_rpm)
        self.spindleValuesChanged.emit()

    @pyqtSlot(str)
    def setInputFeed(self, value):
        self._input_feed = self._format_feed_value(value)
        self._use_case.set_feed_per_rev(self._input_feed)
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
        self._use_case.set_handwheel_enabled("x", enabled)

    @pyqtSlot(bool)
    def setZHandwheelEnabled(self, enabled):
        self._use_case.set_handwheel_enabled("z", enabled)

    def _on_handwheels_changed(self):
        handwheels = self._use_case.handwheels
        self._handwheels_allowed = handwheels.allowed
        self._x_handwheel_enabled = handwheels.x_enabled
        self._z_handwheel_enabled = handwheels.z_enabled
        self.handwheelValuesChanged.emit()

    def setActualRpm(self, value):
        self._actual_rpm = str(abs(int(value or 0)))
        self.spindleValuesChanged.emit()

    def setSpindleRunning(self, running):
        running = bool(running)
        if self._spindle_running == running:
            return
        self._spindle_running = running
        self.spindleValuesChanged.emit()

    def setSpindleCoverOpened(self, opened):
        opened = bool(opened)
        if self._spindle_cover_opened == opened:
            return
        self._spindle_cover_opened = opened
        self.spindleValuesChanged.emit()

    def setSpindleResetRequired(self, required):
        required = bool(required)
        if self._spindle_reset_required == required:
            return
        self._spindle_reset_required = required
        self.spindleValuesChanged.emit()

    def setSpindleAngle(self, angle):
        angle = self._to_float(angle, 0.0)
        angle = angle % 360.0
        if abs(self._spindle_angle - angle) < 0.05:
            return
        self._spindle_angle = angle
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

    def setFeeding(self, feeding):
        feeding = bool(feeding)
        if self._feeding == feeding:
            return
        self._feeding = feeding
        self.feedValuesChanged.emit()

    def setJoystickResetRequired(self, required):
        required = bool(required)
        if self._joystick_reset_required == required:
            return
        self._joystick_reset_required = required
        self.feedValuesChanged.emit()

    def setJogIncrement(self, value):
        try:
            self._jog_increment = f"{float(value):.3f}"
        except Exception:
            self._jog_increment = str(value)
        self.handwheelValuesChanged.emit()

    def _on_angle_feed_changed(self, enabled):
        self._angle_feed_active = bool(enabled)
        self.joystickStateChanged.emit()

    @pyqtSlot()
    def toggleAngleFeedFromJoystick(self):
        if not self._allows_joystick_touch:
            return
        self._use_case.set_angle_feed(not self._angle_feed_active)

    @pyqtSlot(bool)
    def setAngleFeedActive(self, enabled):
        self._use_case.set_angle_feed(enabled)

    @pyqtSlot()
    def resetAngleFeed(self):
        self._use_case.set_angle_feed(False)

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
