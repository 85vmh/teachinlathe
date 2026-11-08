"""The Events list: what the machine says and what the application posts,
in one list, newest last.

* The machine's messages come from MachineMessagesRepository - the only reader
  of LinuxCNC's error channel - and are classified here.
* The application posts with :meth:`EventsUseCase.post`.
* The application's log records at WARNING and above come in as well, as
  "app" events. A record logged with ``extra={"events": False}`` stays in the
  log only: one already posted, or one this list reports in another way.

Every event is also logged, under ``teachinlathe.events`` - once: its
repeats are only counted.

The same event again, within REPEAT_WINDOW of the last, counts on the last
one instead of making a row: a Mesa board that stopped answering says so
many times a second.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from teachinlathe.events.logic.classify import classify
from teachinlathe.events.model.event import Category, Event, RawMachineMessage, Severity

log = logging.getLogger("teachinlathe.events")

MAX_EVENTS = 500
REPEAT_WINDOW = timedelta(seconds=2)

_LOG_LEVELS = {
    Severity.ERROR: logging.ERROR,
    Severity.WARNING: logging.WARNING,
    Severity.INFO: logging.INFO,
}


class _LogBridge(QObject):
    """Takes log records to the GUI thread: a record can be logged from any
    thread, the list lives in this one."""
    recordLogged = pyqtSignal(str, str, str)  # severity, logger name, message


class EventsLogHandler(logging.Handler):
    """The application's WARNING+ log records, as events.

    It sits on the root logger, so it outlives the use case it writes to:
    once Qt deleted the bridge at shutdown it takes itself off instead of
    raising out of every logging call after that.
    """

    def __init__(self, bridge: _LogBridge) -> None:
        super().__init__(logging.WARNING)
        self._bridge: Optional[_LogBridge] = bridge

    def emit(self, record: logging.LogRecord) -> None:
        if self._bridge is None or getattr(record, "events", True) is False:
            return
        if record.name == log.name or record.name.startswith(log.name + "."):
            return
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        severity = Severity.ERROR if record.levelno >= logging.ERROR else Severity.WARNING
        try:
            self._bridge.recordLogged.emit(severity.value, record.name, message)
        except RuntimeError:
            self._bridge = None
            logging.getLogger().removeHandler(self)


class EventsUseCase(QObject):
    #: an Event, appended
    eventAdded = pyqtSignal(object)
    #: an Event that came again: the same id, its count and time moved on
    eventUpdated = pyqtSignal(object)
    #: the id of the oldest event, dropped to keep the list at MAX_EVENTS
    eventRemoved = pyqtSignal(int)
    cleared = pyqtSignal()

    def __init__(self, machine_messages=None, status=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._events: List[Event] = []
        self._next_id = 1

        if machine_messages is None:
            from teachinlathe.core.machine_messages_repository import machine_messages_repository
            machine_messages = machine_messages_repository()
        machine_messages.messageReceived.connect(self._on_machine_message)

        if status is None:
            from teachinlathe.core.status_repository import status_repository
            status = status_repository()
        status.staleChanged.connect(self._on_status_stale)

        self._log_bridge = _LogBridge(self)
        self._log_bridge.recordLogged.connect(self._on_log_record)
        root = logging.getLogger()
        for handler in [h for h in root.handlers if isinstance(h, EventsLogHandler)]:
            root.removeHandler(handler)
        root.addHandler(EventsLogHandler(self._log_bridge))

    def events(self) -> List[Event]:
        return list(self._events)

    def post(self, category: Category, severity: Severity, text: str, source: str = "app") -> None:
        """Add an event, and log it unless it is a repeat."""
        if self._add(category, severity, text, source):
            log.log(_LOG_LEVELS[severity], "[%s] %s", category.value, text)

    def clear(self) -> None:
        if not self._events:
            return
        self._events = []
        self.cleared.emit()

    # -- sources ------------------------------------------------------------

    def _on_machine_message(self, message: RawMachineMessage) -> None:
        if not message.text:
            return
        severity, category = classify(message)
        self.post(category, severity, message.text, source="linuxcnc")

    def _on_status_stale(self, stale: bool) -> None:
        if stale:
            self.post(Category.CONNECTION, Severity.ERROR,
                      "LinuxCNC status is not answering; what the screens show is stale")
        else:
            self.post(Category.CONNECTION, Severity.INFO, "LinuxCNC status answers again")

    def _on_log_record(self, severity: str, name: str, message: str) -> None:
        self._add(Category.APP, Severity(severity), message, name)

    # -- the list -----------------------------------------------------------

    def _add(self, category: Category, severity: Severity, text: str, source: str) -> bool:
        """Whether it is a new event, rather than a repeat of the last."""
        now = datetime.now()
        if self._events:
            last = self._events[-1]
            if ((last.category, last.severity, last.text) == (category, severity, text)
                    and now - last.time <= REPEAT_WINDOW):
                repeated = Event(last.id, now, severity, category, text, source, last.count + 1)
                self._events[-1] = repeated
                self.eventUpdated.emit(repeated)
                return False

        event = Event(self._next_id, now, severity, category, text, source)
        self._next_id += 1
        self._events.append(event)
        self.eventAdded.emit(event)
        while len(self._events) > MAX_EVENTS:
            dropped = self._events.pop(0)
            self.eventRemoved.emit(dropped.id)
        return True


_INSTANCE: Optional[EventsUseCase] = None


def events_use_case() -> EventsUseCase:
    """The shared Events list, listening from first use."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = EventsUseCase()
    return _INSTANCE
