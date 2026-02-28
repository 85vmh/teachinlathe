from PyQt5.QtCore import QObject, pyqtSignal, pyqtProperty, pyqtSlot
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.plugins import getPlugin


class ToolsListProvider(QObject):
    toolsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tools = []
        self._tooltable = getPlugin('tooltable')
        self._status = getPlugin('status')
        self._stat = self._status.stat

        # initial load
        self._update_tools(self._tooltable.getToolTable())

        # update on tool table changes + tool in spindle changes
        self._tooltable.tool_table_changed.connect(self._update_tools)
        self._status.tool_in_spindle.notify(self._refresh_current_tool)

    def _refresh_current_tool(self, *_):
        self._update_tools(self._tooltable.getToolTable())

    def _update_tools(self, tool_table):
        try:
            current_tool = getattr(self._stat, "tool_in_spindle", None)
        except Exception:
            current_tool = None

        tools = []
        try:
            keys = sorted(tool_table)
        except Exception:
            keys = []

        for tnum in keys[1:]:  # skip spindle (0)
            tdata = tool_table.get(tnum, {}) or {}
            x = _safe_float(tdata.get("X", 0.0))
            z = _safe_float(tdata.get("Z", 0.0))
            d = _safe_float(tdata.get("D", 0.0))
            q = _safe_float(tdata.get("Q", 0.0))
            i = _safe_float(tdata.get("I", 0.0))
            j = _safe_float(tdata.get("J", 0.0))
            r = tdata.get("R", "")

            tools.append({
                "t": int(tnum),
                "x": x,
                "z": z,
                "d": d,
                "q": q,
                "i": i,
                "j": j,
                "r": str(r),
                "isCurrent": (current_tool == tnum),
            })

        self._tools = tools
        self.toolsChanged.emit()

    @pyqtProperty("QVariantList", notify=toolsChanged)
    def tools(self):
        return self._tools

    @pyqtSlot(int)
    def loadTool(self, tool_no):
        if tool_no is None:
            return
        issue_mdi("M61 Q%s G43" % int(tool_no))

    @pyqtSlot(int)
    def deleteTool(self, tool_no):
        if tool_no is None:
            return
        tool_no = int(tool_no)
        tool_table = self._tooltable.getToolTable()
        if tool_no not in tool_table:
            return
        if tool_no == getattr(self._stat, "tool_in_spindle", None):
            return
        try:
            del tool_table[tool_no]
        except Exception:
            return
        self._tooltable.saveToolTable(tool_table, self._tooltable.COLUMN_LABELS)
        self._update_tools(self._tooltable.getToolTable())


def _safe_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0
