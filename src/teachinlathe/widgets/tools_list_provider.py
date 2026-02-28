from PyQt5.QtCore import QObject, pyqtSignal, pyqtProperty
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
            q = tdata.get("Q", "")
            i = tdata.get("I", "")
            j = tdata.get("J", "")
            r = tdata.get("R", "")

            tools.append({
                "t": int(tnum),
                "xz": f"X: {x:.3f}\nZ: {z:.3f}",
                "d": f"{d:.1f}",
                "q": q,
                "ij": f"Front: {i}°\nBack: {j}°",
                "r": str(r),
                "isCurrent": (current_tool == tnum),
            })

        self._tools = tools
        self.toolsChanged.emit()

    @pyqtProperty("QVariantList", notify=toolsChanged)
    def tools(self):
        return self._tools


def _safe_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0
