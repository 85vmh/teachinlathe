from qtpy.QtCore import Signal, QObject
from qtpyvcp.utilities.info import Info

INFO = Info()


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
    onDefaultLimits = Signal(object)
    onLimitsChanged = Signal(object)

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MachineLimitsHandler, cls).__new__(cls)
            cls._instance._is_initialized = False
        return cls._instance

    def __init__(self):
        if not self._is_initialized:
            super().__init__()  # Initialize the QObject base class
            _x_bounds = INFO.getAxisMinMax('X')[0]
            _z_bounds = INFO.getAxisMinMax('Z')[0]

            self._is_initialized = True
            self._chuck_limit = 0
            self._tailstock_limit = 0
            self._pause_chuck_limit = False

            self._custom_limits_active = False
            self._custom_x_min_limit = None
            self._custom_x_max_limit = None
            self._custom_z_min_limit = None
            self._custom_z_max_limit = None

            self._default_x_min_limit = _x_bounds[0]
            self._default_x_max_limit = _x_bounds[1]
            self._default_z_min_limit = _z_bounds[0]
            self._default_z_max_limit = _z_bounds[1]

            # emit the initial values
            # self.onLimitsChanged.emit(self.getMachineLimits())
            self.onDefaultLimits.emit(
                MachineLimits(self._default_x_min_limit,
                              self._default_x_max_limit,
                              self._default_z_min_limit,
                              self._default_z_max_limit))

    def setCustomLimits(self, machine_limits):
        self._custom_x_min_limit = machine_limits.x_min_limit
        self._custom_x_max_limit = machine_limits.x_max_limit
        self._custom_z_min_limit = machine_limits.z_min_limit
        self._custom_z_max_limit = machine_limits.z_max_limit
        self.onLimitsChanged.emit(self.getMachineLimits())

    def getMachineLimits(self):
        print("getMachineLimits-chuck:", self._chuck_limit)
        # Apply chuck limit to default Z min limit
        computed_z_min = self._default_z_min_limit + (0 if self._pause_chuck_limit else self._chuck_limit)

        # Apply tailstock limit to default Z max limit
        computed_z_max = self._default_z_max_limit - self._tailstock_limit

        # Use custom limits if they are active and provide a tighter bound
        if self._custom_limits_active:
            if self._custom_z_min_limit is not None:
                computed_z_min = max(computed_z_min, self._custom_z_min_limit)
            if self._custom_z_max_limit is not None:
                computed_z_max = min(computed_z_max, self._custom_z_max_limit)

        # For X axis, use custom limits if active; otherwise, use default limits
        computed_x_min = self._custom_x_min_limit if self._custom_limits_active else self._default_x_min_limit
        computed_x_max = self._custom_x_max_limit if self._custom_limits_active else self._default_x_max_limit

        return MachineLimits(computed_x_min, computed_x_max, computed_z_min, computed_z_max)

    def pauseChuckLimit(self, value):
        self._pause_chuck_limit = value
        self.onLimitsChanged.emit(self.getMachineLimits())

    def setChuckLimit(self, value):
        self._chuck_limit = value
        print("Set chuck limit: ", self._chuck_limit)
        self.onLimitsChanged.emit(self.getMachineLimits())

    # Setter for tailstock_limit
    def setTailstockLimits(self, value):
        self._tailstock_limit = value
        print("Set tailstock limit: ", self._chuck_limit)
        self.onLimitsChanged.emit(self.getMachineLimits())
