import logging

from PyQt6.QtCore import QObject, pyqtSignal
from teachinlathe.core import AxisLimits, ini_repository

log = logging.getLogger(__name__)

INI = ini_repository()


class MachineLimits:
    def __init__(self, x_min_limit=None, x_max_limit=None, z_min_limit=None, z_max_limit=None):
        self.x_min_limit = x_min_limit
        self.x_max_limit = x_max_limit
        self.z_min_limit = z_min_limit
        self.z_max_limit = z_max_limit

    def __repr__(self):
        return (f"MachineLimits("
                f"x_min_limit={self.x_min_limit}, "
                f"x_max_limit={self.x_max_limit}, "
                f"z_min_limit={self.z_min_limit}, "
                f"z_max_limit={self.z_max_limit})")


class MachineLimitsHandler(QObject):
    _instance = None
    onLimitsChanged = pyqtSignal(object)

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MachineLimitsHandler, cls).__new__(cls)
            cls._instance._is_initialized = False
        return cls._instance

    def __init__(self):
        if not self._is_initialized:
            super().__init__()  # Initialize the QObject base class
            # An INI without limits (no machine, or a bad path) reads as zero.
            _x_bounds = INI.axis_limits('X') or AxisLimits(0.0, 0.0)
            _z_bounds = INI.axis_limits('Z') or AxisLimits(0.0, 0.0)

            self._is_initialized = True

            self._chuck_limit_active = False
            self._x_minus_limit_active = False
            self._x_plus_limit_active = False
            self._z_minus_limit_active = False
            self._z_plus_limit_active = False
            self._tailstock_limit_active = False

            self._chuck_limit = 0
            self._tailstock_limit = 0
            self._custom_x_minus_limit = None
            self._custom_x_plus_limit = None
            self._custom_z_minus_limit = None
            self._custom_z_plus_limit = None

            self._default_x_minus_limit = _x_bounds.min
            self._default_x_plus_limit = _x_bounds.max
            self._default_z_minus_limit = _z_bounds.min
            self._default_z_plus_limit = _z_bounds.max

    def getDefaultMachineLimits(self):
        return MachineLimits(self._default_x_minus_limit,
                             self._default_x_plus_limit,
                             self._default_z_minus_limit,
                             self._default_z_plus_limit)

    def getComputedMachineLimits(self):
        computed_chuck_limit = self._chuck_limit if self._chuck_limit_active else self._default_z_minus_limit
        computed_z_minus_limit = self._custom_z_minus_limit if self._z_minus_limit_active else self._default_z_minus_limit
        computed_z_minus = max(computed_chuck_limit, computed_z_minus_limit)

        computed_tailstock_limit = self._tailstock_limit if self._tailstock_limit_active else self._default_z_plus_limit
        computed_z_plus_limit = self._custom_z_plus_limit if self._z_plus_limit_active else self._default_z_plus_limit
        computed_z_plus = min(computed_tailstock_limit, computed_z_plus_limit)

        # For X axis, use custom limits if active; otherwise, use default limits
        computed_x_minus = self._custom_x_minus_limit if self._x_minus_limit_active else self._default_x_minus_limit
        computed_x_plus = self._custom_x_plus_limit if self._x_plus_limit_active else self._default_x_plus_limit

        return MachineLimits(computed_x_minus, computed_x_plus, computed_z_minus, computed_z_plus)

    def setChuckLimitsActive(self, value):
        log.debug("Chuck limit active: %s", value)
        self._chuck_limit_active = value
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setXMinusLimitActive(self, value):
        log.debug("X- limit active: %s", value)
        self._x_minus_limit_active = value
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setXPlusLimitActive(self, value):
        log.debug("X+ limit active: %s", value)
        self._x_plus_limit_active = value
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setZMinusLimitActive(self, value):
        log.debug("Z- limit active: %s", value)
        self._z_minus_limit_active = value
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setZPlusLimitActive(self, value):
        log.debug("Z+ limit active: %s", value)
        self._z_plus_limit_active = value
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setTailstockLimitActive(self, value):
        log.debug("Tailstock limit active: %s", value)
        self._tailstock_limit_active = value
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setChuckLimit(self, value):
        self._chuck_limit = value
        log.debug("Chuck limit set to %s", self._chuck_limit)
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setZMinusLimit(self, value):
        self._custom_z_minus_limit = value
        log.debug("Z- limit set to %s", self._custom_z_minus_limit)

    def setZPlusLimit(self, value):
        self._custom_z_plus_limit = value
        log.debug("Z+ limit set to %s", self._custom_z_plus_limit)

    def setXMinusLimit(self, value):
        self._custom_x_minus_limit = value
        log.debug("X- limit set to %s", self._custom_x_minus_limit)

    def setXPlusLimit(self, value):
        self._custom_x_plus_limit = value
        log.debug("X+ limit set to %s", self._custom_x_plus_limit)

    # Setter for tailstock_limit
    def setTailstockLimit(self, value):
        self._tailstock_limit = value
        log.debug("Tailstock limit set to %s", self._tailstock_limit)
