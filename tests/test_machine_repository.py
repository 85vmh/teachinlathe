"""Tests for MachineRepository.

The axis-to-joint mapping is the part worth pinning down: on this lathe X is
joint 0 and Z is joint 1, which is *not* their index in a nine-axis tuple
(0 and 2). Homing the wrong joint moves the wrong axis.
"""

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import linuxcnc  # noqa: E402
from PyQt5.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.repositories.machine_repository import (  # noqa: E402
    ALL_JOINTS, MachineRepository,
)
from teachinlathe.repositories.status_repository import StatusRepository  # noqa: E402


class FakeStat:
    def __init__(self, **fields):
        self.joints = 2
        self.joint = [{"homed": 1}, {"homed": 1}]
        defaults = dict(task_state=linuxcnc.STATE_ON,
                        task_mode=linuxcnc.MODE_MANUAL,
                        interp_state=linuxcnc.INTERP_IDLE,
                        state=linuxcnc.RCS_DONE)
        defaults.update(fields)
        for name, value in defaults.items():
            setattr(self, name, value)

    def poll(self):
        pass


class FakeIni:
    def __init__(self, coordinates="xz"):
        self.coordinates = coordinates
        self.no_force_homing = False


class FakeCommands:
    def __init__(self, allow_mode=True):
        self.allow_mode = allow_mode
        self.modes = []

    def set_task_mode(self, mode):
        if not self.allow_mode:
            return False
        self.modes.append(mode)
        return True


class FakeCommand:
    def __init__(self):
        self.states = []
        self.homed = []
        self.unhomed = []
        self.teleop = []

    def state(self, value):
        self.states.append(value)

    def home(self, jnum):
        self.homed.append(jnum)

    def unhome(self, jnum):
        self.unhomed.append(jnum)

    def teleop_enable(self, value):
        self.teleop.append(value)


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def repo(qt_app):
    def _make(stat=None, coordinates="xz", allow_mode=True):
        stat = stat or FakeStat()
        ini = FakeIni(coordinates)
        status = StatusRepository(stat=stat, ini=ini)
        status.stop()
        commands = FakeCommands(allow_mode)
        cmd = FakeCommand()
        r = MachineRepository(status=status, commands=commands, command=cmd, ini=ini)
        return r, stat, status, commands, cmd
    return _make


# -- axis to joint ----------------------------------------------------------

def test_lathe_axis_letters_map_to_joint_numbers(repo):
    r, *_ = repo(coordinates="xz")
    assert r.joint_for_axis("x") == 0
    assert r.joint_for_axis("Z") == 1, "Z is joint 1 on an XZ lathe, not 2"


def test_mill_axis_letters_map_by_position_too(repo):
    r, *_ = repo(coordinates="xyz")
    assert (r.joint_for_axis("x"), r.joint_for_axis("y"), r.joint_for_axis("z")) == (0, 1, 2)


def test_an_axis_the_machine_lacks_is_rejected(repo):
    r, *_ = repo(coordinates="xz")
    with pytest.raises(ValueError, match="COORDINATES"):
        r.joint_for_axis("y")


def test_a_joint_number_passes_straight_through(repo):
    r, *_ = repo()
    assert r.joint_for_axis(1) == 1


# -- homing -----------------------------------------------------------------

def test_homing_an_axis_goes_manual_teleop_off_then_homes(repo):
    r, _, _, commands, cmd = repo()
    assert r.home_axis("z") is True
    assert commands.modes == [linuxcnc.MODE_MANUAL]
    assert cmd.teleop == [False]
    assert cmd.homed == [1]


def test_homing_all_uses_the_all_joints_sentinel(repo):
    r, _, _, _, cmd = repo()
    r.home_all()
    assert cmd.homed == [ALL_JOINTS]


def test_homing_an_unknown_axis_does_nothing(repo):
    r, _, _, _, cmd = repo(coordinates="xz")
    assert r.home_axis("y") is False
    assert cmd.homed == []


def test_homing_fails_when_manual_mode_is_refused(repo):
    r, _, _, _, cmd = repo(allow_mode=False)
    assert r.home_axis("x") is False
    assert cmd.homed == []


def test_unhome_axis(repo):
    r, _, _, _, cmd = repo()
    assert r.unhome_axis("x") is True
    assert cmd.unhomed == [0]


def test_is_axis_homed_reads_the_right_joint(repo):
    stat = FakeStat()
    stat.joint = [{"homed": 1}, {"homed": 0}]
    r, *_ = repo(stat)
    assert r.is_axis_homed("x") is True
    assert r.is_axis_homed("z") is False
    assert r.all_homed is False


# -- power and e-stop -------------------------------------------------------

def test_estop_and_reset(repo):
    r, _, _, _, cmd = repo()
    r.estop()
    r.reset_estop()
    assert cmd.states == [linuxcnc.STATE_ESTOP, linuxcnc.STATE_ESTOP_RESET]


def test_toggle_estop_depends_on_the_current_state(repo):
    r, stat, status, _, cmd = repo(FakeStat(task_state=linuxcnc.STATE_ESTOP))
    assert r.is_estopped is True
    r.toggle_estop()
    assert cmd.states == [linuxcnc.STATE_ESTOP_RESET]

    stat.task_state = linuxcnc.STATE_ON
    r.toggle_estop()
    assert cmd.states[-1] == linuxcnc.STATE_ESTOP


def test_power_on_and_off(repo):
    r, _, _, _, cmd = repo()
    r.power_off()
    r.power_on()
    assert cmd.states == [linuxcnc.STATE_OFF, linuxcnc.STATE_ON]


def test_toggle_power(repo):
    r, stat, _, _, cmd = repo(FakeStat(task_state=linuxcnc.STATE_OFF))
    assert r.is_on is False
    r.toggle_power()
    assert cmd.states == [linuxcnc.STATE_ON]


def test_power_cannot_be_switched_on_while_estopped(repo):
    r, *_ = repo(FakeStat(task_state=linuxcnc.STATE_ESTOP))
    ok, reason = r.can_power_on()
    assert ok is False
    assert "E-stop" in reason


def test_power_may_be_switched_on_once_the_estop_is_reset(repo):
    r, *_ = repo(FakeStat(task_state=linuxcnc.STATE_ESTOP_RESET))
    assert r.can_power_on() == (True, "")


def test_state_change_is_announced(repo):
    r, stat, status, _, _ = repo()
    seen = []
    r.stateChanged.connect(lambda: seen.append(True))

    stat.task_state = linuxcnc.STATE_OFF
    status.poll()

    assert seen == [True]


def test_homing_is_refused_with_a_reason_while_the_machine_is_off(repo):
    r, *_ = repo(FakeStat(task_state=linuxcnc.STATE_OFF))
    ok, reason = r.can_home()
    assert ok is False
    assert reason == "Machine must be on to home"


def test_homing_is_allowed_once_the_machine_is_on(repo):
    r, *_ = repo(FakeStat(task_state=linuxcnc.STATE_ON))
    assert r.can_home() == (True, "")


# -- the ready / not-ready rule --------------------------------------------

def machine_view_model(repo_result):
    from teachinlathe.repositories.tools_repository import ToolsRepository
    from teachinlathe.widgets.machine_qml.MachineViewModel import MachineViewModel
    r, stat, status, _, _ = repo_result
    return MachineViewModel(machine=r, status=status, tools=ToolsRepository()), stat, status


def test_machine_is_ready_only_when_free_powered_and_homed(repo):
    vm, stat, status = machine_view_model(repo(FakeStat(task_state=linuxcnc.STATE_ON)))
    assert vm.machineReady is True

    for field, value in (("task_state", linuxcnc.STATE_ESTOP),
                         ("task_state", linuxcnc.STATE_OFF)):
        setattr(stat, field, value)
        status.poll()
        assert vm.machineReady is False, "%s=%s must block" % (field, value)

    stat.task_state = linuxcnc.STATE_ON
    stat.joint = [{"homed": 1}, {"homed": 0}]
    status.poll()
    assert vm.machineReady is False, "an unhomed axis must block"

    stat.joint = [{"homed": 1}, {"homed": 1}]
    status.poll()
    assert vm.machineReady is True
