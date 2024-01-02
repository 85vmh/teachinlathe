import datetime
import threading
import time
from enum import Enum, auto
from abc import ABC, abstractmethod
from collections import deque

import linuxcnc
from qtpyvcp.actions.machine_actions import issue_mdi, jog, mode
from qtpyvcp.plugins.status import STAT

from teachinlathe.feed_helper import getTaperTurningCommand, getStraightTurningCommand
from teachinlathe.lathe_hal_component import TeachInLatheComponent

CMD = linuxcnc.command()


def print_with_timestamp(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp}: {message}")


class JoystickDirection(Enum):
    NONE = auto()
    X_PLUS = auto()
    X_MINUS = auto()
    Z_PLUS = auto()
    Z_MINUS = auto()


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


class FeedMode(Enum):
    PerRev = 0
    PerMin = 1


def isSpindleOn():
    return STAT.spindle[0]['direction'] != 0


class Event(Enum):
    JOYSTICK_TO_NEUTRAL_SP_OFF = auto()
    JOYSTICK_TO_NEUTRAL_SP_ON = auto()
    JOYSTICK_TO_FEED_SP_ON = auto()
    JOYSTICK_TO_FEED_SP_OFF = auto()
    JOYSTICK_TO_JOG_SP_ON = auto()
    JOYSTICK_TO_JOG_SP_OFF = auto()
    FEED_DELAY_EXPIRED = auto()
    FEED_DELAY_CANCELED = auto()


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
    manualTurningStateMachine = None
    messageStack = MessageStack()
    spindleRpm = 300
    spindleCss = 200
    maxSpindleRpm = 2000
    stopAtActive = False
    stopAtAngle = 0
    feedPerRev = 0.1
    feedPerMin = 10
    spindleLever = SpindleLever.NONE
    joystickDirection = JoystickDirection.NONE
    isJoystickRapid = False
    spindleMode = SpindleMode.Rpm
    feedMode = FeedMode.PerRev
    startFeedingTimer = None
    joystickFunction = JoystickFunction.NONE
    joystickResetRequired = None
    isTaperTurning = False
    feedTaperAngle = 0

    class MachineState(ABC):
        @abstractmethod
        def on_entered(self, machine):
            pass

    class IdleState(MachineState):
        def on_entered(self, machine):
            print("ManualLathe.IdleState entered")
            ManualLathe.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = False
            ManualLathe.latheComponent.comp.getPin(TeachInLatheComponent.PinIsPowerFeeding).value = False

    class SpindleOnReadyToFeed(MachineState):
        def on_entered(self, machine):
            print("ManualLathe.SpindleOnReadyToFeed entered")
            if not isSpindleOn():
                ManualLathe.handleSpindleSwitch(ManualLathe._instance)
            # ManualLathe.messageStack.pop(UserMessage.CANNOT_FEED_WITH_SPINDLE_OFF)

    class PreFeedDelay(MachineState):
        def on_entered(self, machine):
            print_with_timestamp("PreFeedDelay entered")
            if ManualLathe.startFeedingTimer is not None:
                ManualLathe.startFeedingTimer.cancel()
            ManualLathe.startFeedingTimer = threading.Timer(0.2, self.startFeeding)  # Delay for 200ms
            ManualLathe.startFeedingTimer.start()

        def startFeeding(self):
            print_with_timestamp("PreFeedDelay finished")
            ManualLathe.startFeedingTimer = None
            ManualLathe._instance.manualTurningStateMachine.handle_event(Event.FEED_DELAY_EXPIRED)

    class Feeding(MachineState):
        def on_entered(self, machine):
            print_with_timestamp("Feeding entered")
            if ManualLathe.isTaperTurning:
                cmd = getTaperTurningCommand(self, ManualLathe.joystickDirection, ManualLathe.feedTaperAngle)
            else:
                cmd = getStraightTurningCommand(self, ManualLathe.joystickDirection)

            if ManualLathe.feedMode == FeedMode.PerRev:
                cmd += f" F{ManualLathe.feedPerRev}"
            else:
                cmd += f" F{ManualLathe.feedPerMin}"

            issue_mdi(cmd)
            ManualLathe.latheComponent.comp.getPin(TeachInLatheComponent.PinIsPowerFeeding).value = True

    class CannotFeedWithSpindleOff(MachineState):
        def on_entered(self, machine):
            print("CannotFeedWithSpindleOff entered")
            ManualLathe.latheComponent.comp.getPin(TeachInLatheComponent.PinIsPowerFeeding).value = False
            ManualLathe.messageStack.push(UserMessage.CANNOT_FEED_WITH_SPINDLE_OFF)

    class JoystickResetRequired(MachineState):
        def on_entered(self, machine):
            print("JoystickResetRequired entered")
            ManualLathe.latheComponent.comp.getPin(TeachInLatheComponent.PinIsPowerFeeding).value = False
            ManualLathe.messageStack.push(UserMessage.JOYSTICK_RESET_REQUIRED)

    class Jogging(MachineState):
        def on_entered(self, machine):
            print("Jogging entered")

    class ManualTurningStateMachine:
        def __init__(self):
            self.previous_state = None
            self.current_state = ManualLathe.IdleState()
            self.transition_map = {
                # joystick is neutral and spindle was turned on
                (ManualLathe.IdleState, Event.JOYSTICK_TO_NEUTRAL_SP_ON): ManualLathe.SpindleOnReadyToFeed,
                # the joystick is moved to feeding position, but the spindle is off
                (ManualLathe.IdleState, Event.JOYSTICK_TO_FEED_SP_OFF): ManualLathe.CannotFeedWithSpindleOff,
                # joystick is neutral and spindle was turned off
                (ManualLathe.SpindleOnReadyToFeed, Event.JOYSTICK_TO_NEUTRAL_SP_OFF): ManualLathe.IdleState,
                # spindle is on, and the joystick is moved into feeding position
                (ManualLathe.SpindleOnReadyToFeed, Event.JOYSTICK_TO_FEED_SP_ON): ManualLathe.PreFeedDelay,
                # before starting the feed there is a delay of 200ms, in case the initial intention was jogging
                (ManualLathe.PreFeedDelay, Event.FEED_DELAY_EXPIRED): ManualLathe.Feeding,
                # spindle is on, the joystick was in feeding position, but it was moved to neutral,
                (ManualLathe.Feeding, Event.JOYSTICK_TO_NEUTRAL_SP_ON): ManualLathe.SpindleOnReadyToFeed,
                # spindle was turned off while the joystick has remained in feeding position
                (ManualLathe.Feeding, Event.JOYSTICK_TO_FEED_SP_OFF): ManualLathe.JoystickResetRequired,
                # spindle is on, it was feeding, but now the joystick is moved to jog
                (ManualLathe.Feeding, Event.JOYSTICK_TO_JOG_SP_ON): ManualLathe.Jogging,
                # the spindle was turned off, the joystick remained in feeding position, and the spindle is turned on again
                (ManualLathe.CannotFeedWithSpindleOff, Event.JOYSTICK_TO_FEED_SP_ON): ManualLathe.JoystickResetRequired,
                # jog position is always after the feed position, in fact jog position is the same as feed position + the rapid switch
                # if the joystick is already in feed position, do the jog even if for the feed was needed a reset
                (ManualLathe.CannotFeedWithSpindleOff, Event.JOYSTICK_TO_JOG_SP_ON): ManualLathe.Jogging,
                # if the spindle is off and the joystick is moved to jog (which is passing through feed) do the jog
                (ManualLathe.CannotFeedWithSpindleOff, Event.JOYSTICK_TO_JOG_SP_OFF): ManualLathe.Jogging,
                # if the joystick remained in a feed position while the spindle was turned off, bringing the joystick to neutral, will trigger the ManualLathe.IdleState
                (ManualLathe.CannotFeedWithSpindleOff, Event.JOYSTICK_TO_NEUTRAL_SP_OFF): ManualLathe.IdleState,
                # if the joystick has remained in feeding position when the spindle has started, bringing the joystick to neutral,
                # will bring the machine again into ManualLathe.ReadyToFeed
                (ManualLathe.JoystickResetRequired, Event.JOYSTICK_TO_NEUTRAL_SP_ON): ManualLathe.SpindleOnReadyToFeed,
                # if the joystick has remained in feeding position when the spindle was stopped started, bringing the joystick to neutral,
                # will move the machine into ManualLathe.IdleState
                (ManualLathe.JoystickResetRequired, Event.JOYSTICK_TO_NEUTRAL_SP_OFF): ManualLathe.IdleState,
                # after finishing a jog, the first rest position of the joystick will be the feeding position,
                # so before any eventual feeding, it needs to be reset
                (ManualLathe.Jogging, Event.JOYSTICK_TO_FEED_SP_ON): ManualLathe.JoystickResetRequired,
                (ManualLathe.Jogging, Event.JOYSTICK_TO_FEED_SP_OFF): ManualLathe.JoystickResetRequired,
                (ManualLathe.Jogging, Event.JOYSTICK_TO_JOG_SP_OFF): ManualLathe.Jogging,  # this is the same state, it should be commented out
            }

        def handle_event(self, event):
            print("CurrentState: ", self.current_state, " Event: ", event)
            next_state_class = self.transition_map.get((type(self.current_state), event))
            if next_state_class:
                self.transition_to(next_state_class())

        def transition_to(self, new_state):
            self.previous_state = self.current_state
            self.current_state = new_state
            self.current_state.on_entered(self)

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

        instance.manualTurningStateMachine = ManualLathe.ManualTurningStateMachine()

    def onSpindleModeChanged(self, value=0):
        self.spindleMode = SpindleMode(value)
        print("spindleMode changed to: ", self.spindleMode)

    def onFeedModeChanged(self, value=0):
        self.feedMode = FeedMode(value)
        print("feedMode changed to: ", self.feedMode)

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

    def onSpindleSwitchRev(self, value=False):
        self.spindleLever = SpindleLever.REV if value else SpindleLever.NONE
        self.evaluateJoystickAndSpindle()

    def onSpindleSwitchFwd(self, value=False):
        self.spindleLever = SpindleLever.FWD if value else SpindleLever.NONE
        self.evaluateJoystickAndSpindle()

    def onJoystickXPlus(self, value=False):
        self.joystickDirection = JoystickDirection.X_PLUS if value else JoystickDirection.NONE
        self.evaluateJoystickAndSpindle()

    def onJoystickXMinus(self, value=False):
        self.joystickDirection = JoystickDirection.X_MINUS if value else JoystickDirection.NONE
        self.evaluateJoystickAndSpindle()

    def onJoystickZPlus(self, value=False):
        self.joystickDirection = JoystickDirection.Z_PLUS if value else JoystickDirection.NONE
        self.evaluateJoystickAndSpindle()

    def onJoystickZMinus(self, value=False):
        self.joystickDirection = JoystickDirection.Z_MINUS if value else JoystickDirection.NONE
        self.evaluateJoystickAndSpindle()

    def onJoystickRapid(self, value=False):
        self.isJoystickRapid = value
        self.evaluateJoystickAndSpindle()

    def handleSpindleSwitch(self):
        match self.spindleLever:
            case SpindleLever.REV:
                cmd = 'M3'
            case SpindleLever.FWD:
                cmd = 'M4'
            case _:
                cmd = None

        if cmd is not None:
            if self.spindleMode == SpindleMode.Rpm:
                cmd += f" G97 S{self.spindleRpm}"
            else:
                cmd += f" G96 S{self.spindleCss} D{self.maxSpindleRpm}"

            if self.feedMode == FeedMode.PerRev:
                cmd += f" G95 F{self.feedPerRev}"
            else:
                cmd += f" G94 F{self.feedPerMin}"

        print(cmd)
        if cmd is not None and STAT.task_mode is not linuxcnc.MODE_MDI:
            issue_mdi(cmd)
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = True
        else:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsSpindleStarted).value = False

    def evaluateJoystickAndSpindle(self):
        event = None
        # print("evaluateJoystickAndSpindle:", self.joystickDirection, self.spindleLever)
        match self.spindleLever:
            case SpindleLever.REV | SpindleLever.FWD:
                match self.joystickDirection:
                    case JoystickDirection.X_PLUS | JoystickDirection.X_MINUS | JoystickDirection.Z_PLUS | JoystickDirection.Z_MINUS:
                        if self.isJoystickRapid:
                            event = Event.JOYSTICK_TO_JOG_SP_ON
                        else:
                            event = Event.JOYSTICK_TO_FEED_SP_ON
                    case JoystickDirection.NONE:
                        if self.isJoystickRapid:
                            event = Event.JOYSTICK_TO_JOG_SP_ON
                        else:
                            event = Event.JOYSTICK_TO_NEUTRAL_SP_ON
            case SpindleLever.NONE:
                match self.joystickDirection:
                    case JoystickDirection.X_PLUS | JoystickDirection.X_MINUS | JoystickDirection.Z_PLUS | JoystickDirection.Z_MINUS:
                        if self.isJoystickRapid:
                            event = Event.JOYSTICK_TO_JOG_SP_OFF
                        else:
                            event = Event.JOYSTICK_TO_FEED_SP_OFF
                    case JoystickDirection.NONE:
                        if self.isJoystickRapid:
                            event = Event.JOYSTICK_TO_JOG_SP_OFF
                        else:
                            event = Event.JOYSTICK_TO_NEUTRAL_SP_OFF

        if event is not None:
            self.manualTurningStateMachine.handle_event(event)

    def delayedFeed(self):
        if self.startFeedingTimer is not None:
            self.startFeedingTimer.cancel()
        self.startFeedingTimer = threading.Timer(0.2, self.startFeeding)  # Delay for 200ms
        self.startFeedingTimer.start()

    def startFeeding(self):
        print("startFeeding")
        if self.isTaperTurning:
            cmd = getTaperTurningCommand(self, self.joystickDirection, self.feedTaperAngle)
        else:
            cmd = getStraightTurningCommand(self, self.joystickDirection)

        self.joystickFunction = JoystickFunction.FEEDING
        if self.feedMode == FeedMode.PerRev:
            cmd += f" F{self.feedPerRev}"
        else:
            cmd += f" F{self.feedPerMin}"

        issue_mdi(cmd)
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsPowerFeeding).value = True

    def handleJoystickNeutral(self):
        print("handleJoystickNeutral")
        self.startFeedingTimer.cancel()
        if self.joystickFunction == JoystickFunction.FEEDING:
            self.stopFeeding()
        elif self.joystickFunction == JoystickFunction.JOGGING:
            self.stopJogging()
        else:
            print("Joystick neutral")
            # remove message: cannot feed with spindle off
        if self.joystickResetRequired:
            self.joystickResetRequired = False
            # remove message: joystick reset required

    def stopFeeding(self):
        self.startFeedingTimer.cancel()
        if self.joystickFunction == JoystickFunction.FEEDING:
            print("stopFeeding")
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinIsPowerFeeding).value = False
            self.joystickFunction = None
            return True
        return False

    def startJogging(self, joystickDirection=None):
        if self.stopFeeding():
            time.sleep(0.1)  # Wait 100ms for the feed to stop before we start jogging

        if self.joystickDirection is not None:
            print("jogDirection: ", joystickDirection)
            self.joystickFunction = JoystickFunction.JOGGING
            jogSpeed = 3000  # use the real value
            mode.manual()
            match joystickDirection:
                case JoystickDirection.X_PLUS:
                    jog.axis('X', 1, speed=jogSpeed)
                case JoystickDirection.X_MINUS:
                    jog.axis('X', -1, speed=jogSpeed)
                case JoystickDirection.Z_PLUS:
                    jog.axis('Z', 1, speed=jogSpeed)
                case JoystickDirection.Z_MINUS:
                    jog.axis('Z', -1, speed=jogSpeed)

    def stopJogging(self, joystickDirection=None):
        if self.joystickFunction == JoystickFunction.JOGGING:
            print("stopJogging")
            mode.manual()
            match joystickDirection:
                case JoystickDirection.X_PLUS | JoystickDirection.X_MINUS:
                    jog.axis('X')
                case JoystickDirection.Z_PLUS | JoystickDirection.Z_MINUS:
                    jog.axis('Z')
            self.joystickFunction = None

    # ---------------- Internal class
