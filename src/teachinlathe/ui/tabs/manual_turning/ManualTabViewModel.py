"""The Manual Turning tab's view model.

The tab is three panels, each with a view model of its own, as properties
of this one: ``turning`` - spindle, feed, joystick and handwheels -, ``dro``
- the readout, touch-off and the teach-in limits - and ``tools`` - the tool
holders on the right, and the title bar's recent toggle. The title bar has
the menu on its left (menuRequested: the tab opens its drawer).
"""

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

from teachinlathe.ui.common.images import image_url

from teachinlathe.ui.tabs.manual_turning.ManualTurningViewModel import ManualTurningViewModel
from teachinlathe.ui.tabs.manual_turning.TeachInLatheDroViewModel import TeachInLatheDroViewModel
from teachinlathe.ui.tabs.tool_library.ManualToolsViewModel import ManualToolsViewModel


#: The title bar's menu, on its left.
_MENU_ACTION = "menu"


class ManualTabViewModel(QObject):
    headerStateChanged = pyqtSignal()
    #: The menu tapped: the drawer opens.
    menuRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._turning = ManualTurningViewModel(self)
        self._dro = TeachInLatheDroViewModel(self)
        self._tools = ManualToolsViewModel(self)
        self._tools.headerStateChanged.connect(self.headerStateChanged)

    @pyqtProperty(QObject, constant=True)
    def turning(self):
        return self._turning

    @pyqtProperty(QObject, constant=True)
    def dro(self):
        return self._dro

    @pyqtProperty(QObject, constant=True)
    def tools(self):
        return self._tools

    # ── the app shell's header: the menu, and the tool list's recent toggle ─

    def getHeaderState(self):
        return {**self._tools.getHeaderState(),
                "left_actions": [{"id": _MENU_ACTION, "icon": image_url("menu.svg"), "enabled": True}]}

    def triggerHeaderAction(self, action_id):
        if action_id == _MENU_ACTION:
            self.menuRequested.emit()
        else:
            self._tools.triggerHeaderAction(action_id)
