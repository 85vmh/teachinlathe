"""Repositories: the only layer that talks to LinuxCNC.

Each repository owns one source of machine truth (the INI file, HAL, the
status channel, the tool table, ...) and exposes it as plain Python or Qt
signals. ViewModels consume repositories; QML consumes ViewModels.

A repository never imports ``PyQt5.QtWidgets`` and never imports ``qtpyvcp``,
so it stays testable without a ``QApplication`` and independent of any VCP
framework.
"""

from .ini_repository import AxisLimits, IniRepository, ini_repository

__all__ = ["AxisLimits", "IniRepository", "ini_repository"]
