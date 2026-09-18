from teachinlathe.repositories.hal_repository import hal_component


class TeachInLatheComponent:
    _instance = None

    PinJoystickXPlus = 'joystick.x-plus'
    PinJoystickXMinus = 'joystick.x-minus'
    PinJoystickZPlus = 'joystick.z-plus'
    PinJoystickZMinus = 'joystick.z-minus'
    PinJoystickRapid = 'joystick.rapid'
    PinJoystickIsFeeding = 'joystick.is-feeding'
    PinJoystickResetRequired = 'joystick.reset-required'
    PinFeedPerRevValue = 'joystick.feed-per-rev'
    PinIsAngleFeed = 'joystick.is-angle-feed'
    PinJogSpeedValue = 'joystick.jog-speed'
    PinIsSpindleStarted = 'app-status.spindle-started'
    PinIsReadyToRunProgram = 'app-status.ready-to-run-program'
    PinProgramLoaded = 'app-status.program-loaded'
    PinProgramCompleted = 'app-status.program-completed'
    PinProgramAborted = 'app-status.program-aborted'
    PinDevMode = 'app-status.dev-mode'
    PinButtonCycleStart = 'button.cycle-start'
    PinCycleStartLed = 'app-status.cycle-start-led'
    PinButtonCycleStop = 'button.cycle-stop'
    PinSpindleCoveredOpened = 'spindle.cover-opened'
    PinSpindleSwitchRevIn = 'spindle.switch-rev-in'
    PinSpindleSwitchFwdIn = 'spindle.switch-fwd-in'
    PinSpindleActualRpm = 'spindle.actual-rpm'
    PinSpindleIsOn = 'spindle.is-on'
    PinSpindleResetRequired = 'spindle.reset-required'
    PinSpindleOrientation = 'spindle.orientation'
    PinSpindleIsFirstGear = 'spindle.is-first-gear'
    PinHandwheelsJogIncrement = 'handwheels.jog-increment'
    PinHandwheelsAllowed = 'handwheels.allowed'
    PinHandwheelsXEnable = 'handwheels.x-enable'
    PinHandwheelsZEnable = 'handwheels.z-enable'
    PinHandwheelsAngleJogEnable = 'handwheels.angle-jog-enabled'
    PinHandwheelsAngleJogValue = 'handwheels.angle-jog-value'
    PinToolChangeToolNo = 'tool-change.number'
    PinToolChangeRequest = 'tool-change.change'
    PinToolChangeResponse = 'tool-change.changed'
    PinToolChangeCanceled = 'tool-change.canceled'
    PinAxisLimitXMin = 'axis-limits.x-min'
    PinAxisLimitXMax = 'axis-limits.x-max'
    PinAxisLimitZMin = 'axis-limits.z-min'
    PinAxisLimitZMax = 'axis-limits.z-max'

    # def __new__(cls, *args, **kwargs):
    #     if not cls._instance:
    #         cls._instance = super(TeachInLatheComponent, cls).__new__(cls)
    #         # Initialize the instance (only once)
    #         cls._initialize(cls._instance)
    #     return cls._instance

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            instance = super().__new__(cls)
            # Only kept once it is actually usable. Setting _instance first
            # and then failing in _initialize left a singleton with no .comp,
            # so the clear HAL error ("duplicate component name") turned into
            # an AttributeError at some unrelated later point.
            instance._initialize()
            cls._instance = instance
        return cls._instance

    def __init__(self):
        pass  # Initialization logic moved to __new__

    def _initialize(self):
        self.comp = hal_component('TeachInLathe')

        self.comp.addPin(self.PinHandwheelsJogIncrement, 'float', 'in')
        self.comp.addPin(self.PinHandwheelsAllowed, 'bit', 'in')
        self.comp.addPin(self.PinHandwheelsXEnable, 'bit', 'out')
        self.comp.addPin(self.PinHandwheelsZEnable, 'bit', 'out')
        self.comp.addPin(self.PinHandwheelsAngleJogEnable, 'bit', 'out')
        self.comp.addPin(self.PinHandwheelsAngleJogValue, 'float', 'out')
        self.comp.addPin(self.PinFeedPerRevValue, 'float', 'out')
        self.comp.addPin(self.PinIsAngleFeed, 'bit', 'out')
        self.comp.addPin(self.PinJogSpeedValue, 'float', 'out')
        self.comp.addPin(self.PinJoystickXPlus, 'bit', 'in')
        self.comp.addPin(self.PinJoystickXMinus, 'bit', 'in')
        self.comp.addPin(self.PinJoystickZPlus, 'bit', 'in')
        self.comp.addPin(self.PinJoystickZMinus, 'bit', 'in')
        self.comp.addPin(self.PinJoystickRapid, 'bit', 'in')
        self.comp.addPin(self.PinJoystickIsFeeding, 'bit', 'in')
        self.comp.addPin(self.PinJoystickResetRequired, 'bit', 'in')
        self.comp.addPin(self.PinSpindleCoveredOpened, 'bit', 'in')
        self.comp.addPin(self.PinSpindleSwitchRevIn, 'bit', 'in')
        self.comp.addPin(self.PinSpindleSwitchFwdIn, 'bit', 'in')
        self.comp.addPin(self.PinSpindleActualRpm, 'float', 'in')
        self.comp.addPin(self.PinSpindleIsOn, 'bit', 'in')
        self.comp.addPin(self.PinSpindleResetRequired, 'bit', 'in')
        self.comp.addPin(self.PinSpindleOrientation, 'float', 'in')
        self.comp.addPin(self.PinSpindleIsFirstGear, 'bit', 'in')
        self.comp.addPin(self.PinButtonCycleStart, 'bit', 'in')
        self.comp.addPin(self.PinButtonCycleStop, 'bit', 'in')
        self.comp.addPin(self.PinToolChangeToolNo, 's32', 'in')
        self.comp.addPin(self.PinToolChangeRequest, 'bit', 'in')
        self.comp.addPin(self.PinToolChangeResponse, 'bit', 'out')
        self.comp.addPin(self.PinToolChangeCanceled, 'bit', 'out')
        self.comp.addPin(self.PinAxisLimitXMin, 'float', 'in')
        self.comp.addPin(self.PinAxisLimitXMax, 'float', 'in')
        self.comp.addPin(self.PinAxisLimitZMin, 'float', 'in')
        self.comp.addPin(self.PinAxisLimitZMax, 'float', 'in')
        self.comp.addPin(self.PinIsSpindleStarted, 'bit', 'out')
        self.comp.addPin(self.PinIsReadyToRunProgram, 'bit', 'out')
        self.comp.addPin(self.PinProgramLoaded, 'bit', 'out')
        self.comp.addPin(self.PinProgramCompleted, 'bit', 'in')
        self.comp.addPin(self.PinProgramAborted, 'bit', 'in')
        self.comp.addPin(self.PinDevMode, 'bit', 'in')
        self.comp.addPin(self.PinCycleStartLed, 'bit', 'in')
        self.comp.ready()
        self.comp.getPin(self.PinToolChangeResponse).value = False
        self.comp.getPin(self.PinToolChangeCanceled).value = False
        print("HalComponent instance is created")
