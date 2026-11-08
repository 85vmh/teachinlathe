"""LinuxCNC's error channel: the one place that reads it.

The channel is a queue - a read takes the message away - so there is one
reader in the application, and it empties the queue on every read: task
waits up to 5 s for room in the 8 KB buffer and then drops the message, so a
reader that took one message per tick would lose a burst.

The messages come out as :class:`RawMachineMessage`, with no ``linuxcnc``
constant in them: another source - the machine's messages decoded from a
WebSocket, say - can stand in for this one as long as it has ``drain()``.
"""

from __future__ import annotations

import logging
from typing import List, Protocol

import linuxcnc

from teachinlathe.events.model.event import MessageKind, RawMachineMessage

log = logging.getLogger(__name__)

#: The kinds LinuxCNC sends, both the legacy NML_* ones and the OPERATOR_* ones task sends today.
_KINDS = {
    linuxcnc.NML_ERROR: MessageKind.ERROR,
    linuxcnc.OPERATOR_ERROR: MessageKind.ERROR,
    linuxcnc.NML_TEXT: MessageKind.TEXT,
    linuxcnc.OPERATOR_TEXT: MessageKind.TEXT,
    linuxcnc.NML_DISPLAY: MessageKind.DISPLAY,
    linuxcnc.OPERATOR_DISPLAY: MessageKind.DISPLAY,
}

#: How many messages one drain takes at most, so a flood cannot hold the GUI thread.
MAX_PER_DRAIN = 100


class MachineMessageSource(Protocol):
    """Where the machine's messages come from."""

    def drain(self) -> List[RawMachineMessage]:
        """The messages that arrived since the last call, oldest first."""


class LinuxCncErrorDataSource:
    """``linuxcnc.error_channel()``, read until it is empty."""

    def __init__(self, channel=None) -> None:
        # injectable, so the draining can be tested without a running machine
        self._channel = linuxcnc.error_channel() if channel is None else channel
        self._failing = False

    def drain(self) -> List[RawMachineMessage]:
        messages: List[RawMachineMessage] = []
        while len(messages) < MAX_PER_DRAIN:
            try:
                error = self._channel.poll()
            except linuxcnc.error:
                if not self._failing:
                    self._failing = True
                    log.warning("the LinuxCNC error channel cannot be read", extra={"events": False})
                break
            if self._failing:
                self._failing = False
                log.info("the LinuxCNC error channel can be read again")
            if not error:
                break
            kind, text = error
            messages.append(RawMachineMessage(_KINDS.get(kind, MessageKind.ERROR), str(text or "").strip()))
        return messages
