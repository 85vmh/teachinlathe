from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

from teachinlathe.core.positions_repository import Positions


#: The work offsets by stat.g5x_index.
WORK_OFFSETS = {1: "G54", 2: "G55", 3: "G56", 4: "G57", 5: "G58", 6: "G59", 7: "G59.1", 8: "G59.2", 9: "G59.3"}


class ProgramsDroViewModel(QObject):
    """Exposes the live X/Z positions to ``ProgramsDro.qml``, and the work
    offset they are in.

    Depends only on :class:`Positions`, the single source of truth for
    position calculations.
    """

    changed = pyqtSignal()

    # X is reported in diameter on a lathe, so the radius values from the
    # source of truth are doubled for display.
    DIAMETER_FACTOR = 2.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._positions = Positions()
        self._x = self._positions.getXPosition()
        self._z = self._positions.getZPosition()
        self._work_offset = self._positions.work_offset()
        self._positions.notify(self._update)

    def _update(self, *_args):
        self._x = self._positions.getXPosition()
        self._z = self._positions.getZPosition()
        self._work_offset = self._positions.work_offset()
        self.changed.emit()

    @pyqtProperty(str, notify=changed)
    def workOffsetName(self):
        """The work offset the positions are in - the program's: "G54" ..."""
        return WORK_OFFSETS.get(self._work_offset, "G54")

    @pyqtProperty(float, notify=changed)
    def xPosition(self):
        return self._x.g5xPosition * self.DIAMETER_FACTOR

    @pyqtProperty(float, notify=changed)
    def xDistanceToGo(self):
        return self._x.distanceToGo * self.DIAMETER_FACTOR

    @pyqtProperty(float, notify=changed)
    def zPosition(self):
        return self._z.g5xPosition

    @pyqtProperty(float, notify=changed)
    def zDistanceToGo(self):
        return self._z.distanceToGo
