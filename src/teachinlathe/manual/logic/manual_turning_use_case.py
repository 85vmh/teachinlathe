"""What the lathe does under the operator's hands, in manual turning.

The spindle lever starts and stops the spindle at the RPM or CSS on the
screen; the joystick feeds or jogs an axis; the handwheels are enabled or
not. This class owns the HAL pins all of that reads and writes, and tells
ManualTurningViewModel what the machine is doing through its signals.

It used to be two things: ManualLathe, the jog and spindle logic, and the
main window's HAL listeners copying pin values into the view model.
"""

from __future__ import annotations

import logging
from collections import namedtuple
from enum import Enum, auto
from typing import Optional

import linuxcnc
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.core.settings_repository import JOG_SPEED, settings_repository
from teachinlathe.core.status_repository import status_repository
from teachinlathe.manual.logic.joystick_state import JoystickState

log = logging.getLogger(__name__)

# The actual RPM is a float that moves all the time; the screen shows it at
# this pace rather than at every poll.
RPM_REFRESH_MS = 300


class JoystickDirection(Enum):
    NONE = auto()
    X_PLUS = auto()
    X_MINUS = auto()
    Z_PLUS = auto()
    Z_MINUS = auto()


class SpindleLever(Enum):
    REV = -1
    NONE = 0
    FWD = 1


class SpindleMode(Enum):
    Rpm = 0
    Css = 1


JOYSTICK_STATES = {
    JoystickDirection.NONE: JoystickState.NEUTRAL,
    JoystickDirection.X_PLUS: JoystickState.FEEDING_X_POS,
    JoystickDirection.X_MINUS: JoystickState.FEEDING_X_NEG,
    JoystickDirection.Z_PLUS: JoystickState.FEEDING_Z_POS,
    JoystickDirection.Z_MINUS: JoystickState.FEEDING_Z_NEG,
}

#: Whether the handwheels may be used at all, and which of them are on.
Handwheels = namedtuple("Handwheels", "allowed x_enabled z_enabled")


class ManualTurningUseCase(QObject):
    spindleRunningChanged = pyqtSignal(bool)
    spindleCoverOpenedChanged = pyqtSignal(bool)
    spindleResetRequiredChanged = pyqtSignal(bool)
    spindleAngleChanged = pyqtSignal(float)
    actualRpmChanged = pyqtSignal(int)
    # 1 or 2
    gearChanged = pyqtSignal(int)
    spindleOverrideChanged = pyqtSignal(float)
    feedOverrideChanged = pyqtSignal(float)
    feedingChanged = pyqtSignal(bool)
    joystickResetRequiredChanged = pyqtSignal(bool)
    # a JoystickState value
    joystickStateChanged = pyqtSignal(int)
    joystickRapidChanged = pyqtSignal(bool)
    angleFeedChanged = pyqtSignal(bool)
    jogIncrementChanged = pyqtSignal(float)
    handwheelsChanged = pyqtSignal()

    def __init__(self, hal: Optional[TeachInLatheComponent] = None, status=None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._comp = (TeachInLatheComponent() if hal is None else hal).comp
        self._status = status_repository() if status is None else status
        self._command = linuxcnc.command()

        # What the operator set on the screen.
        self._spindle_mode = SpindleMode.Rpm
        self._spindle_rpm = 300
        self._spindle_css = 200
        self._max_spindle_rpm = 2000
        self._angle_feed = False

        # What the machine's controls say.
        self._spindle_lever = SpindleLever.NONE
        self._joystick_direction = JoystickDirection.NONE
        self._joystick_rapid = False
        self._spindle_cover_opened = bool(self._pin(TeachInLatheComponent.PinSpindleCoveredOpened))

        # The handwheels the operator switched on, kept while they are not
        # allowed so they come back as they were.
        self._x_handwheel = True
        self._z_handwheel = True
        self._handwheels_allowed = True
        self._set_pin(TeachInLatheComponent.PinHandwheelsXEnable, True)
        self._set_pin(TeachInLatheComponent.PinHandwheelsZEnable, True)

        self._raw_rpm = 0
        self._actual_rpm = 0
        self._rpm_timer = QTimer(self)
        self._rpm_timer.setInterval(RPM_REFRESH_MS)
        self._rpm_timer.timeout.connect(self._publish_actual_rpm)
        self._rpm_timer.start()

        self._listen()

    def _listen(self):
        listen = self._comp.addListener
        pins = TeachInLatheComponent
        listen(pins.PinSpindleSwitchRevIn, self._on_spindle_switch_rev)
        listen(pins.PinSpindleSwitchFwdIn, self._on_spindle_switch_fwd)
        listen(pins.PinSpindleCoveredOpened, self._on_spindle_cover_opened)
        listen(pins.PinSpindleIsOn, self._on_spindle_running)
        listen(pins.PinSpindleResetRequired,
               lambda value: self.spindleResetRequiredChanged.emit(bool(value)))
        listen(pins.PinSpindleOrientation,
               lambda value: self.spindleAngleChanged.emit(float(value)))
        listen(pins.PinSpindleActualRpm, self._on_spindle_rpm)
        listen(pins.PinSpindleIsFirstGear, lambda value: self.gearChanged.emit(1 if value else 2))

        listen(pins.PinJoystickXMinus, lambda v: self._on_joystick(JoystickDirection.X_MINUS, v))
        listen(pins.PinJoystickXPlus, lambda v: self._on_joystick(JoystickDirection.X_PLUS, v))
        listen(pins.PinJoystickZMinus, lambda v: self._on_joystick(JoystickDirection.Z_MINUS, v))
        listen(pins.PinJoystickZPlus, lambda v: self._on_joystick(JoystickDirection.Z_PLUS, v))
        listen(pins.PinJoystickRapid, self._on_joystick_rapid)
        listen(pins.PinJoystickIsFeeding, lambda value: self.feedingChanged.emit(bool(value)))
        listen(pins.PinJoystickResetRequired,
               lambda value: self.joystickResetRequiredChanged.emit(bool(value)))

        listen(pins.PinHandwheelsJogIncrement,
               lambda value: self.jogIncrementChanged.emit(float(value)))
        listen(pins.PinHandwheelsAllowed, self._on_handwheels_allowed)
        listen(pins.PinButtonCycleStop, self._on_cycle_stop)

        self._status.spindle[0].override.signal.connect(
            lambda value: self.spindleOverrideChanged.emit(float(value)))
        self._status.feedrate.signal.connect(
            lambda value: self.feedOverrideChanged.emit(float(value)))

    # ── what the machine is doing now ───────────────────────────────────────

    @property
    def spindle_running(self) -> bool:
        return bool(self._pin(TeachInLatheComponent.PinSpindleIsOn))

    @property
    def spindle_cover_opened(self) -> bool:
        return self._spindle_cover_opened

    @property
    def spindle_reset_required(self) -> bool:
        return bool(self._pin(TeachInLatheComponent.PinSpindleResetRequired))

    @property
    def spindle_angle(self) -> float:
        return float(self._pin(TeachInLatheComponent.PinSpindleOrientation))

    @property
    def gear(self) -> int:
        return 1 if self._pin(TeachInLatheComponent.PinSpindleIsFirstGear) else 2

    @property
    def spindle_override(self) -> float:
        return float(self._status.spindle[0].override.value)

    @property
    def feed_override(self) -> float:
        return float(self._status.feedrate.value)

    @property
    def feeding(self) -> bool:
        return bool(self._pin(TeachInLatheComponent.PinJoystickIsFeeding))

    @property
    def joystick_reset_required(self) -> bool:
        return bool(self._pin(TeachInLatheComponent.PinJoystickResetRequired))

    @property
    def angle_feed(self) -> bool:
        return self._angle_feed

    @property
    def handwheels(self) -> Handwheels:
        if not self._handwheels_allowed:
            return Handwheels(False, False, False)
        return Handwheels(True, self._x_handwheel, self._z_handwheel)

    # ── what the operator set ───────────────────────────────────────────────

    def set_spindle_mode(self, mode) -> None:
        self._spindle_mode = SpindleMode(int(mode))

    def set_spindle_rpm(self, rpm) -> None:
        self._spindle_rpm = rpm

    def set_spindle_css(self, css) -> None:
        self._spindle_css = css

    def set_max_spindle_rpm(self, rpm) -> None:
        self._max_spindle_rpm = rpm

    def set_feed_per_rev(self, feed) -> None:
        self._set_pin(TeachInLatheComponent.PinFeedPerRevValue, float(feed))

    def set_angle_feed(self, enabled) -> None:
        enabled = bool(enabled)
        if enabled == self._angle_feed:
            return
        self._angle_feed = enabled
        self._set_pin(TeachInLatheComponent.PinIsAngleFeed, enabled)
        self.angleFeedChanged.emit(enabled)

    def set_handwheel_enabled(self, axis: str, enabled) -> None:
        enabled = bool(enabled)
        if axis == "x":
            self._x_handwheel = enabled
            self._set_pin(TeachInLatheComponent.PinHandwheelsXEnable, enabled)
        else:
            self._z_handwheel = enabled
            self._set_pin(TeachInLatheComponent.PinHandwheelsZEnable, enabled)
        self.handwheelsChanged.emit()

    # ── the spindle ─────────────────────────────────────────────────────────

    def _on_spindle_switch_rev(self, value=False):
        self._spindle_lever = SpindleLever.REV if value else SpindleLever.NONE
        self._handle_spindle_switch()

    def _on_spindle_switch_fwd(self, value=False):
        self._spindle_lever = SpindleLever.FWD if value else SpindleLever.NONE
        self._handle_spindle_switch()

    def _on_spindle_cover_opened(self, value=True):
        self._spindle_cover_opened = bool(value)
        self.spindleCoverOpenedChanged.emit(self._spindle_cover_opened)
        self._handle_spindle_switch()

    def _on_spindle_running(self, value):
        running = bool(value)
        self.spindleRunningChanged.emit(running)
        if not running and self._angle_feed:
            log.info("spindle stopped: angle feed off")
            self.set_angle_feed(False)

    def _on_spindle_rpm(self, value):
        self._raw_rpm = abs(int(value))

    def _publish_actual_rpm(self):
        if self._raw_rpm != self._actual_rpm:
            self._actual_rpm = self._raw_rpm
            self.actualRpmChanged.emit(self._actual_rpm)

    def _handle_spindle_switch(self):
        if not self._can_handle_manual_operations():
            return  # if the machine is not on or not homed, ignore spindle switch

        if self._spindle_cover_opened or self._spindle_lever is SpindleLever.NONE:
            self._set_pin(TeachInLatheComponent.PinIsSpindleStarted, False)
            return

        reverse = self._spindle_lever == SpindleLever.REV
        match self._spindle_mode:
            case SpindleMode.Rpm:
                direction = linuxcnc.SPINDLE_REVERSE if reverse else linuxcnc.SPINDLE_FORWARD
                self._command.spindle(direction, int(self._spindle_rpm), 0)
                log.info("spindle started at %s rpm", self._spindle_rpm)
                self._set_pin(TeachInLatheComponent.PinIsSpindleStarted, True)
            case SpindleMode.Css:
                cmd = f"{'M4' if reverse else 'M3'} G96 S{self._spindle_css} D{self._max_spindle_rpm}"
                stat = self._status.stat
                stat.poll()
                if stat.task_mode is not linuxcnc.MODE_MDI:
                    self._command.mode(linuxcnc.MODE_MDI)
                    self._command.wait_complete()
                    self._command.mdi(cmd)
                    self._command.mode(linuxcnc.MODE_MANUAL)
                    self._command.wait_complete()
                    log.info("spindle started in CSS: %s", cmd)
                    self._set_pin(TeachInLatheComponent.PinIsSpindleStarted, True)

    # ── the joystick ────────────────────────────────────────────────────────

    def _on_joystick(self, direction, value=False):
        self._joystick_direction = direction if value else JoystickDirection.NONE
        self._handle_joystick()

    def _on_joystick_rapid(self, value=False):
        self._joystick_rapid = bool(value)
        self._handle_joystick()

    def _handle_joystick(self):
        if not self._can_handle_manual_operations():
            return  # if the machine is not on or not homed, ignore joystick

        jog_speed = float(settings_repository().get(JOG_SPEED))
        self._set_pin(TeachInLatheComponent.PinJogSpeedValue, jog_speed)
        self.joystickStateChanged.emit(JOYSTICK_STATES[self._joystick_direction].value)

        if self._joystick_direction == JoystickDirection.NONE:
            self.joystickRapidChanged.emit(False)
        elif self._joystick_rapid:
            self.joystickRapidChanged.emit(True)

    def _on_cycle_stop(self, pressed):
        if pressed and self._angle_feed:
            log.info("cycle stop pressed: angle feed off")
            self.set_angle_feed(False)

    # ── the handwheels ──────────────────────────────────────────────────────

    def _on_handwheels_allowed(self, allowed):
        log.info("handwheels allowed: %s", allowed)
        self._handwheels_allowed = bool(allowed)
        self.handwheelsChanged.emit()

    # ── helpers ─────────────────────────────────────────────────────────────

    def _can_handle_manual_operations(self) -> bool:
        stat = self._status.stat
        stat.poll()
        return (stat.task_state == linuxcnc.STATE_ON and
                self._status.allHomed() and
                stat.task_mode is not linuxcnc.MODE_AUTO)

    def _pin(self, name):
        return self._comp.getPin(name).value

    def _set_pin(self, name, value):
        self._comp.getPin(name).value = value
