"""Tests for ProgramRepository."""

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import linuxcnc  # noqa: E402
from PyQt6.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.core.no_program import NO_PROGRAM, loaded_program  # noqa: E402
from teachinlathe.core.program_repository import ProgramRepository  # noqa: E402


class FakeStat:
    def __init__(self, **fields):
        self.joints = 1
        self.joint = [{"homed": 1}]
        defaults = dict(task_mode=linuxcnc.MODE_MANUAL,
                        task_state=linuxcnc.STATE_ON,
                        interp_state=linuxcnc.INTERP_IDLE,
                        state=linuxcnc.RCS_DONE,
                        paused=False, file="")
        defaults.update(fields)
        for name, value in defaults.items():
            setattr(self, name, value)

    def poll(self):
        pass


class FakeCommands:
    """Stands in for CommandRepository."""

    def __init__(self, stat, allow_mode=True):
        self.stat = stat
        self.allow_mode = allow_mode
        self.modes = []

    def set_task_mode(self, mode):
        if not self.allow_mode:
            return False
        self.modes.append(mode)
        self.stat.task_mode = mode
        return True


class FakeStatus:
    def __init__(self, stat):
        self.stat = stat


class FakeCommand:
    def __init__(self):
        self.auto_calls = []
        self.aborts = 0
        self.opened = []
        self.waits = 0
        self.optional_stop = []
        self.block_delete = []

    def auto(self, *args):
        self.auto_calls.append(args)

    def abort(self):
        self.aborts += 1

    def program_open(self, name):
        self.opened.append(name.decode() if isinstance(name, bytes) else name)

    def wait_complete(self):
        self.waits += 1

    def set_optional_stop(self, value):
        self.optional_stop.append(value)

    def set_block_delete(self, value):
        self.block_delete.append(value)


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def repo(qt_app):
    def _make(stat=None, allow_mode=True):
        stat = stat or FakeStat()
        commands = FakeCommands(stat, allow_mode)
        cmd = FakeCommand()
        r = ProgramRepository(status=FakeStatus(stat), commands=commands, command=cmd)
        return r, stat, commands, cmd
    return _make


def test_run_switches_to_auto_and_starts(repo):
    r, stat, commands, cmd = repo()
    assert r.run() is True
    assert commands.modes == [linuxcnc.MODE_AUTO]
    assert cmd.auto_calls == [(linuxcnc.AUTO_RUN, 0)]


def test_run_from_a_line(repo):
    r, _, _, cmd = repo()
    r.run(start_line=42)
    assert cmd.auto_calls == [(linuxcnc.AUTO_RUN, 42)]


def test_run_on_a_paused_program_resumes_it(repo):
    """Pressing the green button on a paused program means 'carry on'."""
    stat = FakeStat(state=linuxcnc.RCS_EXEC, paused=True)
    r, _, commands, cmd = repo(stat)

    assert r.run() is True
    assert cmd.auto_calls == [(linuxcnc.AUTO_RESUME,)]
    assert commands.modes == [], "no mode change, the program is still loaded"


def test_run_fails_when_the_mode_cannot_be_set(repo):
    r, _, _, cmd = repo(allow_mode=False)
    assert r.run() is False
    assert cmd.auto_calls == []


def test_pause_resume_abort(repo):
    r, _, _, cmd = repo()
    r.pause()
    r.resume()
    r.abort()
    assert cmd.auto_calls == [(linuxcnc.AUTO_PAUSE,), (linuxcnc.AUTO_RESUME,)]
    assert cmd.aborts == 1


def test_step_switches_to_auto(repo):
    r, _, commands, cmd = repo()
    assert r.step() is True
    assert commands.modes == [linuxcnc.MODE_AUTO]
    assert cmd.auto_calls == [(linuxcnc.AUTO_STEP,)]


def test_program_options_are_passed_through(repo):
    r, _, _, cmd = repo()
    r.set_optional_stop(True)
    r.set_block_delete(0)
    assert cmd.optional_stop == [True]
    assert cmd.block_delete == [False]


def test_load_opens_the_file_and_waits(repo, tmp_path):
    path = tmp_path / "part.ngc"
    path.write_text("G0 X0\nM2\n")
    r, _, _, cmd = repo()
    seen = []
    r.programLoaded.connect(seen.append)

    assert r.load(str(path)) is True
    assert cmd.opened == [str(path)]
    assert cmd.waits == 1
    assert seen == [str(path)]


def test_load_refuses_a_missing_file(repo, tmp_path):
    r, _, _, cmd = repo()
    assert r.load(str(tmp_path / "nope.ngc")) is False
    assert cmd.opened == []


def test_load_or_reload_reloads_the_open_program(repo, tmp_path):
    path = tmp_path / "part.ngc"
    path.write_text("M2\n")
    stat = FakeStat(file=str(path))
    r, _, _, cmd = repo(stat)

    assert r.current_file == str(path)
    r.load_or_reload(str(path))
    # Same file: re-opened once, not opened as if it were a different one.
    assert cmd.opened == [str(path)]


def test_load_or_reload_loads_a_different_program(repo, tmp_path):
    open_file = tmp_path / "a.ngc"
    other = tmp_path / "b.ngc"
    open_file.write_text("M2\n")
    other.write_text("M2\n")
    stat = FakeStat(file=str(open_file))
    r, _, _, cmd = repo(stat)

    r.load_or_reload(str(other))
    assert cmd.opened == [str(other)]


def test_reload_with_nothing_loaded_does_nothing(repo):
    r, _, _, cmd = repo()
    assert r.reload() is False
    assert cmd.opened == []


# ── no program: the empty one loaded in its place (core.no_program) ─────
#
# LinuxCNC cannot close a program: program_open("") fails ("can't open") and
# leaves stat.file as it was, which a reset of the interpreter opens again.


def test_clear_loads_the_empty_program(repo):
    r, _, _, cmd = repo(FakeStat(file="/nc/part.ngc"))
    assert r.clear() is True
    assert cmd.opened == [NO_PROGRAM]
    assert cmd.waits == 1


def test_clear_is_refused_while_a_program_runs(repo):
    r, _, _, cmd = repo(FakeStat(file="/nc/part.ngc", interp_state=linuxcnc.INTERP_READING))
    assert r.clear() is False
    assert cmd.opened == []


def test_the_empty_program_loaded_is_none(repo):
    r, _, _, _ = repo(FakeStat(file=NO_PROGRAM))
    assert r.current_file == ""
    assert r.reload() is False


def test_load_of_nothing_unloads(repo):
    r, _, _, cmd = repo(FakeStat(file="/nc/part.ngc"))
    assert r.load("") is True
    assert cmd.opened == [NO_PROGRAM]


def test_a_program_gone_from_the_disk_is_unloaded(repo, tmp_path):
    gone = tmp_path / "M10x1.ngc"
    r, _, _, cmd = repo(FakeStat(file=str(gone)))
    assert r.clear_if_missing() is True
    assert cmd.opened == [NO_PROGRAM]


def test_a_program_still_there_or_none_is_left_loaded(repo, tmp_path):
    there = tmp_path / "part.ngc"
    there.write_text("M2\n")
    for file in (str(there), "", NO_PROGRAM):
        r, _, _, cmd = repo(FakeStat(file=file))
        assert r.clear_if_missing() is False
        assert cmd.opened == []


def test_the_empty_program_does_nothing_when_run():
    """Run - the button, or cycle start - on no program: no M2, which would
    stop the spindle and reset the modal state; between % it ends at once."""
    text = Path(NO_PROGRAM).read_text()
    code = [line for line in text.splitlines() if not line.startswith("(")]
    assert code == ["%", "%"]


def test_loaded_program_is_the_absolute_path_or_none():
    assert loaded_program("") == ""
    assert loaded_program(NO_PROGRAM) == ""
    assert loaded_program("/nc/../nc/part.ngc") == "/nc/part.ngc"
