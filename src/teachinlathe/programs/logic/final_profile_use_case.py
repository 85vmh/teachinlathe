"""The part a G-code file makes - what is left of its stock once all of it
has run - and what the program is (its operations, its tool changes, how long
it runs), worked out off the GUI thread for the Programs screen's preview.

The file is read by LinuxCNC's own interpreter and its moves cut the stock,
as a simulation does (plan_worker's ``final_material``). The stock is the
conversational program's header, which the caller finds beside the file;
with none there is nothing to cut, and no part to show - but the program is
still read, for what it is. What was worked out is kept while the file and
its stock stay the same: going back to a program shows it at once.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

log = logging.getLogger(__name__)

#: How many parts are kept, the last asked for.
KEPT = 16


class FinalProfileUseCase(QObject):
    #: (path, result): what plan_worker's ``final_material`` says of ``path``
    #: - ``material`` None with no stock to cut, ``error`` why the part is not
    #: all there ("" when it is) - or None for no program; ``error`` alone
    #: when it could not be worked out.
    ready = pyqtSignal(str, object)

    def __init__(self, planner, parent: Optional[QObject] = None, ini=None, tools=None):
        """``planner``: what gives the plan_worker the part is worked out in
        (a BackgroundPlanner), made at the first part asked for."""
        super().__init__(parent)
        self._planner_of = planner
        self._planner = None
        self._ini, self._tools = ini, tools
        self._request = None
        self._asked: Optional[Tuple[str, tuple]] = None
        self._kept: Dict[tuple, dict] = {}

    def request(self, path: str, workpiece: dict) -> None:
        """The part ``path`` makes from the bar ``workpiece`` (the header's,
        as a dict): to ``ready``, at once when it was worked out already."""
        from teachinlathe.conversational.gcode.stock import header_material
        from teachinlathe.conversational.model.data_types import Workpiece
        from teachinlathe.tooling.model.tool_snapshot import ToolSnapshot

        from shapely.geometry import Polygon

        self._request = None
        if not path or not path.lower().endswith(".ngc") or not os.path.isfile(path):
            self.ready.emit(path or "", None)
            return
        try:
            stock = header_material(Workpiece.from_dict(dict(workpiece))) if workpiece else Polygon()
        except (KeyError, TypeError, ValueError) as error:
            log.debug("final profile: no stock for %s: %s", path, error)
            stock = Polygon()
        key = (path, os.path.getmtime(path), tuple(sorted((workpiece or {}).items())))
        if key in self._kept:
            self.ready.emit(path, self._kept[key])
            return
        try:
            args = (path, self._ini_repository().ini_path, stock, ToolSnapshot.of(self._tool_library()))
        except Exception as error:
            log.error("final profile of %s failed: %s", path, error)
            self.ready.emit(path, {"material": None, "error": str(error)})
            return
        if self._planner is None:
            self._planner = self._planner_of()
            self._planner.finished.connect(self._on_finished)
        self._asked = (path, key)
        self._request = self._planner.submit("final-profile", "final_material", *args)

    def _on_finished(self, request_id, ok, result):
        if request_id != self._request or self._asked is None:
            return
        self._request = None
        path, key = self._asked
        if ok:
            result = dict(result, error=result["error"] and f"The interpreter stopped: {result['error']}")
            if result["material"] is not None and result["material"].is_empty:
                result["material"] = None
        else:
            log.error("final profile of %s failed: %s", path, result)
            result = {"material": None, "error": str(result)}
        self._kept[key] = result
        while len(self._kept) > KEPT:
            self._kept.pop(next(iter(self._kept)))
        self.ready.emit(path, result)

    def _ini_repository(self):
        if self._ini is None:
            from teachinlathe.core.ini_repository import ini_repository
            self._ini = ini_repository()
        return self._ini

    def _tool_library(self):
        if self._tools is None:
            from teachinlathe.core.tool_library_repository import tool_library_repository
            self._tools = tool_library_repository()
        return self._tools
