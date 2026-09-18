"""The LinuxCNC status channel, polled and published as Qt signals.

Replaces ``qtpyvcp.plugins.status``. One :class:`linuxcnc.stat` is polled on a
single timer; every field read through this repository is a
:class:`StatusChannel` that emits ``valueChanged`` when - and only when - the
field actually moves.

Channels are created on first access, for any attribute ``linuxcnc.stat``
carries, so asking for a field that was never needed before costs a line at the
call site and nothing here. ``all_axes_homed`` is the one channel LinuxCNC does
not provide: it is derived from the joints and the INI's NO_FORCE_HOMING.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

import linuxcnc
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from .ini_repository import ini_repository

log = logging.getLogger(__name__)

DEFAULT_CYCLE_TIME_MS = 75

#: Short and long spellings of ``stat.program_units``, indexed by its value.
PROGRAM_UNITS_SHORT = ("N/A", "in", "mm", "cm")
PROGRAM_UNITS_LONG = ("N/A", "Inches", "Millimeters", "Centimeters")


class StatusChannel(QObject):
    """One field of the status channel.

    ``notify(slot)`` hands the slot the new value; ``notify(slot, 'string')``
    hands it the formatted text instead, which is how the DRO asks for units
    as "mm" rather than 2.
    """

    valueChanged = pyqtSignal(object)

    def __init__(self, name: str, value=None,
                 formatter: Optional[Callable] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._name = name
        self._value = value
        self._formatter = formatter

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self):
        return self._value

    def getValue(self):
        return self._value

    def getString(self, fmt: str = "short") -> str:
        if self._formatter is None:
            return str(self._value)
        return self._formatter(self._value, fmt)

    def setValue(self, value) -> None:
        """Store *value*, emitting only if it differs from the one held."""
        if _same(self._value, value):
            return
        self._value = value
        self.valueChanged.emit(value)

    def notify(self, slot: Callable, *args, **kwargs) -> None:
        """Call *slot* whenever the value changes.

        With no further arguments the slot receives the value. With ``'string'``
        (or ``'str'``) it receives ``getString()``; any remaining arguments are
        passed on to the formatter.

        The plain case connects the slot to the signal directly rather than
        through a wrapper, so that Qt does its usual thing and drops the
        argument for a slot that takes none - ``notify(self.refreshModel)``
        with ``def refreshModel(self)`` is a normal way to ask to be told
        something changed without caring what it changed to.
        """
        if args and args[0] in ("string", "str"):
            fmt_args = args[1:]
            self.valueChanged.connect(
                lambda *_: slot(self.getString(*fmt_args, **kwargs)))
        else:
            self.valueChanged.connect(slot)

    #: qtpyvcp spelled the same thing two ways; both are in use.
    onValueChanged = notify

    @property
    def signal(self):
        """The change signal under qtpyvcp's name for it.

        Kept, like :meth:`notify`, so call sites did not all have to be
        rewritten at once; ``valueChanged`` is this repository's own spelling.
        """
        return self.valueChanged

    def __str__(self) -> str:
        return self.getString()

    def __int__(self) -> int:
        return int(self._value)

    def __float__(self) -> float:
        return float(self._value)

    def __bool__(self) -> bool:
        return bool(self._value)

    def __getitem__(self, item):
        return self._value[item]

    def __repr__(self) -> str:
        return "<StatusChannel {}={!r}>".format(self._name, self._value)


def _same(a, b) -> bool:
    """Whether two channel values are equal, tolerating unequal types.

    ``linuxcnc.stat`` hands back tuples, lists and lists of dicts; comparing
    two of those can raise rather than return False, and a channel that raises
    while polling would stop every channel behind it.
    """
    try:
        return bool(a == b)
    except Exception:
        return False


def _program_units(value, fmt: str = "short") -> str:
    names = PROGRAM_UNITS_LONG if fmt == "long" else PROGRAM_UNITS_SHORT
    try:
        return names[int(value)]
    except (TypeError, ValueError, IndexError):
        return names[0]


#: Channels needing more than ``str()`` to render as text.
FORMATTERS = {"program_units": _program_units}

#: Channels computed here rather than read off ``linuxcnc.stat``.
DERIVED = ("all_axes_homed",)

#: Fields ``linuxcnc.stat`` reports as a list of dicts, one per item. Each
#: entry becomes an :class:`ItemStatus` with a channel per key, so a caller can
#: watch ``spindle[0].override`` rather than the whole list changing at once.
GROUPED = ("spindle", "joint", "axis")


class ItemStatus(QObject):
    """One spindle, joint or axis: a channel per key of its status dict."""

    def __init__(self, field: str, index: int, values: dict,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._field = field
        self._index = index
        self._channels: Dict[str, StatusChannel] = {}
        self._groups: Dict[str, tuple] = {}
        for key, value in values.items():
            chan = StatusChannel("{}[{}].{}".format(field, index, key),
                                 value, parent=self)
            self._channels[key] = chan
            setattr(self, key, chan)

    @property
    def index(self) -> int:
        return self._index

    @property
    def channels(self) -> Dict[str, StatusChannel]:
        return dict(self._channels)

    def channel(self, key: str) -> StatusChannel:
        return self._channels[key]

    def __getitem__(self, key: str):
        return self._channels[key].value

    def update(self, values: dict) -> None:
        for key, value in values.items():
            chan = self._channels.get(key)
            if chan is not None:
                chan.setValue(value)

    def __repr__(self) -> str:
        return "<ItemStatus {}[{}]>".format(self._field, self._index)


class StatusRepository(QObject):
    """The machine's status, polled on one timer."""

    polled = pyqtSignal()

    def __init__(self, cycle_time_ms: int = DEFAULT_CYCLE_TIME_MS,
                 parent: Optional[QObject] = None,
                 stat=None, ini=None) -> None:
        super().__init__(parent)
        # stat/ini are injectable so the arithmetic can be tested without a
        # running machine; in the application both are the real thing.
        self._stat = linuxcnc.stat() if stat is None else stat
        self._ini = ini_repository() if ini is None else ini
        self._no_force_homing = self._ini.no_force_homing
        self._channels: Dict[str, StatusChannel] = {}
        self._groups: Dict[str, tuple] = {}

        self._timer = QTimer(self)
        self._timer.setInterval(cycle_time_ms)
        self._timer.timeout.connect(self.poll)

    @property
    def stat(self):
        """The raw ``linuxcnc.stat``, for callers that want it directly."""
        return self._stat

    @property
    def spindle(self) -> tuple:
        """Per-spindle status, e.g. ``status.spindle[0].override.value``."""
        return self.group("spindle")

    @property
    def joint(self) -> tuple:
        """Per-joint status, e.g. ``status.joint[0].homed.value``."""
        return self.group("joint")

    @property
    def axis(self) -> tuple:
        """Per-axis status, e.g. ``status.axis[0].velocity.value``."""
        return self.group("axis")

    def group(self, field: str) -> tuple:
        """The :class:`ItemStatus` tuple for *field*, built on first use."""
        items = self._groups.get(field)
        if items is None:
            raw = getattr(self._stat, field, ()) or ()
            items = tuple(ItemStatus(field, index, values, parent=self)
                          for index, values in enumerate(raw))
            self._groups[field] = items
        return items

    def start(self) -> None:
        if not self._timer.isActive():
            self.poll()
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def setCycleTime(self, milliseconds: int) -> None:
        self._timer.setInterval(int(milliseconds))

    # -- channels ---------------------------------------------------------

    def channel(self, name: str) -> StatusChannel:
        """The channel for *name*, created on first use."""
        chan = self._channels.get(name)
        if chan is None:
            chan = StatusChannel(name, self._read(name),
                                 formatter=FORMATTERS.get(name), parent=self)
            self._channels[name] = chan
        return chan

    def __getattr__(self, name: str) -> StatusChannel:
        # Only reached for names that are not real attributes, so the timer,
        # the stat and the rest are never shadowed by a channel.
        if name.startswith("_"):
            raise AttributeError(name)
        if name in GROUPED:
            # Reached only if the property above was somehow bypassed; a
            # grouped field is never a plain channel.
            return self.group(name)
        if name not in DERIVED and not hasattr(self._stat, name):
            raise AttributeError(
                "linuxcnc.stat has no field {!r}".format(name))
        return self.channel(name)

    def allHomed(self) -> bool:
        """Whether every joint is homed, or homing is not being forced."""
        if self._no_force_homing:
            return True
        try:
            for joint in range(self._stat.joints):
                if not self._stat.joint[joint]["homed"]:
                    return False
        except Exception:
            log.exception("could not read joint homing state")
            return False
        return True

    # -- polling ----------------------------------------------------------

    def poll(self) -> None:
        try:
            self._stat.poll()
        except Exception:
            log.exception("linuxcnc.stat.poll() failed")
            return

        for name, chan in self._channels.items():
            try:
                chan.setValue(self._read(name))
            except Exception:
                log.exception("could not update status channel %s", name)

        for field, items in self._groups.items():
            raw = getattr(self._stat, field, ()) or ()
            for index, item in enumerate(items):
                try:
                    item.update(raw[index])
                except Exception:
                    log.exception("could not update %s[%d]", field, index)

        self.polled.emit()

    def _read(self, name: str):
        if name == "all_axes_homed":
            return self.allHomed()
        return getattr(self._stat, name, None)


_INSTANCE: Optional[StatusRepository] = None


def status_repository() -> StatusRepository:
    """The shared StatusRepository, polling from first use."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = StatusRepository()
        _INSTANCE.start()
    return _INSTANCE
