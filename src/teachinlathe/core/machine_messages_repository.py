"""The machine's messages - errors, operator texts, (MSG,...) from G-code -
as a Qt signal: the single entry point of the error channel into the
application.

It polls a :class:`MachineMessageSource` - LinuxCNC's error channel unless
told otherwise - and emits each message once, in the order it came.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from teachinlathe.core.linuxcnc_error_data_source import LinuxCncErrorDataSource, MachineMessageSource

POLL_MS = 100


class MachineMessagesRepository(QObject):
    #: a RawMachineMessage
    messageReceived = pyqtSignal(object)

    def __init__(self, source: Optional[MachineMessageSource] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._source = LinuxCncErrorDataSource() if source is None else source
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_MS)
        self._timer.timeout.connect(self.poll)

    def start(self) -> None:
        self._timer.start()

    def poll(self) -> None:
        for message in self._source.drain():
            self.messageReceived.emit(message)


_INSTANCE: Optional[MachineMessagesRepository] = None


def machine_messages_repository() -> MachineMessagesRepository:
    """The shared repository, polling from first use."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = MachineMessagesRepository()
        _INSTANCE.start()
    return _INSTANCE
