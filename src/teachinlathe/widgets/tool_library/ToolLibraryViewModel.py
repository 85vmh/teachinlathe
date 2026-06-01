"""ToolLibraryViewModel — Qt bridge between ToolRepository and QML.

Exposes:
  • tools   QVariantList of display dicts (read-only, reactive)
  • loadTool / deleteTool / saveTool / addTool  slots callable from QML

The tbl_path is resolved from LinuxCNC INI via qtpyvcp Info utility.
"""
from __future__ import annotations

from datetime import date
from typing import List

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from .tool_entry import (
    BoringBarTool, DrillTool, PartingBladeTool, ReamerTool,
    SortBy, TapTool, ToolEntry, ToolType, TrepaningTool,
)
from .tool_repository import ToolRepository

try:
    import linuxcnc as _lnc
    _CMD = _lnc.command()
except Exception:
    _CMD = None

try:
    from qtpyvcp.utilities.info import Info as _Info
    _TBL_PATH: str = _Info().getToolTableFile()
except Exception:
    _TBL_PATH = ""


class ToolLibraryViewModel(QObject):
    toolsChanged = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._repo = ToolRepository(_TBL_PATH, parent=self)
        self._repo.toolsChanged.connect(self.toolsChanged)

    # ── QML property ────────────────────────────────────────────────

    @pyqtProperty("QVariantList", notify=toolsChanged)
    def tools(self) -> List[dict]:
        current = self._repo.current_tool_no
        result = []
        for tool in self._repo.get_tools():
            d = tool.to_display_dict()
            d["isCurrent"] = (tool.t == current)
            result.append(d)
        return result

    @pyqtProperty("QVariantList", notify=toolsChanged)
    def recentTools(self) -> List[dict]:
        current = self._repo.current_tool_no
        loaded = [t for t in self._repo.get_tools(sort_by=SortBy.LAST_USED)
                  if t.last_loaded is not None]
        if not loaded:
            return []

        today = date.today()
        today_tools = [t for t in loaded if date.fromtimestamp(t.last_loaded) == today]
        if today_tools:
            tools_to_show = today_tools
        else:
            distinct_dates: list[date] = []
            for t in loaded:
                d = date.fromtimestamp(t.last_loaded)
                if d not in distinct_dates:
                    distinct_dates.append(d)
                if len(distinct_dates) == 2:
                    break
            tools_to_show = [t for t in loaded
                             if date.fromtimestamp(t.last_loaded) in distinct_dates]

        tools_to_show.sort(key=lambda t: t.t)
        result = []
        for tool in tools_to_show:
            d = tool.to_display_dict()
            d["isCurrent"] = (tool.t == current)
            result.append(d)
        return result

    # ── QML slots ────────────────────────────────────────────────────

    @pyqtSlot(int, result=bool)
    def toolExists(self, tool_no: int) -> bool:
        return self._repo.get_tool(tool_no) is not None

    @pyqtSlot(int)
    def loadTool(self, tool_no: int) -> None:
        if _CMD is not None:
            try:
                _CMD.mode(_lnc.MODE_MDI)
                _CMD.wait_complete()
                _CMD.mdi(f"M61 Q{tool_no}")
                _CMD.wait_complete()
            except Exception:
                pass

    @pyqtSlot(int)
    def deleteTool(self, tool_no: int) -> None:
        self._repo.delete_tool(tool_no)

    @pyqtSlot(int, float, float, float, str, int)
    def saveTool(
        self,
        tool_no: int,
        tip_radius: float,
        front_angle: float,
        back_angle: float,
        comment: str,
        orientation: int,
    ) -> None:
        existing = self._repo.get_tool(tool_no)
        if existing is None:
            return
        existing.d = tip_radius
        existing.i = front_angle
        existing.j = back_angle
        existing.r = comment
        existing.q = orientation
        self._repo.edit_tool(existing)

    @pyqtSlot(int, float, float, float, str, int)
    def addTool(
        self,
        tool_no: int,
        tip_radius: float,
        front_angle: float,
        back_angle: float,
        comment: str,
        orientation: int,
    ) -> None:
        tool = ToolEntry(
            t=tool_no, p=tool_no,
            d=tip_radius, i=front_angle, j=back_angle,
            q=orientation, r=comment,
        )
        self._repo.add_tool(tool)

    # ── Extended save — carries type-specific extras from QML ────────

    @pyqtSlot(int, "QVariantMap")
    def saveToolFull(self, tool_no: int, data: dict) -> None:
        """Save a tool with full type information (orientation-7 subclasses)."""
        existing = self._repo.get_tool(tool_no)
        base = existing if existing is not None else ToolEntry(t=tool_no, p=tool_no)

        # Copy common fields
        base.d = float(data.get("tipRadius",   base.d))
        base.i = float(data.get("frontAngle",  base.i))
        base.j = float(data.get("backAngle",   base.j))
        base.r = str(  data.get("comment",     base.r))
        base.q = int(  data.get("orientation", base.q))

        tool_type_str = data.get("toolType", ToolType.GENERIC.value)
        try:
            tool_type = ToolType(tool_type_str)
        except ValueError:
            tool_type = ToolType.GENERIC

        from .tool_entry import make_tool
        promoted = make_tool(base, tool_type, data)

        new_tool_no = data.get("newToolNo")
        if new_tool_no is not None:
            new_tool_no = int(new_tool_no)

        if new_tool_no is not None and new_tool_no != tool_no:
            promoted.t = new_tool_no
            promoted.p = new_tool_no
            if existing is not None:
                self._repo.delete_tool(tool_no)
            self._repo.add_tool(promoted)
        elif existing is not None:
            self._repo.edit_tool(promoted)
        else:
            self._repo.add_tool(promoted)
