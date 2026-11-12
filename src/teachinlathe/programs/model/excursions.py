"""Where a program sends the tool away from the work and brings it back: to
the tool change position at an M6, to G28 or G30 (Pause to Inspect) - the
moves whose ``target`` is the machine's own position.

The tool goes there (AWAY), waits - the tool change, an M0, an M1 - and is
AWAY still until it starts back: the first move after it is there. It is on
its way BACK through the rapids that follow, up to the first move that is not
one or a stop, and how far along (``progress``) is how much nearer it is to
where they end than it was where they start.

Made from a program's steps (simulation.model.moves); what the run is at is
said by the index of its move among the program's moves - the plan's
segments (tool_changes.ToolChangePlan) are the same moves, in the same order.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Tuple

from teachinlathe.simulation.model.moves import At, Dwell, Move, MoveKind, Stop, ToolChange


class Phase(Enum):
    AWAY = "away"   # on its way there, there, until it starts back
    BACK = "back"   # on its way back to the work


@dataclass(frozen=True)
class Excursion:
    """One trip away: to ``target`` ("M6", "G28", "G30") from move ``away``
    on; back from move ``back`` - None: the program never comes back - by
    the rapids up to move ``back_end`` (None: the first move back is not a
    rapid), from ``start_back`` to ``back_to``, points of the work (z, r)."""
    target: str
    away: int
    back: Optional[int] = None
    back_end: Optional[int] = None
    start_back: Optional[At] = None
    back_to: Optional[At] = None


@dataclass(frozen=True)
class ExcursionMoment:
    """The run on a trip to ``target``, in ``phase``; on its way back,
    ``progress`` from 0 where it starts back to 1 where it is back."""
    target: str
    phase: Phase
    progress: float = 0.0


@dataclass(frozen=True)
class Excursions:
    """A program's trips away, in order."""
    items: Tuple[Excursion, ...] = ()

    @classmethod
    def of(cls, steps: Iterable) -> "Excursions":
        items = []
        move = -1
        away: Optional[Excursion] = None      # gone, not back yet
        last_end: Optional[At] = None         # where the last move ended
        back: Optional[Excursion] = None      # on the rapids back
        for step in steps:
            if isinstance(step, Move):
                move += 1
                if step.target:
                    if back is not None:
                        items.append(back)
                        back = None
                    if away is None:
                        away = Excursion(step.target, move)
                    else:
                        away = Excursion(step.target, away.away)
                elif away is not None:
                    # the first move after it is there: it starts back
                    rapid = step.kind is MoveKind.RAPID
                    back = Excursion(away.target, away.away, move, move if rapid else None, last_end,
                                     step.end if rapid else last_end)
                    away = None
                    if not rapid:
                        items.append(back)
                        back = None
                elif back is not None:
                    if step.kind is MoveKind.RAPID:
                        back = Excursion(back.target, back.away, back.back, move, back.start_back, step.end)
                    else:
                        items.append(back)
                        back = None
                last_end = step.end
            elif isinstance(step, (Stop, ToolChange, Dwell)) and back is not None:
                # a stop on the way back: it is back
                items.append(back)
                back = None
        if back is not None:
            items.append(back)
        if away is not None:
            items.append(away)
        return cls(tuple(items))

    def at(self, move: int, point: Optional[Tuple[float, float]]) -> Optional[ExcursionMoment]:
        """The trip the run is on with move ``move`` under way - or the last
        one made, while it waits - and the tool at ``point`` (z, r); None,
        on none."""
        for excursion in self.items:
            if move < excursion.away:
                return None
            if excursion.back is None or move < excursion.back:
                return ExcursionMoment(excursion.target, Phase.AWAY)
            if excursion.back_end is not None and move <= excursion.back_end:
                return ExcursionMoment(excursion.target, Phase.BACK, _progress(excursion, point))
        return None


def _progress(excursion: Excursion, point) -> float:
    """How far back, 0..1: how much nearer ``point`` is to where the rapids
    back end than where they start."""
    if point is None or excursion.start_back is None or excursion.back_to is None:
        return 0.0
    whole = math.dist(excursion.start_back, excursion.back_to)
    if whole <= 1e-9:
        return 1.0
    return min(1.0, max(0.0, 1.0 - math.dist(point, excursion.back_to) / whole))
