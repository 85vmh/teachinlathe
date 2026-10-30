"""The moves a program's G-code makes, and the G-code made from them.

A Move is one straight move of the control point. The profile planner
(operations/profiling) plans in Moves; GcodeEmitter writes the G-code a move
at a time and keeps each as a Move - a program's, operation by operation
(OperationPath), or one operation's - so what is drawn of it (drawn_lines) is
its G-code, not a second working out of it.
"""

from __future__ import annotations

import math
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional, Tuple

from .config import fmt


@dataclass(frozen=True)
class ArcCenter:
    """The centre an arc move goes round, in (z, r), and which way: clockwise
    as seen with Z to the right and X up (G2)."""
    z: float
    r: float
    clockwise: bool


@dataclass
class Move:
    """One move of the control point, in (z, r) as the machine has them (not
    mirrored): straight, or round ``arc`` when it has one. ``feed`` False is
    a rapid."""
    z0: float
    r0: float
    z1: float
    r1: float
    feed: bool
    pass_no: int = -1
    contour: bool = False
    pocket: bool = False
    #: the last move of a pass, its retract included: where an M1 stop goes
    pass_end: bool = False
    #: a contour move as the profile drawing shows it, (z0, r0, z1, r1): where
    #: the nose touches - along the profile and its stock - rather than the
    #: compensated point the machine is programmed to
    drawn: Optional[Tuple[float, float, float, float]] = None
    arc: Optional[ArcCenter] = None
    #: a feed synchronized with the spindle: threading (G33), tapping (G33.1)
    synced: bool = False


@dataclass
class OperationPath:
    """What one operation of a program moves: ``index`` its place in the
    program's operations, ``tool_holder_id`` the current loaded tool while
    it runs - its own, or the one before's for one that cuts with none, as
    a Position At - 0 before the first tool change. ``known`` False: its
    G-code is not written on the emitter - an interpreter cycle (G76,
    G70/G71) or a generator not moved onto it yet - so its moves are not
    known here. ``optional``: a "/" block, which may be
    skipped at run time. ``z_origin``: where its Z0 is, along Z in the
    program's first one - a Facing's Z End may have become the next Z0 -
    None when that is not known."""
    index: int
    tool_holder_id: int
    moves: List[Move] = field(default_factory=list)
    known: bool = True
    optional: bool = False
    z_origin: Optional[float] = 0.0


@dataclass(frozen=True)
class Point:
    """A point as the canvas draws it: X a diameter."""
    x: float
    z: float


class Arrows(Enum):
    """The arrows a drawn feed carries: where it ends, or along it."""
    END = "end"
    ALONG = "along"


@dataclass(frozen=True)
class DrawnLine:
    """A move as the canvas draws it, X a diameter: ``pass_no`` the pass it
    is of, from 0 (-1 for a rapid), ``contour`` whether it is the finish
    contour's; ``arrows`` the arrows it carries, ``end_tick`` half the width
    of a line across its end - none of either when None."""
    x0: float
    z0: float
    x1: float
    z1: float
    pass_no: int = -1
    contour: bool = False
    arrows: Optional[Arrows] = None
    end_tick: Optional[float] = None


@dataclass(frozen=True)
class OperationPreview:
    """What the editor draws of one operation: its cuts and the rapids
    between them, the profile it cuts and that offset by the stock it leaves
    (empty when it follows none), what it could not do (``warnings``) and why
    it cannot be made at all (``error``, "" when it can)."""
    feeds: Tuple[DrawnLine, ...] = ()
    rapids: Tuple[DrawnLine, ...] = ()
    profile: Tuple[Point, ...] = ()
    offset: Tuple[Point, ...] = ()
    warnings: Tuple[str, ...] = ()
    error: str = ""


def comment(text):
    """``text`` as a G-code comment. LinuxCNC refuses a comment with another
    one in it, so the brackets ``text`` may have are made square."""
    return "( " + str(text).replace("(", "[").replace(")", "]") + " )"


class GcodeEmitter:
    """The G-code of one operation, written as its moves are made: each
    rapid and feed goes to ``lines`` and, as a Move, to ``moves``.

    A move is kept as it is written - to the decimals fmt gives - so the
    moves are the ones the interpreter reads. A word that would not change
    the position is left out, and a move that goes nowhere is not written.
    X is a diameter, as the G-code has it (G7). ``block_delete``: every line
    of the operation a "/" block, an optional one."""

    def __init__(self, block_delete: bool = False):
        self.prefix = "/" if block_delete else ""
        self.lines: List[str] = []
        self.moves: List[Move] = []
        #: a program's operations, as each was written (operation())
        self.operations: List[OperationPath] = []
        self._known = True
        #: where the work's Z0 is, along Z in the work offset the program
        #: started in (set_z_zero moves it); None when it is not known
        self.z_origin: Optional[float] = 0.0
        #: what is wrong with the operation, a line each (also written into
        #: the G-code, as a comment)
        self.errors: List[str] = []
        #: where the control point is: X a diameter; None until a move says
        self.x: Optional[float] = None
        self.z: Optional[float] = None
        #: the pass the feeds belong to, from 0; -1 before the first
        self.pass_no = -1
        #: the moves are the finish contour's (begin_contour)
        self.in_contour = False
        #: a program's stock along its operations (stock.ProgramStock), when
        #: it is one's toolpath (gcode_builder.program_toolpath)
        self.stock = None

    # ── moves ───────────────────────────────────────────────────────────────

    def rapid(self, x: Optional[float] = None, z: Optional[float] = None):
        self._move("G0", False, x, z)

    def feed(self, x: Optional[float] = None, z: Optional[float] = None, f: Optional[float] = None):
        """A G1, ``f`` the feed written with it when given."""
        self._move("G1", True, x, z, f)

    def arc(self, x: float, z: float, i: float, k: float, clockwise: bool):
        """A feed round an arc to ``x`` (a diameter), ``z``: G2 ``clockwise``,
        else G3, its centre ``i`` (on the radius) and ``k`` from where it
        starts. Its end is written as a line's is."""
        new_x, new_z = float(fmt(x)), float(fmt(z))
        i, k = float(fmt(i)), float(fmt(k))
        words = ["G2" if clockwise else "G3"]
        if new_x != self.x:
            words.append(f"X{fmt(new_x)}")
        if new_z != self.z:
            words.append(f"Z{fmt(new_z)}")
        words += [f"I{fmt(i)}", f"K{fmt(k)}"]
        self.lines.append(self.prefix + " ".join(words))
        if self.x is not None and self.z is not None:
            self.moves.append(Move(self.z, self.x / 2, new_z, new_x / 2, True, pass_no=self.pass_no,
                                   contour=self.in_contour,
                                   arc=ArcCenter(self.z + k, self.x / 2 + i, clockwise)))
        self.x, self.z = new_x, new_z

    def thread(self, z: float, pitch: float, angle: Optional[float] = None):
        """A feed along Z synchronized with the spindle (G33): ``pitch`` mm a
        turn, starting ``angle`` degrees after the spindle's index."""
        new_z = float(fmt(z))
        words = [f"G33 Z{fmt(new_z)} K{fmt(pitch)}"]
        if angle is not None:
            words.append(f"D{fmt(angle)}")
        self.lines.append(self.prefix + " ".join(words))
        if self.x is not None and self.z is not None:
            self.moves.append(Move(self.z, self.x / 2, new_z, self.x / 2, True, pass_no=self.pass_no,
                                   synced=True))
        self.z = new_z

    def rigid_tap(self, z: float, pitch: float):
        """Rigid tapping (G33.1): in along Z to ``z`` with the spindle,
        ``pitch`` mm a turn, and back out to where it started - two moves, the
        position the same after."""
        new_z = float(fmt(z))
        self.lines.append(f"{self.prefix}G33.1 Z{fmt(new_z)} K{fmt(pitch)}")
        if self.x is not None and self.z is not None:
            r = self.x / 2
            self.moves.append(Move(self.z, r, new_z, r, True, pass_no=self.pass_no, synced=True))
            self.moves.append(Move(new_z, r, self.z, r, True, pass_no=self.pass_no, synced=True))

    def begin_contour(self):
        """The moves from here on, in this operation, are its finish contour's."""
        self.in_contour = True

    def start_pass(self):
        """The feeds from here on are the next pass's."""
        self.pass_no += 1

    def _move(self, word: str, feed: bool, x: Optional[float], z: Optional[float], f: Optional[float] = None):
        new_x = self.x if x is None else float(fmt(x))
        new_z = self.z if z is None else float(fmt(z))
        words = [word]
        if new_x != self.x:
            words.append(f"X{fmt(new_x)}")
        if new_z != self.z:
            words.append(f"Z{fmt(new_z)}")
        if f is not None:
            words.append(f"F{fmt(f)}")
        if len(words) == 1:
            return
        self.lines.append(self.prefix + " ".join(words))
        if self.x is not None and self.z is not None and new_x is not None and new_z is not None:
            self.moves.append(Move(self.z, self.x / 2, new_z, new_x / 2, feed,
                                   pass_no=self.pass_no if feed else -1, contour=self.in_contour))
        self.x, self.z = new_x, new_z

    # ── what is not a move ──────────────────────────────────────────────────

    def code_comment(self, code: str, comment: str):
        """``code`` and its ``comment`` lined up after it, as the program's
        other such lines are - the "/" before it counted."""
        self.code(f"{code}{' ' * max(1, 5 - len(self.prefix + code))}({comment})")

    def code(self, text: str):
        """A line as it is - the spindle, G95 F, G10 - the "/" before it."""
        self.lines.append(self.prefix + text)

    def codes(self, texts: Iterable[str]):
        for text in texts:
            self.code(text)

    def dwell(self, seconds: float):
        self.code(f"G4 P{fmt(seconds)}")

    def inspect_stop(self, m1_params):
        """Where the operator may Pause to Inspect (M1 P, m1_remap.ngc): the
        tool comes back here, the spindle started again as it was."""
        from .helpers.m1 import m1_gcode
        self.lines.append(m1_gcode(self.prefix, m1_params))

    def blank(self):
        self.lines.append("")

    def follow_toolpath(self, toolpath):
        """Along a groove's ``toolpath`` (operations.profiling.geometry
        ToolpathLine / ToolpathArc, X a diameter) from its start, as G1 / G2 /
        G3 - a ToolpathArc anticlockwise in the profile's own sense is a G2."""
        from .operations.profiling.geometry import ToolpathArc, ToolpathLine
        if not toolpath:
            return
        current_x, current_z = toolpath[0].x, toolpath[0].z
        for element in toolpath[1:]:
            if isinstance(element, ToolpathLine):
                self.feed(element.end_x, element.end_z)
            elif isinstance(element, ToolpathArc):
                self.arc(element.end_x, element.end_z, (element.center_x - current_x) / 2,
                         element.center_z - current_z, clockwise=element.anticlockwise)
            current_x, current_z = element.end_x, element.end_z

    def note(self, text: str):
        """A line as it is, with no "/" before it: a comment that says what
        follows."""
        self.lines.append(text)

    # ── a program, operation by operation ───────────────────────────────────

    @contextmanager
    def operation(self, index: int, block_delete: bool = False, tool_holder_id: int = 0):
        """Writes one operation of a program: what is written in it is its
        OperationPath. An optional block (``block_delete``) may be skipped at
        run time, and the machine is then not where its moves left it: the
        position is not known after it."""
        start = len(self.moves)
        z_origin = self.z_origin
        self.prefix = "/" if block_delete else ""
        self._known = True
        self.in_contour = False
        try:
            yield self
        finally:
            self.operations.append(OperationPath(index, tool_holder_id, self.moves[start:], self._known,
                                                 block_delete, z_origin))
            self.prefix = ""
            if block_delete:
                self.forget_position()

    def foreign(self, lines: Iterable[str]):
        """Lines made elsewhere - by a generator not on the emitter, an
        interpreter cycle - as they are: the moves in them are not known, nor
        where they leave the machine."""
        self.lines.extend(lines)
        self._known = False
        self.forget_position()

    def tool_change(self, tool_holder_id: int, title: str = ""):
        """The change to holder ``tool_holder_id``, M6 T<n> with the tool's
        ``title`` as a comment: M6 is remapped to subroutines/m6_remap.ngc,
        which goes to the machine's tool change position, so where the
        machine is after, in the work's coordinates, is not known here."""
        line = f"M6 T{int(tool_holder_id)}"
        self.lines.append(f"{line} {comment(title)}" if title else line)
        self.forget_position()

    def forget_position(self):
        """Where the machine is is not known: the next move writes X and Z."""
        self.x = self.z = None

    def set_z_zero(self):
        """The work offset was set so that here is Z0 (G10 L20 ... Z0). In a
        "/" block it may not be: where Z0 is is not known after it."""
        if self.z is not None and self.z_origin is not None and not self.prefix:
            self.z_origin += self.z
        else:
            self.z_origin = None
        if self.z is not None:
            self.z = 0.0

    def preview(self) -> OperationPreview:
        """What has been written, as the editor draws it."""
        feeds, rapids = drawn_lines(self.moves)
        return OperationPreview(feeds, rapids, error="; ".join(self.errors))

    def error(self, text: str):
        """The operation cannot be made: why, kept and written as a comment."""
        self.errors.append(text)
        self.lines.append(comment(f"ERROR: {text}"))


#: The step an arc is drawn in, in radians.
_ARC_STEP = math.radians(5)


def arc_points(z0, r0, z1, r1, center_z, center_r, clockwise: bool):
    """The points strictly between the start (z0, r0) and the end (z1, r1)
    of an arc round (center_z, center_r), clockwise as seen with Z to the
    right and X up or not, as [(z, r)] a few degrees apart."""
    radius = math.hypot(z0 - center_z, r0 - center_r)
    start = math.atan2(r0 - center_r, z0 - center_z)
    end = math.atan2(r1 - center_r, z1 - center_z)
    sweep = end - start
    # clockwise is the angle falling
    if clockwise:
        while sweep > 0:
            sweep -= 2 * math.pi
    else:
        while sweep < 0:
            sweep += 2 * math.pi
    steps = max(1, int(math.ceil(abs(sweep) / _ARC_STEP)))
    return [(center_z + radius * math.cos(start + sweep * k / steps),
             center_r + radius * math.sin(start + sweep * k / steps)) for k in range(1, steps)]


def move_points(move: Move):
    """The (z, r) points ``move`` goes through: its ends, and between them,
    for an arc, points a few degrees apart along it."""
    if move.arc is None:
        return [(move.z0, move.r0), (move.z1, move.r1)]
    center = move.arc
    inner = arc_points(move.z0, move.r0, move.z1, move.r1, center.z, center.r, center.clockwise)
    return [(move.z0, move.r0)] + inner + [(move.z1, move.r1)]


def drawn_lines(moves: Iterable[Move]):
    """(feeds, rapids) of ``moves`` as the canvas draws them, DrawnLines:
    the feeds where the nose touches (Move.drawn, when it has one), the
    rapids that go somewhere."""
    feeds, rapids = [], []
    for move in moves:
        z0, r0, z1, r1 = move.drawn or (move.z0, move.r0, move.z1, move.r1)
        if move.feed and move.arc is not None and move.drawn is None:
            # an arc as short lines along it
            points = move_points(move)
            for (az, ar), (bz, br) in zip(points, points[1:]):
                feeds.append(DrawnLine(2 * ar, az, 2 * br, bz, move.pass_no, move.contour))
        elif move.feed:
            feeds.append(DrawnLine(2 * r0, z0, 2 * r1, z1, move.pass_no, move.contour))
        elif (r0, z0) != (r1, z1):
            rapids.append(DrawnLine(2 * r0, z0, 2 * r1, z1))
    return tuple(feeds), tuple(rapids)
