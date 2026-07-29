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
from teachinlathe.lathe_hal_component import TeachInLatheComponent

try:
    import linuxcnc as _lnc
    _CMD = _lnc.command()
    _STAT = _lnc.stat()
except Exception:
    _CMD = None
    _STAT = None

try:
    from qtpyvcp.utilities.info import Info as _Info
    _TBL_PATH: str = _Info().getToolTableFile()
except Exception:
    _TBL_PATH = ""


class ToolLibraryViewModel(QObject):
    toolsChanged = pyqtSignal()
    enabledStateChanged = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._repo = ToolRepository(_TBL_PATH, parent=self)
        self._repo.toolsChanged.connect(self.toolsChanged)
        self._is_feeding = False
        self._lathe_component = TeachInLatheComponent()
        self._lathe_component.comp.addListener(
            TeachInLatheComponent.PinJoystickIsFeeding,
            self.onJoystickFeedingChanged,
        )
        try:
            self._is_feeding = bool(
                self._lathe_component.comp.getPin(TeachInLatheComponent.PinJoystickIsFeeding).value
            )
        except Exception:
            self._is_feeding = False

    # ── QML property ────────────────────────────────────────────────

    @pyqtProperty("QVariantList", notify=toolsChanged)
    def tools(self) -> List[dict]:
        current = self._repo.current_tool_no
        result = []
        for tool in self._repo.get_tools():
            result.append(self._tool_display_dict(tool, current))
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
            result.append(self._tool_display_dict(tool, current))
        return result

    @pyqtProperty(int, notify=toolsChanged)
    def nextToolNo(self) -> int:
        tools = self._repo.get_tools()
        if not tools:
            return 1
        return max(t.t for t in tools) + 1

    @pyqtProperty(bool, notify=enabledStateChanged)
    def addToolEnabled(self) -> bool:
        return not self._is_feeding

    # ── QML slots ────────────────────────────────────────────────────

    @pyqtSlot(int, result=bool)
    def toolExists(self, tool_no: int) -> bool:
        return self._repo.get_tool(tool_no) is not None

    @pyqtSlot(int)
    def loadTool(self, tool_no: int) -> None:
        if tool_no == self._repo.current_tool_no:
            print(f"[ToolLibraryViewModel] manual tool change skipped: T{tool_no} already current")
            return
        if self._is_feeding:
            print(f"[ToolLibraryViewModel] manual tool change blocked while feeding: T{tool_no}")
            return
        if _CMD is None or _STAT is None:
            print(f"[ToolLibraryViewModel] manual tool change unavailable: command/stat missing for T{tool_no}")
            return

        previous_mode = None
        try:
            _STAT.poll()
            previous_mode = int(getattr(_STAT, "task_mode", _lnc.MODE_MANUAL))
            mdi_command = f"M61 Q{tool_no} G43"
            print(f"[ToolLibraryViewModel] manual tool change MDI: {mdi_command}")

            _CMD.mode(_lnc.MODE_MDI)
            _CMD.wait_complete()
            _CMD.mdi(mdi_command)
            _CMD.wait_complete()
            _STAT.poll()
            # print(
            #     "[ToolLibraryViewModel] manual tool change status: "
            #     f"tool_in_spindle={getattr(_STAT, 'tool_in_spindle', None)} "
            #     f"tool_offset={getattr(_STAT, 'tool_offset', None)}"
            # )
        except Exception as e:
            print(f"[ToolLibraryViewModel] manual tool change failed for T{tool_no}: {e}")
        finally:
            if previous_mode == _lnc.MODE_MANUAL:
                try:
                    _CMD.mode(_lnc.MODE_MANUAL)
                    _CMD.wait_complete()
                except Exception:
                    pass

    @pyqtSlot(int)
    def deleteTool(self, tool_no: int) -> None:
        if self._is_feeding:
            return
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
        if self._is_feeding:
            return
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
        if self._is_feeding:
            return
        tool = ToolEntry(
            t=tool_no, p=tool_no,
            d=tip_radius, i=front_angle, j=back_angle,
            q=orientation, r=comment,
        )
        self._repo.add_tool(tool)

    # ── Extended save — carries type-specific extras from QML ────────

    @pyqtSlot(int, "QVariantMap", result=bool)
    def saveToolFull(self, tool_no: int, data: dict) -> bool:
        """Save a tool with full type information (orientation-7 subclasses)."""
        existing = self._repo.get_tool(tool_no)
        if self._is_feeding:
            return False

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
        return True

    def onJoystickFeedingChanged(self, value) -> None:
        feeding = bool(value)
        if feeding == self._is_feeding:
            return
        self._is_feeding = feeding
        self.enabledStateChanged.emit()
        self.toolsChanged.emit()

    def _tool_display_dict(self, tool: ToolEntry, current_tool_no: int) -> dict:
        is_current = tool.t == current_tool_no
        d = tool.to_display_dict()
        d["isCurrent"] = is_current
        d["isEnabled"] = self._tool_enabled(is_current)
        d["actionsEnabled"] = self._tool_actions_enabled()
        return d

    def _tool_enabled(self, is_current: bool) -> bool:
        return is_current or not self._is_feeding

    def _tool_actions_enabled(self) -> bool:
        return not self._is_feeding
