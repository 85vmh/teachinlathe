"""The threads a program cuts, as the backplot draws them: which of its lines
move synced with the spindle (G33, G76) - drawn as the threading tooth's Vs,
not as lines - and the Vs themselves, each where it goes into the material
then, pass after pass. Worked out off the GUI thread with the program's
finished part (plan_worker's ``final_material``) and kept here, by file, for
the plot of the machine and the simulation's alike.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional, Tuple


@dataclass(frozen=True, eq=False)
class ThreadPlan:
    """A program's threads: ``synced_lines``, the lines of the program that
    move synced with the spindle on position; ``trace``, the outline of each
    V the tooth cuts on the tool's side, shapely lines in (z, r) mm, in the
    work coordinates of cycle start - none with no stock to cut them in."""
    synced_lines: FrozenSet[int]
    trace: Tuple[object, ...] = ()


class ThreadPlans:
    """ThreadPlans by program file. A new one for a file is a new object:
    what draws one knows by that that it changed."""

    def __init__(self):
        self._plans: Dict[str, ThreadPlan] = {}

    def put(self, path: str, plan: Optional[ThreadPlan]) -> None:
        """``plan`` for ``path``; none - forgotten - with no line synced."""
        if not path:
            return
        key = os.path.abspath(path)
        if plan is None or not plan.synced_lines:
            self._plans.pop(key, None)
        else:
            self._plans[key] = plan

    def get(self, path: str) -> Optional[ThreadPlan]:
        return self._plans.get(os.path.abspath(path)) if path else None
