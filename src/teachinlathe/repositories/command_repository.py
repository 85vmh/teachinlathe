"""Commands sent to LinuxCNC.

Issuing an MDI command means switching the task to MDI mode, sending it, and
putting the task back the way it was once the interpreter goes idle again.
That last part is what makes this a repository rather than a function: the
restore happens later, when the status says so, so something has to remember
the mode to go back to.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import linuxcnc
from PyQt5.QtCore import QObject, pyqtSignal

from .status_repository import status_repository

log = logging.getLogger(__name__)

MDI_NOT_READY = "Can't issue MDI unless machine is ON, HOMED and IDLE"
MDI_SEPARATOR = ";"


class CommandRepository(QObject):
    """Sends commands to the task controller."""

    #: Emitted with the command text each time one is sent.
    commandIssued = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None,
                 status=None, command=None) -> None:
        super().__init__(parent)
        self._status = status_repository() if status is None else status
        self._cmd = linuxcnc.command() if command is None else command
        self._previous_mode: Optional[int] = None

        # The restore is driven off the poll rather than off an interp_state
        # change, because a command can finish inside one poll cycle and the
        # change then never shows up. Forcing the cached interp_state to an
        # impossible value before each command only papers over that.
        self._status.polled.connect(self._restore_mode_when_idle)

    # -- MDI --------------------------------------------------------------

    def issue_mdi(self, command: str, reset: bool = True) -> bool:
        """Run *command* in MDI mode.

        Several commands may be separated by ``;`` and are sent in order.
        With *reset*, the task returns to the mode it was in once the
        interpreter is idle again.

        Returns whether the command was sent. Like the action it replaces,
        this does not refuse on an unhomed or off machine - that is what
        :meth:`can_issue_mdi` is for, and callers use it to decide whether to
        offer the command at all.
        """
        if reset:
            self._previous_mode = self._task_mode()

        if not self.set_task_mode(linuxcnc.MODE_MDI):
            log.error("failed to issue MDI command: %s", command)
            return False

        for part in command.strip().split(MDI_SEPARATOR):
            part = part.strip()
            if not part:
                continue
            log.info("issuing MDI command: %s", part)
            self._cmd.mdi(part)
            self.commandIssued.emit(part)
        return True

    def can_issue_mdi(self) -> Tuple[bool, str]:
        """Whether MDI is allowed now, and why not when it is not."""
        stat = self._status.stat
        try:
            ready = (stat.task_state == linuxcnc.STATE_ON
                     and self._status.allHomed()
                     and stat.interp_state == linuxcnc.INTERP_IDLE)
        except Exception:
            log.exception("could not read the machine state")
            return False, MDI_NOT_READY
        return (True, "") if ready else (False, MDI_NOT_READY)

    # -- task mode --------------------------------------------------------

    def set_task_mode(self, new_mode: int) -> bool:
        """Switch the task to *new_mode*, unless the machine is moving.

        A mode the task is already in is not set again. That is not just an
        optimisation: a task mode transition makes LinuxCNC re-init the
        interpreter, and ``Interp::init()`` clears the modal state - including
        diameter mode, which goes back to G8. Re-asserting the current mode
        would silently throw G7 away.
        """
        if self._task_mode() == new_mode:
            return True
        if self.is_running():
            log.error("can't set task mode while the machine is running")
            return False
        self._cmd.mode(new_mode)
        return True

    def is_running(self) -> bool:
        """Whether the machine is moving, from MDI or a running program."""
        stat = self._status.stat
        try:
            if stat.state == linuxcnc.RCS_EXEC:
                return True
            return (stat.task_mode == linuxcnc.MODE_AUTO
                    and stat.interp_state != linuxcnc.INTERP_IDLE)
        except Exception:
            log.exception("could not read the machine state")
            return False

    @property
    def pending_mode_restore(self) -> Optional[int]:
        """The mode the task returns to when the interpreter goes idle."""
        return self._previous_mode

    def _restore_mode_when_idle(self) -> None:
        if self._previous_mode is None:
            return
        try:
            if self._status.stat.interp_state != linuxcnc.INTERP_IDLE:
                return
        except Exception:
            log.exception("could not read the interpreter state")
            return

        mode, self._previous_mode = self._previous_mode, None
        if self.set_task_mode(mode):
            log.debug("task mode restored to %s after MDI", mode)

    def _task_mode(self) -> Optional[int]:
        try:
            return self._status.stat.task_mode
        except Exception:
            log.exception("could not read the task mode")
            return None


_INSTANCE: Optional[CommandRepository] = None


def command_repository() -> CommandRepository:
    """The shared CommandRepository."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = CommandRepository()
    return _INSTANCE


def issue_mdi(command: str, reset: bool = True) -> bool:
    """Convenience wrapper, so call sites read as they did before."""
    return command_repository().issue_mdi(command, reset=reset)
