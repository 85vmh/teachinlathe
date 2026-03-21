import ast
import os
from dataclasses import dataclass, field

import linuxcnc
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from qtpyvcp.plugins import getPlugin


@dataclass(frozen=True)
class ProgramExecutionFrame:
    filename: str
    line: int
    subname: str = ''


@dataclass(frozen=True)
class ProgramRuntimeSnapshot:
    machine_file: str = ''
    motion_line: int = 0
    call_level: int = 0
    call_stack: tuple[ProgramExecutionFrame, ...] = field(default_factory=tuple)
    state: int = 0
    paused: bool = False
    task_mode: int = 0
    tool_in_spindle: int = 0
    tool_offset: tuple = field(default_factory=tuple)
    actual_position: tuple = field(default_factory=tuple)
    joint_actual_position: tuple = field(default_factory=tuple)
    homed: tuple = field(default_factory=tuple)
    g5x_offset: tuple = field(default_factory=tuple)
    g92_offset: tuple = field(default_factory=tuple)
    limit: tuple = field(default_factory=tuple)
    motion_mode: int = 0
    current_vel: float = 0.0
    linear_units: int = 0

    @property
    def preview_tool_signature(self):
        return self.tool_in_spindle, self.tool_offset


STATUS = getPlugin('status')


class ProgramRuntimeStore(QObject):
    snapshotChanged = pyqtSignal(object)
    machineFileChanged = pyqtSignal(str)
    motionLineChanged = pyqtSignal(int)
    callLevelChanged = pyqtSignal(int)
    callStackChanged = pyqtSignal(object)

    def __init__(self, parent=None, poll_interval_ms=150):
        super().__init__(parent)
        self._stat = linuxcnc.stat()
        self._snapshot = ProgramRuntimeSnapshot()

        self._timer = QTimer(self)
        self._timer.setInterval(poll_interval_ms)
        self._timer.timeout.connect(self.poll)
        self._timer.start()

        self.poll()

    @property
    def stat(self):
        return self._stat

    @property
    def snapshot(self):
        return self._snapshot

    def poll(self):
        try:
            self._stat.poll()
        except Exception:
            return self._snapshot

        next_snapshot = self._build_snapshot(self._stat)
        previous_snapshot = self._snapshot
        if next_snapshot == previous_snapshot:
            return next_snapshot

        self._snapshot = next_snapshot
        if next_snapshot.machine_file != previous_snapshot.machine_file:
            self.machineFileChanged.emit(next_snapshot.machine_file)
        if next_snapshot.motion_line != previous_snapshot.motion_line:
            self.motionLineChanged.emit(next_snapshot.motion_line)
        if next_snapshot.call_level != previous_snapshot.call_level:
            self.callLevelChanged.emit(next_snapshot.call_level)
        if next_snapshot.call_stack != previous_snapshot.call_stack:
            self.callStackChanged.emit(next_snapshot.call_stack)
        self.snapshotChanged.emit(next_snapshot)
        return next_snapshot

    def _build_snapshot(self, stat):
        status_file = getattr(getattr(STATUS, 'file', None), 'value', '') or ''
        status_motion_line = getattr(getattr(STATUS, 'motion_line', None), 'value', 0)

        machine_file_value = status_file or getattr(stat, 'file', '') or ''
        machine_file = os.path.abspath(machine_file_value) if machine_file_value else ''
        motion_line_value = status_motion_line if status_motion_line is not None else getattr(stat, 'motion_line', 0)

        return ProgramRuntimeSnapshot(
            machine_file=machine_file,
            motion_line=int(motion_line_value or 0),
            call_level=int(getattr(stat, 'call_level', 0) or 0),
            call_stack=self._parse_call_stack(getattr(stat, 'call_stack', ())),
            state=int(getattr(stat, 'state', 0) or 0),
            paused=bool(getattr(stat, 'paused', False)),
            task_mode=int(getattr(stat, 'task_mode', 0) or 0),
            tool_in_spindle=int(getattr(stat, 'tool_in_spindle', 0) or 0),
            tool_offset=tuple(getattr(stat, 'tool_offset', ()) or ()),
            actual_position=tuple(getattr(stat, 'actual_position', ()) or ()),
            joint_actual_position=tuple(getattr(stat, 'joint_actual_position', ()) or ()),
            homed=tuple(getattr(stat, 'homed', ()) or ()),
            g5x_offset=tuple(getattr(stat, 'g5x_offset', ()) or ()),
            g92_offset=tuple(getattr(stat, 'g92_offset', ()) or ()),
            limit=tuple(getattr(stat, 'limit', ()) or ()),
            motion_mode=int(getattr(stat, 'motion_mode', 0) or 0),
            current_vel=float(getattr(stat, 'current_vel', 0.0) or 0.0),
            linear_units=int(getattr(stat, 'linear_units', 0) or 0),
        )

    def _parse_call_stack(self, raw_stack):
        if not raw_stack:
            return ()

        if isinstance(raw_stack, str):
            try:
                raw_stack = ast.literal_eval(raw_stack)
            except Exception:
                return ()

        if isinstance(raw_stack, dict):
            raw_stack = [raw_stack]

        if not isinstance(raw_stack, (list, tuple)):
            return ()

        frames = []
        for entry in raw_stack:
            if not isinstance(entry, dict):
                continue
            filename = os.path.abspath(str(entry.get('filename') or '')) if entry.get('filename') else ''
            if not filename:
                continue
            try:
                line_number = int(entry.get('line') or 0)
            except (TypeError, ValueError):
                line_number = 0
            frames.append(ProgramExecutionFrame(
                filename=filename,
                line=line_number,
                subname=str(entry.get('subname') or ''),
            ))
        return tuple(frames)
