"""Tests for the HAL repository, run against real HAL pins.

Each test builds a throwaway userspace component with a unique name, so the
tests neither collide with each other nor with a running machine.
"""

import itertools
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytest.importorskip("_hal", reason="LinuxCNC HAL is not available")

from PyQt5.QtCore import QCoreApplication, QEventLoop, QTimer  # noqa: E402

from teachinlathe.repositories import hal_repository as halrepo  # noqa: E402


_names = ("teachin_test_%d" % n for n in itertools.count())


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def comp(qt_app):
    """A fresh HAL component, unloaded when the test ends."""
    component = halrepo.hal_component(next(_names))
    yield component
    try:
        component.exit()
    except Exception:
        pass


def spin(milliseconds):
    """Run the Qt event loop for *milliseconds* so the poller can tick."""
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec_()


def test_pins_are_created_with_type_and_direction(comp):
    pin = comp.addPin("speed", "float", "out")
    comp.ready()
    assert (pin.name, pin.type, pin.direction) == ("speed", "float", "out")
    assert comp.getPin("speed") is pin
    assert comp["speed"] is pin
    assert "speed" in comp


def test_writing_a_pin_reads_back_and_notifies(comp):
    comp.addPin("flag", "bit", "out")
    comp.ready()
    seen = []
    comp.addListener("flag", seen.append)

    comp.getPin("flag").value = True

    assert comp.getPin("flag").value is True
    # An output pin reports itself on write - callers rely on that echo.
    assert seen == [True]


def test_only_input_pins_are_polled(comp):
    in_pin = comp.addPin("sensor", "bit", "in")
    out_pin = comp.addPin("lamp", "bit", "out")
    io_pin = comp.addPin("both", "bit", "io")
    comp.ready()

    assert (in_pin.is_polled, io_pin.is_polled, out_pin.is_polled) == (True, True, False)
    polled = halrepo._poller()._pins
    assert in_pin in polled and io_pin in polled
    assert out_pin not in polled


def test_one_timer_serves_every_component(qt_app):
    first = halrepo.hal_component(next(_names))
    second = halrepo.hal_component(next(_names))
    try:
        first.addPin("a", "bit", "in")
        second.addPin("b", "bit", "in")
        first.ready()
        second.ready()
        # Not one timer per pin, and not one per component.
        assert halrepo._poller()._timer.isActive()
        assert len(halrepo._poller()._pins) >= 2
    finally:
        first.exit()
        second.exit()


def test_poller_notices_a_change_on_an_io_pin(comp):
    pin = comp.addPin("echo", "bit", "io")
    comp.ready()
    halrepo.set_poll_interval(10)

    seen = []
    comp.addListener("echo", seen.append)

    # Write through the raw HAL item, behind the repository's back, the way
    # another HAL component would.
    pin._pin.set(True)
    spin(60)

    assert seen == [True]

    # A poll that finds no change must stay quiet.
    spin(60)
    assert seen == [True]


def test_repeated_writes_of_the_same_value_still_echo(comp):
    comp.addPin("trigger", "bit", "out")
    comp.ready()
    seen = []
    comp.addListener("trigger", seen.append)

    comp.getPin("trigger").value = True
    comp.getPin("trigger").value = True

    assert seen == [True, True]


def test_unknown_type_or_direction_is_rejected(comp):
    with pytest.raises(ValueError, match="pin type"):
        comp.addPin("x", "double", "in")
    with pytest.raises(ValueError, match="pin direction"):
        comp.addPin("x", "bit", "sideways")


def test_duplicate_pin_is_rejected(comp):
    comp.addPin("once", "bit", "in")
    with pytest.raises(ValueError, match="already exists"):
        comp.addPin("once", "bit", "in")


def test_hal_component_is_a_registry(qt_app):
    name = next(_names)
    first = halrepo.hal_component(name)
    try:
        assert halrepo.hal_component(name) is first
    finally:
        first.exit()
    # exit() deregisters, so the next call builds a new one.
    assert name not in halrepo.COMPONENTS


def test_exit_stops_pins_being_polled(qt_app):
    component = halrepo.hal_component(next(_names))
    pin = component.addPin("watched", "bit", "in")
    component.ready()
    assert pin in halrepo._poller()._pins

    component.exit()
    assert pin not in halrepo._poller()._pins


def test_removeListener_detaches_the_callback(comp):
    comp.addPin("sig", "bit", "out")
    comp.ready()
    seen = []

    def on_change(value):
        seen.append(value)

    comp.addListener("sig", on_change)
    comp.getPin("sig").value = False

    comp.removeListener("sig", on_change)
    comp.getPin("sig").value = True

    assert seen == [False]
