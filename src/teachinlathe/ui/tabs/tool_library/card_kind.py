"""Which card draws a cutting tool - its thumbnail, title and figures.

Each tool view says its own (``view.card``), so what draws a tool can never
be other than the view it reads: a boring bar is drawn as a turning tool is,
the kinds without a card of their own as a line of text (Summary).

Its enum is QML's (``CardKind.Turning``, ``CardKind.Blade``, ...), registered
by AppWindow; Python has it as ``CardKind.Kind``.
"""

from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import QObject, pyqtEnum


class CardKind(QObject):

    @pyqtEnum
    class Kind(Enum):
        NoCard = 0
        Turning = 1
        Threading = 2
        Blade = 3
        Drilling = 4
        Reaming = 5
        Tapping = 6
        Summary = 7
