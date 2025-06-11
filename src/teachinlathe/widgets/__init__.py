from qtpyvcp.widgets.qtdesigner import _DesignerPlugin

from .conversational.conversational import Conversational
from .conversational.program_item_widget import ProgramItemWidget
from .lathe_fixtures.lathe_fixtures_cards import LatheFixturesCards
from .lathe_tool_table import LatheToolTable
from .lathe_tool_touch_off.tool_touch_off import ToolTouchOff
from .quick_cycles.quick_cycles import QuickCycles
from .teachin_lathe_dro import TeachInLatheDro
from ..TestQml import AxisPlotWidget


class TeachInLatheDro_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return TeachInLatheDro

class AxisPlotWidget_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return AxisPlotWidget


class LatheToolTable_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return LatheToolTable

class ToolTouchOff_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return ToolTouchOff


class QuickCycles_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return QuickCycles


class LatheFixturesCards_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return LatheFixturesCards


class Conversational_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return Conversational