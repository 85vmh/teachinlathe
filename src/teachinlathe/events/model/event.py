"""What the Events list is made of: the machine's messages, and the events
the application posts, mixed in one list."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MessageKind(Enum):
    """What the machine says a message is - all a LinuxCNC message carries
    besides its text."""
    ERROR = "error"
    TEXT = "text"
    DISPLAY = "display"


@dataclass(frozen=True)
class RawMachineMessage:
    """A message as the machine sent it."""
    kind: MessageKind
    text: str


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(Enum):
    """What an event is about - the Events list's filters."""
    #: LinuxCNC's errors and texts: following errors, limits, "machine not on", ...
    MACHINE = "machine"
    #: the program's: (MSG,...), (DEBUG,...), the interpreter's errors
    PROGRAM = "program"
    #: the link to the machine: the Mesa board (hm2), the status channel
    CONNECTION = "connection"
    #: the application's own
    APP = "app"


@dataclass(frozen=True)
class Event:
    id: int
    time: datetime
    severity: Severity
    category: Category
    text: str
    #: who posted it: "linuxcnc", "app", the logger's name, ...
    source: str
    #: how many times it came in a row (repeats are counted, not listed)
    count: int = 1
