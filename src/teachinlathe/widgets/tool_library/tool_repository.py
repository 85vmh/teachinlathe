"""ToolRepository — single source of truth for the tool table.

Responsibilities:
  • Parse .tbl + extras JSON → typed ToolEntry objects
  • Persist edits (write .tbl + JSON, notify LinuxCNC)
  • Watch for external .tbl changes (another process / MDI editing)
  • Track which tool is currently in the spindle and update last_loaded

LinuxCNC integration:
  • `linuxcnc.command().load_tool_table()` reloads after writes
  • `linuxcnc.stat().tool_in_spindle` tells us the current tool
  • We poll stat via a QTimer because there is no push notification
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from .tool_entry import (
    SortBy, ToolEntry, ToolType,
    make_tool,
)
from .tool_table_file import parse_tbl, write_tbl
from .tool_extras_store import ToolExtrasStore

try:
    import linuxcnc as _lnc
    _LINUXCNC_AVAILABLE = True
except ImportError:
    _lnc = None                          # type: ignore[assignment]
    _LINUXCNC_AVAILABLE = False


class ToolRepository(QObject):
    """Manages the tool table as a list of typed ToolEntry objects.

    Signals:
        toolsChanged  — tool list has changed (reload QML model)
    """

    toolsChanged = pyqtSignal()

    def __init__(self, tbl_path: str, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._tbl_path   = Path(tbl_path)
        self._extras     = ToolExtrasStore(tbl_path)
        self._tools: List[ToolEntry] = []
        self._current_tool_no: int   = 0
        self._cmd  = None
        self._stat = None

        self._init_linuxcnc()
        self._load()
        self._start_watchers()

    # ── Public API ───────────────────────────────────────────────────

    def get_tools(self, sort_by: SortBy = SortBy.NUMBER) -> List[ToolEntry]:
        tools = list(self._tools)
        if sort_by == SortBy.LAST_USED:
            tools.sort(key=lambda t: t.last_loaded or 0.0, reverse=True)
        else:
            tools.sort(key=lambda t: t.t)
        return tools

    def get_tool(self, tool_no: int) -> Optional[ToolEntry]:
        for t in self._tools:
            if t.t == tool_no:
                return t
        return None

    def add_tool(self, tool: ToolEntry) -> None:
        """Add a new tool; raises ValueError if the number already exists."""
        if any(t.t == tool.t for t in self._tools):
            raise ValueError(f"Tool T{tool.t} already exists")
        self._tools.append(tool)
        self._persist()

    def edit_tool(self, tool: ToolEntry) -> None:
        """Replace an existing tool entry."""
        for i, t in enumerate(self._tools):
            if t.t == tool.t:
                self._tools[i] = tool
                self._persist()
                return
        raise ValueError(f"Tool T{tool.t} not found")

    def delete_tool(self, tool_no: int) -> None:
        before = len(self._tools)
        self._tools = [t for t in self._tools if t.t != tool_no]
        if len(self._tools) < before:
            self._extras.delete(tool_no)
            self._persist()

    @property
    def current_tool_no(self) -> int:
        return self._current_tool_no

    # ── Internal: load ───────────────────────────────────────────────

    def _load(self) -> None:
        if not self._tbl_path.exists():
            self._tools = []
            self.toolsChanged.emit()
            return

        base_tools = parse_tbl(self._tbl_path)
        result: List[ToolEntry] = []
        for base in base_tools:
            extras = self._extras.get(base.t)
            tool_type_str = extras.get("tool_type", ToolType.GENERIC.value)
            try:
                tool_type = ToolType(tool_type_str)
            except ValueError:
                tool_type = ToolType.GENERIC

            promoted = make_tool(base, tool_type, extras)
            promoted.last_loaded = extras.get("last_loaded", None)
            result.append(promoted)

        self._tools = result
        self.toolsChanged.emit()

    # ── Internal: persist ────────────────────────────────────────────

    def _persist(self) -> None:
        write_tbl(self._tbl_path, self._tools)
        for tool in self._tools:
            self._extras.save(tool.t, tool.to_extras_dict())
        self._notify_linuxcnc()
        self.toolsChanged.emit()

    def _notify_linuxcnc(self) -> None:
        if self._cmd is not None:
            try:
                self._cmd.load_tool_table()
            except Exception:
                pass

    # ── Internal: LinuxCNC ───────────────────────────────────────────

    def _init_linuxcnc(self) -> None:
        if not _LINUXCNC_AVAILABLE:
            return
        try:
            self._cmd  = _lnc.command()
            self._stat = _lnc.stat()
        except Exception:
            self._cmd  = None
            self._stat = None

    def _start_watchers(self) -> None:
        # Poll LinuxCNC stat for spindle tool changes
        if self._stat is not None:
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(500)
            self._poll_timer.timeout.connect(self._poll_spindle)
            self._poll_timer.start()

        # Watch .tbl file for external edits
        try:
            from PyQt5.QtCore import QFileSystemWatcher
            self._watcher = QFileSystemWatcher([str(self._tbl_path)], self)
            self._watcher.fileChanged.connect(self._on_tbl_changed)
        except Exception:
            pass

    def _poll_spindle(self) -> None:
        try:
            self._stat.poll()
            tool_in_spindle = self._stat.tool_in_spindle
        except Exception:
            return

        if tool_in_spindle != self._current_tool_no:
            prev = self._current_tool_no
            self._current_tool_no = tool_in_spindle
            if tool_in_spindle != 0:
                self._record_last_loaded(tool_in_spindle)
            # Always emit so isCurrent flag refreshes in QML
            self.toolsChanged.emit()

    def _record_last_loaded(self, tool_no: int) -> None:
        ts = time.time()
        self._extras.update_last_loaded(tool_no, ts)
        for tool in self._tools:
            if tool.t == tool_no:
                tool.last_loaded = ts
                break

    def _on_tbl_changed(self, path: str) -> None:
        # Re-add watch because some editors replace the file (inode changes)
        if self._tbl_path.exists():
            try:
                self._watcher.addPath(str(self._tbl_path))
            except Exception:
                pass
        self._load()
