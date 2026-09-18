"""Tests for ToolsRepository.

These launch real processes - harmless ones - because the bug that made this
file necessary was a wrong ``QProcess.startDetached`` overload: the code was
fine to read and to import, and only the actual call failed.
"""

import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt5.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.repositories.tools_repository import (  # noqa: E402
    ExternalTool, ToolsRepository,
)


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def repo(qt_app):
    return ToolsRepository()


# -- launching --------------------------------------------------------------

def test_a_tool_actually_starts(repo):
    repo._tools['probe'] = ExternalTool('probe', 'Probe', ['sleep', '0.1'])
    assert repo.launch('probe') is True


def test_a_missing_program_is_reported_not_raised(repo):
    repo._tools['absent'] = ExternalTool('absent', 'Absent', ['no-such-program-here'])
    assert repo.launch('absent') is False


def test_an_unknown_key_is_refused(repo):
    assert repo.launch('not-a-tool') is False
    ok, reason = repo.can_launch('not-a-tool')
    assert ok is False
    assert 'No such tool' in reason


# -- what each tool runs ----------------------------------------------------

def test_every_tool_has_a_program_and_a_label(repo):
    for tool in repo.tools:
        assert tool.argv, tool.key
        assert tool.label, tool.key


def test_the_expected_tools_are_offered(repo):
    keys = [t.key for t in repo.tools]
    assert keys == ['halshow', 'halmeter', 'halscope',
                    'classicladder', 'status', 'calibration']


def test_calibration_is_given_the_ini_file_at_launch_time(repo, monkeypatch):
    """The INI is read when the tool runs, not when it was declared.

    The repository can be built before the INI path is known, and an empty
    ``-ini`` makes emccalib fail in a way that points nowhere.
    """
    monkeypatch.setenv('INI_FILE_NAME', '/some/machine.ini')
    argv = repo._tools['calibration'].argv
    assert argv[-2:] == ['-ini', '/some/machine.ini']

    monkeypatch.setenv('INI_FILE_NAME', '/another/machine.ini')
    assert repo._tools['calibration'].argv[-1] == '/another/machine.ini'


def test_calibration_is_refused_without_an_ini(repo, monkeypatch):
    monkeypatch.delenv('INI_FILE_NAME', raising=False)
    ok, reason = repo.can_launch('calibration')
    assert ok is False
    assert 'INI' in reason


def test_tools_that_need_no_ini_do_not_get_one(repo):
    assert '-ini' not in repo._tools['halmeter'].argv


def test_classic_ladder_waits_for_its_hal_component(repo):
    # HAL cannot answer in a process that owns no component, which reads the
    # same as "not loaded" - either way the button is off rather than opening
    # a window with nothing in it.
    ok, reason = repo.can_launch('classicladder')
    if not ok:
        assert 'classicladder_rt' in reason


def test_the_working_directory_follows_the_config(repo, monkeypatch):
    monkeypatch.setenv('CONFIG_DIR', '/tmp')
    assert repo._working_directory() == '/tmp'

    monkeypatch.delenv('CONFIG_DIR', raising=False)
    assert repo._working_directory() == os.path.expanduser('~')
