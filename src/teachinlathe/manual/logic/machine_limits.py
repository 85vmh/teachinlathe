import logging

from PyQt6.QtCore import QObject, pyqtSignal
from teachinlathe.core import AxisLimits, ini_repository

log = logging.getLogger(__name__)

INI = ini_repository()

#: The tool limits, set in the current loaded tool's coordinates.
TOOL_LIMIT_KEYS = ("xMinus", "xPlus", "zMinus", "zPlus")


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
            self._tailstock_limit_active = False
            self._chuck_limit = 0
            self._tailstock_limit = 0
            # the tool limits on the machine, by key, and whether each is in use
            self._tool_limits = {key: None for key in TOOL_LIMIT_KEYS}
            self._tool_limits_active = {key: False for key in TOOL_LIMIT_KEYS}

            self._default_x_minus_limit = _x_bounds.min
            self._default_x_plus_limit = _x_bounds.max
            self._default_z_minus_limit = _z_bounds.min
            self._default_z_plus_limit = _z_bounds.max

    def getDefaultMachineLimits(self):
        return MachineLimits(self._default_x_minus_limit,
                             self._default_x_plus_limit,
                             self._default_z_minus_limit,
                             self._default_z_plus_limit)

    def _tool_limit(self, key, default):
        return self._tool_limits[key] if self._tool_limits_active[key] else default

    def getComputedMachineLimits(self):
        computed_chuck_limit = self._chuck_limit if self._chuck_limit_active else self._default_z_minus_limit
        computed_z_minus = max(computed_chuck_limit, self._tool_limit("zMinus", self._default_z_minus_limit))

        computed_tailstock_limit = self._tailstock_limit if self._tailstock_limit_active else self._default_z_plus_limit
        computed_z_plus = min(computed_tailstock_limit, self._tool_limit("zPlus", self._default_z_plus_limit))

        computed_x_minus = self._tool_limit("xMinus", self._default_x_minus_limit)
        computed_x_plus = self._tool_limit("xPlus", self._default_x_plus_limit)

        return MachineLimits(computed_x_minus, computed_x_plus, computed_z_minus, computed_z_plus)

    def setChuckLimitsActive(self, value):
        log.debug("Chuck limit active: %s", value)
        self._chuck_limit_active = value
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setToolLimitActive(self, key, active):
        """A tool limit - "xMinus", "xPlus", "zMinus" or "zPlus" - in use or not."""
        log.debug("%s limit active: %s", key, active)
        self._tool_limits_active[key] = active
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setTailstockLimitActive(self, value):
        log.debug("Tailstock limit active: %s", value)
        self._tailstock_limit_active = value
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setChuckLimit(self, value):
        self._chuck_limit = value
        log.debug("Chuck limit set to %s", self._chuck_limit)
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    def setToolLimit(self, key, value):
        """Where a tool limit is on the machine; told with its being in use
        (setToolLimitActive)."""
        self._tool_limits[key] = value
        log.debug("%s limit set to %s", key, value)

    def moveToolLimits(self, limits):
        """Tool limits in use somewhere else on the machine, {key: value}: the
        current loaded tool's offset changed, and the limits, set in its
        coordinates, go with it. Told once, for all of them."""
        self._tool_limits.update(limits)
        log.debug("tool limits moved: %s", limits)
        self.onLimitsChanged.emit(self.getComputedMachineLimits())

    # Setter for tailstock_limit
    def setTailstockLimit(self, value):
        self._tailstock_limit = value
        log.debug("Tailstock limit set to %s", self._tailstock_limit)
