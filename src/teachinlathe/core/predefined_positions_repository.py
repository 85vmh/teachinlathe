"""Whether the machine's predefined positions are set: the tool change
position (TC Pos), G28's and G30's.

* **TC Pos** is set when the application's settings hold one
  (TOOL_CHANGE_X / TOOL_CHANGE_Z, settings_repository) that is not the INI's
  ``[EMCIO] TOOL_CHANGE_POSITION``: the INI's is where the machine starts, one
  of the operator's own is what moves it.
* **G28** and **G30** are set when their X or Z in the interpreter's parameter
  file (``[RS274NGC] PARAMETER_FILE``: 5161 and 5163 for G28, 5181 and 5183
  for G30) is not zero, the value they have before anything sets them
  (G28.1, G30.1). The file is read again when LinuxCNC writes it.

The tool change position the operator sets is handed to LinuxCNC on the
TeachInLathe component's tool-change.position pins, which the HAL wires to
iocontrol.0.tool-change-pos-*: enabled while it is set, M6 goes there.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from .ini_repository import ini_repository
from .settings_repository import TOOL_CHANGE_X, TOOL_CHANGE_Z, settings_repository
from .status_repository import status_repository

log = logging.getLogger(__name__)

#: The parameters each position's X and Z are in.
G28_PARAMETERS = (5161, 5163)
G30_PARAMETERS = (5181, 5183)

#: How near two positions are to be the same, in machine units.
SAME = 1e-6


class PredefinedPositions(QObject):
    """Whether TC Pos, G28 and G30 are set (the module), and where each is,
    kept up to date: ``changed`` when either does."""

    changed = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None, ini=None, settings=None, status=None) -> None:
        super().__init__(parent)
        self._ini = ini_repository() if ini is None else ini
        self._settings = settings_repository() if settings is None else settings
        self._status = status_repository() if status is None else status
        self._parameter_file = self._ini.file_path("RS274NGC", "PARAMETER_FILE") or ""
        self._parameters_read_at = None
        self._parameters: Dict[int, float] = {}
        # whether each is set, and where each is: what ``changed`` is for
        self._state = None
        self._pins_written = None
        self._settings.settingChanged.connect(self._on_setting)
        self._status.polled.connect(self._refresh)
        self._refresh()

    def set_tool_change(self, x: Optional[float] = None, z: Optional[float] = None) -> None:
        """Set the tool change position's ``x`` (a radius) and/or ``z``,
        machine coordinates; the other, not set yet, from where it is now -
        the INI's - so both are."""
        now_x, now_z, _custom = self.tool_change_position()
        x = now_x if x is None else x
        z = now_z if z is None else z
        if x is None or z is None:
            return
        self._settings.set(TOOL_CHANGE_X, float(x))
        self._settings.set(TOOL_CHANGE_Z, float(z))

    @property
    def tool_change_set(self) -> bool:
        return self._tool_change_is_set()

    @property
    def g28_set(self) -> bool:
        return self._is_set(G28_PARAMETERS)

    @property
    def g30_set(self) -> bool:
        return self._is_set(G30_PARAMETERS)

    def tool_change_position(self) -> Tuple[Optional[float], Optional[float], bool]:
        """(x, z, custom): where M6 takes the tool, machine coordinates (X a
        radius) - the operator's (custom) when set, else the INI's; None for
        what neither says."""
        if self._tool_change_is_set():
            return self._settings.get(TOOL_CHANGE_X), self._settings.get(TOOL_CHANGE_Z), True
        ini = self._ini_tool_change()
        return (ini[0], ini[1], False) if ini is not None else (None, None, False)

    def g28_position(self) -> Tuple[float, float]:
        """(x, z) G28 holds, machine coordinates; (0, 0) until it is set."""
        return self._position(G28_PARAMETERS)

    def g30_position(self) -> Tuple[float, float]:
        return self._position(G30_PARAMETERS)

    def _position(self, parameters) -> Tuple[float, float]:
        self._read_parameters()
        return tuple(self._parameters.get(number, 0.0) for number in parameters)

    def _on_setting(self, name, _value) -> None:
        if name in (TOOL_CHANGE_X, TOOL_CHANGE_Z):
            self._refresh()

    def _refresh(self) -> None:
        self._read_parameters()
        state = (self._tool_change_is_set(), self._is_set(G28_PARAMETERS), self._is_set(G30_PARAMETERS),
                 self.tool_change_position(), self._position(G28_PARAMETERS), self._position(G30_PARAMETERS))
        self._write_pins()
        if state != self._state:
            self._state = state
            self.changed.emit()

    def _write_pins(self) -> None:
        """The tool change position on the component's pins, when it changed:
        enabled only while one of the operator's is set. The pins share their
        signals with iocontrol's, so without one X and Z keep what iocontrol
        put there (the INI's position)."""
        x, z, custom = self.tool_change_position()
        wanted = (float(x), float(z), True) if custom else (None, None, False)
        if wanted == self._pins_written:
            return
        try:
            from .lathe_hal_component import TeachInLatheComponent
            component = TeachInLatheComponent()
            if custom:
                component.comp.getPin(TeachInLatheComponent.PinToolChangePositionX).value = wanted[0]
                component.comp.getPin(TeachInLatheComponent.PinToolChangePositionZ).value = wanted[1]
            component.comp.getPin(TeachInLatheComponent.PinToolChangePositionEnable).value = wanted[2]
        except Exception as error:
            log.debug("predefined positions: cannot write the tool change pins: %s", error)
            return
        self._pins_written = wanted

    def _tool_change_is_set(self) -> bool:
        x, z = self._settings.get(TOOL_CHANGE_X), self._settings.get(TOOL_CHANGE_Z)
        if x is None or z is None:
            return False
        ini = self._ini_tool_change()
        return ini is None or abs(x - ini[0]) > SAME or abs(z - ini[1]) > SAME

    def _ini_tool_change(self) -> Optional[Tuple[float, float]]:
        """(x, z) of the INI's TOOL_CHANGE_POSITION ("X Y Z"), or None."""
        words = (self._ini.find("EMCIO", "TOOL_CHANGE_POSITION") or "").split()
        try:
            return float(words[0]), float(words[2])
        except (IndexError, ValueError):
            return None

    def _is_set(self, parameters) -> bool:
        return any(abs(self._parameters.get(number, 0.0)) > SAME for number in parameters)

    def _read_parameters(self) -> None:
        """The parameter file again, when it has changed since it was read."""
        try:
            stamp = os.stat(self._parameter_file).st_mtime_ns
        except OSError:
            stamp = None
        if stamp == self._parameters_read_at:
            return
        self._parameters_read_at = stamp
        values = {}
        try:
            with open(self._parameter_file, encoding="utf-8") as handle:
                for line in handle:
                    fields = line.split()
                    if len(fields) >= 2:
                        try:
                            values[int(fields[0])] = float(fields[1])
                        except ValueError:
                            continue
        except OSError as error:
            log.debug("predefined positions: cannot read %s: %s", self._parameter_file, error)
        self._parameters = values


_instance: Optional[PredefinedPositions] = None


def predefined_positions() -> PredefinedPositions:
    global _instance
    if _instance is None:
        _instance = PredefinedPositions()
    return _instance
