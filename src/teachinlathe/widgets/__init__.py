from qtpyvcp.widgets.qtdesigner import _DesignerPlugin

from .add_edit_tool.add_edit_tool import AddEditToolWidget
from .conversational_qml.ConversationalQml import ConversationalQml
from .lathe_fixtures.lathe_fixtures_cards import LatheFixturesCards
from .lathe_tool_table import LatheToolTable
from .lathe_tool_touch_off.tool_touch_off import ToolTouchOff
from .quick_cycles.quick_cycles import QuickCycles


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


class ConversationalQml_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return ConversationalQml

class AddEditToolWidget_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return AddEditToolWidget
