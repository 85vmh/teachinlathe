"""Single source of truth for axis position calculations.

All reads from the qtpyvcp ``Status`` and ``position`` plugins (and ``Info``)
live in this module. The rest of the application should depend only on
:class:`Positions` / :class:`Position`, so that decoupling from qtpyvcp later
requires changes in as few places as possible.
"""

from dataclasses import dataclass

from qtpyvcp.plugins import getPlugin
from qtpyvcp.utilities.info import Info
from qtpyvcp.widgets.base_widgets.dro_base_widget import Axis

INFO = Info()


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


class Positions:
    """Provides axis positions read from the qtpyvcp plugins.

    This is the only place that talks to the qtpyvcp ``position`` plugin, so
    callers stay independent of qtpyvcp.
    """

    def __init__(self):
        self._status = getPlugin('status')
        self._position = getPlugin('position')

    def getXPosition(self) -> Position:
        return self._getAxisPosition(Axis.X)

    def getZPosition(self) -> Position:
        return self._getAxisPosition(Axis.Z)

    def _getAxisPosition(self, anum) -> Position:
        machine = getattr(self._position, 'abs').getValue()
        g5x = getattr(self._position, 'rel').getValue()
        dtg = getattr(self._position, 'dtg').getValue()
        return Position(
            machinePosition=machine[anum],
            g5xPosition=g5x[anum],
            distanceToGo=dtg[anum],
        )

    def notify(self, callback):
        """Register *callback* to be invoked whenever the positions update."""
        getattr(self._position, 'rel').notify(callback)
