"""A program as the machine runs it: the moves and the events the LinuxCNC
interpreter makes of its G-code (core/gcode_moves.py), in order, for the
simulator to time, to cut the stock with and to play.

Everything is in work coordinates - the program's as at cycle start, its
work offset (G54...) and the tool's offset taken out; a G10 L20 or a G92 in
the program does not move them - in mm: Z, and r the radius, X being a
diameter only in the G-code. A point is where the tip of the current loaded
tool is, as the program commands it. A time is in seconds from cycle
start, as LinuxCNC's estimate has it (the one its preview shows): the
machine's limits, its look-ahead, G95/G96 and the tool change; stops and
M66 waits take none.
"""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional, Tuple, Union


class At(NamedTuple):
    """A point of the work: its Z and its radius, mm."""
    z: float
    r: float


@dataclass(frozen=True)
class Where:
    """Where in the G-code a step comes from: ``line`` of ``file`` (absolute),
    ``depth`` calls deep - 0 in the program, 1 in an M6 remap's sub - and
    ``program_line``, the line of the program itself being run: the call's,
    inside a subroutine or a remap."""
    file: str
    line: int
    depth: int
    program_line: int


class MoveKind(Enum):
    RAPID = "rapid"                 # G0, and the G28/G30 moves
    FEED = "feed"                   # G1, and G33/G33.1/G76's synced passes
    ARC = "arc"                     # G2/G3
    TOOL_CHANGE = "tool_change"     # to the tool change position, made by LinuxCNC's task at an M6


@dataclass(frozen=True)
class Spindle:
    """The spindle and the feed a move is made with.

    ``turning``: 1 M3, -1 M4, 0 stopped. ``speed``: the S word - rpm under
    G97, the surface speed in m/min under G96 - and ``css_max`` the rpm G96
    is capped at (its D word), 0 under G97, ``float("inf")`` for a G96 with no
    D. ``feed``: mm/rev when ``per_rev`` (G95), else mm/min. ``sync_pitch``:
    mm a turn while the motion is synced with the spindle (G33, G33.1, G76),
    0 otherwise."""
    turning: int = 0
    speed: float = 0.0
    css_max: float = 0.0
    feed: float = 0.0
    per_rev: bool = False
    sync_pitch: float = 0.0


@dataclass(frozen=True)
class Move:
    """A move of the tool from ``start`` to ``end``, as ``kind`` says, with
    tool ``tool`` (its T number, 0 for none) and ``spindle``; an arc goes
    round ``center``, counter-clockwise (G3) with Z to the right and X up
    when ``ccw``. ``where``: the line it is written on. ``ends_at``: when it
    ends, None when the program is not timed."""
    kind: MoveKind
    start: At
    end: At
    tool: int
    spindle: Spindle
    where: Where
    center: Optional[At] = None
    ccw: bool = False
    ends_at: Optional[float] = None


class StopKind(Enum):
    PROGRAM_STOP = "M0"             # M0, M60: waits for cycle start
    OPTIONAL_STOP = "M1"            # M1: waits for cycle start when Optional Stop is on
    PROGRAM_END = "M2"              # M2, M30


@dataclass(frozen=True)
class Stop:
    """The program stops here (``kind``)."""
    kind: StopKind
    where: Where


@dataclass(frozen=True)
class Dwell:
    """The tool stands still ``seconds`` (G4), till ``ends_at``."""
    seconds: float
    where: Where
    ends_at: Optional[float] = None


@dataclass(frozen=True)
class ToolChange:
    """Tool ``tool`` becomes the current loaded tool (M6): after the move to the tool
    change position, before the program goes on, done at ``ends_at``."""
    tool: int
    where: Where
    ends_at: Optional[float] = None


@dataclass(frozen=True)
class OperationStart:
    """Where operation ``number`` (from 1) of a conversational program, called
    ``title``, starts: its heading comment."""
    number: int
    title: str
    where: Where


@dataclass(frozen=True)
class OriginShift:
    """The program moves its work origin here (G10 L20, G92 - a Facing's new
    Z0 - or another work offset, G55...): from here on its Z0 and X0 are at
    ``origin``, a point of the work coordinates of cycle start, in work
    offset ``work_offset`` (1 for G54 ... 9 for G59.3). The moves stay in
    those coordinates; this is for what shows the origin."""
    origin: At
    where: Where
    work_offset: int = 1


Step = Union[Move, Stop, Dwell, ToolChange, OperationStart, OriginShift]


@dataclass(frozen=True)
class ProgramMoves:
    """A program as the interpreter made it: its ``steps`` in order, and the
    interpreter's error, "" with none, where it stopped making them.
    ``start``: where the tool is at cycle start - the machine's position
    when it was given, else the end of the first move - None with no move.
    ``time_flags``: what the time estimate could not model ("css-unbounded",
    "sync-no-spindle", ...). ``start_tool``: the current loaded tool's T number
    at cycle start, 0 for none. ``start_work_offset``: the work offset in use
    there, 1 for G54 ... 9 for G59.3."""
    steps: Tuple[Step, ...]
    error: str = ""
    start: Optional[At] = None
    time_flags: Tuple[str, ...] = ()
    start_tool: int = 0
    start_work_offset: int = 1

    @property
    def moves(self) -> Tuple[Move, ...]:
        return tuple(step for step in self.steps if isinstance(step, Move))

    @property
    def duration(self) -> Optional[float]:
        """How long it runs, None when it is not timed."""
        times = [step.ends_at for step in self.steps if getattr(step, "ends_at", None) is not None]
        return times[-1] if times else None
