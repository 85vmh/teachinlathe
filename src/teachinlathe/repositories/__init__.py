"""Repositories: the only layer that talks to LinuxCNC.

Each repository owns one source of machine truth (the INI file, HAL, the
status channel, the tool table, ...) and exposes it as plain Python or Qt
signals. ViewModels consume repositories; QML consumes ViewModels.

A repository never imports ``PyQt6.QtWidgets``, so it stays testable without
a ``QApplication`` and independent of any UI framework.
"""

from .command_repository import CommandRepository, command_repository, issue_mdi
from .hal_repository import (
    HalComponent, HalPin, hal_component, set_poll_interval, unload_all,
)
from .ini_repository import AxisLimits, IniRepository, ini_repository
from .machine_repository import MachineRepository, machine_repository
from .positions_repository import Axis, Position, Positions
from .program_repository import ProgramRepository, program_repository
from .settings_repository import (
    SettingSpec, SettingsRepository, get_setting, set_setting, settings_repository,
)
from .status_repository import StatusChannel, StatusRepository, status_repository
from .tool_table_repository import ToolTableRepository, tool_table_repository

__all__ = [
    "Axis",
    "CommandRepository",
    "AxisLimits",
    "HalComponent",
    "HalPin",
    "IniRepository",
    "MachineRepository",
    "Position",
    "Positions",
    "ProgramRepository",
    "SettingSpec",
    "SettingsRepository",
    "StatusChannel",
    "StatusRepository",
    "ToolTableRepository",
    "command_repository",
    "get_setting",
    "hal_component",
    "ini_repository",
    "machine_repository",
    "issue_mdi",
    "program_repository",
    "set_poll_interval",
    "set_setting",
    "settings_repository",
    "status_repository",
    "tool_table_repository",
    "unload_all",
]
