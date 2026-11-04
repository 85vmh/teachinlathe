"""A ToolLibraryRepository on a temporary directory, with no LinuxCNC behind
it: the tool table and the library's own files in that directory, a machine
that is not homed and has no tool loaded, and commands that are only
recorded."""

import dataclasses
import json
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

from teachinlathe.core.lathe_tool_extras_data_source import TOOL_HOLDERS_FILE, LatheToolExtrasDataSource
from teachinlathe.core.tool_library_repository import ToolLibraryRepository
from teachinlathe.core.tool_tbl_file_data_source import ToolTblFileDataSource, parse_line

TOOL_TABLE_FILE = "tool.tbl"


class FakeValue:
    def __init__(self, value):
        self.value = value

    def notify(self, slot, *args, **kwargs):
        pass


class FakeStatus(QObject):
    polled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.tool_in_spindle = FakeValue(0)
        self.all_axes_homed = FakeValue(False)
        self.enabled = FakeValue(False)


class FakeCommands:
    """Records what would have been sent: MDI lines, and tool table reloads."""

    def __init__(self):
        self.mdi = []
        self.tool_table_reloads = 0

    def issue_mdi(self, line):
        self.mdi.append(line)
        return True

    def load_tool_table(self):
        self.tool_table_reloads += 1


def tool_library(directory) -> ToolLibraryRepository:
    directory = Path(directory)
    (directory / TOOL_TABLE_FILE).touch()
    commands = FakeCommands()
    return ToolLibraryRepository(
        ToolTblFileDataSource(directory / TOOL_TABLE_FILE, command=commands),
        LatheToolExtrasDataSource(directory),
        status=FakeStatus(), commands=commands)


def touch_off(directory, tool_holder_id, x, z):
    """Holder ``tool_holder_id`` as if touched off at ``x``, ``z``: the offsets
    in the tool table, the holder marked touched off in both axes. Done to
    the files, for the next repository made on ``directory`` to read."""
    directory = Path(directory)
    table = directory / TOOL_TABLE_FILE
    lines = []
    for line in table.read_text(encoding="utf-8").splitlines():
        entry = parse_line(line)
        if entry is not None and entry.t == tool_holder_id:
            line = dataclasses.replace(entry, x=x, z=z).to_line()
        lines.append(line)
    table.write_text("".join(line + "\n" for line in lines), encoding="utf-8")

    holders_file = directory / TOOL_HOLDERS_FILE
    holders = json.loads(holders_file.read_text(encoding="utf-8"))
    for holder in holders["tool_holders"]:
        if holder["tool_holder_id"] == tool_holder_id:
            holder["x_touched"] = holder["z_touched"] = True
    holders_file.write_text(json.dumps(holders), encoding="utf-8")
