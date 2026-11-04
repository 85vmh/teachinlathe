from enum import Enum


class JoystickState(Enum):
    NEUTRAL = 0
    FEEDING_X_NEG = 1
    FEEDING_X_POS = 2
    FEEDING_Z_NEG = 3
    FEEDING_Z_POS = 4
