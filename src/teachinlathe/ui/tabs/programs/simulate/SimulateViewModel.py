"""The Simulate screen's view model: a G-code file played as the machine would
run it, on its stock. The run itself - its clock, its buttons, where it is -
is a SimulatedRunSource (programs.logic.run), shown as every run is
(``run``, a ProgramRunViewModel): the DRO, the tool box, the timeline, and
the backplot drawn from it as from the machine (plot_source.SimulationSource).
This keeps what only a simulation has: the program's text, reading it
(``loading``, ``error``), Break on M1, Skip Blocks, the rapids through the
material, the operation under way.
"""

import logging
import os

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.programs.logic.run import SimulatedRunSource
from teachinlathe.simulation.logic.program_run import MarkKind
from teachinlathe.ui.tabs.programs.ProgramRunViewModel import ProgramRunViewModel
from teachinlathe.ui.tabs.programs.gcode_viewer.GCodeSyntaxHighlighter import GCodeSyntaxHighlighter

LOG = logging.getLogger(__name__)


class SimulateViewModel(QObject):
    fileChanged = pyqtSignal()
    loadingChanged = pyqtSignal()
    errorChanged = pyqtSignal()
    runChanged = pyqtSignal()
    momentChanged = pyqtSignal()
    optionalStopChanged = pyqtSignal()
    blockDeleteChanged = pyqtSignal()

    def __init__(self, use_case, parent=None):
        """``use_case``: what works the run out (SimulateUseCase)."""
        super().__init__(parent)
        from teachinlathe.ui.tabs.programs.backplot.plot_source import SimulationSource

        self._source = SimulatedRunSource(use_case, self)
        self._run = ProgramRunViewModel(self._source, lambda: SimulationSource(self._source), self)
        self._source.loadingChanged.connect(self.loadingChanged)
        self._source.errorChanged.connect(self.errorChanged)
        self._source.runChanged.connect(self.runChanged)
        self._source.changed.connect(self.momentChanged)
        self._content = ""
        self._highlighter = GCodeSyntaxHighlighter(self)

    def open(self, ngc_path: str, json_path: str = "", optional_stop: bool = False,
             block_delete: bool = False):
        """A simulation of ``ngc_path``: its stock from the conversational
        program at ``json_path``, if any, Break on M1 as on the machine."""
        self._content = _read(ngc_path)
        self._highlighter.set_optional_stop(bool(optional_stop))
        self._highlighter.set_block_delete(bool(block_delete))
        self._source.open(ngc_path, json_path, optional_stop, block_delete)
        self.fileChanged.emit()
        self.optionalStopChanged.emit()
        self.blockDeleteChanged.emit()

    def close(self):
        """Left: nothing goes on playing."""
        self._source.close()

    @pyqtProperty(QObject, constant=True)
    def run(self):
        """The run, as every run is shown (ProgramRunViewModel)."""
        return self._run

    @pyqtSlot(QObject)
    def attachHighlighter(self, quick_document):
        """The code's colours, as the Programs screen's: M1s greyed while
        Break on M1 is off."""
        self._highlighter.attach(quick_document)

    @pyqtSlot(bool)
    def setOptionalStop(self, on):
        """Break on M1: the program read again - an M1's remap takes another
        way with it on - from where it is."""
        on = bool(on)
        if on == self._source.optional_stop:
            return
        self._highlighter.set_optional_stop(on)
        self._source.set_optional_stop(on)
        self.optionalStopChanged.emit()

    @pyqtSlot(bool)
    def setBlockDelete(self, on):
        on = bool(on)
        if on == self._source.block_delete:
            return
        self._highlighter.set_block_delete(on)
        self._source.set_block_delete(on)
        self.blockDeleteChanged.emit()

    # ── what QML reads ───────────────────────────────────────────────────

    @pyqtProperty(str, notify=fileChanged)
    def content(self):
        """The program's text."""
        return self._content

    @pyqtProperty(str, notify=fileChanged)
    def programFile(self):
        """The file run: what the backplot previews."""
        return self._source.program_file

    @pyqtProperty(str, notify=fileChanged)
    def fileName(self):
        return os.path.basename(self._source.program_file)

    @pyqtProperty(bool, notify=loadingChanged)
    def loading(self):
        return self._source.loading

    @pyqtProperty(str, notify=errorChanged)
    def error(self):
        return self._source.error

    @pyqtProperty(bool, notify=runChanged)
    def ready(self):
        return self._source.run is not None

    @pyqtProperty("QVariantList", notify=runChanged)
    def collisions(self):
        """The rapids through the material: {time}."""
        run = self._source.run
        return [{"time": c.time} for c in run.collisions] if run is not None else []

    @pyqtProperty(bool, notify=optionalStopChanged)
    def optionalStop(self):
        return self._source.optional_stop

    @pyqtProperty(bool, notify=blockDeleteChanged)
    def blockDelete(self):
        return self._source.block_delete

    @pyqtProperty(str, notify=momentChanged)
    def operation(self):
        """The operation under way: "Op 3 - Profile Roughing P1", or ""."""
        run, played = self._source.run, self._source.played
        if run is None or played is None:
            return ""
        current = ""
        for mark in run.marks:
            if mark.kind is MarkKind.OPERATION and mark.step <= played.step:
                current = f"Op {mark.number} - {mark.label}"
        return current


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError as error:
        LOG.error("simulation: could not read %s: %s", path, error)
        return ""
