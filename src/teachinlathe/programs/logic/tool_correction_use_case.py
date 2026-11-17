"""A correction of the current loaded tool at an M1 (subroutines/m1_remap.ngc).

While the program waits at the M1 the operator measures the part and may arm
a correction: the HAL pins say what it is, and the remap reads them after
Cycle Start and writes it into the tool's offsets with G10 L1 - LinuxCNC
writes tool.tbl, and the Tool Library follows it through its watcher. Nothing
here writes the tool table: while a program is paused in AUTO, LinuxCNC
refuses it.

The pins are armed (``correction-x``, ``correction-z``, then
``correction-apply``) only while the machine waits at an M1 with a tool
loaded, and cleared - so that a correction never carries over to another
stop - when the remap says it applied it (``correction-applied``), when it
has read them (``at-stop`` off), at the next M1, and when the program ends or
is aborted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.programs.model.run_moment import RunState
from teachinlathe.programs.model.tool_correction import ToolCorrection, check, corrected_offsets

Offsets = Tuple[float, float]   # X (a radius, as LinuxCNC keeps it), Z


@dataclass(frozen=True)
class ArmedCorrection:
    tool: int
    correction: ToolCorrection
    #: the tool's offsets when it was armed: None, not in the Tool Library
    offsets: Optional[Offsets]


class ToolCorrectionUseCase(QObject):
    #: Whether a correction can be armed, the one armed, the one applied.
    changed = pyqtSignal()
    #: The remap applied the armed correction (ArmedCorrection).
    applied = pyqtSignal(object)

    def __init__(self, run_source, tools=None, hal: Optional[TeachInLatheComponent] = None,
                 parent: Optional[QObject] = None) -> None:
        """``run_source``: the machine's run (MachineRunSource) - never a
        simulation's: there the correction is not offered; ``tools``: the
        Tool Library (ToolLibraryRepository), for the tool's offsets."""
        super().__init__(parent)
        self._run = run_source
        if tools is None:
            from teachinlathe.core.tool_library_repository import tool_library_repository
            tools = tool_library_repository()
        self._tools = tools
        self._comp = (TeachInLatheComponent() if hal is None else hal).comp
        self._armed: Optional[ArmedCorrection] = None
        # armed, and read by the remap (at-stop off): applied-pin may come
        # after at-stop, or before it, in the same poll of the pins
        self._sent: Optional[ArmedCorrection] = None
        self._applied: Optional[ArmedCorrection] = None
        self._available = self._read_available()

        pins = TeachInLatheComponent
        self._comp.addListener(pins.PinInspectCorrectionApplied, self._on_applied_pin)
        self._comp.addListener(pins.PinInspectAtStop, self._on_at_stop_pin)
        run_source.changed.connect(self._on_run_changed)
        tools.toolsChanged.connect(self.changed)
        self._clear_pins()

    # ── what it shows ────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """At an M1, with a tool loaded: a correction can be armed."""
        return self._available

    @property
    def tool(self) -> int:
        """The current loaded tool, 0 for none."""
        return int(self._run.moment.tool or 0)

    @property
    def armed(self) -> Optional[ArmedCorrection]:
        return self._armed

    @property
    def last_applied(self) -> Optional[ArmedCorrection]:
        """The correction the remap applied at this stop, None before."""
        return self._applied

    def offsets(self, tool: int) -> Optional[Offsets]:
        """The tool's offsets as the tool table has them now; None, a tool
        the Tool Library does not know."""
        holder = self._tools.find_holder(tool)
        if holder is None:
            return None
        return float(holder.x_offset or 0.0), float(holder.z_offset or 0.0)

    def expected_offsets(self, tool: int, correction: ToolCorrection) -> Optional[Offsets]:
        """The tool's offsets once ``correction`` is applied."""
        offsets = self.offsets(tool)
        return None if offsets is None else corrected_offsets(offsets[0], offsets[1], correction)

    # ── what the operator does ───────────────────────────────────────────

    def arm(self, correction: ToolCorrection) -> str:
        """Arm ``correction`` for Cycle Start; why it cannot be, "" when armed."""
        if not self._available:
            return "A tool correction is only possible while the program waits at an M1"
        error = check(correction)
        if error:
            return error
        tool = self.tool
        pins = TeachInLatheComponent
        # the values first: the remap reads apply, then them
        self._set(pins.PinInspectCorrectionX, float(correction.dx))
        self._set(pins.PinInspectCorrectionZ, float(correction.dz))
        self._set(pins.PinInspectCorrectionApply, True)
        self._armed = ArmedCorrection(tool, correction, self.offsets(tool))
        self.changed.emit()
        return ""

    def disarm(self) -> None:
        """Cycle Start goes on without a correction."""
        self._clear_pins()
        if self._armed is not None:
            self._armed = None
            self.changed.emit()

    # ── what the machine does ────────────────────────────────────────────

    def _on_applied_pin(self, value) -> None:
        if not value:
            return
        applied = self._armed or self._sent
        self._clear_pins()
        self._armed = self._sent = None
        if applied is not None:
            self._applied = applied
            self.applied.emit(applied)
        self.changed.emit()

    def _on_at_stop_pin(self, value) -> None:
        # on: a new M1 - nothing armed yet, nothing applied at it yet;
        # off: the remap has read the pins
        if value:
            self._applied = None
            self._sent = None
        else:
            self._sent = self._armed
        self._clear_pins()
        self._armed = None
        self.changed.emit()

    def _on_run_changed(self) -> None:
        changed = False
        if self._run.state is RunState.IDLE and (self._armed or self._sent or self._applied):
            # ended or aborted: nothing carries over to the next run
            self._armed = self._sent = self._applied = None
            self._clear_pins()
            changed = True
        available = self._read_available()
        if available != self._available:
            self._available = available
            changed = True
        if changed:
            self.changed.emit()

    def _read_available(self) -> bool:
        return (self._run.state is RunState.WAITING and self._run.waiting_for == "M1"
                and self.tool > 0)

    def _clear_pins(self) -> None:
        pins = TeachInLatheComponent
        self._set(pins.PinInspectCorrectionApply, False)
        self._set(pins.PinInspectCorrectionX, 0.0)
        self._set(pins.PinInspectCorrectionZ, 0.0)

    def _set(self, name, value) -> None:
        self._comp.getPin(name).value = value
