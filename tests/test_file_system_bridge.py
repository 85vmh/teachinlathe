"""Something deleted in the Programs tab's browser (FileSystemBridge.
forgetFilesGone, on FileSystemViewModel.entryDeleted): the program shown in
the code view, whose path the backplot was told to show, is shown no more if
it went with it - and the machine's program is unloaded if it did."""

import pytest
from PyQt6.QtTest import QSignalSpy

from teachinlathe.ui.tabs.programs.filesystemview import FileSystemBridge as bridge_module
from teachinlathe.ui.tabs.programs.filesystemview.FileSystemBridge import FileSystemBridge


@pytest.fixture
def unloads(monkeypatch):
    """How many times the machine's program was asked to be unloaded if gone."""
    calls = []
    monkeypatch.setattr(bridge_module, "unload_program_if_missing", lambda: calls.append(True))
    return calls


def _showing(tmp_path, name="M10x1.ngc"):
    program = tmp_path / name
    program.write_text("G0 X10\nM30\n")
    bridge = FileSystemBridge()
    bridge.selectFileByAbsolutePath(str(program))
    assert bridge.currentFilePath == str(program)
    return bridge, program


def test_the_file_shown_deleted_is_shown_no_more(tmp_path, unloads):
    bridge, program = _showing(tmp_path)
    paths, contents = QSignalSpy(bridge.filePathChanged), QSignalSpy(bridge.fileContentChanged)

    program.unlink()
    bridge.forgetFilesGone(str(program))

    assert bridge.currentFilePath == ""
    assert list(paths[-1]) == [""]
    assert list(contents[-1]) == [""]
    assert unloads == [True]


def test_the_file_shown_still_there_stays_but_the_machine_is_checked(tmp_path, unloads):
    bridge, program = _showing(tmp_path)
    other = tmp_path / "other.ngc"
    paths = QSignalSpy(bridge.filePathChanged)

    bridge.forgetFilesGone(str(other))

    assert bridge.currentFilePath == str(program)
    assert len(paths) == 0
    # the machine's program may be another than the one shown
    assert unloads == [True]
