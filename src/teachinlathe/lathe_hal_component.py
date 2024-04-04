from qtpyvcp import hal

from teachinlathe import IN_DESIGNER


class TeachInLatheComponent:
    _instance = None

    PinJoystickXPlus = 'joystick.x-plus'
    PinJoystickXMinus = 'joystick.x-minus'
    PinJoystickZPlus = 'joystick.z-plus'
    PinJoystickZMinus = 'joystick.z-minus'
    PinJoystickRapid = 'joystick.rapid'
    PinIsPowerFeeding = 'app-status.power-feeding'
    PinIsSpindleStarted = 'app-status.spindle-started'
    PinIsReadyToRunProgram = 'app-status.ready-to-run-program'
    PinButtonCycleStart = 'button.cycle-start'
    PinButtonCycleStop = 'button.cycle-stop'
    PinSpindleCoveredOpened = 'spindle.cover-opened'
    PinSpindleSwitchRevIn = 'spindle.switch-rev-in'
    PinSpindleSwitchFwdIn = 'spindle.switch-fwd-in'
    PinSpindleActualRpm = 'spindle.actual-rpm'
    PinSpindleIsFirstGear = 'spindle.is-first-gear'
    PinHandwheelsJogIncrement = 'handwheels.jog-increment'
    PinHandwheelsXIsEnabled = 'handwheels.x-is-enabled'
    PinHandwheelsZIsEnabled = 'handwheels.z-is-enabled'
    PinHandwheelsXEnable = 'handwheels.x-enable'
    PinHandwheelsZEnable = 'handwheels.z-enable'
    PinHandwheelsAngleJogEnable = 'handwheels.angle-jog-enabled'
    PinHandwheelsAngleJogValue = 'handwheels.angle-jog-value'
    PinToolChangeToolNo = 'tool-change.number'
    PinToolChangeRequest = 'tool-change.change'
    PinToolChangeResponse = 'tool-change.changed'
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
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def __init__(self):
        pass  # Initialization logic moved to __new__

    def _initialize(self):
        if IN_DESIGNER:
            self.comp = hal.component('Designer')
        else:
            self.comp = hal.component('TeachInLathe')
            self.comp.addPin(self.PinHandwheelsJogIncrement, 'float', 'in')
            self.comp.addPin(self.PinHandwheelsXIsEnabled, 'float', 'in')
            self.comp.addPin(self.PinHandwheelsZIsEnabled, 'float', 'in')
            self.comp.addPin(self.PinHandwheelsXEnable, 'bit', 'out')
            self.comp.addPin(self.PinHandwheelsZEnable, 'bit', 'out')
            self.comp.addPin(self.PinHandwheelsAngleJogEnable, 'bit', 'out')
            self.comp.addPin(self.PinHandwheelsAngleJogValue, 'float', 'out')
            self.comp.addPin(self.PinJoystickXPlus, 'bit', 'in')
            self.comp.addPin(self.PinJoystickXMinus, 'bit', 'in')
            self.comp.addPin(self.PinJoystickZPlus, 'bit', 'in')
            self.comp.addPin(self.PinJoystickZMinus, 'bit', 'in')
            self.comp.addPin(self.PinJoystickRapid, 'bit', 'in')
            self.comp.addPin(self.PinSpindleCoveredOpened, 'bit', 'in')
            self.comp.addPin(self.PinSpindleSwitchRevIn, 'bit', 'in')
            self.comp.addPin(self.PinSpindleSwitchFwdIn, 'bit', 'in')
            self.comp.addPin(self.PinSpindleActualRpm, 'float', 'in')
            self.comp.addPin(self.PinSpindleIsFirstGear, 'bit', 'in')
            self.comp.addPin(self.PinButtonCycleStart, 'bit', 'in')
            self.comp.addPin(self.PinButtonCycleStop, 'bit', 'in')
            self.comp.addPin(self.PinAxisLimitXMin, 'float', 'in')
            self.comp.addPin(self.PinAxisLimitXMax, 'float', 'in')
            self.comp.addPin(self.PinAxisLimitZMin, 'float', 'in')
            self.comp.addPin(self.PinAxisLimitZMax, 'float', 'in')
            self.comp.addPin(self.PinIsPowerFeeding, 'bit', 'out')
            self.comp.addPin(self.PinIsSpindleStarted, 'bit', 'out')
            self.comp.addPin(self.PinIsReadyToRunProgram, 'bit', 'out')
            self.comp.ready()
        print("HalComponent instance is created")
