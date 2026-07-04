"""Screen states for the Programs tab, shared by Python and QML.

``ProgramsScreen`` is the single source of truth (a plain ``IntEnum``).
``ProgramsScreenEnum`` exposes the same values to QML as a context property
named ``ProgramsScreen`` (so QML uses ``ProgramsScreen.Running`` etc.) without
registering a QML type.
"""

from enum import IntEnum

from PyQt5.QtCore import QObject, pyqtProperty


class ProgramsScreen(IntEnum):
    FileSystem = 0      # file system browser
    ProgramLoaded = 1     # loaded program (DRO + gremlin + execution)
    ProgramRunning = 2    # program running, full screen


class ProgramsScreenEnum(QObject):
    """QML-facing holder so QML can reference ``ProgramsScreen.<State>``."""

    @pyqtProperty(int, constant=True)
    def Files(self):
        return int(ProgramsScreen.FileSystem)

    @pyqtProperty(int, constant=True)
    def Loaded(self):
        return int(ProgramsScreen.ProgramLoaded)

    @pyqtProperty(int, constant=True)
    def Running(self):
        return int(ProgramsScreen.ProgramRunning)
