import datetime
import threading
import time
from collections import deque
from enum import Enum, auto

import linuxcnc
from qtpyvcp import SETTINGS
from qtpyvcp.actions.machine_actions import jog
from qtpyvcp.plugins import getPlugin
from qtpyvcp.plugins.status import STAT
from qtpyvcp.utilities.info import Info

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.machine_limits import MachineLimitsHandler
from qtpyvcp.widgets.base_widgets.dro_base_widget import Axis

LINUXCNC_CMD = linuxcnc.command()
INFO = Info()
STATUS = getPlugin('status')
POSITION = getPlugin('position')


def print_with_timestamp(message):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:23]  # Slice to get milliseconds
    print(f"{timestamp}: {message}")


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


class UserMessage(Enum):
    CANNOT_FEED_WITH_SPINDLE_OFF = ('Cannot feed with spindle off',)
    JOYSTICK_RESET_REQUIRED = ('Joystick reset required',)

    def __init__(self, message):
        self.message = message


class MessageStack:
    def __init__(self):
        self.stack = deque()

    def push(self, message):
        self.stack.append(message)

    def pop(self):
        if self.stack:
            return self.stack.pop()
        return None

    def clear(self):
        self.stack.clear()

    def is_empty(self):
        return len(self.stack) == 0

    def __repr__(self):
        return repr(self.stack)


def canHandleManualOperations():
    STAT.poll()
    return (STAT.task_state == linuxcnc.STATE_ON and
            STATUS.allHomed() and
            STAT.task_mode is not linuxcnc.MODE_AUTO)


class ManualLathe:
    _instance = None
    latheComponent = TeachInLatheComponent()
    messageStack = MessageStack()
    limitsHandler = MachineLimitsHandler()
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
    startFeedingTimer = None
    joystickFunction = JoystickFunction.NONE
    joystickResetRequired = None
    isTaperTurning = False
    feedTaperAngle = 0
    previousMachineLimits = None
    currentMachineLimits = None

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
        getattr(POSITION, 'abs').notify(instance.positionUpdated)
        instance.limitsHandler.onLimitsChanged.connect(instance.onMachineLimitsChanged)

    def positionUpdated(self, pos):
        if self.previousMachineLimits != self.currentMachineLimits:
            if pos is None:
                pos = getattr(POSITION, 'abs').getValue()
            x_abs = pos[Axis.X]
            z_abs = pos[Axis.Z]
            print("x_abs: ", x_abs)
            print("z_abs: ", z_abs)

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

    def onMachineLimitsChanged(self, machine_limits):
        print("Machine limits changed: ", machine_limits)
        self.currentMachineLimits = machine_limits

    def onSpindleModeChanged(self, value=0):
        self.spindleMode = SpindleMode(value)

    def onInputRpmChanged(self, value=spindleRpm):
        self.spindleRpm = value

    def onInputCssChanged(self, value=spindleCss):
        self.spindleCss = value

    def onMaxSpindleRpmChanged(self, value=maxSpindleRpm):
        self.maxSpindleRpm = value

    def onStopAtActiveChanged(self, value=stopAtActive):
        self.stopAtActive = value

    def onStopAtAngleChanged(self, value=stopAtAngle):
        self.stopAtAngle = value

    def onInputFeedChanged(self, value=feedPerRev):
        self.feedPerRev = value

    def onTaperTurningChanged(self, value=False):
        self.isTaperTurning = value

    def onFeedAngleChanged(self, value=0):
        self.feedTaperAngle = float(value)

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

        if self.spindleMode == SpindleMode.Rpm:
            if self.spindleLever is not SpindleLever.NONE:
                direction = linuxcnc.SPINDLE_REVERSE if self.spindleLever == SpindleLever.REV else linuxcnc.SPINDLE_FORWARD
                LINUXCNC_CMD.spindle(direction, int(self.spindleRpm), 0)
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = True
            else:
                return self.handleSpindleOff()
        else:
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
                    self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = True
            else:
                return self.handleSpindleOff()

    def handleSpindleOff(self):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = False
        if self.stopFeeding():
            self.joystickResetRequired = True
        return

    def handleJoystick(self):
        if not canHandleManualOperations():
            return  # if the machine is not on or not homed, ignore joystick

        if self.joystickDirection == JoystickDirection.NONE:
            self.handleJoystickNeutral()
            return
        elif self.joystickDirection is not JoystickDirection.NONE and self.isJoystickRapid:
            print("Joystick not none, rapid on")
            self.startJogging()
            self.joystickResetRequired = True
        elif self.joystickFunction == JoystickFunction.JOGGING:
            self.stopJogging()
            self.joystickResetRequired = True

        if self.spindleLever is not SpindleLever.NONE:
            if self.joystickResetRequired:
                print("Joystick reset required")
            else:
                self.delayedFeed()
        else:
            match self.joystickFunction:
                case JoystickFunction.FEEDING:
                    self.stopFeeding()
                case JoystickFunction.JOGGING:
                    print("")
                case JoystickFunction.NONE:
                    print("Feed attempted while spindle is off")

    def delayedFeed(self):
        print_with_timestamp("delayedFeed")
        if self.startFeedingTimer is not None:
            self.startFeedingTimer.cancel()

        self.startFeedingTimer = threading.Timer(0.3, self.startFeeding)  # Delay for 300ms
        self.startFeedingTimer.start()

    def startFeeding(self):
        print_with_timestamp("startFeeding")
        self.startFeedingTimer = None

        # importing it in the beginning of the file causes circular import
        from teachinlathe.turning_helper import TurningHelper

        cmd = f"G95 F{self.feedPerRev} "

        if self.isTaperTurning:
            cmd += TurningHelper.getTaperTurningCommand(self.joystickDirection, self.feedTaperAngle)
        else:
            cmd += TurningHelper.getStraightTurningCommand(self.joystickDirection)

        self.joystickFunction = JoystickFunction.FEEDING
        LINUXCNC_CMD.mode(linuxcnc.MODE_MDI)
        LINUXCNC_CMD.wait_complete()

        print_with_timestamp("execute mdi command: " + cmd)
        LINUXCNC_CMD.mdi(cmd)

        # STAT.poll()
        # print("motion mode: ", STAT.motion_mode)
        # print("motion type: ", STAT.motion_type)
        # print("mdi queue: ", STAT.queue)

        # if STAT.motion_mode == linuxcnc.TRAJ_MODE_COORD and STAT.queue > 0:
        #     if STAT.motion_type == 0:  # motion_type == 0 means the command is not executed
        #         print_with_timestamp("mdi command failed, wait_complete: " + cmd)
        #         LINUXCNC_CMD.wait_complete()
        #         print_with_timestamp("wait_complete finished")
        #     elif STAT.motion_type == 2:  # motion_type == 2 means "Feed"
        #         print_with_timestamp("mdi command succeeded at first attempt")
        #     else:
        #         print_with_timestamp("unhandled motion type is: " + STAT.motion_type)

        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsPowerFeeding).value = True

    def handleJoystickNeutral(self):
        print("handleJoystickNeutral")
        if self.startFeedingTimer is not None:
            self.startFeedingTimer.cancel()

        match self.joystickFunction:
            case JoystickFunction.FEEDING:
                self.stopFeeding()
            case JoystickFunction.JOGGING:
                self.stopJogging()
            case JoystickFunction.NONE:
                print("Joystick neutral")
                self.joggedAxis = JoggedAxis.NONE
                # remove message: cannot feed with spindle off

        if self.joystickResetRequired:
            self.joystickResetRequired = False
            # remove message: joystick reset required

    def stopFeeding(self):
        if self.startFeedingTimer is not None:
            print("timer was on, canceling")
            self.startFeedingTimer.cancel()

        if self.joystickFunction == JoystickFunction.FEEDING:
            print("stopFeeding")
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsPowerFeeding).value = False
            self.joystickFunction = None
            return True
        return False

    def startJogging(self):
        if self.stopFeeding():
            time.sleep(0.2)  # Wait 100ms for the feed to stop before we start jogging

        if self.joystickDirection is not None:
            jog_speed = float(SETTINGS.get('machine.jog.linear-speed').getValue())

            print("jogDirection: " + self.joystickDirection.name + ", jogSpeed: " + str(jog_speed))
            self.joystickFunction = JoystickFunction.JOGGING

            STAT.poll()
            current_state = STAT.state
            print("task mode: ", current_state)

            if current_state is not linuxcnc.MODE_MANUAL:
                LINUXCNC_CMD.mode(linuxcnc.MODE_MANUAL)
                LINUXCNC_CMD.wait_complete()
                STAT.poll()
                print("task mode changed: ", STAT.task_mode)

            actual_jog_speed = jog_speed / 60
            match self.joystickDirection:
                case JoystickDirection.X_PLUS:
                    jog.axis('X', 1, speed=actual_jog_speed)
                    self.joggedAxis = JoggedAxis.X
                case JoystickDirection.X_MINUS:
                    jog.axis('X', -1, speed=actual_jog_speed)
                    self.joggedAxis = JoggedAxis.X
                case JoystickDirection.Z_PLUS:
                    jog.axis('Z', 1, speed=actual_jog_speed)
                    self.joggedAxis = JoggedAxis.Z
                case JoystickDirection.Z_MINUS:
                    jog.axis('Z', -1, speed=actual_jog_speed)
                    self.joggedAxis = JoggedAxis.Z

    def stopJogging(self):
        if self.joystickFunction == JoystickFunction.JOGGING:
            print("stopJogging")

            STAT.poll()
            if STAT.task_mode is not linuxcnc.MODE_MANUAL:
                LINUXCNC_CMD.mode(linuxcnc.MODE_MANUAL)
                LINUXCNC_CMD.wait_complete()

            match self.joggedAxis:
                case JoggedAxis.X:
                    jog.axis('X')
                case JoggedAxis.Z:
                    jog.axis('Z')
            self.joystickFunction = None
