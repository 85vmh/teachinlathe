"""A G-code file as the machine would run it: LinuxCNC's own interpreter
(the ``gcode`` module's ``parse``, the same rs274ngc ``Interp`` milltask
runs) over the file, with the machine's INI - its remaps, subroutines,
parameter file and tool table - into a simulation.model.moves.ProgramMoves.

The module does at an M6 what LinuxCNC's task and iocontrol do: the move to
the tool change position (tool_change_move), the new tool's data in the
spindle's slot, the interpreter's position after it (set_position).

``gcode.load_tool_table`` gives the whole process a tool table of its own,
so this is meant for a process of its own - the planning worker - not for
one that reads LinuxCNC's tool data through ``linuxcnc.stat()``.
"""

from __future__ import annotations

import contextlib
import dataclasses
import math
import os
import re
import shutil
import tempfile
from typing import List, Optional, Sequence, Tuple

from teachinlathe.core.ini_repository import IniRepository
from teachinlathe.simulation.model.moves import (
    At, Dwell, Move, MoveKind, OperationStart, OriginShift, ProgramMoves, Spindle, Stop, StopKind, ToolChange,
    Where,
)

#: The canon's lengths are inches, whatever the machine's and the program's units.
MM_PER_INCH = 25.4

#: The heading comment the conversational G-code opens each operation with:
#: (---#01 Facing---).
_OPERATION = re.compile(r"^\s*-+\s*#(\d+)\s+(.*?)\s*-+\s*$")

#: The interpreter's plane codes: G17, G19, G18.
_PLANE_XZ = 3


@dataclasses.dataclass(frozen=True)
class WorkOffset:
    """The work offset in use, as linuxcnc.stat() has it: ``index`` 1 for
    G54 ... 9 for G59.3, the nine ``offsets`` in machine units and the XY
    ``rotation`` in degrees."""
    index: int
    offsets: Tuple[float, ...]
    rotation: float = 0.0


@dataclasses.dataclass(frozen=True)
class MachineState:
    """The machine at cycle start, as linuxcnc.stat() has it: ``position``
    (x, z) in machine coordinates and units - X a radius - the current
    loaded tool's T number (0 for none), the tool offset in effect, (x, z) in machine
    units, None for none (as after G49), and the work offset, None for the
    parameter file's."""
    position: Tuple[float, float]
    current_loaded_tool: int = 0
    tool_offset: Optional[Tuple[float, float]] = None
    work_offset: Optional[WorkOffset] = None


def write_work_offset(parameter_file: str, offset: WorkOffset) -> None:
    """``parameter_file`` - a copy, for a parse - with ``offset`` as the
    work offset in use: a touch-off changes the interpreter's before the
    machine's parameter file is saved. The other systems and the user's
    parameters stay as the copy has them."""
    parameters = {}
    if os.path.exists(parameter_file):
        with open(parameter_file, encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if fields:
                    parameters[int(fields[0])] = fields[1]
    parameters[5220] = str(int(offset.index))
    base = 5200 + 20 * int(offset.index)
    for axis, value in enumerate(offset.offsets, 1):
        parameters[base + axis] = format(value, ".17g")
    parameters[base + 10] = format(offset.rotation, ".17g")
    with open(parameter_file, "w", encoding="utf-8") as handle:
        for number, value in sorted(parameters.items()):
            handle.write(f"{number} {value}\n")


def read_moves(ngc_path: str, ini: IniRepository, optional_stop: bool = False,
               machine: Optional[MachineState] = None) -> ProgramMoves:
    """The program in ``ngc_path`` as the machine of ``ini`` would run it,
    Optional Stop on or not (``optional_stop``: what M66 P0 - Optional Stop
    being on, as custom.hal wires it - reads, so an M1's remap takes its
    branch as the machine would); M6 takes the tool to the INI's
    TOOL_CHANGE_POSITION. ``machine``: the machine at cycle start; None, as
    the interpreter starts on its own. The steps are timed as LinuxCNC's
    preview times them, with the machine's limits from ``ini``."""
    import gcode
    import linuxcnc
    from rs274.program_time import MachineLimits

    gcode.load_tool_table(ini.tool_table_file, _random_toolchanger(ini))
    limits = MachineLimits.from_ini(linuxcnc.ini(ini.ini_path))
    with tempfile.TemporaryDirectory() as scratch, _running_in(ini):
        parameter_file = _parameter_copy(ini, scratch)
        if machine is not None and machine.work_offset is not None:
            write_work_offset(parameter_file, machine.work_offset)
        canon = _Canon(parameter_file, optional_stop, _metric(ini), machine, limits)
        result, line = gcode.parse(ngc_path, canon, "G21" if _metric(ini) else "G20",
                                   ini.find("RS274NGC", "RS274NGC_STARTUP_CODE") or "")
    error = f"line {line}: {gcode.strerror(result)}" if result > gcode.MIN_ERROR else ""
    return ProgramMoves(canon.timed_steps(), error, canon.start, canon.time_flags, canon.start_tool,
                        canon.start_work_offset)


def _metric(ini: IniRepository) -> bool:
    return (ini.find("TRAJ", "LINEAR_UNITS") or "mm").strip().lower() in ("mm", "metric")


def _random_toolchanger(ini: IniRepository) -> bool:
    return (ini.find("EMCIO", "RANDOM_TOOLCHANGER") or "0").strip() == "1"


def _parameter_copy(ini: IniRepository, scratch: str) -> str:
    """A copy of the parameter file for the parse: the interpreter writes it
    when it ends, and the machine's own must not change."""
    source = ini.file_path("RS274NGC", "PARAMETER_FILE")
    copy = os.path.join(scratch, os.path.basename(source or "linuxcnc.var"))
    if source and os.path.exists(source):
        shutil.copy(source, copy)
    return copy


@contextlib.contextmanager
def _running_in(ini: IniRepository):
    """As LinuxCNC runs: INI_FILE_NAME the INI - where the interpreter reads
    its remaps from - and the INI's folder the working directory, which its
    relative paths are from."""
    old_ini, old_dir = os.environ.get("INI_FILE_NAME"), os.getcwd()
    os.environ["INI_FILE_NAME"] = ini.ini_path
    try:
        os.chdir(ini.config_dir)
        yield
    finally:
        os.chdir(old_dir)
        if old_ini is None:
            os.environ.pop("INI_FILE_NAME", None)
        else:
            os.environ["INI_FILE_NAME"] = old_ini


def _mm(value: float) -> float:
    return value * MM_PER_INCH


class _Canon:
    """What the interpreter calls (the gcode module's callback protocol),
    made into the steps of a ProgramMoves."""

    def __init__(self, parameter_file: str, optional_stop: bool, metric: bool,
                 machine: Optional["MachineState"], limits):
        self.parameter_file = parameter_file
        self.steps: List = []
        self.start: Optional[At] = None
        self.time_flags: Tuple[str, ...] = ()
        # for each timed event delivered, in order, the step it made, or None
        self._timed: List[Optional[int]] = []
        self._times: Optional[Sequence[float]] = None
        self._machine = machine
        self._limits = limits
        self._optional_stop = optional_stop
        self._machine_mm = 1.0 if metric else MM_PER_INCH
        self._where = Where("", 0, 0, 0)
        self._plane = _PLANE_XZ
        self._at: Optional[At] = None
        # the current loaded tool: the machine's at cycle start
        self._tool = self.start_tool = int(machine.current_loaded_tool or 0) if machine is not None else 0
        self._spindle = Spindle()
        # the work offset (G5x + G92), (x, z) in mm: as at cycle start, and now
        self._g5x = self._g92 = (0.0, 0.0)
        self._origin_at_start: Optional[Tuple[float, float]] = None
        # where the origin is now, from cycle start's, and in which work
        # offset: the last OriginShift's
        self._origin = At(0.0, 0.0)
        self._g5x_index = self._shown_index = self.start_work_offset = 1

    # ── what the interpreter asks ────────────────────────────────────────

    def get_tool_change_position(self):
        # None: the INI's TOOL_CHANGE_POSITION, as task has it without the pins
        return None

    def get_initial_position(self):
        if self._machine is None:
            return None
        x, z = self._machine.position
        return (x, 0.0, z, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    def get_tool_in_spindle(self):
        return None if self._machine is None else self._machine.current_loaded_tool

    def get_tool_offset(self):
        if self._machine is None or self._machine.tool_offset is None:
            return None
        x, z = self._machine.tool_offset
        return (x, 0.0, z, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    def machine_limits(self):
        return self._limits

    def set_move_times(self, times):
        self._times = list(times)

    def set_time_flags(self, flags):
        self.time_flags = tuple(flags)

    def timed_steps(self) -> tuple:
        """The steps, each timed one with when it ends."""
        steps = list(self.steps)
        if self._times is not None and len(self._times) == len(self._timed):
            for index, ends_at in zip(self._timed, self._times):
                if index is not None:
                    steps[index] = dataclasses.replace(steps[index], ends_at=ends_at)
        return tuple(steps)

    def get_external_length_units(self):
        # the machine's units, as linuxcnc.stat().linear_units has them: a mm is 1
        return 1.0 / self._machine_mm

    def get_external_angular_units(self):
        return 1.0

    def get_axis_mask(self):
        return 0b101                # X and Z

    def get_block_delete(self):
        return False

    def check_abort(self):
        return False

    def get_digital_input(self, index, default):
        # motion.digital-in-00 is halui.program.optional-stop.is-on (custom.hal)
        return int(self._optional_stop) if index == 0 else default

    def get_analog_input(self, index, default):
        return default

    def wait(self, index, input_type, wait_type, timeout):
        return 0

    # ── the line, the modes ──────────────────────────────────────────────

    def next_line(self, state):
        pass

    def source_line(self, filename, line, call_level):
        program_line = line if call_level == 0 else self._where.program_line
        self._where = Where(filename, line, call_level, program_line)

    def set_plane(self, plane):
        self._plane = plane

    def set_feed_rate(self, rate):
        self._set_spindle(feed=_mm(rate))

    def set_feed_mode(self, per_rev):
        self._set_spindle(per_rev=bool(per_rev))

    def set_spindle_speed(self, speed):
        self._set_spindle(speed=speed)

    def set_spindle_mode(self, css_max):
        self._set_spindle(css_max=math.inf if css_max >= 1e29 else css_max)

    def set_spindle_sync(self, units_per_rev):
        self._set_spindle(sync_pitch=_mm(units_per_rev))

    def spindle_on(self, direction):
        self._set_spindle(turning=1 if direction > 0 else -1)

    def spindle_off(self):
        self._set_spindle(turning=0)

    def _set_spindle(self, **changes):
        self._spindle = Spindle(**{**self._spindle.__dict__, **changes})

    def set_traverse_rate(self, rate):
        pass

    def set_xy_rotation(self, degrees):
        pass

    def set_g68_frame(self, *frame):
        pass

    def user_defined_function(self, number, p, q):
        pass

    def message(self, text):
        pass

    def comment(self, text):
        found = _OPERATION.search(text)
        if found:
            self.steps.append(OperationStart(int(found.group(1)), found.group(2), self._where))

    # ── the offsets, the point the next move starts from ────────────────

    def set_g5x_offset(self, index, x, y, z, *rest):
        self._g5x = (_mm(x), _mm(z))
        self._g5x_index = int(index)
        self._origin_moved()

    def set_g92_offset(self, x, y, z, *rest):
        self._g92 = (_mm(x), _mm(z))
        self._origin_moved()

    def _origin_moved(self):
        # once the program is under way: before it, the origin is cycle start's
        if self._origin_at_start is not None:
            x0, z0 = self._origin_at_start
            origin = At(self._g5x[1] + self._g92[1] - z0, self._g5x[0] + self._g92[0] - x0)
            if (origin, self._g5x_index) != (self._origin, self._shown_index):
                self._origin, self._shown_index = origin, self._g5x_index
                self.steps.append(OriginShift(origin, self._where, self._g5x_index))

    def _work(self, x: float, z: float) -> At:
        """The point (x, z) of the program - inches, X a radius - in the work
        coordinates of cycle start: a G10 L20 or a G92 later in the program
        moves its coordinates, not the part."""
        origin = (self._g5x[0] + self._g92[0], self._g5x[1] + self._g92[1])
        if self._origin_at_start is None:
            self._origin_at_start = origin
            self.start_work_offset = self._shown_index = self._g5x_index
        return At(_mm(z) + origin[1] - self._origin_at_start[1], _mm(x) + origin[0] - self._origin_at_start[0])

    def tool_offset(self, *offsets):
        pass

    def set_position(self, x, y, z, *rest):
        # where the interpreter is now with no move there: the machine at
        # cycle start, a new tool's offset, the position after an M6
        self._at = self._work(x, z)
        if self.start is None:
            self.start = self._at

    # ── the moves ────────────────────────────────────────────────────────

    def straight_traverse(self, x, y, z, *rest):
        self._move(MoveKind.RAPID, self._work(x, z))

    def straight_feed(self, x, y, z, *rest):
        self._move(MoveKind.FEED, self._work(x, z))

    def straight_probe(self, x, y, z, *rest):
        self._move(MoveKind.FEED, self._work(x, z))

    def rigid_tap(self, x, y, z):
        # in to the point and back out where it started, as G33.1 does
        start = self._at
        self._move(MoveKind.FEED, self._work(x, z))
        if start is not None:
            self._move(MoveKind.FEED, start)

    def arc_feed(self, first_end, second_end, first_axis, second_axis, rotation, axis_end, *rest):
        if self._plane != _PLANE_XZ:
            self._timed.append(None)
            return
        # in the XZ plane the first is Z and the second X; turning counter-
        # clockwise in (Z, X) is G3
        end = self._work(second_end, first_end)
        center = self._work(second_axis, first_axis)
        self._move(MoveKind.ARC, end, center=center, ccw=rotation > 0)

    def dwell(self, seconds):
        self._timed.append(len(self.steps))
        self.steps.append(Dwell(seconds, self._where))

    def _move(self, kind: MoveKind, end: At, center: Optional[At] = None, ccw: bool = False):
        if self._at is not None:
            self._timed.append(len(self.steps))
            self.steps.append(Move(kind, self._at, end, self._tool, self._spindle, self._where, center, ccw))
        else:
            self._timed.append(None)
            if self.start is None:
                self.start = end
        self._at = end

    # ── the tool change and the stops ────────────────────────────────────

    def tool_change_move(self, x, y, z, *rest):
        # to the tool change position, as task makes it at an M6
        self._move(MoveKind.TOOL_CHANGE, self._work(x, z))

    def change_tool(self, tool):
        self._tool = tool
        self._timed.append(len(self.steps))
        self.steps.append(ToolChange(tool, self._where))

    def program_stop(self):
        self.steps.append(Stop(StopKind.PROGRAM_STOP, self._where))

    def optional_program_stop(self):
        self.steps.append(Stop(StopKind.OPTIONAL_STOP, self._where))

    def program_end(self):
        self.steps.append(Stop(StopKind.PROGRAM_END, self._where))
