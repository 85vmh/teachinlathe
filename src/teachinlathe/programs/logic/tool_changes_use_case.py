"""The next tool of the program loaded and how long until the machine stops
for it, for the Programs screen's tool box.

The program is read by LinuxCNC's own interpreter, in the planning worker
(plan_worker's ``tool_changes``), when it is loaded - from the machine as it
is then - and again when it starts to run, from the machine as it starts:
the current loaded tool, where it is, the work offset. While it runs, the
line the machine reports and where the tool is say which of its moves is
being made (programs.model.tool_changes).
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from teachinlathe.core.gcode_moves import MachineState
from teachinlathe.programs.model.tool_changes import LineKey, NextTool, ToolChangePlan

log = logging.getLogger(__name__)


class ToolChangesUseCase(QObject):
    #: The next tool, or how long until it, may be other than it was.
    changed = pyqtSignal()

    def __init__(self, planner: Callable, parent: Optional[QObject] = None, ini=None, status=None):
        """``planner``: what gives the plan_worker the program is read in (a
        BackgroundPlanner), made at the first program read."""
        super().__init__(parent)
        self._planner_of = planner
        self._planner = None
        self._ini, self._status = ini, status
        self._request = None
        self._path = ""
        self._optional_stop = False
        self._plan: Optional[ToolChangePlan] = None
        self._running = False
        # the move being made, its index in the plan's segments
        self._index = 0
        # the work origin (g5x + g92), (x, z) in machine units, as the run started
        self._origin = (0.0, 0.0)
        self._point = (0.0, 0.0)

    def load(self, path: str) -> None:
        """The program at ``path`` is loaded ("" for none)."""
        self._path = path if path and path.lower().endswith(".ngc") else ""
        self._plan, self._index = None, 0
        self._read()
        self.changed.emit()

    def set_optional_stop(self, on: bool) -> None:
        """Optional Stop on or off: an M1 takes another branch."""
        if bool(on) == self._optional_stop:
            return
        self._optional_stop = bool(on)
        self._read()

    def start_run(self, snapshot) -> None:
        """The program starts to run, the machine as ``snapshot`` has it."""
        self._running, self._index = True, 0
        g5x, g92 = tuple(snapshot.g5x_offset) or (0.0,) * 3, tuple(snapshot.g92_offset) or (0.0,) * 3
        self._origin = (g5x[0] + g92[0], g5x[2] + g92[2])
        self._read()
        self.follow(snapshot)

    def stop_run(self) -> None:
        """The program is no longer running: ended, or stopped."""
        if not self._running:
            return
        self._running, self._index = False, 0
        self.changed.emit()

    def follow(self, snapshot) -> None:
        """Where the running program is, as ``snapshot`` (a
        ProgramRuntimeSnapshot) has it."""
        if not self._running or self._plan is None:
            return
        self._point = self._tool_point(snapshot)
        index = self._plan.locate(_line_key(snapshot), self._point, self._index)
        if index is not None:
            self._index = index
        self.changed.emit()

    def next_tool(self, current_tool: int) -> Optional[NextTool]:
        """The tool after ``current_tool``, the current loaded tool; None with
        none, or the program not read yet. The seconds until it only while
        the program runs."""
        if self._plan is None:
            return None
        if not self._running:
            tool = self._plan.next_tool(current_tool)
            return None if tool is None else NextTool(tool, None)
        return self._plan.next_tool_at(current_tool, self._index, self._point)

    def _tool_point(self, snapshot):
        """Where the tip of the tool is: (z, r) in mm, in the work
        coordinates of the run's start - those the plan's moves are in."""
        position = tuple(snapshot.actual_position) or (0.0,) * 3
        offset = tuple(snapshot.tool_offset) or (0.0,) * 3
        per_mm = float(snapshot.linear_units or 1.0)
        return ((position[2] - offset[2] - self._origin[1]) / per_mm,
                (position[0] - offset[0] - self._origin[0]) / per_mm)

    def _read(self):
        if not self._path:
            return
        try:
            stat = self._status_repository().stat
            stat.poll()
            args = (self._path, self._ini_repository().ini_path, MachineState.of(stat), self._optional_stop)
        except Exception as error:
            log.error("tool changes of %s: %s", self._path, error)
            return
        if self._planner is None:
            self._planner = self._planner_of()
            self._planner.finished.connect(self._on_finished)
        self._request = (self._path, self._planner.submit("tool-changes", "tool_changes", *args))

    def _on_finished(self, request_id, ok, result):
        if self._request is None or request_id != self._request[1]:
            return
        path, _id = self._request
        self._request = None
        if path != self._path:
            return
        if not ok:
            log.error("tool changes of %s failed: %s", path, result)
            return
        self._plan = result
        self._index = 0
        self.changed.emit()

    def _ini_repository(self):
        if self._ini is None:
            from teachinlathe.core.ini_repository import ini_repository
            self._ini = ini_repository()
        return self._ini

    def _status_repository(self):
        if self._status is None:
            from teachinlathe.core.status_repository import status_repository
            self._status = status_repository()
        return self._status


def _line_key(snapshot) -> LineKey:
    """The line the machine is running: inside a subroutine, the program's
    own is the line of the outermost call."""
    line = int(snapshot.motion_line or 0)
    depth = int(snapshot.call_level or 0)
    stack = snapshot.call_stack
    program_line = stack[0].line if depth > 0 and stack else line
    return LineKey(depth, program_line, line)
