"""A simulation of a G-code file: the program as the machine would run it, from
the state the machine is in now, worked out off the GUI thread.

The file is read by LinuxCNC's own interpreter with the machine's INI
(core.gcode_moves) and run on its stock (simulation.logic.program_run) in a
worker process of its own (plan_worker's ``simulate``), started with the first
simulation. The stock is the conversational program's header - a program in
Generated Programs keeps the one it was generated from - else none: the moves
alone.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from teachinlathe.core.gcode_moves import MachineState

log = logging.getLogger(__name__)


class SimulateUseCase(QObject):
    #: The run worked out: a simulation.logic.program_run.ProgramRun.
    ready = pyqtSignal(object)
    #: Why there is no run.
    failed = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None, ini=None, status=None, tools=None, planner=None):
        """``planner``: what gives the plan_worker the run is worked out in,
        made at the first simulation - shared with the other use cases of the
        screen; None, one of its own."""
        super().__init__(parent)
        self._ini, self._status, self._tools = ini, status, tools
        self._planner_of = planner
        self._planner = None
        self._request = None

    def start(self, ngc_path: str, json_path: str = "", optional_stop: bool = False,
              block_delete: bool = False) -> None:
        """A simulation of ``ngc_path``, the program behind it at ``json_path``
        ("" for none) giving its stock, Optional Stop and Skip ``/`` Blocks
        on or not: to ``ready``."""
        from teachinlathe.conversational.logic.plan_worker import BackgroundPlanner
        from teachinlathe.tooling.model.tool_snapshot import ToolSnapshot

        try:
            args = (ngc_path, self._ini_repository().ini_path, _stock(json_path), self._machine(),
                    bool(optional_stop), bool(block_delete), ToolSnapshot.of(self._tool_library()))
        except Exception as error:
            log.error("simulation of %s failed: %s", ngc_path, error)
            self.failed.emit(str(error))
            return
        if self._planner is None:
            self._planner = self._planner_of() if self._planner_of is not None else BackgroundPlanner(self)
            self._planner.finished.connect(self._on_finished)
        self._request = self._planner.submit("simulation", "simulate", *args)

    def _on_finished(self, request_id, ok, result):
        if request_id != self._request:
            return
        self._request = None
        if ok:
            self.ready.emit(result)
        else:
            log.error("simulation failed: %s", result)
            self.failed.emit(str(result))

    def _machine(self) -> MachineState:
        """The machine now, as the run starts from it: where it is, its
        current loaded tool, that tool's offset and the work offset in use."""
        stat = self._status_repository().stat
        stat.poll()
        return MachineState.of(stat)

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

    def _tool_library(self):
        if self._tools is None:
            from teachinlathe.core.tool_library_repository import tool_library_repository
            self._tools = tool_library_repository()
        return self._tools


def _stock(json_path: str):
    """The stock the conversational program at ``json_path`` says it starts
    from (stock.header_material), an empty shape with none."""
    from shapely.geometry import Polygon

    from teachinlathe.conversational.gcode.stock import header_material
    from teachinlathe.conversational.model.data_types import Program

    if not json_path:
        return Polygon()
    try:
        with open(json_path, encoding="utf-8") as handle:
            program = Program.from_dict(json.load(handle))
    except (OSError, ValueError, KeyError) as error:
        log.warning("no stock for the simulation from %s: %s", json_path, error)
        return Polygon()
    return header_material(program.header.workpiece)
