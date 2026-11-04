"""What the machine says and is told about running a program.

The HAL pins of a program run: whether one is loaded and may be started,
the machine's Cycle Start and Cycle Stop buttons, and whether the program
completed or was aborted. ProgramsViewModel turns these into what the
Programs screen shows.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent


class ProgramsUseCase(QObject):
    #: The machine's Cycle Start button was pressed.
    cycleStartPressed = pyqtSignal()
    programCompletedChanged = pyqtSignal(bool)
    programAborted = pyqtSignal()

    def __init__(self, hal: Optional[TeachInLatheComponent] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._comp = (TeachInLatheComponent() if hal is None else hal).comp
        pins = TeachInLatheComponent
        self._comp.addListener(pins.PinProgramCompleted,
                               lambda _value: self.programCompletedChanged.emit(self.program_completed))
        self._comp.addListener(pins.PinButtonCycleStart, self._on_cycle_start_button)
        self._comp.addListener(pins.PinButtonCycleStop, self._on_cycle_stop_button)
        self._comp.addListener(pins.PinProgramAborted, self._on_program_aborted)

    @property
    def program_completed(self) -> bool:
        return self._pin(TeachInLatheComponent.PinProgramCompleted)

    def set_program_loaded(self, loaded: bool) -> None:
        self._comp.getPin(TeachInLatheComponent.PinProgramLoaded).value = bool(loaded)

    def set_ready_to_run(self, ready: bool) -> None:
        """The machine may only start a program while the operator is looking at it."""
        self._comp.getPin(TeachInLatheComponent.PinIsReadyToRunProgram).value = bool(ready)

    def _on_cycle_start_button(self, _value):
        if self._pin(TeachInLatheComponent.PinButtonCycleStart):
            self.cycleStartPressed.emit()

    def _on_cycle_stop_button(self, _value):
        if self._pin(TeachInLatheComponent.PinButtonCycleStop):
            self.set_program_loaded(False)

    def _on_program_aborted(self, _value):
        if self._pin(TeachInLatheComponent.PinProgramAborted):
            self.programAborted.emit()

    def _pin(self, name) -> bool:
        return bool(self._comp.getPin(name).value)
