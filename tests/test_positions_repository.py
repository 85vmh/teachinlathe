"""Tests for PositionsRepository.

The core of it is a differential test: the position arithmetic the DRO has
always shown is restated here verbatim as a reference and the two are compared
over randomised machine states. If the repository ever drifts from what the DRO
used to show, this fails.
"""

import math
import random
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt6.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.repositories.positions_repository import (  # noqa: E402
    Axis, Position, Positions,
)
from teachinlathe.repositories.status_repository import StatusRepository  # noqa: E402

UNITS_INCH, UNITS_MM = 1, 2


class FakeStat:
    def __init__(self, **fields):
        self.joints = 2
        self.joint = [{"homed": 1}, {"homed": 1}]
        defaults = dict(
            actual_position=(0.0,) * 9,
            position=(0.0,) * 9,
            dtg=(0.0,) * 9,
            g5x_offset=(0.0,) * 9,
            g92_offset=(0.0,) * 9,
            tool_offset=(0.0,) * 9,
            rotation_xy=0.0,
            program_units=UNITS_MM,
        )
        defaults.update(fields)
        for name, value in defaults.items():
            setattr(self, name, value)

    def poll(self):
        pass


class FakeIni:
    def __init__(self, metric=True, actual=True, axes=(0, 2)):
        self.is_metric = metric
        self.position_feedback_is_actual = actual
        self.axis_numbers = list(axes)
        self.no_force_homing = False


def reference_positions(stat, axis_numbers, machine_units, report_actual):
    """The original ``Position._update``, restated. The behaviour preserved."""
    pos = stat.actual_position if report_actual else stat.position
    dtg = stat.dtg
    g5x_offset = stat.g5x_offset
    g92_offset = stat.g92_offset
    tool_offset = stat.tool_offset

    rel = [0] * 9
    for axis in axis_numbers:
        rel[axis] = pos[axis] - g5x_offset[axis] - tool_offset[axis]

    if stat.rotation_xy != 0:
        t = math.radians(-stat.rotation_xy)
        xr = rel[0] * math.cos(t) - rel[1] * math.sin(t)
        yr = rel[0] * math.sin(t) + rel[1] * math.cos(t)
        rel[0] = xr
        rel[1] = yr

    for axis in axis_numbers:
        rel[axis] -= g92_offset[axis]

    if machine_units == UNITS_MM:
        factors = [1.0 / 25.4] * 3 + [1] * 3 + [1.0 / 25.4] * 3
    else:
        factors = [25.4] * 3 + [1] * 3 + [25.4] * 3

    if stat.program_units != machine_units:
        pos = [pos[i] * factors[i] for i in range(9)]
        rel = [rel[i] * factors[i] for i in range(9)]
        dtg = [dtg[i] * factors[i] for i in range(9)]

    return tuple(pos), tuple(rel), tuple(dtg)


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def build(qt_app, stat, ini):
    status = StatusRepository(stat=stat, ini=ini)
    status.stop()
    return Positions(status=status, ini=ini), status


def nine(rng, scale=100.0):
    return tuple(round(rng.uniform(-scale, scale), 4) for _ in range(9))


@pytest.mark.parametrize("seed", range(40))
def test_matches_reference_arithmetic(qt_app, seed):
    rng = random.Random(seed)
    metric = rng.choice([True, False])
    actual = rng.choice([True, False])
    axes = rng.choice([(0, 2), (0, 1, 2), (0, 1, 2, 3, 4, 5)])

    stat = FakeStat(
        actual_position=nine(rng), position=nine(rng), dtg=nine(rng),
        g5x_offset=nine(rng, 50), g92_offset=nine(rng, 10),
        tool_offset=nine(rng, 20),
        rotation_xy=rng.choice([0.0, 0.0, 30.0, -45.0]),
        program_units=rng.choice([UNITS_INCH, UNITS_MM]),
    )
    ini = FakeIni(metric=metric, actual=actual, axes=axes)
    positions, _ = build(qt_app, stat, ini)

    want = reference_positions(stat, list(axes), UNITS_MM if metric else UNITS_INCH, actual)
    got = (positions.abs, positions.rel, positions.dtg)

    for frame, (w, g) in enumerate(zip(want, got)):
        for i in range(9):
            assert g[i] == pytest.approx(w[i], abs=1e-9), \
                "frame %d axis %d" % (frame, i)


def test_rel_subtracts_g5x_tool_and_g92(qt_app):
    stat = FakeStat(
        actual_position=(10.0, 0, 20.0) + (0.0,) * 6,
        g5x_offset=(1.0, 0, 2.0) + (0.0,) * 6,
        tool_offset=(0.5, 0, 3.0) + (0.0,) * 6,
        g92_offset=(0.25, 0, 0.5) + (0.0,) * 6,
    )
    positions, _ = build(qt_app, stat, FakeIni())

    assert positions.rel[Axis.X] == pytest.approx(10.0 - 1.0 - 0.5 - 0.25)
    assert positions.rel[Axis.Z] == pytest.approx(20.0 - 2.0 - 3.0 - 0.5)


def test_offset_property_maps_machine_to_work(qt_app):
    stat = FakeStat(
        actual_position=(10.0, 0, 20.0) + (0.0,) * 6,
        g5x_offset=(1.0, 0, 2.0) + (0.0,) * 6,
        tool_offset=(0.5, 0, 3.0) + (0.0,) * 6,
        g92_offset=(0.25, 0, 0.5) + (0.0,) * 6,
    )
    positions, _ = build(qt_app, stat, FakeIni())
    x = positions.getXPosition()
    assert isinstance(x, Position)
    assert x.offset == pytest.approx(1.0 + 0.5 + 0.25)


def test_axes_the_machine_does_not_have_stay_zero(qt_app):
    stat = FakeStat(actual_position=(1.0, 2.0, 3.0) + (4.0,) * 6,
                    g5x_offset=(0.5,) * 9)
    positions, _ = build(qt_app, stat, FakeIni(axes=(0, 2)))
    # Y is not a machine axis here, so rel[Y] is never computed.
    assert positions.rel[Axis.Y] == 0.0
    assert positions.rel[Axis.X] == pytest.approx(0.5)


def test_commanded_position_used_when_feedback_is_not_actual(qt_app):
    stat = FakeStat(actual_position=(1.0,) * 9, position=(2.0,) * 9)
    on_actual, _ = build(qt_app, stat, FakeIni(actual=True))
    on_commanded, _ = build(qt_app, stat, FakeIni(actual=False))
    assert on_actual.abs[Axis.X] == 1.0
    assert on_commanded.abs[Axis.X] == 2.0


def test_units_convert_when_program_disagrees_with_machine(qt_app):
    stat = FakeStat(actual_position=(25.4,) * 9, program_units=UNITS_INCH)
    positions, _ = build(qt_app, stat, FakeIni(metric=True))
    # Metric machine running in G20: millimetres shown as inches.
    assert positions.abs[Axis.X] == pytest.approx(1.0)
    # Rotary axes are not linear, so they are left alone.
    assert positions.abs[Axis.A] == pytest.approx(25.4)


def test_units_do_not_convert_when_they_agree(qt_app):
    stat = FakeStat(actual_position=(25.4,) * 9, program_units=UNITS_MM)
    positions, _ = build(qt_app, stat, FakeIni(metric=True))
    assert positions.abs[Axis.X] == pytest.approx(25.4)


def test_notify_fires_on_a_move_and_stays_quiet_otherwise(qt_app):
    stat = FakeStat(actual_position=(1.0,) * 9)
    positions, status = build(qt_app, stat, FakeIni())
    seen = []
    positions.notify(lambda rel: seen.append(rel[Axis.X]))

    status.poll()
    assert seen == []                     # nothing moved

    stat.actual_position = (5.0,) * 9
    status.poll()
    assert seen == [5.0]

    status.poll()
    assert seen == [5.0]                  # still nothing moved


def test_teach_in_returns_work_or_machine_coordinates(qt_app):
    stat = FakeStat(actual_position=(10.0, 0, 20.0) + (0.0,) * 6,
                    g5x_offset=(4.0, 0, 5.0) + (0.0,) * 6)
    positions, _ = build(qt_app, stat, FakeIni())
    assert positions.teachInX() == pytest.approx(6.0)
    assert positions.teachInX(machineCoordinate=True) == pytest.approx(10.0)
    assert positions.teachInZ() == pytest.approx(15.0)
    assert positions.teachInZ(machineCoordinate=True) == pytest.approx(20.0)


def test_notify_accepts_slots_that_take_the_value_or_not(qt_app):
    stat = FakeStat(actual_position=(1.0,) * 9)
    positions, status = build(qt_app, stat, FakeIni())

    calls = {"none": 0, "one": [], "any": []}

    def no_arg():
        calls["none"] += 1

    def one_arg(rel):
        calls["one"].append(rel[Axis.X])

    def any_args(*args):
        calls["any"].append(args)

    positions.notify(no_arg)
    positions.notify(one_arg)
    positions.notify(any_args)

    stat.actual_position = (3.0,) * 9
    status.poll()

    assert calls["none"] == 1
    assert calls["one"] == [3.0]
    assert len(calls["any"]) == 1
