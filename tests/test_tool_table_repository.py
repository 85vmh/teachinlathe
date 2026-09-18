"""Tests for ToolTableRepository, against real .tbl files on disk."""

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import linuxcnc  # noqa: E402
from PyQt5.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.repositories.status_repository import StatusRepository  # noqa: E402
from teachinlathe.repositories.tool_table_repository import (  # noqa: E402
    NO_TOOL, ToolTableRepository,
)

SAMPLE_TBL = """\
T1 P1 X-1.5 Z-3.25 D0.4 I95.0 J30.0 Q2 ;Roughing tool
T2 P2 X0.0 Z0.0 D0.2 I60.0 J60.0 Q3 ;Threading tool
T5 P5 X2.125 Z-10.0 D0.8 Q1 ;Parting blade
"""


class FakeStat:
    def __init__(self, **fields):
        self.joints = 2
        self.joint = [{"homed": 1}, {"homed": 1}]
        defaults = dict(tool_in_spindle=0, enabled=True,
                        task_state=linuxcnc.STATE_ON,
                        task_mode=linuxcnc.MODE_MANUAL,
                        interp_state=linuxcnc.INTERP_IDLE,
                        state=linuxcnc.RCS_DONE)
        defaults.update(fields)
        for name, value in defaults.items():
            setattr(self, name, value)

    def poll(self):
        pass


class FakeIni:
    def __init__(self, tbl, config_dir):
        self.tool_table_file = str(tbl)
        self.config_dir = str(config_dir)
        self.no_force_homing = False


class FakeCommands:
    def __init__(self):
        self.mdi = []

    def issue_mdi(self, command, reset=True):
        self.mdi.append(command)
        return True


class FakeCommand:
    def __init__(self):
        self.reloads = 0

    def load_tool_table(self):
        self.reloads += 1


def spin(milliseconds):
    """Run the event loop so a singleShot timer can fire."""
    from PyQt5.QtCore import QEventLoop, QTimer
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec_()


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def repo(qt_app, tmp_path):
    def _make(content=SAMPLE_TBL, stat=None, remember=True):
        tbl = tmp_path / "lathe.tbl"
        tbl.write_text(content)
        stat = stat or FakeStat()
        ini = FakeIni(tbl, tmp_path)
        status = StatusRepository(stat=stat, ini=ini)
        status.stop()
        commands = FakeCommands()
        cmd = FakeCommand()
        r = ToolTableRepository(tool_file=str(tbl), remember_tool_in_spindle=remember,
                                status=status, commands=commands, command=cmd, ini=ini)
        return r, tbl, stat, status, commands, cmd
    return _make


# -- reading ----------------------------------------------------------------

def test_tools_are_read_into_a_table_keyed_by_tool_number(repo):
    r, *_ = repo()
    table = r.getToolTable()
    assert sorted(table) == [0, 1, 2, 5]
    assert table[1]["X"] == pytest.approx(-1.5)
    assert table[1]["Z"] == pytest.approx(-3.25)
    assert table[1]["Q"] == 2
    assert table[1]["R"] == "Roughing tool"


def test_tool_zero_is_the_no_tool_entry(repo):
    r, *_ = repo()
    assert r.getToolTable()[0] == NO_TOOL


def test_a_missing_file_gives_an_empty_table_rather_than_an_error(repo, tmp_path):
    r, tbl, *_ = repo()
    tbl.unlink()
    table = r.loadToolTable()
    assert sorted(table) == [0]


def test_loading_announces_the_table(repo):
    r, *_ = repo()
    seen = []
    r.tool_table_changed.connect(seen.append)
    r.loadToolTable()
    assert len(seen) == 1
    assert sorted(seen[0]) == [0, 1, 2, 5]


# -- writing ----------------------------------------------------------------

def test_saving_writes_the_file_and_asks_linuxcnc_to_reread_it(repo):
    r, tbl, _, _, _, cmd = repo()
    table = r.getToolTable()
    table[1]["X"] = -9.75
    r.saveToolTable(table)

    assert cmd.reloads == 1
    assert r.getToolTable()[1]["X"] == pytest.approx(-9.75)
    assert "T1" in tbl.read_text()


def test_saving_round_trips_every_field(repo):
    r, _, *_ = repo()
    before = dict(r.getToolTable()[1])
    r.saveToolTable(r.getToolTable())
    after = r.getToolTable()[1]
    for key in ("T", "P", "X", "Z", "D", "I", "J", "Q", "R"):
        assert after[key] == before[key], key


def test_tool_zero_is_not_written_to_the_file(repo):
    r, tbl, *_ = repo()
    r.saveToolTable(r.getToolTable())
    assert "No Tool Loaded" not in tbl.read_text()


def test_new_tool_takes_the_next_free_number(repo):
    r, *_ = repo()
    tool = r.newTool()
    assert tool["T"] == 6          # highest is 5
    assert tool["X"] == 0.0

    assert r.newTool(tnum=12)["T"] == 12


# -- the tool in the spindle ------------------------------------------------

def test_the_tool_in_the_spindle_is_remembered_across_a_restart(repo, tmp_path):
    r, _, stat, status, _, _ = repo()
    stat.tool_in_spindle = 3
    status.poll()

    state = json.loads((tmp_path / ".teachinlathe_state.json").read_text())
    assert state["tool-in-spindle"] == 3


def test_the_remembered_tool_is_restored_once_homing_finishes(repo, tmp_path):
    (tmp_path / ".teachinlathe_state.json").write_text('{"tool-in-spindle": 4}')
    stat = FakeStat(tool_in_spindle=0)
    stat.joint = [{"homed": 0}, {"homed": 0}]
    r, _, stat, status, commands, _ = repo(stat=stat)

    r.reload_tool()
    assert commands.mdi == [], "not homed yet"

    stat.joint = [{"homed": 1}, {"homed": 1}]
    status.poll()          # all_axes_homed goes true, which asks for the restore

    # Issued on a timer, so let it fire.
    spin(300)

    assert commands.mdi == ["M61 Q4 G43"]


def test_the_restore_is_not_queued_twice(qt_app, repo, tmp_path):
    """A tool change is a real movement; asking twice must not do it twice."""
    (tmp_path / ".teachinlathe_state.json").write_text('{"tool-in-spindle": 4}')
    r, _, _, _, commands, _ = repo(stat=FakeStat(tool_in_spindle=0))

    r.reload_tool()
    r.reload_tool()
    r.reload_tool()
    spin(300)

    assert commands.mdi == ["M61 Q4 G43"]


def test_a_tool_already_in_the_spindle_is_not_second_guessed(repo, tmp_path):
    (tmp_path / ".teachinlathe_state.json").write_text('{"tool-in-spindle": 4}')
    r, _, stat, _, commands, _ = repo(stat=FakeStat(tool_in_spindle=2))

    r.reload_tool()
    assert commands.mdi == []


def test_nothing_is_restored_when_remembering_is_off(repo, tmp_path):
    (tmp_path / ".teachinlathe_state.json").write_text('{"tool-in-spindle": 4}')
    r, _, _, _, commands, _ = repo(remember=False)
    r.reload_tool()
    assert commands.mdi == []


def test_a_corrupt_state_file_is_survivable(repo, tmp_path):
    (tmp_path / ".teachinlathe_state.json").write_text("not json at all")
    r, _, _, _, commands, _ = repo()
    r.reload_tool()
    assert commands.mdi == []
