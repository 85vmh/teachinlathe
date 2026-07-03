"""Screen states for the Programs tab, shared by Python and QML.

``ProgramsScreen`` is the single source of truth (a plain ``IntEnum``).
``ProgramsScreenEnum`` exposes the same values to QML as a context property
named ``ProgramsScreen`` (so QML uses ``ProgramsScreen.Running`` etc.) without
registering a QML type.
"""

from enum import IntEnum

from PyQt5.QtCore import QObject, pyqtProperty


class ProgramsScreen(IntEnum):
    Files = 0      # file system browser
    Loaded = 1     # loaded program (DRO + gremlin + execution)
    Running = 2    # program running, full screen


class ProgramsScreenEnum(QObject):
    """QML-facing holder so QML can reference ``ProgramsScreen.<State>``."""

    @pyqtProperty(int, constant=True)
    def Files(self):
        return int(ProgramsScreen.Files)

    @pyqtProperty(int, constant=True)
    def Loaded(self):
        return int(ProgramsScreen.Loaded)

    @pyqtProperty(int, constant=True)
    def Running(self):
        return int(ProgramsScreen.Running)
