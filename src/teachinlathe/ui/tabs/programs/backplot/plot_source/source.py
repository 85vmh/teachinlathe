"""Where the plot's picture comes from: the machine (MachineSource) or a
simulated run of a program (SimulationSource). Everything drawn - the
toolpath, the stock, the trail, the tool, the material left - is drawn the
same from either: the plot reads a source's ``status`` (a PlotStatus, as
LinuxCNC's renderer reads ``linuxcnc.stat``), its ``trail`` (a Trail, as it
reads a position logger) and the material it says is left, and nothing
else; each poll the source brings them up to date.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Optional, Protocol

from teachinlathe.diagnostics.model import operations
from teachinlathe.diagnostics.model.spans import timed
from teachinlathe.ui.tabs.programs.backplot.plot_source.material import TrailMaterial
from teachinlathe.ui.tabs.programs.backplot.plot_source.status import (
    NO_AXES, MachineConfig, PlotFrame, PlotStatus, _axes)
from teachinlathe.ui.tabs.programs.backplot.plot_source.trail import LoggerTrail, RunTrail, Trail

#: [DISPLAY] GEOMETRY: the axes' letters - X, Y, Z and the parallel U, V, W -
#: and the sign before a letter that turns the axis the other way.
GEOMETRY_LINEAR = "XYZ"
GEOMETRY_PARALLEL = "UVW"
GEOMETRY_REVERSED = "-"

LOG = logging.getLogger(__name__)

#: A run, or a moment, not seen yet.
_UNSEEN = object()


def machine_status():
    """A ``linuxcnc.stat``, polled; the fake one qtvcp has with no machine."""
    import linuxcnc

    stat = linuxcnc.stat()
    try:
        stat.poll()
    except Exception:
        from qtvcp.widgets.fake_status import fakeStatus
        stat = fakeStatus()
    return stat


def _position_logger(linuxcnc, colors, geometry, foam):
    """The machine's position logger: noting how each line it logs is synced
    with the spindle (``sync_points``, a thread's passes) where LinuxCNC can
    (spindle-sync-info), as before where it cannot."""
    if hasattr(linuxcnc, "SPINDLE_SYNC_POSITION"):
        try:
            return linuxcnc.positionlogger(linuxcnc.stat(), *colors, geometry, foam, sync=True)
        except TypeError as exc:
            LOG.warning("backplot: position logger without spindle sync: %s", exc)
    return linuxcnc.positionlogger(linuxcnc.stat(), *colors, geometry, foam)


class PlotSource(ABC):
    """What the plot shows: a ``status``, a ``trail`` and the material left,
    brought up to date by ``poll``. ``mirror``: mirrored or not when the plot
    starts; None, as the operator last left the machine's plot."""

    mirror: Optional[bool] = None

    def __init__(self, thread_plans=None, lifecycle=None):
        from teachinlathe.programs.model.backplot_lifecycle import BackplotLifecycle

        self.status = PlotStatus()
        self.trail: Optional[Trail] = None
        self._thread_plans = thread_plans
        #: when the plot polls, and - a machine's - logs its trail
        #: (programs.model.backplot_lifecycle); the plot attaches to it
        self.lifecycle = lifecycle if lifecycle is not None else BackplotLifecycle(records_trail=False)

    def thread_plan(self, path: str):
        """The threads of program ``path`` (a programs.model.thread_plans
        ThreadPlan), None while they are not known, or it cuts none."""
        return self._thread_plans.get(path) if self._thread_plans is not None and path else None

    @abstractmethod
    def start(self, colors, geometry, foam) -> None:
        """Ready to be polled: ``colors`` the trail's, in COLOR_NAMES' order."""

    @abstractmethod
    def poll(self) -> None:
        """The status and the trail as they are now."""

    def start_logging(self, host) -> None:
        """The trail logged from now (a machine's)."""

    def stop_logging(self, host) -> None:
        """The trail no longer logged; what it has stays."""

    def reset_trail(self) -> None:
        """The trail, and the material cut from it, gone."""

    def shutdown(self) -> None:
        """Nothing left running: the application is closing."""

    @abstractmethod
    def material_left(self, ctx, host):
        """The part as it is being cut - something with ``material`` (a
        simulation.logic.material.Part, mm, in the work coordinates) and ``version``
        - or None with no stock to cut. ``host``: the plot, for the bar it
        holds (``stock``) and the frame the bar is drawn in (``preview_origin``)."""

    @staticmethod
    def _poll_machine(stat) -> bool:
        try:
            stat.poll()
        except Exception:
            return False
        return True


class MachineSource(PlotSource):
    """The machine: its status, and its position logger's trail - each
    point made with the tool in and on the line of the program run when the
    poll after it was logged - and the material left cut from that trail."""

    def __init__(self, thread_plans=None, lifecycle=None):
        from teachinlathe.programs.model.backplot_lifecycle import BackplotLifecycle

        super().__init__(thread_plans, lifecycle if lifecycle is not None else BackplotLifecycle())
        self._stat = None
        self._geometry = ""
        self._material = TrailMaterial()
        # (file, line) of the innermost call -> the file it runs
        self._called_files = {}

    def start(self, colors, geometry, foam):
        """Ready to be polled. The logger is not started here: the lifecycle
        starts it when a program runs (start_logging)."""
        import linuxcnc

        self._stat = machine_status()
        self._geometry = str(geometry or "")
        self.trail = LoggerTrail(lambda: _position_logger(linuxcnc, colors, geometry, foam),
                                 colors, self._tool_tip)
        self._update()

    def poll(self):
        if self._poll_machine(self._stat):
            self._update()
            if self.trail.logging:
                with timed(operations.BACKPLOT_TRAIL_READ):
                    self.trail.refresh(self.status.tool_in_spindle, self._program_line())

    def start_logging(self, host):
        self._poll_machine(self._stat)
        self._update()
        self.trail.start_logging()

    def stop_logging(self, host):
        # the material cut by the points logged so far, before they stop
        # coming: the trail of a run ended stays, and so does what it cut
        self.trail.stop_logging()
        self.trail.refresh(self.status.tool_in_spindle, self._program_line())
        self._consume_material(host)

    def reset_trail(self):
        self.trail.reset()
        self._material.reset()

    def shutdown(self):
        if self.trail is not None:
            self.trail.stop_logging()

    def _tool_tip(self):
        """Where the tool's tip is, (x, y, z, a, b, c) in machine units - as
        the position logger works out its points: the commanded position less
        the tool's offset, each linear axis as the geometry names it (a lathe
        has no rotary one to turn the point by)."""
        stat = self._stat
        if stat is None:
            return None
        try:
            pt = [p - o for p, o in zip(tuple(stat.position)[:9], tuple(stat.tool_offset)[:9])]
        except (AttributeError, TypeError):
            return None
        pt += [0.0] * (9 - len(pt))
        tip, sign = [0.0, 0.0, 0.0], 1.0
        for letter in self._geometry.upper():
            if letter == GEOMETRY_REVERSED:
                sign = -1.0
                continue
            axis = GEOMETRY_LINEAR.find(letter)
            if axis < 0:
                axis = GEOMETRY_PARALLEL.find(letter)
                value = pt[6 + axis] if axis >= 0 else None
            else:
                value = pt[axis]
            if value is not None:
                tip[axis] += sign * value
            sign = 1.0
        return (tip[0], tip[1], tip[2], pt[3], -pt[4], pt[5])

    def _consume_material(self, host):
        if host is None:
            return
        status = self.status
        origin = self._origin(host)
        self._material.material_left(self.trail, status, getattr(host, "stock", None) or {}, origin)

    def _update(self):
        self.status.update(MachineConfig.of(self._stat), PlotFrame.of(self._stat))

    def _program_line(self) -> int:
        """The line of the program being run - 0 inside a subroutine of
        another file, as a tool change's."""
        from teachinlathe.programs.model.program_runtime import parse_call_stack

        stat = self._stat
        line = int(stat.motion_line or 0)
        level = int(getattr(stat, "call_level", 0) or 0)
        if level <= 0:
            return line
        frames = parse_call_stack(getattr(stat, "call_stack", ()))[:level]
        if not frames:
            return 0
        innermost = (frames[-1].filename, frames[-1].line)
        if innermost not in self._called_files:
            from teachinlathe.programs.model.program_stack import ProgramCallStackResolver
            path, _name = ProgramCallStackResolver().resolve_subroutine_from_line(*innermost)
            self._called_files[innermost] = os.path.abspath(path) if path else ""
        called = self._called_files[innermost]
        return line if called and called == os.path.abspath(frames[0].filename) else 0

    def material_left(self, ctx, host):
        status = self.status
        origin = self._origin(host)
        with timed(operations.BACKPLOT_MATERIAL):
            return self._material.material_left(self.trail, status, getattr(host, "stock", None) or {}, origin)

    def clear_live_plot(self, host):
        """Clear the visible machine trail, preserving the material already cut."""
        self.poll()
        status = self.status
        origin = self._origin(host)
        self._material.clear_trace(self.trail, status,
                                  getattr(host, "stock", None) or {}, origin)

    def _origin(self, host):
        """The frame the material is cut in: the preview's (``host``'s
        ``preview_origin``) or, with none, the machine's work offsets now."""
        status = self.status
        return getattr(host, "preview_origin", None) or (
            tuple(status.g5x_offset), tuple(status.g92_offset), float(status.rotation_xy))

    def reset_material(self):
        """Forget cuts when a different program is loaded into the preview."""
        self._material.reset()


class RunPlayback(Protocol):
    """A simulated run as it plays: ``run`` (a ProgramRun, None until it is
    worked out), the moment shown (``played``, a program_run.Moment, or
    None) and the program run (``program_file``)."""
    run: object
    played: object
    program_file: str


class SimulationSource(PlotSource):
    """A simulated run (a RunPlayback) as the machine running it would be.

    What the run does not say is the machine's - its axes, units, tool table,
    homing and limits - read off the machine as the MachineSource reads them.
    The work offset and the tool's offset are as they were when the run was
    worked out from them, moved as the program moves its origin (a Facing's
    new Z0); a tool's offset is the machine's tool table's, as the M6 that
    loads it sets it. While it plays the program is running: the plot does
    not read it again."""

    mirror = True

    def __init__(self, playback: RunPlayback, thread_plans=None, lifecycle=None):
        super().__init__(thread_plans, lifecycle)
        self._playback = playback
        self._machine = None
        self._run = self._moment = _UNSEEN
        self._started = {}                      # the machine's offsets as the run started
        self._left = None

    def start(self, colors, geometry, foam):
        self._machine = machine_status()
        self.trail = RunTrail(colors)
        self.poll()

    def poll(self):
        self._poll_machine(self._machine)
        config = MachineConfig.of(self._machine)
        run, moment = self._playback.run, self._playback.played
        if run is not self._run:
            self._start_run(run, config)
        if moment is self._moment and self.status.frame.file:
            self.status.update(config, self.status.frame)
            return
        self._moment = moment
        if run is None or moment is None:
            self.trail.show(None, 0.0)
            self.status.update(config, self._frame(None, self._machine_tool(), 0, None, config))
            return
        steps = run.program.steps
        step = steps[moment.step] if moment.step < len(steps) else None
        self.trail.show(moment.step, run.fraction(moment.step, moment.time))
        line = step.where.program_line if step is not None else 0
        self.status.update(config, self._frame(self.trail.last(), moment.tool, line, moment.origin, config))
        # a new one only when the material is: the still layer it is drawn in
        # is drawn again for it, and a rapid or a stop cuts nothing
        if self._left is None or self._left.material is not moment.material:
            self._left = _Left(moment.material, moment.time)

    def _start_run(self, run, config):
        """The offsets now, kept for the run, as it was worked out from them."""
        m = self._machine
        self._run, self._moment, self._left = run, _UNSEEN, None
        self._started = {"g5x_offset": _axes(m.g5x_offset), "g92_offset": _axes(m.g92_offset),
                         "g5x_index": int(m.g5x_index), "rotation_xy": float(m.rotation_xy),
                         "tool_offset": _axes(m.tool_offset)}
        g5x, g92 = self._started["g5x_offset"], self._started["g92_offset"]
        self.trail.set_run(run, (g5x[0] + g92[0], g5x[2] + g92[2]), config.linear_units,
                           self._playback.program_file)

    def _machine_tool(self) -> int:
        if self._run is not None and self._run is not _UNSEEN:
            return int(self._run.program.start_tool)
        return int(self._machine.tool_in_spindle or 0)

    def _frame(self, tip, tool, line, origin, config) -> PlotFrame:
        """The machine with its tool's tip at ``tip`` - the trail's point, in
        machine units - tool ``tool`` in, on ``line`` of the program, its work
        origin at ``origin`` (mm (z, r) from the one the run started from;
        None, there)."""
        import linuxcnc

        started = self._started or {"g5x_offset": _axes(self._machine.g5x_offset),
                                    "g92_offset": _axes(self._machine.g92_offset),
                                    "g5x_index": int(self._machine.g5x_index),
                                    "rotation_xy": float(self._machine.rotation_xy),
                                    "tool_offset": _axes(self._machine.tool_offset)}
        offset = self._tool_offset(int(tool), started["tool_offset"], config)
        if tip is None:
            position = _axes(self._machine.actual_position)
        else:
            position = tuple(t + o for t, o in zip(tuple(tip[:3]) + NO_AXES[3:], offset))
        g5x = started["g5x_offset"]
        if origin is not None and (origin.z or origin.r):
            moved = list(g5x)
            moved[0] += origin.r * config.linear_units
            moved[2] += origin.z * config.linear_units
            g5x = tuple(moved)
        return PlotFrame(position=position, joint_position=position, tool=int(tool), tool_offset=offset,
                         file=self._playback.program_file or "", motion_line=int(line), call_level=0,
                         task_mode=linuxcnc.MODE_AUTO, interp_state=linuxcnc.INTERP_READING,
                         g5x_index=started["g5x_index"], g5x_offset=g5x, g92_offset=started["g92_offset"],
                         rotation_xy=started["rotation_xy"])

    @staticmethod
    def _tool_offset(tool, started, config):
        """Tool ``tool``'s offset in the machine's tool table, as
        ``stat.tool_offset`` has one; none for no tool, and the one the run
        started with for a tool the table does not have."""
        if tool <= 0:
            return NO_AXES
        for entry in config.tool_table:
            if int(getattr(entry, "id", -1)) == tool:
                return tuple(float(getattr(entry, axis + "offset", 0.0)) for axis in "xyzabcuvw")
        return started

    def material_left(self, ctx, host):
        return self._left


class _Left:
    """The material at a moment of the run, as a MaterialLeft reads: what
    is left, and something that changes when it does."""

    def __init__(self, material, version):
        self.material = material
        self.version = version
