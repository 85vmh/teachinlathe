"""Axis positions in the three frames the UI shows.

The arithmetic is the same one every LinuxCNC front-end does, stated once here:

* **abs** - the machine position, straight off the status channel. Actual or
  commanded, per ``[DISPLAY] POSITION_FEEDBACK``.
* **rel** - the same point in the current work coordinate system: the machine
  position less the G5x origin and the tool offset, rotated by ``G10 L2 R`` if
  the plane is rotated, then less the G92 offset.
* **dtg** - what the status channel reports as remaining on the current move.

All three are converted to the program's units when G20/G21 disagrees with the
machine's native unit, so the numbers match the G-code the operator is reading.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal

from .ini_repository import ini_repository
from .status_repository import status_repository

#: Millimetres, as ``stat.program_units`` and ``[TRAJ] LINEAR_UNITS`` spell it.
UNITS_METRIC = 2
MM_PER_INCH = 25.4


class Axis(IntEnum):
    """Index of an axis into a nine-axis position tuple."""

    ALL = -1
    X, Y, Z, A, B, C, U, V, W = range(9)


@dataclass
class Position:
    """The different reference frames of a single axis position.

    ``g5xPosition`` is the position in the current work coordinate system
    (G54..G59.3) and already accounts for the G92 offset and the tool offset.
    """

    machinePosition: float
    g5xPosition: float
    distanceToGo: float

    @property
    def offset(self) -> float:
        """Offset of the current WCS origin in machine coordinates.

        Equals ``g5x_offset + g92_offset + tool_offset`` for the axis, i.e.
        the amount that maps a machine coordinate to a work coordinate.
        """
        return self.machinePosition - self.g5xPosition


class Positions(QObject):
    """Axis positions, recomputed on every status poll."""

    #: Carries the work-coordinate (rel) tuple, so a slot can take it or not.
    positionsChanged = pyqtSignal(object)

    def __init__(self, parent: Optional[QObject] = None,
                 status=None, ini=None) -> None:
        super().__init__(parent)
        self._ini = ini_repository() if ini is None else ini
        self._status = status_repository() if status is None else status
        self._stat = self._status.stat

        self._report_actual = self._ini.position_feedback_is_actual
        self._axis_numbers = self._ini.axis_numbers
        self._machine_units = UNITS_METRIC if self._ini.is_metric else 1

        self._abs = (0.0,) * 9
        self._rel = (0.0,) * 9
        self._dtg = (0.0,) * 9

        self._status.polled.connect(self._update)
        self._update()

    # -- the three frames -------------------------------------------------

    @property
    def abs(self) -> tuple:
        return self._abs

    @property
    def rel(self) -> tuple:
        return self._rel

    @property
    def dtg(self) -> tuple:
        return self._dtg

    def getXPosition(self) -> Position:
        return self._getAxisPosition(Axis.X)

    def getZPosition(self) -> Position:
        return self._getAxisPosition(Axis.Z)

    def _getAxisPosition(self, anum) -> Position:
        return Position(
            machinePosition=self._abs[anum],
            g5xPosition=self._rel[anum],
            distanceToGo=self._dtg[anum],
        )

    def teachInX(self, machineCoordinate: bool = False) -> float:
        """Current X position to teach into a field.

        Returns the work-coordinate (current G5x WCS) value by default, or the
        machine-coordinate value when *machineCoordinate* is True. The value is
        in radius (the lathe diameter doubling is a display concern applied by
        the caller).
        """
        pos = self.getXPosition()
        return pos.machinePosition if machineCoordinate else pos.g5xPosition

    def teachInZ(self, machineCoordinate: bool = False) -> float:
        """Current Z position to teach into a field (work coordinate by
        default, machine coordinate when *machineCoordinate* is True)."""
        pos = self.getZPosition()
        return pos.machinePosition if machineCoordinate else pos.g5xPosition

    def notify(self, callback: Callable) -> None:
        """Register *callback* to be invoked whenever the positions update.

        Connected directly, so Qt drops the argument for a callback that takes
        none and passes the work-coordinate tuple to one that takes it.
        """
        self.positionsChanged.connect(callback)

    # -- the arithmetic ---------------------------------------------------

    def _update(self) -> None:
        stat = self._stat
        pos = stat.actual_position if self._report_actual else stat.position
        dtg = stat.dtg
        g5x_offset = stat.g5x_offset
        g92_offset = stat.g92_offset
        tool_offset = stat.tool_offset

        rel = [0.0] * 9
        for anum in self._axis_numbers:
            rel[anum] = pos[anum] - g5x_offset[anum] - tool_offset[anum]

        if stat.rotation_xy != 0:
            angle = math.radians(-stat.rotation_xy)
            x = rel[0] * math.cos(angle) - rel[1] * math.sin(angle)
            y = rel[0] * math.sin(angle) + rel[1] * math.cos(angle)
            rel[0], rel[1] = x, y

        for anum in self._axis_numbers:
            rel[anum] -= g92_offset[anum]

        if stat.program_units != self._machine_units:
            factors = self._conversion_factors()
            pos = [pos[i] * factors[i] for i in range(9)]
            rel = [rel[i] * factors[i] for i in range(9)]
            dtg = [dtg[i] * factors[i] for i in range(9)]

        abs_, rel_, dtg_ = tuple(pos), tuple(rel), tuple(dtg)
        if (abs_, rel_, dtg_) == (self._abs, self._rel, self._dtg):
            return

        self._abs, self._rel, self._dtg = abs_, rel_, dtg_
        self.positionsChanged.emit(rel_)

    def _conversion_factors(self) -> list:
        """Linear axes convert, rotary axes (ABC) do not."""
        scale = 1.0 / MM_PER_INCH if self._machine_units == UNITS_METRIC else MM_PER_INCH
        return [scale] * 3 + [1.0] * 3 + [scale] * 3
