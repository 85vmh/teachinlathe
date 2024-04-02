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

            self._chuck_limit_active = False
            self._x_minus_limit_active = False
            self._x_plus_limit_active = False
            self._z_minus_limit_active = False
            self._z_plus_limit_active = False

            self._chuck_limit = 0
            self._tailstock_limit = 0
            self._custom_x_minus_limit = None
            self._custom_x_plus_limit = None
            self._custom_z_minus_limit = None
            self._custom_z_plus_limit = None

            self._default_x_minus_limit = _x_bounds[0]
            self._default_x_plus_limit = _x_bounds[1]
            self._default_z_minus_limit = _z_bounds[0]
            self._default_z_plus_limit = _z_bounds[1]

            # emit the initial values
            # self.onLimitsChanged.emit(self.getMachineLimits())
            self.onDefaultLimits.emit(
                MachineLimits(self._default_x_minus_limit,
                              self._default_x_plus_limit,
                              self._default_z_minus_limit,
                              self._default_z_plus_limit))

    def getMachineLimits(self):
        print("getMachineLimits-chuck:", self._chuck_limit)
        # Apply chuck limit to default Z min limit
        computed_z_minus = self._default_z_minus_limit + (0 if self._chuck_limit_active else self._chuck_limit)

        # Apply tailstock limit to default Z max limit
        computed_z_plus = self._default_z_plus_limit - self._tailstock_limit

        # Use custom limits if they are active and provide a tighter bound
        if self._z_minus_limit_active:
            if self._custom_z_minus_limit is not None:
                computed_z_minus = max(computed_z_minus, self._custom_z_minus_limit)

        if self._z_plus_limit_active:
            if self._custom_z_plus_limit is not None:
                computed_z_plus = min(computed_z_plus, self._custom_z_plus_limit)

        # For X axis, use custom limits if active; otherwise, use default limits
        computed_x_minus = self._custom_x_minus_limit if self._x_minus_limit_active else self._default_x_minus_limit
        computed_x_plus = self._custom_x_plus_limit if self._x_plus_limit_active else self._default_x_plus_limit

        return MachineLimits(computed_x_minus, computed_x_plus, computed_z_minus, computed_z_plus)

    def setChuckLimitsActive(self, value):
        self._chuck_limit_active = value
        self.onLimitsChanged.emit(self.getMachineLimits())

    def setXMinusLimitActive(self, value):
        self._x_minus_limit_active = value / 2
        self.onLimitsChanged.emit(self.getMachineLimits())

    def setXPlusLimitActive(self, value):
        self._x_plus_limit_active = value / 2
        self.onLimitsChanged.emit(self.getMachineLimits())

    def setZMinusLimitActive(self, value):
        self._z_minus_limit_active = value
        self.onLimitsChanged.emit(self.getMachineLimits())

    def setZPlusLimitActive(self, value):
        self._z_plus_limit_active = value
        self.onLimitsChanged.emit(self.getMachineLimits())

    def setChuckLimit(self, value):
        self._chuck_limit = value
        print("Set chuck limit: ", self._chuck_limit)
        self.onLimitsChanged.emit(self.getMachineLimits())

    def setZMinusLimit(self, value):
        self._custom_z_minus_limit = value
        print("Set Z- limit: ", self._custom_z_minus_limit)

    def setZPlusLimit(self, value):
        self._custom_z_plus_limit = value
        print("Set Z+ limit: ", self._custom_z_plus_limit)

    def setXMinusLimit(self, value):
        self._custom_x_minus_limit = value
        print("Set X- limit: ", self._custom_x_minus_limit)

    def setXPlusLimit(self, value):
        self._custom_x_plus_limit = value
        print("Set X+ limit: ", self._custom_x_plus_limit)

    # Setter for tailstock_limit
    def setTailstockLimits(self, value):
        self._tailstock_limit = value
        print("Set tailstock limit: ", self._chuck_limit)
        self.onLimitsChanged.emit(self.getMachineLimits())
