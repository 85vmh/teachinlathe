"""Repositories: the only layer that talks to LinuxCNC.

Each repository owns one source of machine truth (the INI file, HAL, the
status channel, the tool table, ...) and exposes it as plain Python or Qt
signals. ViewModels consume repositories; QML consumes ViewModels.

A repository never imports ``PyQt5.QtWidgets`` and never imports ``qtpyvcp``,
so it stays testable without a ``QApplication`` and independent of any VCP
framework.
"""

from .hal_repository import (
    HalComponent, HalPin, hal_component, set_poll_interval, unload_all,
)
from .ini_repository import AxisLimits, IniRepository, ini_repository
from .positions_repository import Axis, Position, Positions
from .status_repository import StatusChannel, StatusRepository, status_repository

__all__ = [
    "Axis",
    "AxisLimits",
    "HalComponent",
    "HalPin",
    "IniRepository",
    "Position",
    "Positions",
    "StatusChannel",
    "StatusRepository",
    "hal_component",
    "ini_repository",
    "set_poll_interval",
    "status_repository",
    "unload_all",
]
