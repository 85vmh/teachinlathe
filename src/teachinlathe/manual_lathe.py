import datetime
from collections import deque
from enum import Enum, auto

import linuxcnc
from qtpyvcp import SETTINGS
from qtpyvcp.actions.machine_actions import jog
from qtpyvcp.plugins import getPlugin
from qtpyvcp.plugins.status import STAT
from qtpyvcp.utilities.info import Info

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.widgets.manual_qml.joystick_state import JoystickState

LINUXCNC_CMD = linuxcnc.command()
INFO = Info()
STATUS = getPlugin('status')

class JoystickDirection(Enum):
    NONE = auto()
    X_PLUS = auto()
    X_MINUS = auto()
    Z_PLUS = auto()
    Z_MINUS = auto()


class JoggedAxis(Enum):
    NONE = auto()
    X = auto()
    Z = auto()


class JoystickFunction(Enum):
    NONE = auto()
    FEEDING = auto()
    JOGGING = auto()


class SpindleLever(Enum):
    REV = -1
    NONE = 0
    FWD = 1


class SpindleMode(Enum):
    Rpm = 0
    Css = 1


def isSpindleOn():
    return STAT.spindle[0]['direction'] != 0


def canHandleManualOperations():
    STAT.poll()
    return (STAT.task_state == linuxcnc.STATE_ON and
            STATUS.allHomed() and
            STAT.task_mode is not linuxcnc.MODE_AUTO)


class ManualLathe:
    _instance = None
    latheComponent = TeachInLatheComponent()
    spindleRpm = 300
    spindleCss = 200
    maxSpindleRpm = 2000
    stopAtActive = False
    stopAtAngle = 0
    feedPerRev = 0.1
    spindleLever = SpindleLever.NONE
    joystickDirection = JoystickDirection.NONE
    spindleCoverOpened = True
    isJoystickRapid = False
    joggedAxis = JoggedAxis.NONE
    spindleMode = SpindleMode.Rpm
    joystickFunction = JoystickFunction.NONE
    isTaperTurning = False
    joystickWidget = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ManualLathe, cls).__new__(cls)
            # Initialize the instance (only once)
            cls._initialize(cls._instance)
        return cls._instance

    @staticmethod
    def _initialize(instance):
        print("ManualLathe instance is created")
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleSwitchRevIn, instance.onSpindleSwitchRev)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleSwitchFwdIn, instance.onSpindleSwitchFwd)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinSpindleCoveredOpened, instance.onSpindleCoverOpened)
        instance.spindleCoverOpened = instance.latheComponent.comp.getPin(TeachInLatheComponent.PinSpindleCoveredOpened).value

        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickXMinus, instance.onJoystickXMinus)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickXPlus, instance.onJoystickXPlus)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickZMinus, instance.onJoystickZMinus)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickZPlus, instance.onJoystickZPlus)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickRapid, instance.onJoystickRapid)

    def setJoystickWidget(self, joystickWidget):
        self.joystickWidget = joystickWidget

    def onSpindleModeChanged(self, value=0):
        self.spindleMode = SpindleMode(value)

    def onInputRpmChanged(self, value=spindleRpm):
        print("onInputRpmChanged: ", value)
        self.spindleRpm = value

    def onInputCssChanged(self, value=spindleCss):
        print("onInputCssChanged: ", value)
        self.spindleCss = value

    def onMaxSpindleRpmChanged(self, value=maxSpindleRpm):
        print("onMaxSpindleRpmChanged: ", value)
        self.maxSpindleRpm = value

    def onStopAtActiveChanged(self, value=stopAtActive):
        self.stopAtActive = value

    def onStopAtAngleChanged(self, value=stopAtAngle):
        self.stopAtAngle = value

    def onInputFeedChanged(self, value=feedPerRev):
        print("onInputFeedChanged: ", value)
        self.feedPerRev = value
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinFeedPerRevValue).value = self.feedPerRev

    def onTaperTurningChanged(self, value=False):
        self.isTaperTurning = value

    def onSpindleSwitchRev(self, value=False):
        self.spindleLever = SpindleLever.REV if value else SpindleLever.NONE
        self.handleSpindleSwitch()

    def onSpindleSwitchFwd(self, value=False):
        self.spindleLever = SpindleLever.FWD if value else SpindleLever.NONE
        self.handleSpindleSwitch()

    def onSpindleCoverOpened(self, value=True):
        self.spindleCoverOpened = value
        self.handleSpindleSwitch()

    def onJoystickXPlus(self, value=False):
        self.joystickDirection = JoystickDirection.X_PLUS if value else JoystickDirection.NONE
        self.handleJoystick()

    def onJoystickXMinus(self, value=False):
        self.joystickDirection = JoystickDirection.X_MINUS if value else JoystickDirection.NONE
        self.handleJoystick()

    def onJoystickZPlus(self, value=False):
        self.joystickDirection = JoystickDirection.Z_PLUS if value else JoystickDirection.NONE
        self.handleJoystick()

    def onJoystickZMinus(self, value=False):
        self.joystickDirection = JoystickDirection.Z_MINUS if value else JoystickDirection.NONE
        self.handleJoystick()

    def onJoystickRapid(self, value=False):
        self.isJoystickRapid = value
        self.handleJoystick()

    def handleSpindleSwitch(self):
        if not canHandleManualOperations():
            return  # if the machine is not on or not homed, ignore spindle switch

        if self.spindleCoverOpened:
            print("Spindle cover is opened")
            return self.handleSpindleOff()

        match self.spindleMode:
            case SpindleMode.Rpm:
                if self.spindleLever is not SpindleLever.NONE:
                    direction = linuxcnc.SPINDLE_REVERSE if self.spindleLever == SpindleLever.REV else linuxcnc.SPINDLE_FORWARD
                    LINUXCNC_CMD.spindle(direction, int(self.spindleRpm), 0)
                    print("Spindle started in RPM mode")
                    self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = True
                else:
                    return self.handleSpindleOff()
            case SpindleMode.Css:
                if self.spindleLever is not SpindleLever.NONE:
                    direction = 'M4' if self.spindleLever == SpindleLever.REV else 'M3'
                    cmd = f"{direction} G96 S{self.spindleCss} D{self.maxSpindleRpm}"
                    STAT.poll()
                    if cmd is not None and STAT.task_mode is not linuxcnc.MODE_MDI:
                        LINUXCNC_CMD.mode(linuxcnc.MODE_MDI)
                        LINUXCNC_CMD.wait_complete()
                        LINUXCNC_CMD.mdi(cmd)
                        LINUXCNC_CMD.mode(linuxcnc.MODE_MANUAL)
                        LINUXCNC_CMD.wait_complete()
                        print("Spindle started in CSS mode")
                        print("MDI command executed: ", cmd)
                        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = True
                else:
                    return self.handleSpindleOff()
        return None

    def handleSpindleOff(self):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = False

    def handleJoystick(self):
        if not canHandleManualOperations():
            return  # if the machine is not on or not homed, ignore joystick

        if self.joystickWidget is not None:
            jog_speed = float(SETTINGS.get('machine.jog.linear-speed').getValue())
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinJogSpeedValue).value = jog_speed

            match self.joystickDirection:
                case JoystickDirection.NONE:
                    self.joystickWidget.setJoystickState(JoystickState.NEUTRAL)
                case JoystickDirection.X_PLUS:
                    self.joystickWidget.setJoystickState(JoystickState.FEEDING_X_POS)
                case JoystickDirection.X_MINUS:
                    self.joystickWidget.setJoystickState(JoystickState.FEEDING_X_NEG)
                case JoystickDirection.Z_PLUS:
                    self.joystickWidget.setJoystickState(JoystickState.FEEDING_Z_POS)
                case JoystickDirection.Z_MINUS:
                    self.joystickWidget.setJoystickState(JoystickState.FEEDING_Z_NEG)

        if self.joystickDirection == JoystickDirection.NONE:
            self.joystickWidget.setRapid(False)
            return
        elif self.joystickDirection is not JoystickDirection.NONE and self.isJoystickRapid:
            print("Joystick not none, rapid on")
            self.joystickWidget.setRapid(True)
