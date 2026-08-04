from qtpyvcp.widgets.qtdesigner import _DesignerPlugin

from .conversational_qml.ConversationalQml import ConversationalQml
from .lathe_fixtures.lathe_fixtures_cards import LatheFixturesCards
from .lathe_tool_table import LatheToolTable
from .lathe_tool_touch_off.tool_touch_off import ToolTouchOff


class LatheToolTable_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return LatheToolTable

class ToolTouchOff_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return ToolTouchOff


class LatheFixturesCards_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return LatheFixturesCards


class ConversationalQml_Plugin(_DesignerPlugin):
    def pluginClass(self):
        return ConversationalQml
