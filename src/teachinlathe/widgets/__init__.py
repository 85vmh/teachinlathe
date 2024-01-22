from qtpyvcp.widgets.qtdesigner import _DesignerPlugin

from .lathe_tool_touch_off.tool_touch_off import ToolTouchOff
from .teachin_lathe_dro import TeachInLatheDro
from .lathe_tool_table import LatheToolTable


class TeachInLatheDro_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return TeachInLatheDro


class LatheToolTable_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return LatheToolTable

class ToolTouchOff_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return ToolTouchOff