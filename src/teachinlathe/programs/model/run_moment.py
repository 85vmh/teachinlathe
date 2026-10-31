"""A program run as the Programs screens show it, whatever runs it - the
machine or a simulation (programs.logic.run): its state, where it is, the
tool, the feed and the spindle, its time and the marks along it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

from teachinlathe.programs.model.tool_changes import NextTool


class RunState(Enum):
    IDLE = "idle"           # not started, or stopped
    RUNNING = "running"
    HELD = "held"           # Feed Hold
    WAITING = "waiting"     # at an M0, or an M1 with Optional Stop on: Cycle Start goes on
    FINISHED = "finished"


@dataclass(frozen=True)
class MotionReadout:
    """The feed and the spindle: ``rapid`` a rapid (``feed`` then mm/min),
    else ``feed`` mm/rev - or mm/min when not ``per_rev`` - and the
    overrides of each, 1.0 for 100%. ``rpm`` the spindle's speed, ``css``
    the surface speed in m/min under G96, None under G97."""
    rapid: bool = False
    feed: float = 0.0
    per_rev: bool = True
    feed_override: float = 1.0
    rpm: float = 0.0
    spindle_override: float = 1.0
    css: Optional[float] = None


@dataclass(frozen=True)
class RunMoment:
    """Where the run is: the tool's tip in the work offset in use (``x`` a
    diameter, ``z``, mm) and what is left of the move under way, that work
    offset (1 for G54 ... 9 for G59.3), the program's line, the current
    loaded tool and the next one, the feed and the spindle, and the time
    from cycle start (None, not known)."""
    x: float = 0.0
    z: float = 0.0
    x_to_go: float = 0.0
    z_to_go: float = 0.0
    work_offset: int = 1
    program_line: int = 0
    tool: int = 0
    next_tool: Optional[NextTool] = None
    motion: MotionReadout = field(default_factory=MotionReadout)
    time: Optional[float] = None


@dataclass(frozen=True)
class RunMark:
    """A moment along the run a seek bar shows: at ``time``, ``kind``
    ("operation", "tool_change", "stop", "end") - an operation (``number``,
    ``label`` its title), a tool change (``number`` the tool), a stop
    (``label`` "M0" or "M1")."""
    time: float
    kind: str
    number: int = 0
    label: str = ""
    tool_change: bool = False


NO_MARKS: Tuple[RunMark, ...] = ()
