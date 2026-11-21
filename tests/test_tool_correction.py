"""A correction of the current loaded tool at an M1: what it does to the
tool's offsets (programs/model/tool_correction.py), what the remap does with it
(subroutines/m1_remap.ngc), and when the app arms its pins and clears them
(programs/logic/tool_correction_use_case.py).

What is pinned down here:

* ``dx`` is a diameter, ``dz`` a shift along Z, where the tool cuts: the X
  offset, a radius, takes half of ``dx``; Z takes ``dz`` as it is.
* Nothing under half a micron is a correction; over MAX_CORRECTION either way
  is refused - by the app, and by the remap with the same limit.
* A correction is armed only while the program waits at an M1 with a tool
  loaded: the values first, then apply. Its pins are cleared - so that it never
  carries over to another stop - once the remap applied it, once it read them
  (at-stop off), at the next M1, and when the program ends or is aborted.
"""

from __future__ import annotations

import re
import types
from pathlib import Path

import pytest
from PyQt6.QtCore import QObject, pyqtSignal

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent as Pins
from teachinlathe.programs.logic.tool_correction_use_case import ToolCorrectionUseCase
from teachinlathe.programs.model.run_moment import RunState
from teachinlathe.programs.model.tool_correction import (
    MAX_CORRECTION, ToolCorrection, check, corrected_offsets,
)

REMAP = Path(__file__).resolve().parents[1] / "subroutines" / "m1_remap.ngc"


# ── the correction ──────────────────────────────────────────────────────

def test_x_offset_takes_half_of_the_diameter_correction():
    # a part 0.04 too big on the diameter: the X offset, a radius, loses 0.02
    x, z = corrected_offsets(10.0, -50.0, ToolCorrection(dx=-0.04, dz=0.0))
    assert x == pytest.approx(9.98)
    assert z == pytest.approx(-50.0)


def test_z_offset_takes_the_z_correction_as_it_is():
    x, z = corrected_offsets(10.0, -50.0, ToolCorrection(dx=0.0, dz=-0.02))
    assert x == pytest.approx(10.0)
    assert z == pytest.approx(-50.02)


@pytest.mark.parametrize("dx, effect", [(-0.04, "smaller"), (0.04, "bigger")])
def test_what_dx_does_to_the_diameter(dx, effect):
    assert ToolCorrection(dx=dx).diameter_effect == effect


@pytest.mark.parametrize("dz, side", [(-0.02, "Z-"), (0.02, "Z+")])
def test_where_dz_moves_the_cut(dz, side):
    assert ToolCorrection(dz=dz).z_side == side


def test_under_half_a_micron_is_no_correction():
    tiny = ToolCorrection(dx=0.0004, dz=-0.0004)
    assert tiny.empty and not tiny.changes_x and not tiny.changes_z
    assert check(tiny) != ""
    assert ToolCorrection(dx=0.0005).changes_x
    assert ToolCorrection(dz=-0.0005).changes_z


@pytest.mark.parametrize("correction", [
    ToolCorrection(dx=MAX_CORRECTION), ToolCorrection(dx=-MAX_CORRECTION),
    ToolCorrection(dz=MAX_CORRECTION), ToolCorrection(dz=-MAX_CORRECTION),
    ToolCorrection(dx=0.04, dz=-0.02),
])
def test_up_to_the_largest_correction_can_be_applied(correction):
    assert check(correction) == ""


@pytest.mark.parametrize("correction", [
    ToolCorrection(dx=MAX_CORRECTION + 0.001), ToolCorrection(dx=-MAX_CORRECTION - 0.001),
    ToolCorrection(dz=MAX_CORRECTION + 0.001), ToolCorrection(dz=-MAX_CORRECTION - 0.001),
])
def test_over_the_largest_correction_is_refused(correction):
    assert check(correction) != ""


# ── the remap ───────────────────────────────────────────────────────────

def _remap_code():
    """The remap's lines, without their comments."""
    return [re.sub(r"\([^)]*\)", "", line).strip() for line in REMAP.read_text().splitlines()]


def test_the_remap_refuses_past_the_same_largest_correction():
    code = _remap_code()
    limit = next(line for line in code if line.startswith("#<max_correction>"))
    assert float(limit.split("=")[1]) == MAX_CORRECTION
    assert any("ABS[#<dx>] GT #<max_correction>" in line and "ABS[#<dz>] GT #<max_correction>" in line
               for line in code)


def test_the_remap_adds_half_of_dx_to_the_x_offset_as_a_radius():
    code = _remap_code()
    g10 = code.index("G10 L1 P#5400 X[#5401 + #<dx> / 2] Z[#5403 + #<dz>]")
    # in G8, X words are radii: in G7 the interpreter would halve it again
    assert "G8" in code[:g10][-3:]
    assert code[g10 + 1] == "G43"


def test_the_remap_reads_the_pins_the_app_writes():
    code = "\n".join(_remap_code())
    # motion.digital-in-02 apply, analog-in-00 X, analog-in-01 Z; out-02 applied, out-03 at the stop
    assert "M66 P2 L0" in code and "M66 E0 L0" in code and "M66 E1 L0" in code
    assert "M64 P2" in code and "M64 P3" in code and "M65 P3" in code
    # a preview, or no correction armed, reads 0, not the Optional Stop's 1
    assert code.index("#5399 = 0") < code.index("M66 P2 L0")


def test_the_remap_applies_no_correction_under_cutter_compensation():
    code = _remap_code()
    correct = code.index("o<correct> if [#5399 EQ 1]")
    g10 = next(i for i, line in enumerate(code) if line.startswith("G10 L1"))
    assert any("#<_ccomp> NE 400" in line for line in code[correct:g10])


# ── when the pins are armed and cleared ─────────────────────────────────

class _Pin:
    def __init__(self, value):
        self.value = value


class _Component:
    """The correction's pins, and the listeners on the remap's."""

    def __init__(self):
        self.pins = {Pins.PinInspectCorrectionX: _Pin(0.0), Pins.PinInspectCorrectionZ: _Pin(0.0),
                     Pins.PinInspectCorrectionApply: _Pin(False)}
        self.listeners = {}
        self.writes = []

    def getPin(self, name):
        pin = self.pins[name]
        component = self

        class _Recording:
            @property
            def value(self):
                return pin.value

            @value.setter
            def value(self, value):
                component.writes.append(name)
                pin.value = value

        return _Recording()

    def addListener(self, name, callback):
        self.listeners[name] = callback

    def remap_sets(self, name, value):
        self.listeners[name](value)

    @property
    def armed(self):
        return (self.pins[Pins.PinInspectCorrectionApply].value, self.pins[Pins.PinInspectCorrectionX].value,
                self.pins[Pins.PinInspectCorrectionZ].value)


class _Run(QObject):
    changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.state = RunState.RUNNING
        self.waiting_for = ""
        self.moment = types.SimpleNamespace(tool=3)

    def set(self, state, waiting_for="", tool=None):
        self.state, self.waiting_for = state, waiting_for
        if tool is not None:
            self.moment = types.SimpleNamespace(tool=tool)
        self.changed.emit()


class _Tools(QObject):
    toolsChanged = pyqtSignal()

    def find_holder(self, tool):
        return types.SimpleNamespace(x_offset=10.0, z_offset=-50.0) if tool == 3 else None


@pytest.fixture
def setup():
    comp, run = _Component(), _Run()
    use_case = ToolCorrectionUseCase(run, tools=_Tools(), hal=types.SimpleNamespace(comp=comp))
    return use_case, comp, run


CLEAR = (False, 0.0, 0.0)
CORRECTION = ToolCorrection(dx=-0.04, dz=0.02)


def _at_m1(use_case, comp, run):
    run.set(RunState.WAITING, "M1")
    comp.remap_sets(Pins.PinInspectAtStop, True)
    assert use_case.available


def test_a_correction_is_armed_only_at_an_m1_with_a_tool(setup):
    use_case, comp, run = setup
    assert not use_case.available
    assert use_case.arm(CORRECTION) != ""
    run.set(RunState.WAITING, "M0")
    assert not use_case.available and use_case.arm(CORRECTION) != ""
    run.set(RunState.WAITING, "M1", tool=0)
    assert not use_case.available and use_case.arm(CORRECTION) != ""
    assert comp.armed == CLEAR


def test_arming_writes_the_values_before_apply(setup):
    use_case, comp, run = setup
    _at_m1(use_case, comp, run)
    comp.writes.clear()
    assert use_case.arm(CORRECTION) == ""
    assert comp.armed == (True, -0.04, 0.02)
    assert comp.writes.index(Pins.PinInspectCorrectionApply) > comp.writes.index(Pins.PinInspectCorrectionX)
    assert comp.writes.index(Pins.PinInspectCorrectionApply) > comp.writes.index(Pins.PinInspectCorrectionZ)
    armed = use_case.armed
    assert (armed.tool, armed.correction, armed.offsets) == (3, CORRECTION, (10.0, -50.0))
    assert use_case.expected_offsets(3, CORRECTION) == pytest.approx((9.98, -49.98))


def test_a_correction_refused_arms_nothing(setup):
    use_case, comp, run = setup
    _at_m1(use_case, comp, run)
    assert use_case.arm(ToolCorrection(dx=MAX_CORRECTION + 0.1)) != ""
    assert use_case.arm(ToolCorrection()) != ""
    assert use_case.armed is None and comp.armed == CLEAR


def test_disarming_clears_the_pins(setup):
    use_case, comp, run = setup
    _at_m1(use_case, comp, run)
    use_case.arm(CORRECTION)
    use_case.disarm()
    assert use_case.armed is None and comp.armed == CLEAR


@pytest.mark.parametrize("applied_first", [True, False])
def test_once_applied_the_pins_are_cleared_and_it_is_the_last_applied(setup, applied_first):
    # the remap's applied pin can come before at-stop goes off, or after it
    use_case, comp, run = setup
    _at_m1(use_case, comp, run)
    use_case.arm(CORRECTION)
    applied = []
    use_case.applied.connect(applied.append)
    if applied_first:
        comp.remap_sets(Pins.PinInspectCorrectionApplied, True)
        comp.remap_sets(Pins.PinInspectAtStop, False)
    else:
        comp.remap_sets(Pins.PinInspectAtStop, False)
        comp.remap_sets(Pins.PinInspectCorrectionApplied, True)
    assert comp.armed == CLEAR and use_case.armed is None
    assert [a.correction for a in applied] == [CORRECTION]
    assert use_case.last_applied.correction == CORRECTION


def test_once_the_remap_read_the_pins_they_are_cleared(setup):
    use_case, comp, run = setup
    _at_m1(use_case, comp, run)
    use_case.arm(CORRECTION)
    comp.remap_sets(Pins.PinInspectAtStop, False)
    assert comp.armed == CLEAR and use_case.armed is None


def test_the_next_m1_starts_with_nothing_armed_nor_applied(setup):
    use_case, comp, run = setup
    _at_m1(use_case, comp, run)
    use_case.arm(CORRECTION)
    comp.remap_sets(Pins.PinInspectCorrectionApplied, True)
    comp.remap_sets(Pins.PinInspectAtStop, False)
    run.set(RunState.RUNNING)
    _at_m1(use_case, comp, run)
    assert use_case.last_applied is None and use_case.armed is None and comp.armed == CLEAR


def test_the_end_of_the_program_clears_everything(setup):
    use_case, comp, run = setup
    _at_m1(use_case, comp, run)
    use_case.arm(CORRECTION)
    run.set(RunState.IDLE)
    assert not use_case.available
    assert use_case.armed is None and use_case.last_applied is None and comp.armed == CLEAR
