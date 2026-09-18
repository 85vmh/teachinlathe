"""E-stop, power and homing.

The ``machine.estop.*``, ``machine.power.*`` and ``machine.home.*`` actions
that the old .ui wired into its action buttons by name. Those buttons never
appeared as an import, which is why this was the last part of the machine to
be brought into a repository.

An axis letter is turned into a joint number through ``[TRAJ] COORDINATES``:
on this lathe ``X`` is joint 0 and ``Z`` is joint 1, which is not the same as
their index in a nine-axis position tuple.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import linuxcnc
from PyQt5.QtCore import QObject, pyqtSignal

from .command_repository import command_repository
from .ini_repository import ini_repository
from .status_repository import status_repository

log = logging.getLogger(__name__)

ALL_JOINTS = -1


class MachineRepository(QObject):
    """The machine's power state and homing."""

    stateChanged = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None,
                 status=None, commands=None, command=None, ini=None) -> None:
        super().__init__(parent)
        self._ini = ini_repository() if ini is None else ini
        self._status = status_repository() if status is None else status
        self._commands = command_repository() if commands is None else commands
        self._cmd = linuxcnc.command() if command is None else command

        self._status.task_state.notify(lambda *_: self.stateChanged.emit())

    # -- state ------------------------------------------------------------

    @property
    def is_estopped(self) -> bool:
        try:
            return self._status.stat.task_state == linuxcnc.STATE_ESTOP
        except Exception:
            log.exception("could not read the task state")
            return True

    @property
    def is_on(self) -> bool:
        try:
            return self._status.stat.task_state == linuxcnc.STATE_ON
        except Exception:
            log.exception("could not read the task state")
            return False

    # -- e-stop -----------------------------------------------------------

    def estop(self) -> None:
        log.info("engaging E-stop")
        self._cmd.state(linuxcnc.STATE_ESTOP)

    def reset_estop(self) -> None:
        log.info("resetting E-stop")
        self._cmd.state(linuxcnc.STATE_ESTOP_RESET)

    def toggle_estop(self) -> None:
        if self.is_estopped:
            self.reset_estop()
        else:
            self.estop()

    # -- power ------------------------------------------------------------

    def power_on(self) -> None:
        log.info("turning machine power on")
        self._cmd.state(linuxcnc.STATE_ON)

    def power_off(self) -> None:
        log.info("turning machine power off")
        self._cmd.state(linuxcnc.STATE_OFF)

    def toggle_power(self) -> None:
        if self.is_on:
            self.power_off()
        else:
            self.power_on()

    def can_power_on(self) -> Tuple[bool, str]:
        """Whether power may be switched on, and why not when it may not."""
        if self.is_estopped:
            return False, "Reset the E-stop before turning the machine on"
        return True, ""

    # -- homing -----------------------------------------------------------

    def can_home(self) -> Tuple[bool, str]:
        """Whether homing is allowed now, and why not when it is not.

        The rule the old .ui's home buttons enforced: the machine has to be on.
        """
        if not self.is_on:
            return False, "Machine must be on to home"
        return True, ""

    def joint_for_axis(self, axis) -> int:
        """The joint number driving *axis*, given as a letter or a number."""
        coordinates = self._ini.coordinates
        if isinstance(axis, int):
            return axis
        letter = str(axis).strip().lower()
        if letter not in coordinates:
            raise ValueError(
                "axis {!r} is not in [TRAJ] COORDINATES ({!r})"
                .format(axis, coordinates.upper()))
        return coordinates.index(letter)

    def home_axis(self, axis) -> bool:
        """Home the joint driving *axis*."""
        try:
            jnum = self.joint_for_axis(axis)
        except ValueError:
            log.exception("cannot home an axis this machine does not have")
            return False
        log.info("homing axis %s (joint %d)", str(axis).upper(), jnum)
        return self._home_joint(jnum)

    def home_all(self) -> bool:
        log.info("homing all axes")
        return self._home_joint(ALL_JOINTS)

    def unhome_axis(self, axis) -> bool:
        try:
            jnum = self.joint_for_axis(axis)
        except ValueError:
            log.exception("cannot unhome an axis this machine does not have")
            return False
        log.info("unhoming axis %s (joint %d)", str(axis).upper(), jnum)
        return self._unhome_joint(jnum)

    @property
    def all_homed(self) -> bool:
        return self._status.allHomed()

    def is_axis_homed(self, axis) -> bool:
        try:
            jnum = self.joint_for_axis(axis)
            return bool(self._status.stat.joint[jnum]["homed"])
        except Exception:
            log.exception("could not read the homing state")
            return False

    def _home_joint(self, jnum: int) -> bool:
        # Homing runs in MANUAL with teleop off: the joint is commanded
        # directly, not through the kinematics.
        if not self._commands.set_task_mode(linuxcnc.MODE_MANUAL):
            log.error("could not switch to MANUAL to home")
            return False
        self._cmd.teleop_enable(False)
        self._cmd.home(jnum)
        return True

    def _unhome_joint(self, jnum: int) -> bool:
        if not self._commands.set_task_mode(linuxcnc.MODE_MANUAL):
            log.error("could not switch to MANUAL to unhome")
            return False
        self._cmd.teleop_enable(False)
        self._cmd.unhome(jnum)
        return True


_INSTANCE: Optional[MachineRepository] = None


def machine_repository() -> MachineRepository:
    """The shared MachineRepository."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = MachineRepository()
    return _INSTANCE
