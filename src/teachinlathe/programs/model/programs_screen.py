"""Screen states for the Programs tab.

QML does not compare against these: ProgramsViewModel answers what it asks
(``programShown``, ``running``) from them.
"""

from enum import IntEnum


class ProgramsScreen(IntEnum):
    FileSystem = 0      # file system browser
    ProgramLoaded = 1     # loaded program (DRO + gremlin + execution)
    ProgramRunning = 2    # program running, full screen
