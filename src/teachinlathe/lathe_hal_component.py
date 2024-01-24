from qtpyvcp import hal


class TeachInLatheComponent:
    _instance = None

    COMPONENT_NAME = 'TeachInLathe'
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

    comp = hal.component('TeachInLathe')

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(TeachInLatheComponent, cls).__new__(cls)
            # Initialize the instance (only once)
            cls._initialize(cls._instance)
        return cls._instance

    @staticmethod
    def _initialize(instance):
        instance.comp.addPin(instance.PinHandwheelsJogIncrement, 'float', 'in')
        instance.comp.addPin(instance.PinHandwheelsXIsEnabled, 'float', 'in')
        instance.comp.addPin(instance.PinHandwheelsZIsEnabled, 'float', 'in')
        instance.comp.addPin(instance.PinHandwheelsXEnable, 'bit', 'out')
        instance.comp.addPin(instance.PinHandwheelsZEnable, 'bit', 'out')
        instance.comp.addPin(instance.PinHandwheelsAngleJogEnable, 'bit', 'out')
        instance.comp.addPin(instance.PinHandwheelsAngleJogValue, 'float', 'out')
        instance.comp.addPin(instance.PinJoystickXPlus, 'bit', 'in')
        instance.comp.addPin(instance.PinJoystickXMinus, 'bit', 'in')
        instance.comp.addPin(instance.PinJoystickZPlus, 'bit', 'in')
        instance.comp.addPin(instance.PinJoystickZMinus, 'bit', 'in')
        instance.comp.addPin(instance.PinJoystickRapid, 'bit', 'in')
        instance.comp.addPin(instance.PinSpindleCoveredOpened, 'bit', 'in')
        instance.comp.addPin(instance.PinSpindleSwitchRevIn, 'bit', 'in')
        instance.comp.addPin(instance.PinSpindleSwitchFwdIn, 'bit', 'in')
        instance.comp.addPin(instance.PinSpindleActualRpm, 'float', 'in')
        instance.comp.addPin(instance.PinSpindleIsFirstGear, 'bit', 'in')
        instance.comp.addPin(instance.PinButtonCycleStart, 'bit', 'in')
        instance.comp.addPin(instance.PinButtonCycleStop, 'bit', 'in')
        instance.comp.addPin(instance.PinAxisLimitXMin, 'float', 'in')
        instance.comp.addPin(instance.PinAxisLimitXMax, 'float', 'in')
        instance.comp.addPin(instance.PinAxisLimitZMin, 'float', 'in')
        instance.comp.addPin(instance.PinAxisLimitZMax, 'float', 'in')
        instance.comp.addPin(instance.PinIsPowerFeeding, 'bit', 'out')
        instance.comp.addPin(instance.PinIsSpindleStarted, 'bit', 'out')
        instance.comp.addPin(instance.PinIsReadyToRunProgram, 'bit', 'out')
        instance.comp.ready()
        print("HalComponent instance is created")
