"""Tests for CommandRepository.

The interesting behaviour is the mode round-trip: an MDI command switches the
task to MDI and something has to put it back once the interpreter is idle,
however briefly the command ran.
"""

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import linuxcnc  # noqa: E402
from PyQt6.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.repositories.command_repository import (  # noqa: E402
    MDI_NOT_READY, CommandRepository,
)
from teachinlathe.repositories.status_repository import StatusRepository  # noqa: E402


class FakeStat:
    def __init__(self, **fields):
        self.joints = 1
        self.joint = [{"homed": 1}]
        defaults = dict(
            task_mode=linuxcnc.MODE_MANUAL,
            task_state=linuxcnc.STATE_ON,
            interp_state=linuxcnc.INTERP_IDLE,
            state=linuxcnc.RCS_DONE,
        )
        defaults.update(fields)
        for name, value in defaults.items():
            setattr(self, name, value)

    def poll(self):
        pass


class FakeIni:
    no_force_homing = False


class FakeCommand:
    """Records what was sent, the way linuxcnc.command would receive it.

    A mode change is reflected back into the stat, because that is what the
    real system does: the command is asynchronous and shows up in
    ``stat.task_mode`` on a later poll. Code that asks "am I already in this
    mode?" needs the stat to answer honestly.
    """

    def __init__(self, stat=None):
        self.stat = stat
        self.modes = []
        self.mdi_commands = []

    def mode(self, new_mode):
        self.modes.append(new_mode)
        if self.stat is not None:
            self.stat.task_mode = new_mode

    def mdi(self, command):
        self.mdi_commands.append(command)


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def repo(qt_app):
    def _make(stat=None):
        stat = stat or FakeStat()
        status = StatusRepository(stat=stat, ini=FakeIni())
        status.stop()
        cmd = FakeCommand(stat)
        return CommandRepository(status=status, command=cmd), stat, status, cmd
    return _make


def test_mdi_switches_mode_then_sends_the_command(repo):
    r, stat, _, cmd = repo()
    assert r.issue_mdi("G0 X5") is True
    assert cmd.modes == [linuxcnc.MODE_MDI]
    assert cmd.mdi_commands == ["G0 X5"]


def test_several_commands_are_split_on_semicolons(repo):
    r, _, _, cmd = repo()
    r.issue_mdi("G28.1 ; G0 X0 ;; G1 Z-1")
    assert cmd.mdi_commands == ["G28.1", "G0 X0", "G1 Z-1"]


def test_the_command_is_emitted_for_listeners(repo):
    r, _, _, cmd = repo()
    seen = []
    r.commandIssued.connect(seen.append)
    r.issue_mdi("M6 T3 G43")
    assert seen == ["M6 T3 G43"]


def test_mode_is_restored_once_the_interpreter_is_idle(repo):
    stat = FakeStat(task_mode=linuxcnc.MODE_MANUAL)
    r, stat, status, cmd = repo(stat)

    r.issue_mdi("G0 X5")
    assert r.pending_mode_restore == linuxcnc.MODE_MANUAL

    # Still running: nothing is restored yet.
    stat.interp_state = linuxcnc.INTERP_READING
    status.poll()
    assert cmd.modes == [linuxcnc.MODE_MDI]

    stat.interp_state = linuxcnc.INTERP_IDLE
    status.poll()
    assert cmd.modes == [linuxcnc.MODE_MDI, linuxcnc.MODE_MANUAL]
    assert r.pending_mode_restore is None


def test_a_command_finishing_inside_one_poll_still_restores(repo):
    """The case a cache-invalidation trick would be needed for.

    The interpreter never leaves INTERP_IDLE as far as the poll can see, so a
    restore driven by an interp_state *change* would never fire.
    """
    r, stat, status, cmd = repo()
    r.issue_mdi("G28.1")
    status.poll()
    assert cmd.modes == [linuxcnc.MODE_MDI, linuxcnc.MODE_MANUAL]


def test_restore_happens_once_not_on_every_poll(repo):
    r, stat, status, cmd = repo()
    r.issue_mdi("G28.1")
    for _ in range(5):
        status.poll()
    assert cmd.modes == [linuxcnc.MODE_MDI, linuxcnc.MODE_MANUAL]


def test_reset_false_leaves_the_task_in_mdi(repo):
    r, stat, status, cmd = repo()
    r.issue_mdi("G0 X5", reset=False)
    assert r.pending_mode_restore is None
    status.poll()
    assert cmd.modes == [linuxcnc.MODE_MDI]


def test_mode_is_not_changed_while_the_machine_is_moving(repo):
    stat = FakeStat(state=linuxcnc.RCS_EXEC)
    r, stat, _, cmd = repo(stat)

    assert r.is_running() is True
    assert r.issue_mdi("G0 X5") is False
    assert cmd.modes == []
    assert cmd.mdi_commands == []


def test_auto_mode_mid_program_counts_as_running(repo):
    stat = FakeStat(state=linuxcnc.RCS_DONE,
                    task_mode=linuxcnc.MODE_AUTO,
                    interp_state=linuxcnc.INTERP_READING)
    r, _, _, _ = repo(stat)
    assert r.is_running() is True


def test_auto_mode_when_idle_does_not_count_as_running(repo):
    stat = FakeStat(task_mode=linuxcnc.MODE_AUTO,
                    interp_state=linuxcnc.INTERP_IDLE)
    r, _, _, _ = repo(stat)
    assert r.is_running() is False


def test_can_issue_mdi_requires_on_homed_and_idle(repo):
    r, _, _, _ = repo()
    assert r.can_issue_mdi() == (True, "")


@pytest.mark.parametrize("field,value", [
    ("task_state", linuxcnc.STATE_OFF),
    ("interp_state", linuxcnc.INTERP_READING),
])
def test_can_issue_mdi_refuses_and_says_why(repo, field, value):
    r, stat, _, _ = repo(FakeStat(**{field: value}))
    ok, reason = r.can_issue_mdi()
    assert ok is False
    assert reason == MDI_NOT_READY


def test_can_issue_mdi_refuses_when_not_homed(repo):
    stat = FakeStat()
    stat.joint = [{"homed": 0}]
    r, _, _, _ = repo(stat)
    assert r.can_issue_mdi()[0] is False


def test_issue_mdi_does_not_itself_refuse_an_unhomed_machine(repo):
    """Faithful to the action it replaces: the readiness check gates the UI,
    not the command - homing itself is issued this way."""
    stat = FakeStat()
    stat.joint = [{"homed": 0}]
    r, _, _, cmd = repo(stat)

    assert r.can_issue_mdi()[0] is False
    assert r.issue_mdi("G28.1") is True
    assert cmd.mdi_commands == ["G28.1"]


def test_a_mode_already_active_is_not_set_again(repo):
    """Re-asserting the mode would re-init the interpreter and lose G7."""
    stat = FakeStat(task_mode=linuxcnc.MODE_MDI)
    r, stat, status, cmd = repo(stat)

    assert r.set_task_mode(linuxcnc.MODE_MDI) is True
    assert cmd.modes == []


def test_mdi_from_mdi_mode_does_not_switch_modes_at_all(repo):
    stat = FakeStat(task_mode=linuxcnc.MODE_MDI)
    r, stat, status, cmd = repo(stat)

    r.issue_mdi("G0 X5")
    status.poll()

    assert cmd.modes == [], "no transition, so the modal state survives"
    assert cmd.mdi_commands == ["G0 X5"]
