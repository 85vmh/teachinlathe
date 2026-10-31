"""A program run, behind one interface whatever runs it: the machine
(MachineRunSource) or a simulation of it (SimulatedRunSource). The Programs
screens show a run - its state, where it is, its tool, feed and spindle, its
time - and drive it through this, never knowing which it is.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from teachinlathe.programs.model.run_moment import NO_MARKS, RunMark, RunMoment, RunState


class _QABCMeta(type(QObject), ABCMeta):
    """A QObject's metaclass and an ABC's at once: a QObject with abstract
    methods it cannot be made without."""


class ProgramRunSource(QObject, metaclass=_QABCMeta):
    """A program run. ``changed``: its state or the moment may be other
    than they were; ``runChanged``: what it runs - its duration, its marks.

    The machine's buttons drive it (``cycle_start``, ``feed_hold`` - Feed
    Resume when held - ``cycle_stop``). A run that can be moved in
    (``seekable``) is moved by ``seek`` and ``seek_to_line``, and played at
    one of its ``speeds``; one that cannot ignores them."""

    changed = pyqtSignal()
    runChanged = pyqtSignal()

    @property
    @abstractmethod
    def state(self) -> RunState:
        """Running, held, waiting at a stop, ..."""

    @property
    @abstractmethod
    def moment(self) -> RunMoment:
        """Where the run is now."""

    @property
    @abstractmethod
    def duration(self) -> Optional[float]:
        """How long it runs, seconds; None, not known."""

    @property
    def marks(self) -> Tuple[RunMark, ...]:
        """The moments along it a seek bar shows."""
        return NO_MARKS

    @property
    def waiting_for(self) -> str:
        """"M0" or "M1" while it waits there for Cycle Start, else ""."""
        return ""

    @abstractmethod
    def cycle_start(self) -> None:
        """Cycle Start: runs it, or goes on from a stop."""

    @abstractmethod
    def feed_hold(self) -> None:
        """Feed Hold; Feed Resume when held."""

    @abstractmethod
    def cycle_stop(self) -> None:
        """Ends the run."""

    # ── moving in it ─────────────────────────────────────────────────────

    seekable = False
    speeds: Tuple[float, ...] = ()

    @property
    def speed(self) -> float:
        """How fast it plays, times the machine's speed."""
        return 1.0

    def set_speed(self, speed: float) -> None:
        pass

    def seek(self, time: float) -> None:
        pass

    def seek_to_line(self, line: int) -> None:
        pass
