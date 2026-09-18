"""The LinuxCNC tool table.

The table is kept as a dict of tool number to a dict of single-letter fields,
because that is the shape the tool table view reads, and reshaping a view that
is due to be rewritten in QML would be work thrown away twice.

Parsing and writing the ``.tbl`` itself is not reimplemented here: it already
lives in ``widgets.tool_library.tool_table_file``, and one parser for one file
format is enough.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional

import linuxcnc
from PyQt5.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal

from .command_repository import command_repository
from .ini_repository import ini_repository
from .status_repository import status_repository

log = logging.getLogger(__name__)

#: Header shown per column by the tool table view.
COLUMN_LABELS = {
    'A': 'A Offset', 'B': 'B Offset', 'C': 'C Offset', 'D': 'Diameter',
    'I': 'Fnt Ang', 'J': 'Bak Ang', 'P': 'Pocket', 'Q': 'Orient',
    'R': 'Remark', 'T': 'Tool', 'U': 'U Offset', 'V': 'V Offset',
    'W': 'W Offset', 'X': 'X Offset', 'Y': 'Y Offset', 'Z': 'Z Offset',
}

DEFAULT_TOOL = {
    'A': 0.0, 'B': 0.0, 'C': 0.0, 'D': 0.0, 'I': 0.0, 'J': 0.0,
    'P': 0, 'Q': 1, 'T': -1, 'U': 0.0, 'V': 0.0, 'W': 0.0,
    'X': 0.0, 'Y': 0.0, 'Z': 0.0, 'R': '',
}

NO_TOOL = dict(DEFAULT_TOOL, T=0, R='No Tool Loaded')

#: How long to wait after homing before restoring the remembered tool, so
#: LinuxCNC has finished switching modes.
RELOAD_TOOL_DELAY_MS = 200

STATE_FILE = '.teachinlathe_state.json'


class ToolTableRepository(QObject):
    """The tool table file, as a table."""

    #: Emitted with the whole table whenever it changes.
    tool_table_changed = pyqtSignal(dict)

    COLUMN_LABELS = COLUMN_LABELS
    DEFAULT_TOOL = DEFAULT_TOOL

    def __init__(self, parent: Optional[QObject] = None,
                 tool_file: Optional[str] = None,
                 remember_tool_in_spindle: bool = True,
                 status=None, commands=None, command=None, ini=None) -> None:
        super().__init__(parent)
        self._ini = ini_repository() if ini is None else ini
        self._status = status_repository() if status is None else status
        self._commands = command_repository() if commands is None else commands
        self._cmd = linuxcnc.command() if command is None else command

        self._tool_file = tool_file or self._ini.tool_table_file
        self._remember_tool_in_spindle = remember_tool_in_spindle
        self._state_path = os.path.join(self._ini.config_dir, STATE_FILE)
        self._table: Dict[int, dict] = {0: dict(NO_TOOL)}
        self._restore_in_flight = False

        self.loadToolTable()

        # Another process (or an MDI G10) can rewrite the file underneath us.
        self._watcher = QFileSystemWatcher(self)
        if os.path.isfile(self._tool_file):
            self._watcher.addPath(self._tool_file)
        self._watcher.fileChanged.connect(self._on_file_changed)

        self._status.tool_in_spindle.notify(self._on_tool_in_spindle_changed)
        if self._remember_tool_in_spindle:
            self._status.all_axes_homed.notify(self.reload_tool)

    # -- the table --------------------------------------------------------

    @property
    def tool_file(self) -> str:
        return self._tool_file

    def getToolTable(self) -> Dict[int, dict]:
        return self._table

    def loadToolTable(self, tool_file: Optional[str] = None) -> Dict[int, dict]:
        """Read the .tbl from disk into the table."""
        path = tool_file or self._tool_file
        table: Dict[int, dict] = {0: dict(NO_TOOL)}

        if not os.path.isfile(path):
            log.error("tool table file does not exist: %s", path)
            self._table = table
            self.tool_table_changed.emit(table)
            return table

        from teachinlathe.widgets.tool_library.tool_table_file import parse_tbl

        try:
            entries = parse_tbl(path)
        except Exception:
            log.exception("could not read the tool table: %s", path)
            self._table = table
            self.tool_table_changed.emit(table)
            return table

        for entry in entries:
            if entry.t == -1:
                continue
            table[entry.t] = {
                'T': entry.t, 'P': entry.p,
                'X': entry.x, 'Y': entry.y, 'Z': entry.z,
                'A': entry.a, 'B': entry.b, 'C': entry.c,
                'U': entry.u, 'V': entry.v, 'W': entry.w,
                'D': entry.d, 'I': entry.i, 'J': entry.j,
                'Q': entry.q, 'R': entry.r,
            }

        self._table = table
        log.debug("loaded %d tools from %s", len(table) - 1, path)
        self.tool_table_changed.emit(table)
        return table

    def saveToolTable(self, tool_table: Dict[int, dict],
                      columns=None, tool_file: Optional[str] = None) -> None:
        """Write *tool_table* back to the .tbl and tell LinuxCNC to re-read it."""
        path = tool_file or self._tool_file
        from teachinlathe.widgets.tool_library.tool_entry import ToolEntry
        from teachinlathe.widgets.tool_library.tool_table_file import write_tbl

        entries = []
        for tnum, tool in tool_table.items():
            if tnum == 0:
                continue
            entries.append(ToolEntry(
                t=int(tool.get('T', tnum)), p=int(tool.get('P', 0)),
                x=float(tool.get('X', 0.0)), y=float(tool.get('Y', 0.0)),
                z=float(tool.get('Z', 0.0)), a=float(tool.get('A', 0.0)),
                b=float(tool.get('B', 0.0)), c=float(tool.get('C', 0.0)),
                u=float(tool.get('U', 0.0)), v=float(tool.get('V', 0.0)),
                w=float(tool.get('W', 0.0)), d=float(tool.get('D', 0.0)),
                i=float(tool.get('I', 0.0)), j=float(tool.get('J', 0.0)),
                q=int(tool.get('Q', 1)), r=str(tool.get('R', '')),
            ))

        try:
            write_tbl(path, entries)
        except Exception:
            log.exception("could not write the tool table: %s", path)
            return

        log.info("saved %d tools to %s", len(entries), path)
        try:
            self._cmd.load_tool_table()
        except Exception:
            log.exception("LinuxCNC refused to reload the tool table")
        self.loadToolTable(path)

    def newTool(self, tnum: Optional[int] = None) -> dict:
        """A blank tool, numbered *tnum* or the next free number."""
        if tnum is None:
            tnum = max(self._table) + 1 if self._table else 1
        return dict(DEFAULT_TOOL, T=int(tnum), P=int(tnum))

    # -- the tool in the spindle ------------------------------------------

    @property
    def current_tool_number(self) -> int:
        try:
            return int(self._status.stat.tool_in_spindle)
        except Exception:
            return 0

    def reload_tool(self, *_args) -> None:
        """Put the remembered tool back in the spindle once homing is done.

        The machine forgets what is in the spindle across a restart; the
        operator does not, and the tool is still physically there. Only done
        when the spindle reads as empty, so a real tool change is never
        second-guessed.
        """
        if not self._remember_tool_in_spindle:
            return
        try:
            if not (self._status.all_axes_homed.value
                    and self._status.enabled.value):
                return
        except Exception:
            log.exception("could not read the machine state")
            return

        remembered = self._read_remembered_tool()
        if remembered <= 0 or self.current_tool_number != 0:
            return

        # One restore at a time. The command is issued on a timer, so a second
        # call before it fires would queue a second tool change - and a tool
        # change is a real movement on a real machine, not an idempotent read.
        if self._restore_in_flight:
            return
        self._restore_in_flight = True

        command = "M61 Q{} G43".format(remembered)
        log.info("restoring the tool that was in the spindle: %d", remembered)
        # Delayed, because LinuxCNC is still settling the mode change that
        # finishing homing brings with it.
        QTimer.singleShot(RELOAD_TOOL_DELAY_MS, lambda: self._issue_restore(command))

    def _issue_restore(self, command: str) -> None:
        try:
            self._commands.issue_mdi(command)
        finally:
            self._restore_in_flight = False

    def _on_tool_in_spindle_changed(self, tool_number) -> None:
        self._write_remembered_tool(int(tool_number))

    def _read_remembered_tool(self) -> int:
        try:
            with open(self._state_path) as fh:
                return int(json.load(fh).get('tool-in-spindle', 0))
        except (OSError, ValueError, TypeError):
            return 0

    def _write_remembered_tool(self, tool_number: int) -> None:
        state = {}
        try:
            with open(self._state_path) as fh:
                state = json.load(fh)
        except (OSError, ValueError):
            pass
        state['tool-in-spindle'] = int(tool_number)
        try:
            with open(self._state_path, 'w') as fh:
                json.dump(state, fh, indent=2, sort_keys=True)
        except OSError:
            log.warning("could not remember the tool in spindle in %s",
                        self._state_path, exc_info=True)

    def _on_file_changed(self, path: str) -> None:
        # Editors replace rather than rewrite, which drops the watch.
        if path not in self._watcher.files() and os.path.isfile(path):
            self._watcher.addPath(path)
        self.loadToolTable()


_INSTANCE: Optional[ToolTableRepository] = None


def tool_table_repository() -> ToolTableRepository:
    """The shared ToolTableRepository."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = ToolTableRepository()
    return _INSTANCE
