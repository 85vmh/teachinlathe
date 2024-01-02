

def getStraightTurningCommand(self, joystickDirection):
    # TODO use the actual limits from the machine
    # zMinLimit = 0
    # zMaxLimit = 100
    # xMinLimit = 0
    # xMaxLimit = 100
    # if joystickDirection == JoystickDirection.XPlus:
    #     return 'G53 G1 X%f' % xMaxLimit
    # elif joystickDirection == JoystickDirection.XMinus:
    #     return 'G53 G1 X%f' % xMinLimit
    # elif joystickDirection == JoystickDirection.ZPlus:
    #     return 'G53 G1 Z%f' % zMaxLimit
    # elif joystickDirection == JoystickDirection.ZMinus:
    #     return 'G53 G1 Z%f' % zMinLimit
    # else:
    return "G53 G1 Z0"


def getTaperTurningCommand(self, joystickDirection, angle):
    # TODO use the actual limits from the machine
    # zMinLimit = 0
    # zMaxLimit = 100
    # xMinLimit = 0
    # xMaxLimit = 100
    # if joystickDirection == JoystickDirection.XPlus:
    #     return 'G53 G1 X%f' % xMaxLimit
    # elif joystickDirection == JoystickDirection.XMinus:
    #     return 'G53 G1 X%f' % xMinLimit
    # elif joystickDirection == JoystickDirection.ZPlus:
    #     return 'G53 G1 Z%f' % zMaxLimit
    # elif joystickDirection == JoystickDirection.ZMinus:
    #     return 'G53 G1 Z%f' % zMinLimit
    # else:
    return "G53 G1 Z0"