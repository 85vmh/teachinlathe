"""The Manual Turning tab's limits: what each one puts on the machine's
limit pins, and when.

What is pinned down here:

* A tool limit (X-, X+, Z-, Z+) is in the coordinates of the current loaded
  tool: on the machine it is the axis's offset (work offset, G92, tool) plus
  the value - half of it on X, set as a diameter. Another tool, another
  offset: the limit moves with it. The tailstock is the machine's and stays.
* A limit is written to its pin only while the axis is inside it, or when it
  moves away from the axis (given up, widened). One the axis is already past
  stays pending, the pin keeping what it had: written past the axis, LinuxCNC
  goes on a soft limit and the handwheels stop both ways - what a Z+ taught
  a rounding short of the axis did, through the tailstock's pin writes.
* Z+ and the tailstock share the Z max pin: the nearer of the two.
* On its limit (within LIMIT_REACHED_TOLERANCE) a limit is REACHED - its
  border red - with one limit in use as with several.

The view model is made without its constructor - that wants the HAL
component and LinuxCNC's status - and given what its limits use: the
positions, the limit pins and the real MachineLimitsHandler.
"""

from __future__ import annotations

import os
import types

import pytest
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtQml import QQmlComponent, QQmlEngine

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.manual.logic.machine_limits import MachineLimitsHandler
from teachinlathe.ui import QML_IMPORT_DIR
from teachinlathe.ui.tabs.manual_turning.TeachInLatheDroViewModel import (
    LimitStatus, TeachInLatheDroViewModel,
)

X_MIN, X_MAX, Z_MIN, Z_MAX = -500.0, 500.0, -1000.0, 1000.0

PIN = {
    "x-min": TeachInLatheComponent.PinAxisLimitXMin,
    "x-max": TeachInLatheComponent.PinAxisLimitXMax,
    "z-min": TeachInLatheComponent.PinAxisLimitZMin,
    "z-max": TeachInLatheComponent.PinAxisLimitZMax,
}


class _Pin:
    def __init__(self, value):
        self.value = value


class _Component:
    """The HAL component's limit pins, at the machine's own limits."""

    def __init__(self):
        self.pins = {PIN["x-min"]: _Pin(X_MIN), PIN["x-max"]: _Pin(X_MAX),
                     PIN["z-min"]: _Pin(Z_MIN), PIN["z-max"]: _Pin(Z_MAX)}

    def getPin(self, name):
        return self.pins[name]


class _Positions:
    """Where the axes are on the machine (X on the radius), and each axis's
    offset: work offset, G92 and the current loaded tool's."""

    def __init__(self):
        self.machine = {"x": 0.0, "z": 0.0}
        self.offset = {"x": 0.0, "z": 0.0}

    def _axis(self, axis):
        return types.SimpleNamespace(offset=self.offset[axis], machinePosition=self.machine[axis])

    def getXPosition(self):
        return self._axis("x")

    def getZPosition(self):
        return self._axis("z")


class Lathe:
    """The view model's limits, the machine under them, and what moves it."""

    def __init__(self):
        MachineLimitsHandler._instance = None
        handler = MachineLimitsHandler()
        # the machine's own limits, whatever the INI the tests run with says
        handler._default_x_minus_limit, handler._default_x_plus_limit = X_MIN, X_MAX
        handler._default_z_minus_limit, handler._default_z_plus_limit = Z_MIN, Z_MAX

        vm = TeachInLatheDroViewModel.__new__(TeachInLatheDroViewModel)
        QObject.__init__(vm)
        vm.positions = _Positions()
        vm.latheComponent = types.SimpleNamespace(comp=_Component())
        vm.limitsHandler = handler
        vm.previousMachineLimits = None
        vm.currentMachineLimits = None
        vm.limit_status = {key: LimitStatus.DISABLED for key in vm.LIMIT_KEYS}
        vm.limit_values = {key: vm.LIMIT_NONE for key in vm.LIMIT_KEYS}
        vm.toggle_enabled = {key: False for key in vm.LIMIT_KEYS}
        # a tool limit is offered only with the current loaded tool's offset
        # set on its axis: here it is, on both
        vm._tool_set = {"x": True, "z": True}
        vm._offsets = vm._current_offsets()
        handler.onLimitsChanged.connect(vm.onMachineLimitsChanged)
        self.vm = vm

    # -- the machine ----------------------------------------------------------

    def load_tool(self, x_offset=None, z_offset=None):
        """Another tool (or touch-off, or work offset): the offsets change,
        and the positions update as they do on every poll."""
        if x_offset is not None:
            self.vm.positions.offset["x"] = x_offset
        if z_offset is not None:
            self.vm.positions.offset["z"] = z_offset
        self._poll()

    def move_to(self, x=None, z=None):
        """The axes at these machine positions (X on the radius)."""
        if x is not None:
            self.vm.positions.machine["x"] = x
        if z is not None:
            self.vm.positions.machine["z"] = z
        self._poll()

    def _poll(self):
        # what Positions.notify calls, in the view model's order
        self.vm._follow_offsets()
        self.vm.onAbsPositionUpdated()

    # -- the operator ---------------------------------------------------------

    def enable(self, key, value):
        self.vm.limit_values[key] = "%10.3f" % value
        self.vm.toggleLimit(key)
        assert self.status(key) is not LimitStatus.DISABLED

    def disable(self, key):
        assert self.status(key) is not LimitStatus.DISABLED
        self.vm.toggleLimit(key)

    # -- what it shows --------------------------------------------------------

    def pin(self, name):
        return self.vm.latheComponent.comp.getPin(PIN[name]).value

    def status(self, key):
        return self.vm.limit_status[key]


@pytest.fixture
def lathe():
    lathe = Lathe()
    yield lathe
    MachineLimitsHandler._instance = None


# -- a tool limit on the machine -----------------------------------------------

def test_a_z_limit_is_the_offset_plus_its_value(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=120.0)
    lathe.enable("zMinus", -10.0)
    assert lathe.status("zMinus") is LimitStatus.ENABLED
    assert lathe.pin("z-min") == pytest.approx(90.0)


def test_an_x_limit_is_a_diameter_put_on_the_radius(lathe):
    lathe.load_tool(x_offset=10.0)
    lathe.move_to(x=35.0)                       # Ø50 for this tool
    lathe.enable("xMinus", 20.0)
    lathe.enable("xPlus", 80.0)
    assert lathe.pin("x-min") == pytest.approx(10.0 + 10.0)
    assert lathe.pin("x-max") == pytest.approx(10.0 + 40.0)


# -- another tool --------------------------------------------------------------

def test_every_tool_limit_moves_with_the_tool(lathe):
    lathe.load_tool(x_offset=10.0, z_offset=100.0)
    lathe.move_to(x=35.0, z=100.0)
    lathe.enable("xMinus", 20.0)
    lathe.enable("xPlus", 80.0)
    lathe.enable("zMinus", -10.0)
    lathe.enable("zPlus", 5.0)

    # inside all four for the new tool too: written at once
    lathe.load_tool(x_offset=12.0, z_offset=103.0)

    assert lathe.pin("x-min") == pytest.approx(22.0)
    assert lathe.pin("x-max") == pytest.approx(52.0)
    assert lathe.pin("z-min") == pytest.approx(93.0)
    assert lathe.pin("z-max") == pytest.approx(108.0)
    for key in ("xMinus", "xPlus", "zMinus", "zPlus"):
        assert lathe.status(key) is LimitStatus.ENABLED


def test_a_limit_not_in_use_does_not_follow_the_tool(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=100.0)
    lathe.vm.limit_values["zMinus"] = "-10.000"   # typed, never enabled
    lathe.load_tool(z_offset=103.0)
    assert lathe.status("zMinus") is LimitStatus.DISABLED
    assert lathe.pin("z-min") == pytest.approx(Z_MIN)


def test_the_tailstock_stays_where_it_is_on_the_machine(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=100.0)
    lathe.enable("tailstock", 150.0)
    assert lathe.pin("z-max") == pytest.approx(150.0)
    lathe.load_tool(z_offset=120.0)
    assert lathe.pin("z-max") == pytest.approx(150.0)
    assert lathe.status("tailstock") is LimitStatus.ENABLED


def test_a_tool_already_past_its_limit_leaves_it_pending_until_it_is_back(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=95.0)
    lathe.enable("zMinus", -10.0)                 # 90 on the machine
    assert lathe.pin("z-min") == pytest.approx(90.0)

    # a longer tool: its -10 is 98 on the machine, and the axis is at 95
    lathe.load_tool(z_offset=108.0)
    assert lathe.status("zMinus") is LimitStatus.PENDING
    assert lathe.pin("z-min") == pytest.approx(90.0)   # what it had

    lathe.move_to(z=99.0)
    assert lathe.status("zMinus") is LimitStatus.ENABLED
    assert lathe.pin("z-min") == pytest.approx(98.0)


# -- never written past the axis -------------------------------------------------

def test_z_plus_taught_a_rounding_short_of_the_axis_stays_pending(lathe):
    """The handwheels stopping both ways: Z+ taught at 5.0004 is 5.000, under
    the axis, and the tailstock's pin writes - it was off - put it on the
    machine anyway, LinuxCNC on a soft limit."""
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=105.0004)
    lathe.enable("zPlus", 5.0)
    assert lathe.status("zPlus") is LimitStatus.PENDING
    assert lathe.pin("z-max") == pytest.approx(Z_MAX)

    lathe.move_to(z=104.9)
    assert lathe.status("zPlus") is LimitStatus.ENABLED
    assert lathe.pin("z-max") == pytest.approx(105.0)


@pytest.mark.parametrize("key, pin, axis, past, value", [
    ("xMinus", "x-min", "x", 4.0, 10.0),     # Ø10 is radius 5; the axis at 4
    ("xPlus", "x-max", "x", 6.0, 10.0),
    ("zMinus", "z-min", "z", -1.0, 0.0),
    ("zPlus", "z-max", "z", 1.0, 0.0),
])
def test_no_limit_is_written_with_the_axis_past_it(lathe, key, pin, axis, past, value):
    lathe.move_to(**{axis: past})
    before = lathe.pin(pin)
    lathe.enable(key, value)
    assert lathe.status(key) is LimitStatus.PENDING
    assert lathe.pin(pin) == before


def test_a_limit_given_up_is_written_at_once_wherever_the_axis_is(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=104.0)
    lathe.enable("zPlus", 5.0)
    assert lathe.pin("z-max") == pytest.approx(105.0)
    lathe.load_tool(z_offset=98.0)                # 103 now, the axis past it
    assert lathe.status("zPlus") is LimitStatus.PENDING
    lathe.disable("zPlus")
    assert lathe.status("zPlus") is LimitStatus.DISABLED
    assert lathe.pin("z-max") == pytest.approx(Z_MAX)


# -- Z+ and the tailstock share a pin ----------------------------------------------

def test_z_max_is_the_nearer_of_z_plus_and_the_tailstock(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=100.0)
    lathe.enable("tailstock", 150.0)
    lathe.enable("zPlus", 20.0)                   # 120 on the machine
    assert lathe.pin("z-max") == pytest.approx(120.0)
    lathe.disable("zPlus")
    assert lathe.pin("z-max") == pytest.approx(150.0)


def test_an_enabled_tailstock_does_not_write_a_pending_z_plus(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=100.0)
    lathe.enable("tailstock", 150.0)
    lathe.move_to(z=125.0)
    lathe.enable("zPlus", 20.0)                   # 120: the axis is past it
    assert lathe.status("zPlus") is LimitStatus.PENDING
    assert lathe.pin("z-max") == pytest.approx(150.0)


# -- on the limit ----------------------------------------------------------------

def test_one_limit_alone_is_reached_on_it(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=120.0)
    lathe.enable("zMinus", -10.0)
    lathe.move_to(z=90.002)
    assert lathe.status("zMinus") is LimitStatus.REACHED
    lathe.move_to(z=95.0)
    assert lathe.status("zMinus") is LimitStatus.ENABLED


def test_a_limit_is_not_reached_short_of_it(lathe):
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=120.0)
    lathe.enable("zMinus", -10.0)
    lathe.move_to(z=90.01)
    assert lathe.status("zMinus") is LimitStatus.ENABLED


def test_the_screen_is_told_only_of_a_change(lathe):
    """Every position update goes through the limits: while nothing on them
    changes, the screen - some 25 properties and the limits drawing - is not
    told."""
    lathe.load_tool(z_offset=100.0)
    lathe.move_to(z=120.0)
    lathe.enable("zMinus", -10.0)
    told = []
    lathe.vm.limitsChanged.connect(lambda: told.append(1))
    lathe.move_to(z=110.0)
    lathe.move_to(z=100.0)
    assert told == []
    lathe.move_to(z=90.0)                         # on it: REACHED
    assert len(told) == 1


# -- the limit's field -------------------------------------------------------------

TEACH_SEQUENCE = """
import QtQuick
import tabs.manual_turning
Item {
    // the view model's value, as LimitsPanel binds it
    property string modelValue: "--none--"
    property var shown: []
    TeachableLimit {
        id: limit
        value: parent.modelValue
        onCommitted: function(v) { parent.modelValue = v }
    }
    function field(item) {
        if (item.valueFollowsModel !== undefined) return item
        for (var i = 0; i < item.children.length; ++i) {
            var found = field(item.children[i])
            if (found) return found
        }
        return null
    }
    Component.onCompleted: {
        var f = field(limit)
        f.commit("12.5")                   // typed on the numpad
        shown.push(f.text)
        modelValue = "-3.250"              // TeachIn: the view model's new value
        shown.push(f.text)
        f.commit("7")
        modelValue = "1.000"
        shown.push(f.text)
    }
}
"""


def test_teach_in_overwrites_a_typed_value():
    engine = QQmlEngine()
    engine.addImportPath(QML_IMPORT_DIR)
    component = QQmlComponent(engine)
    component.setData(TEACH_SEQUENCE.encode(), QUrl.fromLocalFile(os.path.join(QML_IMPORT_DIR, "teach.qml")))
    item = component.create()
    assert item is not None, [e.toString() for e in component.errors()]
    assert [s.strip() for s in item.property("shown").toVariant()] == ["12.500", "-3.250", "1.000"]
