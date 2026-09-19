"""Userspace HAL components, as Qt objects.

A :class:`HalComponent` owns its pins; a
:class:`HalPin` exposes the HAL value as a Python property and emits
``valueChanged`` when it moves.

HAL has no push notification, so input pins have to be polled. They are polled
by **one** shared timer for the whole process (see :class:`_PinPoller`), not by
a timer per pin: this application declares around sixty pins, and a timer each
means sixty wakeups per cycle to do work one loop can do.

Only ``in`` and ``io`` pins are polled. An ``out`` pin can only be changed by
us, and writing one emits ``valueChanged`` on the spot, so polling it would
never find anything.
"""

from __future__ import annotations

import atexit
import logging
import sys
from typing import Callable, Dict, Iterator, Optional

import _hal
import hal
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

log = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_MS = 100

PIN_TYPES = {
    "float": hal.HAL_FLOAT,
    "s32": hal.HAL_S32,
    "u32": hal.HAL_U32,
    "bit": hal.HAL_BIT,
}

PIN_DIRECTIONS = {
    "in": hal.HAL_IN,
    "out": hal.HAL_OUT,
    "io": hal.HAL_IO,
}

POLLED_DIRECTIONS = ("in", "io")


class HalPin(QObject):
    """One HAL pin.

    ``valueChanged`` carries the new value. It fires when the poller sees an
    input pin move, and on every write to any pin - writing is how an output
    pin reports itself, and callers rely on that echo.
    """

    valueChanged = pyqtSignal(object)

    def __init__(self, comp, name: str, pin_type: str, direction: str,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._name = name
        self._type = pin_type
        self._direction = direction
        self._pin = comp.newpin(name, PIN_TYPES[pin_type], PIN_DIRECTIONS[direction])
        self._last = self._pin.get()

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> str:
        return self._type

    @property
    def direction(self) -> str:
        return self._direction

    @property
    def is_polled(self) -> bool:
        return self._direction in POLLED_DIRECTIONS

    @property
    def value(self):
        return self._pin.get()

    @value.setter
    def value(self, new_value) -> None:
        self._last = new_value
        self._pin.set(new_value)
        self.valueChanged.emit(new_value)

    def poll(self) -> None:
        """Emit ``valueChanged`` if the pin moved since the last look."""
        current = self._pin.get()
        if current != self._last:
            self._last = current
            self.valueChanged.emit(current)

    def __repr__(self) -> str:
        return "<HalPin {} ({} {})>".format(self._name, self._type, self._direction)


class _PinPoller(QObject):
    """The single timer that polls every input pin in the process."""

    def __init__(self) -> None:
        super().__init__()
        self._pins: list[HalPin] = []
        self._timer = QTimer(self)
        self._timer.setInterval(DEFAULT_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._tick)

    def add(self, pin: HalPin) -> None:
        if not pin.is_polled:
            return
        self._pins.append(pin)
        if not self._timer.isActive():
            self._timer.start()

    def remove_all(self, pins) -> None:
        keep = [p for p in self._pins if p not in set(pins)]
        self._pins = keep
        if not self._pins:
            self._timer.stop()

    def set_interval(self, milliseconds: int) -> None:
        self._timer.setInterval(int(milliseconds))

    def _tick(self) -> None:
        for pin in self._pins:
            try:
                pin.poll()
            except Exception:
                # One misbehaving listener must not stop the others from
                # being told about their pins.
                log.exception("error polling HAL pin %s", pin.name)


_POLLER: Optional[_PinPoller] = None


def _poller() -> _PinPoller:
    global _POLLER
    if _POLLER is None:
        _POLLER = _PinPoller()
    return _POLLER


class HalComponent(QObject):
    """A userspace HAL component and the pins it owns."""

    def __init__(self, name: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._name = name
        self._comp = _hal.component(name)
        self._pins: Dict[str, HalPin] = {}
        self._ready = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def pins(self) -> Dict[str, HalPin]:
        return dict(self._pins)

    def addPin(self, name: str, pin_type: str, direction: str) -> HalPin:
        """Create pin ``<component>.<name>`` and return it."""
        pin_type = pin_type.lower()
        direction = direction.lower()
        if pin_type not in PIN_TYPES:
            raise ValueError("unknown HAL pin type {!r}, expected one of {}"
                             .format(pin_type, sorted(PIN_TYPES)))
        if direction not in PIN_DIRECTIONS:
            raise ValueError("unknown HAL pin direction {!r}, expected one of {}"
                             .format(direction, sorted(PIN_DIRECTIONS)))
        if name in self._pins:
            raise ValueError("HAL pin {}.{} already exists".format(self._name, name))

        log.debug("adding HAL pin %s.%s (%s %s)", self._name, name, pin_type, direction)
        pin = HalPin(self._comp, name, pin_type, direction, parent=self)
        self._pins[name] = pin
        _poller().add(pin)
        return pin

    def getPin(self, name: str) -> HalPin:
        return self._pins[name]

    def addListener(self, name: str, callback: Callable) -> None:
        """Call *callback* with the new value whenever the pin changes."""
        self._pins[name].valueChanged.connect(callback)

    def removeListener(self, name: str, callback: Callable) -> None:
        self._pins[name].valueChanged.disconnect(callback)

    def ready(self) -> None:
        """Tell HAL the pins are all declared. No pin may be added after this."""
        if self._ready:
            return
        self._comp.ready()
        self._ready = True

    def exit(self):
        """Unload the component, stopping its pins from being polled."""
        _poller().remove_all(self._pins.values())
        COMPONENTS.pop(self._name, None)
        return self._comp.exit()

    def __getitem__(self, name: str) -> HalPin:
        return self._pins[name]

    def __contains__(self, name: object) -> bool:
        return name in self._pins

    def __iter__(self) -> Iterator[str]:
        return iter(self._pins)

    def __repr__(self) -> str:
        return "<HalComponent {} ({} pins)>".format(self._name, len(self._pins))


COMPONENTS: Dict[str, HalComponent] = {}


def hal_component(name: str) -> HalComponent:
    """The HAL component called *name*, created on first use."""
    comp = COMPONENTS.get(name)
    if comp is None:
        log.info("creating HAL component: %s", name)
        comp = HalComponent(name)
        COMPONENTS[name] = comp
    return comp


def set_poll_interval(milliseconds: int) -> None:
    """Change how often input pins are read (default 100 ms)."""
    _poller().set_interval(milliseconds)


def unload_all() -> None:
    """Unload every component this process created.

    Registered with :mod:`atexit`, because a component that outlives its
    process stays registered in HAL's shared memory: the next run then dies on
    "duplicate component name" and the stale one has to be cleared by hand.

    Signals are deliberately not handled here. Installing a handler is a
    change to process-global state, and a library module that does it on
    import fights whoever else wants it - which is how Ctrl-C ended up
    unloading HAL and then raising KeyboardInterrupt through the event loop.
    The application installs its own, and this runs on the way out either way.
    """
    for comp in list(COMPONENTS.values()):
        # Unload first, then say so. At interpreter shutdown a log handler can
        # raise - it may be writing to something Qt has already deleted - and
        # a component that is not unloaded blocks the next start, while a
        # message that is not printed costs nothing.
        name = comp.name
        try:
            comp.exit()
        except Exception as error:
            _report("error unloading HAL component %s: %s" % (name, error))
            continue
        _report("unloaded HAL component: %s" % name)


def _report(message: str) -> None:
    """Log *message*, falling back to stderr if logging itself is gone."""
    try:
        log.info(message)
    except Exception:
        try:
            print(message, file=sys.stderr)
        except Exception:
            pass



atexit.register(unload_all)
