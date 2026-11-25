"""Loading and running NC programs.

``run`` is the one with a wrinkle: pressing it on a *paused* program resumes
instead of restarting, which is what the operator means by pressing the green
button twice.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import linuxcnc
from PyQt6.QtCore import QObject, pyqtSignal

from .command_repository import command_repository
from .no_program import NO_PROGRAM, loaded_program
from .status_repository import status_repository

log = logging.getLogger(__name__)


class ProgramRepository(QObject):
    """The loaded NC program: load it, run it, stop it."""

    #: The path that was just loaded.
    programLoaded = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None,
                 status=None, commands=None, command=None) -> None:
        super().__init__(parent)
        self._status = status_repository() if status is None else status
        self._commands = command_repository() if commands is None else commands
        self._cmd = linuxcnc.command() if command is None else command

    # -- running ----------------------------------------------------------

    def run(self, start_line: int = 0) -> bool:
        """Run the loaded program, or resume it if it is paused."""
        stat = self._status.stat
        if stat.state == linuxcnc.RCS_EXEC and stat.paused:
            log.debug("resuming the paused program instead of restarting it")
            self._cmd.auto(linuxcnc.AUTO_RESUME)
            return True

        if not self._commands.set_task_mode(linuxcnc.MODE_AUTO):
            log.error("could not switch to AUTO to run the program")
            return False

        log.info("running program from line %d", start_line)
        self._cmd.auto(linuxcnc.AUTO_RUN, start_line)
        return True

    def step(self) -> bool:
        """Run one line and stop."""
        if not self._commands.set_task_mode(linuxcnc.MODE_AUTO):
            return False
        self._cmd.auto(linuxcnc.AUTO_STEP)
        return True

    def pause(self) -> None:
        log.debug("pausing program execution")
        self._cmd.auto(linuxcnc.AUTO_PAUSE)

    def resume(self) -> None:
        log.debug("resuming program execution")
        self._cmd.auto(linuxcnc.AUTO_RESUME)

    def abort(self) -> None:
        """Stop the running program, MDI command or homing operation."""
        log.debug("aborting")
        self._cmd.abort()

    # -- program options --------------------------------------------------

    def set_optional_stop(self, enabled: bool) -> None:
        self._cmd.set_optional_stop(bool(enabled))

    def set_block_delete(self, enabled: bool) -> None:
        self._cmd.set_block_delete(bool(enabled))

    # -- loading ----------------------------------------------------------

    def load(self, path: str) -> bool:
        """Open *path* as the current program."""
        if not path:
            return self.clear()

        path = os.path.abspath(path)
        if not os.path.isfile(path):
            log.error("no such NC program: %s", path)
            return False

        log.info("loading NC program: %s", path)
        self._cmd.program_open(path.encode("utf-8"))
        self._cmd.wait_complete()
        self.programLoaded.emit(path)
        return True

    def reload(self) -> bool:
        """Re-open the program that is already loaded, picking up edits."""
        current = self.current_file
        if not current:
            return False
        return self.load(current)

    def load_or_reload(self, path: str) -> bool:
        """Load *path*, reloading in place when it is already the open one."""
        if not path or not os.path.isfile(path):
            return False

        requested = os.path.abspath(path)
        if self.current_file == requested:
            return self.reload()
        return self.load(requested)

    def clear(self) -> bool:
        """No program loaded: the empty one (NO_PROGRAM) opened in its place -
        LinuxCNC has no way to close one. Not while one runs."""
        if self._status.stat.interp_state != linuxcnc.INTERP_IDLE:
            log.warning("the program is not unloaded: one is running")
            return False
        log.info("unloading the program (%s)", self.current_file or "none")
        self._cmd.program_open(NO_PROGRAM.encode("utf-8"))
        self._cmd.wait_complete()
        return True

    def clear_if_missing(self) -> bool:
        """Unloads the program when its file is gone from the disk (deleted,
        moved, its stick pulled out): the Run button and the backplot would
        read it again. True when it was unloaded."""
        current = self.current_file
        if not current or os.path.isfile(current):
            return False
        log.warning("the loaded program %s is gone from the disk", current)
        return self.clear()

    @property
    def current_file(self) -> str:
        """Absolute path of the loaded program, or "" when none is (the
        empty one, loaded for none, included)."""
        try:
            name = getattr(self._status.stat, "file", "") or ""
        except Exception:
            log.exception("could not read the loaded program")
            return ""
        return loaded_program(name)


_INSTANCE: Optional[ProgramRepository] = None


def program_repository() -> ProgramRepository:
    """The shared ProgramRepository."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = ProgramRepository()
    return _INSTANCE
