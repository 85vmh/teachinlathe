"""The status the plot draws from: what LinuxCNC's renderer (glcanon) and the
plot read as ``linuxcnc.stat``, every field of it said here - whatever the
plot shows, the machine or a simulation.

It is two parts, each made whole by the source that shows it: the machine's
configuration and state (MachineConfig) - its axes, units, tool table,
homing and limits, which both sources read off the machine - and the moment
shown (PlotFrame) - where the tool is, which tool, which line, the offsets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

#: Nine axes, X Y Z A B C U V W, as linuxcnc.stat has every position.
Axes = Tuple[float, ...]
NO_AXES: Axes = (0.0,) * 9


def _axes(values) -> Axes:
    values = tuple(float(v) for v in (values or ()))
    return values + NO_AXES[len(values):]


@dataclass(frozen=True)
class MachineConfig:
    """What belongs to the machine, not to the program run: its axes, units,
    joints, tool table, and which joints are homed and on a limit."""
    axis: tuple = ()
    axis_mask: int = 0b101
    joints: int = 0
    num_extrajoints: int = 0
    kinematics_type: int = 1
    linear_units: float = 1.0
    angular_units: float = 1.0
    tool_table: tuple = ()
    homed: tuple = ()
    limit: tuple = ()

    @classmethod
    def of(cls, stat) -> "MachineConfig":
        """The machine as a polled ``linuxcnc.stat`` has it."""
        return cls(axis=tuple(stat.axis), axis_mask=int(stat.axis_mask), joints=int(stat.joints),
                   num_extrajoints=int(getattr(stat, "num_extrajoints", 0) or 0),
                   kinematics_type=int(stat.kinematics_type), linear_units=float(stat.linear_units or 1.0),
                   angular_units=float(stat.angular_units or 1.0), tool_table=tuple(stat.tool_table),
                   homed=tuple(stat.homed), limit=tuple(stat.limit))


@dataclass(frozen=True)
class PlotFrame:
    """The moment shown, in machine coordinates and units: where the
    controlled point is (``position``: the tool's tip plus its offset), the
    current loaded tool and its offset, the line run of the file run, and the
    work offset in use. ``task_mode`` and ``interp_state`` say whether a
    program runs: while one does, the plot does not read it again."""
    position: Axes = NO_AXES
    joint_position: Axes = NO_AXES
    tool: int = 0
    tool_offset: Axes = NO_AXES
    file: str = ""
    motion_line: int = 0
    call_level: int = 0
    task_mode: int = 1
    interp_state: int = 1
    motion_mode: int = 0
    current_vel: float = 0.0
    distance_to_go: float = 0.0
    dtg: Axes = NO_AXES
    g5x_index: int = 1
    g5x_offset: Axes = NO_AXES
    g92_offset: Axes = NO_AXES
    rotation_xy: float = 0.0
    g68_active: bool = False
    g68_offset: Axes = NO_AXES
    g68_rotation: tuple = field(default=(1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))

    @classmethod
    def of(cls, stat) -> "PlotFrame":
        """The moment as a polled ``linuxcnc.stat`` has it."""
        return cls(position=_axes(stat.actual_position), joint_position=_axes(stat.joint_actual_position),
                   tool=int(stat.tool_in_spindle or 0), tool_offset=_axes(stat.tool_offset),
                   file=stat.file or "", motion_line=int(stat.motion_line or 0),
                   call_level=int(getattr(stat, "call_level", 0) or 0), task_mode=int(stat.task_mode),
                   interp_state=int(stat.interp_state), motion_mode=int(stat.motion_mode),
                   current_vel=float(stat.current_vel), distance_to_go=float(stat.distance_to_go),
                   dtg=_axes(stat.dtg), g5x_index=int(stat.g5x_index), g5x_offset=_axes(stat.g5x_offset),
                   g92_offset=_axes(stat.g92_offset), rotation_xy=float(stat.rotation_xy),
                   g68_active=bool(getattr(stat, "g68_active", False)),
                   g68_offset=_axes(getattr(stat, "g68_offset", ())),
                   g68_rotation=tuple(getattr(stat, "g68_rotation", ()) or PlotFrame.g68_rotation))


class PlotStatus:
    """``linuxcnc.stat`` as the plot reads it: every field from the machine's
    configuration or the moment shown, none from anywhere else. The source
    showing it brings it up to date (``update``), the two parts swapped in at
    once - the render thread reads it while the GUI thread polls - so
    ``poll`` has nothing to do."""

    def __init__(self, config: MachineConfig = MachineConfig(), frame: PlotFrame = PlotFrame()):
        self._parts = (config, frame)

    def update(self, config: MachineConfig, frame: PlotFrame) -> None:
        self._parts = (config, frame)

    @property
    def config(self) -> MachineConfig:
        return self._parts[0]

    @property
    def frame(self) -> PlotFrame:
        return self._parts[1]

    def poll(self) -> None:
        pass

    # ── the machine ──────────────────────────────────────────────────────

    axis = property(lambda self: self._parts[0].axis)
    axis_mask = property(lambda self: self._parts[0].axis_mask)
    joints = property(lambda self: self._parts[0].joints)
    num_extrajoints = property(lambda self: self._parts[0].num_extrajoints)
    kinematics_type = property(lambda self: self._parts[0].kinematics_type)
    linear_units = property(lambda self: self._parts[0].linear_units)
    angular_units = property(lambda self: self._parts[0].angular_units)
    tool_table = property(lambda self: self._parts[0].tool_table)
    homed = property(lambda self: self._parts[0].homed)
    limit = property(lambda self: self._parts[0].limit)

    # ── the moment ───────────────────────────────────────────────────────

    actual_position = property(lambda self: self._parts[1].position)
    position = property(lambda self: self._parts[1].position)
    joint_actual_position = property(lambda self: self._parts[1].joint_position)
    tool_in_spindle = property(lambda self: self._parts[1].tool)
    tool_offset = property(lambda self: self._parts[1].tool_offset)
    file = property(lambda self: self._parts[1].file)
    motion_line = property(lambda self: self._parts[1].motion_line)
    current_line = property(lambda self: self._parts[1].motion_line)
    call_level = property(lambda self: self._parts[1].call_level)
    task_mode = property(lambda self: self._parts[1].task_mode)
    interp_state = property(lambda self: self._parts[1].interp_state)
    motion_mode = property(lambda self: self._parts[1].motion_mode)
    current_vel = property(lambda self: self._parts[1].current_vel)
    distance_to_go = property(lambda self: self._parts[1].distance_to_go)
    dtg = property(lambda self: self._parts[1].dtg)
    g5x_index = property(lambda self: self._parts[1].g5x_index)
    g5x_offset = property(lambda self: self._parts[1].g5x_offset)
    g92_offset = property(lambda self: self._parts[1].g92_offset)
    rotation_xy = property(lambda self: self._parts[1].rotation_xy)
    g68_active = property(lambda self: self._parts[1].g68_active)
    g68_offset = property(lambda self: self._parts[1].g68_offset)
    g68_rotation = property(lambda self: self._parts[1].g68_rotation)
