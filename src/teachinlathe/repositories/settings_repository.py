"""Persistent application settings.

Settings are plain values kept in a JSON file next to the machine config, and
each declares its type, bounds and default once. Reading one that was never
written gives its default; writing one clamps it to its bounds and tells
listeners.

Two settings are not stored but computed, because they are two views of the
same thing: the jog speed in units per minute and the same speed as a
percentage of the machine's maximum. Setting either moves the other, which is
what the rapid-override slider and the jog-speed HAL pin both depend on.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from .ini_repository import ini_repository

log = logging.getLogger(__name__)

SETTINGS_FILE = 'teachinlathe_settings.json'

JOG_SPEED = 'machine.jog.linear-speed'
JOG_SPEED_PERCENTAGE = 'machine.jog.linear-speed-percentage'
RAPID_PERCENTAGE = 'rapid_speeds.percentage'


@dataclass(frozen=True)
class SettingSpec:
    """What a setting is: its type, its default and its bounds."""

    default: Any
    value_type: type = float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    persistent: bool = True
    description: str = ''

    def coerce(self, value):
        try:
            value = self.value_type(value)
        except (TypeError, ValueError):
            log.warning("cannot read %r as %s; using the default %r",
                        value, self.value_type.__name__, self.default)
            return self.default
        return self.clamp(value)

    def clamp(self, value):
        if self.min_value is not None and value < self.min_value:
            return self.value_type(self.min_value)
        if self.max_value is not None and value > self.max_value:
            return self.value_type(self.max_value)
        return value


class SettingsRepository(QObject):
    """The application's settings, as a file and a set of signals."""

    #: Emitted with (name, value) whenever any setting changes.
    settingChanged = pyqtSignal(str, object)

    def __init__(self, parent: Optional[QObject] = None,
                 path: Optional[str] = None, ini=None) -> None:
        super().__init__(parent)
        self._ini = ini_repository() if ini is None else ini
        self._path = path or os.path.join(self._ini.config_dir, SETTINGS_FILE)
        self._values: Dict[str, Any] = {}
        self._specs: Dict[str, SettingSpec] = dict(self._default_specs())
        self._load()

    def _default_specs(self) -> Dict[str, SettingSpec]:
        return {
            RAPID_PERCENTAGE: SettingSpec(
                default=50, value_type=int, min_value=0, max_value=100,
                description='Rapid speed, as a percentage of maximum'),
            JOG_SPEED: SettingSpec(
                default=self._ini.default_jog_velocity, value_type=float,
                min_value=0.0, max_value=self._ini.max_jog_velocity,
                description='Jog speed, in units per minute'),
            JOG_SPEED_PERCENTAGE: SettingSpec(
                default=self._percentage_of(self._ini.default_jog_velocity),
                value_type=int, min_value=0, max_value=100, persistent=False,
                description='Jog speed, as a percentage of maximum'),
        }

    # -- declaring --------------------------------------------------------

    def declare(self, name: str, spec: SettingSpec) -> None:
        """Add a setting the application did not know about at start-up."""
        self._specs[name] = spec

    def spec(self, name: str) -> Optional[SettingSpec]:
        return self._specs.get(name)

    # -- reading and writing ----------------------------------------------

    def get(self, name: str, default=None):
        """The value of *name*, or its declared default, or *default*."""
        if name == JOG_SPEED_PERCENTAGE:
            return self._percentage_of(self.get(JOG_SPEED))

        if name in self._values:
            return self._values[name]

        spec = self._specs.get(name)
        if spec is not None:
            return spec.default
        return default

    def set(self, name: str, value) -> None:
        """Store *value* under *name*, clamped to the setting's bounds."""
        if name == JOG_SPEED_PERCENTAGE:
            # The percentage is a view of the speed, so write the speed.
            spec = self._specs[JOG_SPEED_PERCENTAGE]
            percentage = spec.coerce(value)
            self.set(JOG_SPEED, self._ini.max_jog_velocity * percentage / 100.0)
            return

        spec = self._specs.get(name)
        value = spec.coerce(value) if spec is not None else value

        if self._values.get(name) == value and name in self._values:
            return

        self._values[name] = value
        self.settingChanged.emit(name, value)

        if name == JOG_SPEED:
            self.settingChanged.emit(JOG_SPEED_PERCENTAGE,
                                     self._percentage_of(value))

        if spec is None or spec.persistent:
            self._save()

    def notify(self, name: str, slot: Callable) -> None:
        """Call *slot* with the new value whenever *name* changes."""
        self.settingChanged.connect(
            lambda changed, value: slot(value) if changed == name else None)

    def _percentage_of(self, speed) -> int:
        maximum = self._ini.max_jog_velocity
        if not maximum:
            return 0
        return int(float(speed) * 100 / maximum)

    # -- the file ---------------------------------------------------------

    @property
    def path(self) -> str:
        return self._path

    def _load(self) -> None:
        try:
            with open(self._path) as fh:
                stored = json.load(fh)
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            log.warning("could not read the settings file %s; using defaults",
                        self._path, exc_info=True)
            return

        if not isinstance(stored, dict):
            log.warning("settings file %s does not hold an object; ignoring it",
                        self._path)
            return

        for name, value in stored.items():
            spec = self._specs.get(name)
            self._values[name] = spec.coerce(value) if spec else value

    def _save(self) -> None:
        persistent = {
            name: value for name, value in self._values.items()
            if self._specs.get(name) is None or self._specs[name].persistent
        }
        try:
            with open(self._path, 'w') as fh:
                json.dump(persistent, fh, indent=2, sort_keys=True)
        except OSError:
            log.warning("could not write the settings file %s", self._path,
                        exc_info=True)


_INSTANCE: Optional[SettingsRepository] = None


def settings_repository() -> SettingsRepository:
    """The shared SettingsRepository."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = SettingsRepository()
    return _INSTANCE


def get_setting(name: str, default=None):
    return settings_repository().get(name, default)


def set_setting(name: str, value) -> None:
    settings_repository().set(name, value)
