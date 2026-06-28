"""QML bridge exposing live axis teach-in values.

:class:`Positions` (data_source) is plain Python and cannot be called from QML;
this thin QObject forwards ``teachInX`` / ``teachInZ`` to it so QML teach
buttons can read the current position. The lathe diameter doubling for X is
applied by the QML caller (the fields are in diameter).
"""

from PyQt5.QtCore import QObject, pyqtSlot

from teachinlathe.data_source.positions import Positions


class PositionsBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._positions = Positions()

    @pyqtSlot(result=float)
    @pyqtSlot(bool, result=float)
    def teachInX(self, machineCoordinate=False):
        return self._positions.teachInX(machineCoordinate)

    @pyqtSlot(result=float)
    @pyqtSlot(bool, result=float)
    def teachInZ(self, machineCoordinate=False):
        return self._positions.teachInZ(machineCoordinate)
