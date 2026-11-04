"""The machine running the program loaded, as a ProgramRunSource: its state
and buttons (ProgramsActionSource), where it is (Positions), the line and
the tool (ProgramRuntimeStore), the spindle's real speed (the HAL pin), and
the next tool and the time from LinuxCNC's estimate (ToolChangesUseCase).
"""

from __future__ import annotations

from typing import Optional

import linuxcnc

from teachinlathe.programs.logic.run.run_source import ProgramRunSource
from teachinlathe.programs.model.run_moment import MotionReadout, RunMoment, RunState

#: X is a radius in LinuxCNC, a diameter on a lathe's DRO.
DIAMETER = 2.0


class MachineRunSource(ProgramRunSource):

    def __init__(self, runtime_store, actions, tool_changes, parent=None, positions=None, component=None):
        """``runtime_store``: the machine's status (ProgramRuntimeStore);
        ``actions``: its buttons (ProgramsActionSource); ``tool_changes``:
        the program loaded's tool changes (ToolChangesUseCase)."""
        super().__init__(parent)
        self._runtime_store = runtime_store
        self._actions = actions
        self._tool_changes = tool_changes
        self._moment: Optional[RunMoment] = None
        self._actual_rpm = 0.0

        if positions is None:
            from teachinlathe.core.positions_repository import Positions
            positions = Positions()
        self._positions = positions
        self._positions.notify(lambda *_args: self._changed())

        from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
        component = TeachInLatheComponent() if component is None else component
        component.comp.addListener(TeachInLatheComponent.PinSpindleActualRpm, self._on_actual_rpm)

        runtime_store.snapshotChanged.connect(lambda _snapshot: self._changed())
        actions.stateChanged.connect(self._changed)
        tool_changes.changed.connect(self._on_tool_changes)

    # ── the run ──────────────────────────────────────────────────────────

    @property
    def state(self):
        if not self._actions.isActive:
            return RunState.IDLE
        return RunState.HELD if self._runtime_store.snapshot.paused else RunState.RUNNING

    @property
    def moment(self):
        if self._moment is None:
            self._moment = self._read_moment()
        return self._moment

    @property
    def duration(self):
        return self._tool_changes.duration()

    def cycle_start(self):
        self._actions.triggerCycleStart()

    def feed_hold(self):
        self._actions.triggerPauseResume()

    def cycle_stop(self):
        self._actions.triggerStop()

    # ── where it is ──────────────────────────────────────────────────────

    def _read_moment(self) -> RunMoment:
        snapshot = self._runtime_store.snapshot
        x, z = self._positions.getXPosition(), self._positions.getZPosition()
        tool = int(snapshot.current_loaded_tool or 0)
        return RunMoment(x=x.g5xPosition * DIAMETER, z=z.g5xPosition,
                         x_to_go=x.distanceToGo * DIAMETER, z_to_go=z.distanceToGo,
                         work_offset=self._positions.work_offset(), program_line=_program_line(snapshot),
                         tool=tool, next_tool=self._tool_changes.next_tool(tool),
                         motion=self._motion(snapshot), time=self._tool_changes.time())

    def _motion(self, snapshot) -> MotionReadout:
        motion_type = int(snapshot.motion_type or 0)
        rapid = motion_type == linuxcnc.MOTION_TYPE_TRAVERSE
        per_minute = float(snapshot.current_vel or 0.0) * 60.0
        if rapid:
            feed, override = per_minute, snapshot.rapidrate
        else:
            override = snapshot.feedrate
            moving = motion_type in (linuxcnc.MOTION_TYPE_FEED, linuxcnc.MOTION_TYPE_ARC)
            if moving and self._actual_rpm > 0:
                feed = per_minute / self._actual_rpm
            else:
                settings = tuple(snapshot.interpreter_settings or ())
                feed = float(settings[1] or 0.0) if len(settings) > 1 else 0.0
        return MotionReadout(rapid=rapid, feed=feed, per_rev=not rapid, feed_override=_ratio(override),
                             rpm=self._actual_rpm, spindle_override=_ratio(snapshot.spindle_override))

    # ── what changes it ──────────────────────────────────────────────────

    def _changed(self):
        self._moment = None
        self.changed.emit()

    def _on_tool_changes(self):
        self._changed()
        self.runChanged.emit()

    def _on_actual_rpm(self, value):
        try:
            rpm = abs(float(value or 0.0))
        except (TypeError, ValueError):
            rpm = 0.0
        if int(round(rpm)) == int(round(self._actual_rpm)):
            return
        self._actual_rpm = rpm
        self._changed()


def _program_line(snapshot) -> int:
    """The line of the program being run: inside a subroutine, the call's."""
    if snapshot.call_level > 0 and snapshot.call_stack:
        return int(snapshot.call_stack[0].line or 0)
    return int(snapshot.motion_line or 0)


def _ratio(value) -> float:
    """An override as a ratio, 1.0 when there is none."""
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return 1.0
    return ratio if ratio > 0 else 1.0
