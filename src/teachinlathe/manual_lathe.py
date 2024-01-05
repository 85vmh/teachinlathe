import datetime
import threading
import time
from collections import deque
from enum import Enum, auto, IntEnum

import linuxcnc
from qtpyvcp.actions.machine_actions import jog
from qtpyvcp.plugins import getPlugin
from qtpyvcp.plugins.status import STAT
from qtpyvcp.widgets.base_widgets.dro_base_widget import RefType

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from qtpyvcp.utilities.info import Info

LINUXCNC_CMD = linuxcnc.command()
INFO = Info()
from qtpyvcp import SETTINGS


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


class ManualLathe:
    _instance = None
    latheComponent = TeachInLatheComponent()
    messageStack = MessageStack()
    spindleRpm = 300
    spindleCss = 200
    maxSpindleRpm = 2000
    stopAtActive = False
    stopAtAngle = 0
    feedPerRev = 0.1
    spindleLever = SpindleLever.NONE
    joystickDirection = JoystickDirection.NONE
    isJoystickRapid = False
    joggedAxis = JoggedAxis.NONE
    spindleMode = SpindleMode.Rpm
    startFeedingTimer = None
    joystickFunction = JoystickFunction.NONE
    joystickResetRequired = None
    isTaperTurning = False
    feedTaperAngle = 0

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

        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickXMinus, instance.onJoystickXMinus)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickXPlus, instance.onJoystickXPlus)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickZMinus, instance.onJoystickZMinus)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickZPlus, instance.onJoystickZPlus)
        instance.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickRapid, instance.onJoystickRapid)

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
        self.feedTaperAngle = value

    def onSpindleSwitchRev(self, value=False):
        self.spindleLever = SpindleLever.REV if value else SpindleLever.NONE
        self.handleSpindleSwitch()

    def onSpindleSwitchFwd(self, value=False):
        self.spindleLever = SpindleLever.FWD if value else SpindleLever.NONE
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
        match self.spindleLever:
            case SpindleLever.REV:
                cmd = 'M4'
            case SpindleLever.FWD:
                cmd = 'M3'
            case _:
                self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = False
                if self.stopFeeding():
                    self.joystickResetRequired = True
                return

        if cmd is not None:
            if self.spindleMode == SpindleMode.Rpm:
                cmd += f" G97 S{self.spindleRpm}"
            else:
                cmd += f" G96 S{self.spindleCss} D{self.maxSpindleRpm}"

        print(cmd)
        STAT.poll()
        if cmd is not None and STAT.task_mode is not linuxcnc.MODE_MDI:
            LINUXCNC_CMD.mode(linuxcnc.MODE_MDI)
            LINUXCNC_CMD.wait_complete()
            LINUXCNC_CMD.mdi(cmd)
            LINUXCNC_CMD.mode(linuxcnc.MODE_MANUAL)
            LINUXCNC_CMD.wait_complete()
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = True

    def handleJoystick(self):
        if self.joystickDirection == JoystickDirection.NONE:
            self.handleJoystickNeutral()
            return
        elif self.joystickDirection is not JoystickDirection.NONE and self.isJoystickRapid:
            print("joystick not none, rapid on")
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
                    print("feed attempted while spindle is off")

    def delayedFeed(self):
        print_with_timestamp("delayedFeed")
        if self.startFeedingTimer is not None:
            self.startFeedingTimer.cancel()

        self.startFeedingTimer = threading.Timer(0.3, self.startFeeding)  # Delay for 300ms
        self.startFeedingTimer.start()

    def startFeeding(self):
        print_with_timestamp("startFeeding")
        self.startFeedingTimer = None

        cmd = f"G95 F{self.feedPerRev} "

        if self.isTaperTurning:
            cmd += self.getTaperTurningCommand()
        else:
            cmd += self.getStraightTurningCommand()

        self.joystickFunction = JoystickFunction.FEEDING
        LINUXCNC_CMD.mode(linuxcnc.MODE_MDI)
        LINUXCNC_CMD.wait_complete()

        print_with_timestamp("execute mdi command: " + cmd)
        LINUXCNC_CMD.mdi(cmd)
        STAT.poll()

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

            match self.joystickDirection:
                case JoystickDirection.X_PLUS:
                    jog.axis('X', 1, speed=jog_speed / 60)
                    self.joggedAxis = JoggedAxis.X
                case JoystickDirection.X_MINUS:
                    jog.axis('X', -1, speed=jog_speed / 60)
                    self.joggedAxis = JoggedAxis.X
                case JoystickDirection.Z_PLUS:
                    jog.axis('Z', 1, speed=jog_speed / 60)
                    self.joggedAxis = JoggedAxis.Z
                case JoystickDirection.Z_MINUS:
                    jog.axis('Z', -1, speed=jog_speed / 60)
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

    def getStraightTurningCommand(self):
        x_bounds = INFO.getAxisMinMax('X')[0]
        z_bounds = INFO.getAxisMinMax('Z')[0]

        x_min_limit = x_bounds[0]
        x_max_limit = x_bounds[1]
        z_min_limit = z_bounds[0]
        z_max_limit = z_bounds[1]

        if self.joystickDirection == JoystickDirection.X_PLUS:
            return 'G53 G1 X%f' % x_max_limit
        elif self.joystickDirection == JoystickDirection.X_MINUS:
            return 'G53 G1 X%f' % x_min_limit
        elif self.joystickDirection == JoystickDirection.Z_PLUS:
            return 'G53 G1 Z%f' % z_max_limit
        elif self.joystickDirection == JoystickDirection.Z_MINUS:
            return 'G53 G1 Z%f' % z_min_limit
        else:
            return ""

    class Axis(IntEnum):
        X = 0
        Z = 2

    def getTaperTurningCommand(self):
        x_bounds = INFO.getAxisMinMax('X')[0]
        z_bounds = INFO.getAxisMinMax('Z')[0]

        x_min_limit = x_bounds[0]
        x_max_limit = x_bounds[1]
        z_min_limit = z_bounds[0]
        z_max_limit = z_bounds[1]

        pos = getPlugin('position')
        xPos = pos.abs(self.Axis.X)
        zPos = pos.abs(self.Axis.Z)

        print("xPos: ", getattr(pos, RefType.Absolute.name))
        print("zPos: ", zPos)

        # getattr(self.pos, self._ref_typ.name).notify(self.updateValue)
        # self.updateValue()

        if self.joystickDirection == JoystickDirection.X_PLUS:
            return 'G53 G1 X%f' % x_max_limit
        elif self.joystickDirection == JoystickDirection.X_MINUS:
            return 'G53 G1 X%f' % x_min_limit
        elif self.joystickDirection == JoystickDirection.Z_PLUS:
            return 'G53 G1 Z%f' % z_max_limit
        elif self.joystickDirection == JoystickDirection.Z_MINUS:
            return 'G53 G1 Z%f' % z_min_limit
        else:
            return ""
