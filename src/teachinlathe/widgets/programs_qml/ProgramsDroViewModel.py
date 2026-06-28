from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal

from teachinlathe.data_source.positions import Positions


class ProgramsDroViewModel(QObject):
    """Exposes the live X/Z positions to ``ProgramsDro.qml``.

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
        self._positions.notify(self._update)

    def _update(self, *_args):
        self._x = self._positions.getXPosition()
        self._z = self._positions.getZPosition()
        self.changed.emit()

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
