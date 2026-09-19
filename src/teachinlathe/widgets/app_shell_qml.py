"""The model behind the application chrome.

The chrome itself - title bar, bottom tab bar, events drawer, toast - used to
be AppShellQmlWidget: a QWidget holding one QQuickWidget per bar, with a
QStackedWidget between them, and Python computing the drawer's geometry on
every resize. The bars were always QML; only the box around them was not.
That box is AppShell.qml now, so what is left here is the bridge the bars
read from.
"""

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot


class AppShellBridge(QObject):
    currentTabChanged = pyqtSignal()
    titleChanged = pyqtSignal()
    headerVisibleChanged = pyqtSignal()
    leftActionsChanged = pyqtSignal()
    rightActionsChanged = pyqtSignal()
    logsExpandedChanged = pyqtSignal()
    eventsChanged = pyqtSignal()
    statusSummaryChanged = pyqtSignal()
    toastChanged = pyqtSignal()

    def __init__(self, app_state, feature_controllers=None, parent=None):
        super().__init__(parent)
        self._app_state = app_state
        self._nav_store = app_state.navigationStore
        self._cnc_store = app_state.cncStore
        self._feature_controllers = feature_controllers or {}
        self._title = ""
        self._left_actions = []
        self._right_actions = []
        self._status_summary = ""
        self._toast_text = ""
        self._toast_visible = False
        self._toast_timer = QTimer(self)
        self._toast_timer.setSingleShot(True)
        self._toast_timer.setInterval(3000)
        self._toast_timer.timeout.connect(self._hide_toast)

        self._nav_store.currentTabChanged.connect(self._refresh)
        self._nav_store.currentTitleChanged.connect(self._refresh)
        self._nav_store.headerVisibleChanged.connect(self._refresh)
        self._nav_store.logsExpandedChanged.connect(self.logsExpandedChanged)
        self._cnc_store.eventsChanged.connect(self.eventsChanged)
        self._cnc_store.taskModeChanged.connect(self._refresh_status_summary)
        self._cnc_store.machineStateChanged.connect(self._refresh_status_summary)
        self._cnc_store.activeFileChanged.connect(self._refresh_status_summary)
        self._cnc_store.lastCommandChanged.connect(self._refresh_status_summary)

        for controller in self._feature_controllers.values():
            signal = getattr(controller, "headerStateChanged", None)
            if signal is not None:
                signal.connect(self._refresh)

        self._refresh()
        self._refresh_status_summary()

    @pyqtProperty(str, notify=currentTabChanged)
    def currentTab(self):
        return self._nav_store.currentTab

    @pyqtProperty(str, notify=titleChanged)
    def title(self):
        return self._title

    @pyqtProperty(bool, notify=headerVisibleChanged)
    def headerVisible(self):
        return self._nav_store.headerVisible

    @pyqtProperty("QVariantList", notify=leftActionsChanged)
    def leftActions(self):
        return list(self._left_actions)

    @pyqtProperty("QVariantList", notify=rightActionsChanged)
    def rightActions(self):
        return list(self._right_actions)

    @pyqtProperty(bool, notify=logsExpandedChanged)
    def logsExpanded(self):
        return self._nav_store.logsExpanded

    @pyqtProperty("QVariantList", notify=eventsChanged)
    def events(self):
        return self._cnc_store.events

    @pyqtProperty(str, notify=statusSummaryChanged)
    def statusSummary(self):
        return self._status_summary

    @pyqtProperty(str, notify=toastChanged)
    def toastText(self):
        return self._toast_text

    @pyqtProperty(bool, notify=toastChanged)
    def toastVisible(self):
        return self._toast_visible

    @pyqtSlot(str)
    def activateTab(self, tab_id):
        self._app_state.activateTab(tab_id)

    @pyqtSlot()
    def toggleLogs(self):
        self._nav_store.toggleLogs()

    @pyqtSlot()
    def clearEvents(self):
        self._cnc_store.clearEvents()

    @pyqtSlot(str)
    def triggerHeaderAction(self, action_id):
        controller = self._feature_controllers.get(self._nav_store.currentTab)
        if controller is None or not hasattr(controller, "triggerHeaderAction"):
            return
        controller.triggerHeaderAction(action_id)
        self._refresh()

    @pyqtSlot(str)
    def showToast(self, message):
        self._toast_text = str(message or "")
        self._toast_visible = bool(self._toast_text)
        self.toastChanged.emit()
        self._toast_timer.start()

    def _hide_toast(self):
        if not self._toast_visible:
            return
        self._toast_visible = False
        self.toastChanged.emit()

    def _refresh(self):
        current_tab = self._nav_store.currentTab
        title = self._nav_store.currentTitle
        left_actions = []
        right_actions = []

        controller = self._feature_controllers.get(current_tab)
        if controller is not None and hasattr(controller, "getHeaderState"):
            try:
                header_state = controller.getHeaderState() or {}
            except Exception:
                header_state = {}
            title = header_state.get("title") or title
            left_actions = list(header_state.get("left_actions") or [])
            right_actions = list(header_state.get("right_actions") or [])

        title_changed = self._title != title
        left_changed = self._left_actions != left_actions
        right_changed = self._right_actions != right_actions

        self._title = title
        self._left_actions = left_actions
        self._right_actions = right_actions

        self.currentTabChanged.emit()
        self.headerVisibleChanged.emit()
        if title_changed:
            self.titleChanged.emit()
        if left_changed:
            self.leftActionsChanged.emit()
        if right_changed:
            self.rightActionsChanged.emit()

    def _refresh_status_summary(self):
        summary = (
            f"State: {self._cnc_store.machineState or '-'}\n"
            f"Task Mode: {self._cnc_store.taskMode or '-'}\n"
            f"Active File: {self._cnc_store.activeFile or '-'}\n"
            f"Last Command: {self._cnc_store.lastCommand or '-'}"
        )
        if self._status_summary != summary:
            self._status_summary = summary
            self.statusSummaryChanged.emit()
