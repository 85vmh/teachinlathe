from enum import IntEnum

from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities.info import Info
from math import tan, radians, fabs
from qtpyvcp.widgets.base_widgets.dro_base_widget import RefType

from teachinlathe.manual_lathe import JoystickDirection

INFO = Info()


class CartesianPoint:
    def __init__(self, x, z):
        self.x = x
        self.z = z

    def __repr__(self):
        return f"CodegenPoint(x={self.x}, z={self.z})"


class Axis(IntEnum):
    X = 0
    Z = 2


class TurningHelper:

    @staticmethod
    def getStraightTurningCommand(joystick_direction):
        x_bounds = INFO.getAxisMinMax('X')[0]
        z_bounds = INFO.getAxisMinMax('Z')[0]

        x_min_limit = x_bounds[0] * 2  # diameter mode
        x_max_limit = x_bounds[1] * 2  # diameter mode
        z_min_limit = z_bounds[0]
        z_max_limit = z_bounds[1]

        print("Straight turning command for: ", joystick_direction)
        destination = ''
        match joystick_direction:
            case JoystickDirection.X_PLUS:
                destination = 'X%f' % x_max_limit
            case JoystickDirection.X_MINUS:
                destination = 'X%f' % x_min_limit
            case JoystickDirection.Z_PLUS:
                destination = 'Z%f' % z_max_limit
            case JoystickDirection.Z_MINUS:
                destination = 'Z%f' % z_min_limit
        return 'G40 G53 G1 {}'.format(destination)

    @staticmethod
    def getTaperTurningCommand(joystick_direction, angle):
        corner_point = TurningHelper.create_corner_point(joystick_direction)
        start_point = TurningHelper.get_start_point()
        print("Start point: ", start_point)
        print("Corner point: ", corner_point)
        destination_point = TurningHelper.compute_destination_point(start_point, corner_point, angle)
        print("Destination point: ", destination_point)

        print("Taper turning command for: ", joystick_direction)
        return f'G40 G53 G1 X{destination_point.x:.3f} Z{destination_point.z:.3f}'

    @staticmethod
    def get_start_point():
        pos = getattr(getPlugin('position'), RefType.Absolute.name).getValue()
        return CartesianPoint(pos[0] * 2, pos[2])

    @staticmethod
    def create_corner_point(joystick_direction):
        x_bounds = INFO.getAxisMinMax('X')[0]
        z_bounds = INFO.getAxisMinMax('Z')[0]

        x_min_limit = x_bounds[0]
        x_max_limit = x_bounds[1]
        z_min_limit = z_bounds[0]
        z_max_limit = z_bounds[1]

        match joystick_direction:
            case JoystickDirection.X_PLUS:
                return CartesianPoint(x_max_limit * 2, z_min_limit)
            case JoystickDirection.X_MINUS:
                return CartesianPoint(x_min_limit * 2, z_max_limit)
            case JoystickDirection.Z_PLUS:
                return CartesianPoint(x_max_limit * 2, z_max_limit)
            case JoystickDirection.Z_MINUS:
                return CartesianPoint(x_min_limit * 2, z_min_limit)

    @staticmethod
    def compute_destination_point(start_point, corner_point, angle):
        opposite = fabs(corner_point.x - start_point.x)
        adjacent = (opposite / tan(radians(angle))) / 2  # divided by 2 due to diameter mode
        max_dist_z = fabs(corner_point.z - start_point.z)

        if adjacent > max_dist_z:
            extra_dist_z = adjacent - max_dist_z
            sign = -1 if corner_point.x > 0 else 1
            small_opposite = extra_dist_z * tan(radians(angle))
            dest_point_x = corner_point.x + (2 * small_opposite * sign)  # minus when xMaxLimit, plus when xMinLimit
            return CartesianPoint(dest_point_x, corner_point.z)
        else:
            sign = 1 if corner_point.z > 0 else -1
            return CartesianPoint(corner_point.x, start_point.z + (adjacent * sign))
