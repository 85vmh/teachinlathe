"""Tests for StatusRepository, driven by a fake linuxcnc.stat."""

import logging
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt6.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.repositories.status_repository import (  # noqa: E402
    StatusChannel, StatusRepository,
)


class FakeStat:
    """Stands in for linuxcnc.stat: fields are set, poll() is a no-op."""

    def __init__(self, **fields):
        self.joints = fields.pop("joints", 2)
        self.joint = fields.pop("joint", [{"homed": 1}, {"homed": 1}])
        self.polls = 0
        for name, value in fields.items():
            setattr(self, name, value)

    def poll(self):
        self.polls += 1


class FakeIni:
    def __init__(self, no_force_homing=False):
        self.no_force_homing = no_force_homing


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def repo(qt_app):
    def _make(stat=None, **ini_kwargs):
        stat = stat or FakeStat(task_mode=1, program_units=2, tool_in_spindle=3)
        r = StatusRepository(stat=stat, ini=FakeIni(**ini_kwargs))
        r.stop()          # tests drive poll() by hand
        return r
    return _make


def test_channel_reads_the_field(repo):
    r = repo()
    assert r.task_mode.value == 1
    assert r.tool_in_spindle.value == 3


def test_same_channel_object_is_returned_each_time(repo):
    r = repo()
    assert r.task_mode is r.task_mode
    assert r.channel("task_mode") is r.task_mode


def test_unknown_field_raises_rather_than_returning_a_dead_channel(repo):
    r = repo()
    with pytest.raises(AttributeError, match="no field"):
        r.not_a_real_field


def test_real_attributes_are_not_shadowed_by_channels(repo):
    stat = FakeStat(task_mode=1)
    r = repo(stat)
    # .stat must be the stat, not a StatusChannel called "stat"
    assert r.stat is stat
    assert not isinstance(r.stat, StatusChannel)


def test_poll_emits_only_on_change(repo):
    stat = FakeStat(task_mode=1)
    r = repo(stat)
    seen = []
    r.task_mode.notify(seen.append)

    r.poll()                      # unchanged
    assert seen == []

    stat.task_mode = 2
    r.poll()
    assert seen == [2]

    r.poll()                      # unchanged again
    assert seen == [2]


def test_poll_survives_a_field_that_cannot_be_compared(repo):
    class Hostile:
        def __eq__(self, other):
            raise RuntimeError("no comparing me")

    stat = FakeStat(task_mode=1, file=Hostile())
    r = repo(stat)
    r.file                        # create the channel
    seen = []
    r.task_mode.notify(seen.append)

    stat.task_mode = 7
    r.poll()                      # must not be stopped by the hostile field

    assert seen == [7]


def test_program_units_formats_as_text(repo):
    r = repo(FakeStat(program_units=2))
    assert str(r.program_units) == "mm"
    assert r.program_units.getString("long") == "Millimeters"

    r2 = repo(FakeStat(program_units=1))
    assert str(r2.program_units) == "in"


def test_notify_with_string_hands_the_slot_the_text(repo):
    stat = FakeStat(program_units=1)
    r = repo(stat)
    seen = []
    r.program_units.notify(seen.append, "string")

    stat.program_units = 2
    r.poll()

    assert seen == ["mm"]


def test_onValueChanged_is_the_same_as_notify(repo):
    stat = FakeStat(task_mode=1)
    r = repo(stat)
    seen = []
    r.task_mode.onValueChanged(seen.append)
    stat.task_mode = 5
    r.poll()
    assert seen == [5]


def test_allHomed_checks_every_joint(repo):
    r = repo(FakeStat(joint=[{"homed": 1}, {"homed": 1}], joints=2))
    assert r.allHomed() is True

    r2 = repo(FakeStat(joint=[{"homed": 1}, {"homed": 0}], joints=2))
    assert r2.allHomed() is False


def test_allHomed_is_true_when_homing_is_not_forced(repo):
    r = repo(FakeStat(joint=[{"homed": 0}, {"homed": 0}], joints=2),
             no_force_homing=True)
    assert r.allHomed() is True


def test_all_axes_homed_is_a_channel_although_stat_has_no_such_field(repo):
    stat = FakeStat(joint=[{"homed": 0}], joints=1)
    r = repo(stat)
    assert r.all_axes_homed.value is False

    seen = []
    r.all_axes_homed.notify(seen.append)
    stat.joint = [{"homed": 1}]
    r.poll()
    assert seen == [True]


def test_channel_behaves_like_its_value(repo):
    r = repo(FakeStat(task_mode=2, homed=(1, 0, 1)))
    assert int(r.task_mode) == 2
    assert bool(r.task_mode) is True
    assert r.homed[1] == 0


# --- grouped fields: spindle / joint / axis ---------------------------------

def grouped_stat(**overrides):
    stat = FakeStat(task_mode=1)
    stat.spindle = [{"override": 1.0, "direction": 0, "speed": 0.0}
                    for _ in range(8)]
    stat.joint = [{"homed": 1, "fault": 0} for _ in range(2)]
    stat.axis = [{"velocity": 0.0} for _ in range(3)]
    for name, value in overrides.items():
        setattr(stat, name, value)
    return stat


def test_spindle_exposes_a_channel_per_key(repo):
    r = repo(grouped_stat())
    assert r.spindle[0].override.value == 1.0
    assert r.spindle[0].direction.value == 0
    assert len(r.spindle) == 8


def test_spindle_channel_emits_on_change(repo):
    stat = grouped_stat()
    r = repo(stat)
    seen = []
    r.spindle[0].override.notify(seen.append)

    stat.spindle[0]["override"] = 0.75
    r.poll()
    assert seen == [0.75]

    r.poll()
    assert seen == [0.75]          # unchanged, so quiet


def test_one_spindle_changing_leaves_the_others_alone(repo):
    stat = grouped_stat()
    r = repo(stat)
    seen = []
    r.spindle[1].override.notify(lambda v: seen.append(("s1", v)))

    stat.spindle[0]["override"] = 0.5
    r.poll()
    assert seen == []


def test_joint_and_axis_are_grouped_too(repo):
    stat = grouped_stat()
    r = repo(stat)
    assert r.joint[0].homed.value == 1
    assert r.axis[0].velocity.value == 0.0

    seen = []
    r.joint[1].homed.notify(seen.append)
    stat.joint[1]["homed"] = 0
    r.poll()
    assert seen == [0]


def test_group_is_built_once(repo):
    r = repo(grouped_stat())
    assert r.spindle is r.spindle
    assert r.spindle[0].override is r.spindle[0].override


def test_item_status_indexes_by_key(repo):
    r = repo(grouped_stat())
    assert r.spindle[0]["override"] == 1.0


def test_signal_is_an_alias_for_valueChanged(repo):
    stat = grouped_stat()
    r = repo(stat)
    seen = []
    # the older spelling, still used by mainwindow
    r.task_mode.signal.connect(seen.append)
    r.spindle[0].override.signal.connect(lambda v: seen.append(("s", v)))

    stat.task_mode = 9
    stat.spindle[0]["override"] = 0.25
    r.poll()

    assert seen == [9, ("s", 0.25)]


def test_unknown_channel_returns_the_getattr_default(repo):
    r = repo(grouped_stat())
    # programs_action_source relies on this for optional channels
    assert getattr(r, "no_such_channel", None) is None


# --- slot arity: Qt drops the argument for a slot that takes none -----------

class Listener:
    """Slots of each shape a call site actually uses."""

    def __init__(self):
        self.no_arg = 0
        self.one_arg = []
        self.optional = []
        self.varargs = []

    def on_changed(self):                      # lathe_tool_table.refreshModel
        self.no_arg += 1

    def on_value(self, value):                 # mainwindow.onTaskModeChanged
        self.one_arg.append(value)

    def on_optional(self, value=None):         # DroViewModel.updateValues
        self.optional.append(value)

    def on_any(self, *args):                   # ProgramsDroViewModel._update
        self.varargs.append(args)


def test_notify_accepts_a_slot_that_takes_no_argument(repo):
    stat = FakeStat(tool_in_spindle=1)
    r = repo(stat)
    listener = Listener()
    r.tool_in_spindle.notify(listener.on_changed)

    stat.tool_in_spindle = 4
    r.poll()

    assert listener.no_arg == 1


def test_notify_passes_the_value_to_slots_that_want_it(repo):
    stat = FakeStat(tool_in_spindle=1)
    r = repo(stat)
    listener = Listener()
    r.tool_in_spindle.notify(listener.on_value)
    r.tool_in_spindle.notify(listener.on_optional)
    r.tool_in_spindle.notify(listener.on_any)

    stat.tool_in_spindle = 4
    r.poll()

    assert listener.one_arg == [4]
    assert listener.optional == [4]
    assert listener.varargs == [(4,)]


def test_every_slot_shape_can_share_one_channel(repo):
    stat = FakeStat(tool_in_spindle=1)
    r = repo(stat)
    listener = Listener()
    for slot in (listener.on_changed, listener.on_value,
                 listener.on_optional, listener.on_any):
        r.tool_in_spindle.notify(slot)

    stat.tool_in_spindle = 7
    r.poll()

    assert (listener.no_arg, listener.one_arg) == (1, [7])
    assert (listener.optional, listener.varargs) == ([7], [(7,)])


# --- a failing poll is reported once, not on every tick ---------------------

class BrokenStat(FakeStat):
    def __init__(self, **fields):
        super().__init__(**fields)
        self.failing = True

    def poll(self):
        self.polls += 1
        if self.failing:
            raise RuntimeError("emcStatusBuffer invalid err=3")


def test_a_failing_poll_is_logged_once_and_again_on_recovery(repo, caplog):
    stat = BrokenStat(task_mode=1)
    r = repo(stat)

    with caplog.at_level(logging.ERROR,
                         logger="teachinlathe.repositories.status_repository"):
        for _ in range(10):
            r.poll()

    errors = [rec for rec in caplog.records if rec.levelno >= logging.ERROR]
    assert len(errors) == 1, "a poll failing every tick must not log every tick"
    assert stat.polls == 10, "it must keep trying"


def test_recovery_is_reported_and_then_it_stays_quiet(repo, caplog):
    stat = BrokenStat(task_mode=1)
    r = repo(stat)
    logger_name = "teachinlathe.repositories.status_repository"

    with caplog.at_level(logging.INFO, logger=logger_name):
        r.poll()
        r.poll()
        stat.failing = False
        r.poll()
        r.poll()
        r.poll()

    messages = [rec.getMessage() for rec in caplog.records]
    assert sum("recovered" in m for m in messages) == 1


def test_channels_keep_updating_after_a_recovery(repo):
    stat = BrokenStat(task_mode=1)
    r = repo(stat)
    seen = []
    r.task_mode.notify(seen.append)

    r.poll()                      # fails, nothing changes
    assert seen == []

    stat.failing = False
    stat.task_mode = 6
    r.poll()
    assert seen == [6]


def test_a_listener_may_ask_for_a_new_channel_while_polling(repo):
    """A slot woken by one channel often reads another; the first time it
    does, that channel is created - during the poll loop."""
    stat = FakeStat(task_mode=1, tool_in_spindle=0, enabled=True)
    r = repo(stat)
    seen = []

    def on_change(value):
        # 'enabled' has no channel yet: this creates one, mid-poll.
        seen.append((value, r.enabled.value))

    r.tool_in_spindle.notify(on_change)
    stat.tool_in_spindle = 3
    r.poll()

    assert seen == [(3, True)]
