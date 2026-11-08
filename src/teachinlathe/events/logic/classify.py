"""Which severity and category a machine message gets.

LinuxCNC tells only error / text / display apart: a warning cannot be told
from an error, and what the message is about is read from its text.
"""

from __future__ import annotations

from typing import Tuple

from teachinlathe.events.model.event import Category, MessageKind, RawMachineMessage, Severity

#: The Mesa driver's messages: rtapi errors from hostmot2, hm2_eth, ...
_CONNECTION_PREFIXES = ("hm2/", "hm2_", "hm2:")

#: The interpreter's errors end with where they happened: "Near line 12 of ..."
_PROGRAM_MARKER = "near line"


def classify(message: RawMachineMessage) -> Tuple[Severity, Category]:
    text = message.text.lower()
    if text.startswith(_CONNECTION_PREFIXES):
        category = Category.CONNECTION
    elif message.kind is MessageKind.DISPLAY or _PROGRAM_MARKER in text:
        category = Category.PROGRAM
    else:
        category = Category.MACHINE
    severity = Severity.ERROR if message.kind is MessageKind.ERROR else Severity.INFO
    return severity, category
