import os

from PyQt5.QtCore import QObject, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QWidget


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


class AppShellQmlWidget(QWidget):
    CONTENT_PADDING = 6

    TAB_CONFIG = [
        ("manual", "Manual Turning", 0),
        ("conversational", "Conversational", 1),
        ("programs", "Programs", 2),
    ]

    INDEX_TO_TAB = {
        0: "manual",
        1: "conversational",
        2: "programs",
    }

    TAB_TO_INDEX = {tab_id: index for tab_id, _label, index in TAB_CONFIG}

    def __init__(self, content_stack, app_state, parent=None, feature_controllers=None):
        super().__init__(parent)
        self._content_stack = content_stack
        self._app_state = app_state
        self._nav_store = app_state.navigationStore
        self._bridge = AppShellBridge(app_state, feature_controllers or {}, self)
        self._qml_dir = os.path.join(os.path.dirname(__file__), "app_shell_qml")

        self._content_stack.setParent(None)
        if hasattr(self._content_stack, "tabBar"):
            self._content_stack.tabBar().hide()
        if hasattr(self._content_stack, "setDocumentMode"):
            self._content_stack.setDocumentMode(True)
        self._content_stack.setStyleSheet("QStackedWidget { border: 0; margin: 0; padding: 0; }")

        self._build_ui()
        self._wire()
        self._sync_from_tab_index(self._content_stack.currentIndex())
        self._sync_from_store()

    @property
    def title_bar(self):
        return self.top_bar

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.top_bar = self._create_qml_widget("AppShellTopBar.qml")
        self.top_bar.setFixedHeight(64)
        layout.addWidget(self.top_bar)

        self.content_host = QFrame(self)
        self.content_host.setObjectName("appShellContentHost")
        self.content_host.setStyleSheet("QFrame#appShellContentHost { background: #ffffff; border: none; }")
        self.content_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._content_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._content_stack.setMinimumSize(0, 0)
        content_layout = QVBoxLayout(self.content_host)
        content_layout.setContentsMargins(
            self.CONTENT_PADDING,
            self.CONTENT_PADDING,
            self.CONTENT_PADDING,
            self.CONTENT_PADDING,
        )
        content_layout.setSpacing(0)
        content_layout.addWidget(self._content_stack)
        layout.addWidget(self.content_host, 1)

        self.drawer = self._create_qml_widget("AppShellEventsDrawer.qml")
        self.drawer.setFixedHeight(300)
        self.drawer.setParent(self)
        self.drawer.hide()

        self.bottom_bar = self._create_qml_widget("AppShellBottomBar.qml")
        self.bottom_bar.setFixedHeight(64)
        layout.addWidget(self.bottom_bar)

        self.toast_overlay = self._create_qml_widget("AppShellToastOverlay.qml")
        self.toast_overlay.setParent(self)
        self.toast_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.toast_overlay.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        self.toast_overlay.setAttribute(Qt.WA_TranslucentBackground, True)
        self.toast_overlay.setClearColor(QColor(0, 0, 0, 0))
        self.toast_overlay.setGeometry(0, 0, self.width(), self.height())
        self.toast_overlay.raise_()

    def _create_qml_widget(self, file_name):
        widget = QQuickWidget(self)
        widget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        widget.setClearColor(QColor("#ffffff"))
        ctx = widget.engine().rootContext()
        ctx.setContextProperty("appShellBridge", self._bridge)
        ctx.setContextProperty("appState", self._app_state)
        ctx.setContextProperty("cncStore", self._app_state.cncStore)
        ctx.setContextProperty("navigationStore", self._app_state.navigationStore)
        widget.setSource(QUrl.fromLocalFile(os.path.join(self._qml_dir, file_name)))
        return widget

    def showToast(self, message):
        self._bridge.showToast(message)
        if hasattr(self, "toast_overlay"):
            self.toast_overlay.show()
            self.toast_overlay.raise_()

    def _wire(self):
        self._content_stack.currentChanged.connect(self._sync_from_tab_index)
        self._nav_store.currentTabChanged.connect(self._sync_from_store)
        self._nav_store.headerVisibleChanged.connect(self._sync_from_store)
        self._nav_store.logsExpandedChanged.connect(self._sync_from_store)

    def _sync_from_tab_index(self, index):
        tab_id = self.INDEX_TO_TAB.get(index, "manual")
        self._app_state.activateTab(tab_id)

    def _sync_from_store(self):
        current_tab = self._nav_store.currentTab
        target_index = self.TAB_TO_INDEX.get(current_tab)
        if target_index is not None and self._content_stack.currentIndex() != target_index:
            self._content_stack.setCurrentIndex(target_index)

        self.top_bar.setVisible(self._nav_store.headerVisible)
        self.drawer.setVisible(self._nav_store.logsExpanded)
        if self._nav_store.logsExpanded:
            self._position_drawer_overlay()
            self.drawer.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "toast_overlay"):
            self.toast_overlay.setGeometry(0, 0, self.width(), self.height())
            self.toast_overlay.raise_()
        self._position_drawer_overlay()

    def _position_drawer_overlay(self):
        if not hasattr(self, "drawer"):
            return
        width = min(max(420, self.width() // 2), max(0, self.width() - 24))
        height = min(300, max(0, self.content_host.height() - 24))
        if height <= 0:
            height = 220
        x = self.width() - width - 12
        y = self.height() - self.bottom_bar.height() - height
        self.drawer.setGeometry(x, y, width, height)
