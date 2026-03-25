from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class AppShellWidget(QWidget):
    TAB_CONFIG = [
        ('manual', 'Manual Turning', 0),
        ('conversational', 'Conversational', 1),
        ('programs', 'Programs', 2),
        ('settings', 'Machine Settings', 4),
    ]

    INDEX_TO_TAB = {
        0: 'manual',
        1: 'conversational',
        2: 'programs',
        3: 'tools',
        4: 'settings',
    }

    TAB_TO_INDEX = {tab_id: index for tab_id, _label, index in TAB_CONFIG}
    TAB_TO_INDEX['tools'] = 3

    def __init__(self, tab_widget, app_state, parent=None, feature_controllers=None):
        super().__init__(parent)
        self._tab_widget = tab_widget
        self._app_state = app_state
        self._nav_store = app_state.navigationStore
        self._cnc_store = app_state.cncStore
        self._feature_controllers = feature_controllers or {}
        self._buttons = {}

        self._tab_widget.setParent(None)
        self._tab_widget.tabBar().hide()
        self._tab_widget.setDocumentMode(True)

        self._build_ui()
        self._wire()
        self._sync_from_tab_index(self._tab_widget.currentIndex())
        self._refresh_events()
        self._apply_log_panel_state()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.title_bar = QFrame(self)
        self.title_bar.setObjectName('appShellTitleBar')
        self.title_bar.setStyleSheet(
            'QFrame#appShellTitleBar { background: #f5f7fb; border-bottom: 1px solid #d6dce7; }'
            'QLabel#appShellTitle { color: #1e2430; font: 700 17pt "Noto Sans"; }'
            'QPushButton#appShellActionButton { background: #2d7d46; color: white; border: 1px solid #3fb950; padding: 8px 14px; font: 12pt "Noto Sans"; border-radius: 6px; }'
            'QPushButton#appShellActionButton:hover { background: #25673a; }'
            'QPushButton#appShellActionButton:checked { background: #7a5a12; border-color: #d7ba7d; }'
            'QPushButton#appShellActionButton:hover:checked { background: #684b0f; }'
            'QPushButton#appShellActionButton:disabled { color: #d9e7de; background: #8ea99a; border-color: #8ea99a; }'
            'QPushButton#appShellBackButton { background: #eef3fb; color: #1e2430; border: 1px solid #c5d0df; padding: 7px 11px; font: 11pt "Noto Sans"; border-radius: 6px; min-width: 0px; }'
            'QPushButton#appShellBackButton:hover { background: #e5edf9; }'
            'QPushButton#appShellBackButton:disabled { color: #8c97a8; background: #f3f5f8; border-color: #d5dbe4; }'
        )
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(20, 10, 20, 10)
        title_layout.setSpacing(12)

        self.left_actions = QWidget(self.title_bar)
        self.left_actions_layout = QHBoxLayout(self.left_actions)
        self.left_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.left_actions_layout.setSpacing(10)
        self.left_actions_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_layout.addWidget(self.left_actions, 1)

        self.title_label = QLabel('', self.title_bar)
        self.title_label.setObjectName('appShellTitle')
        self.title_label.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(self.title_label, 0, Qt.AlignCenter)

        self.right_actions = QWidget(self.title_bar)
        self.right_actions_layout = QHBoxLayout(self.right_actions)
        self.right_actions_layout.setContentsMargins(0, 0, 0, 0)
        self.right_actions_layout.setSpacing(10)
        self.right_actions_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_layout.addWidget(self.right_actions, 1)

        root.addWidget(self.title_bar)

        self.content_host = QFrame(self)
        self.content_host.setObjectName('appShellContentHost')
        self.content_host.setStyleSheet('QFrame#appShellContentHost { background: #ffffff; }')
        content_layout = QVBoxLayout(self.content_host)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._tab_widget)
        root.addWidget(self.content_host, 1)

        self.drawer_host = QWidget(self)
        drawer_host_layout = QHBoxLayout(self.drawer_host)
        drawer_host_layout.setContentsMargins(0, 0, 0, 0)
        drawer_host_layout.setSpacing(0)
        drawer_host_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.drawer_container = QFrame(self.drawer_host)
        self.drawer_container.setObjectName('appShellDrawerWrap')
        self.drawer_container.setStyleSheet(
            'QFrame#appShellDrawerWrap { background: #11161d; border: 1px solid #2b3440; border-bottom: none; }'
            'QLabel { color: white; }'
            'QListWidget { background: #11161d; color: #d8e0ef; border: none; font: 11pt "Noto Sans Mono"; }'
            'QPushButton { background: #263244; color: white; border: 1px solid #3b4b62; padding: 8px 12px; }'
            'QPushButton:hover { background: #32425a; }'
        )
        drawer_layout = QVBoxLayout(self.drawer_container)
        drawer_layout.setContentsMargins(16, 16, 16, 16)
        drawer_layout.setSpacing(10)

        drawer_header = QHBoxLayout()
        drawer_title = QLabel('Application Events', self.drawer_container)
        drawer_title.setStyleSheet('font: 700 15pt "Noto Sans";')
        drawer_header.addWidget(drawer_title)
        drawer_header.addStretch(1)
        self.clear_events_btn = QPushButton('Clear', self.drawer_container)
        drawer_header.addWidget(self.clear_events_btn)
        drawer_layout.addLayout(drawer_header)

        self.status_summary = QLabel('', self.drawer_container)
        self.status_summary.setWordWrap(True)
        self.status_summary.setStyleSheet('color: #9fb0c7; font: 10pt "Noto Sans";')
        drawer_layout.addWidget(self.status_summary)

        self.events_list = QListWidget(self.drawer_container)
        self.events_list.setAlternatingRowColors(False)
        drawer_layout.addWidget(self.events_list, 1)

        drawer_host_layout.addWidget(self.drawer_container)
        self.drawer_host.hide()

        self.bottom_bar = QFrame(self)
        self.bottom_bar.setObjectName('appShellBottomBar')
        self.bottom_bar.setStyleSheet(
            'QFrame#appShellBottomBar { background: #f5f7fb; border-top: 1px solid #d6dce7; }'
            'QToolButton { color: #4a5568; background: transparent; border: none; padding: 14px 18px; font: 12pt "Noto Sans"; border-radius: 0px; }'
            'QToolButton:checked { color: #1e2430; background: #e6edf7; border-top: 3px solid #2d7d46; padding-top: 11px; }'
            'QToolButton:hover:!checked { background: #eef3fb; color: #1e2430; }'
            'QPushButton { background: transparent; color: #4a5568; border: none; padding: 14px 18px; font: 12pt "Noto Sans"; }'
            'QPushButton:hover { background: #eef3fb; color: #1e2430; }'
        )
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(12, 0, 12, 0)
        bottom_layout.setSpacing(6)

        for tab_id, label, _index in self.TAB_CONFIG:
            btn = QToolButton(self.bottom_bar)
            btn.setCheckable(True)
            btn.setText(label)
            btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btn.setFixedWidth(200)
            btn.clicked.connect(lambda _checked=False, tid=tab_id: self._app_state.activateTab(tid))
            bottom_layout.addWidget(btn)
            self._buttons[tab_id] = btn

        bottom_layout.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.drawer_toggle = QPushButton('Events', self.bottom_bar)
        bottom_layout.addWidget(self.drawer_toggle)
        root.addWidget(self.bottom_bar)

    def _wire(self):
        self._tab_widget.currentChanged.connect(self._sync_from_tab_index)
        self._nav_store.currentTabChanged.connect(self._sync_from_store)
        self._nav_store.currentTitleChanged.connect(self._sync_from_store)
        self._nav_store.headerVisibleChanged.connect(self._sync_from_store)
        self._nav_store.logsExpandedChanged.connect(self._apply_log_panel_state)
        self._cnc_store.eventsChanged.connect(self._refresh_events)
        self._cnc_store.taskModeChanged.connect(self._refresh_status_summary)
        self._cnc_store.machineStateChanged.connect(self._refresh_status_summary)
        self._cnc_store.activeFileChanged.connect(self._refresh_status_summary)
        self._cnc_store.lastCommandChanged.connect(self._refresh_status_summary)
        self.drawer_toggle.clicked.connect(self._nav_store.toggleLogs)
        self.clear_events_btn.clicked.connect(self._cnc_store.clearEvents)

        for controller in self._feature_controllers.values():
            signal = getattr(controller, 'headerStateChanged', None)
            if signal is not None:
                signal.connect(self._sync_from_store)

    def _sync_from_tab_index(self, index):
        tab_id = self.INDEX_TO_TAB.get(index, 'manual')
        self._app_state.activateTab(tab_id)

    def _sync_from_store(self):
        current_tab = self._nav_store.currentTab
        target_index = self.TAB_TO_INDEX.get(current_tab)
        if target_index is not None and self._tab_widget.currentIndex() != target_index:
            self._tab_widget.setCurrentIndex(target_index)

        for tab_id, button in self._buttons.items():
            button.blockSignals(True)
            button.setChecked(tab_id == current_tab)
            button.blockSignals(False)

        title = self._nav_store.currentTitle
        left_actions = []
        right_actions = []
        controller = self._feature_controllers.get(current_tab)
        if controller is not None and hasattr(controller, 'getHeaderState'):
            try:
                header_state = controller.getHeaderState() or {}
            except Exception:
                header_state = {}
            title = header_state.get('title') or title
            left_actions = list(header_state.get('left_actions') or [])
            right_actions = list(header_state.get('right_actions') or [])

        self.title_label.setText(title)
        self.title_bar.setVisible(self._nav_store.headerVisible)
        self._rebuild_header_actions(self.left_actions_layout, left_actions)
        self._rebuild_header_actions(self.right_actions_layout, right_actions)
        self._refresh_status_summary()

    def _rebuild_header_actions(self, layout, actions):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        current_tab = self._nav_store.currentTab
        for action in actions:
            button = QPushButton(action.get('text', ''), self.title_bar)
            if action.get('id') == 'back':
                button.setObjectName('appShellBackButton')
                button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            else:
                button.setObjectName('appShellActionButton')
                button.setCheckable(bool(action.get('checked', False)))
                button.setChecked(bool(action.get('checked', False)))
            button.setEnabled(bool(action.get('enabled', True)))
            action_id = action.get('id')
            button.clicked.connect(lambda _checked=False, tid=current_tab, aid=action_id: self._trigger_header_action(tid, aid))
            layout.addWidget(button)

    def _trigger_header_action(self, tab_id, action_id):
        controller = self._feature_controllers.get(tab_id)
        if controller is None or not hasattr(controller, 'triggerHeaderAction'):
            return
        controller.triggerHeaderAction(action_id)
        self._sync_from_store()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_drawer_overlay()

    def _position_drawer_overlay(self):
        if self.bottom_bar is None or self.content_host is None:
            return

        width = max(420, self.width() // 2)
        width = min(width, max(0, self.width() - 24))
        height = max(220, self.height() // 3)
        max_height = max(0, self.content_host.height() - 24)
        if max_height > 0:
            height = min(height, max_height)

        bottom_bar_height = self.bottom_bar.height()
        x = self.width() - width - 12
        y = self.height() - bottom_bar_height - height
        self.drawer_host.setGeometry(x, y, width, height)
        self.drawer_container.setFixedWidth(width)
        self.drawer_container.setFixedHeight(height)

    def _apply_log_panel_state(self):
        expanded = self._nav_store.logsExpanded
        self.drawer_container.setVisible(expanded)
        self.drawer_host.setVisible(expanded)
        if expanded:
            self._position_drawer_overlay()
            self.drawer_host.raise_()
        else:
            self.drawer_container.setFixedWidth(0)
            self.drawer_container.setFixedHeight(0)
        self.drawer_toggle.setText('Close Events' if expanded else 'Events')

    def _refresh_status_summary(self):
        summary = (
            f"State: {self._cnc_store.machineState or '-'}\n"
            f"Task Mode: {self._cnc_store.taskMode or '-'}\n"
            f"Active File: {self._cnc_store.activeFile or '-'}\n"
            f"Last Command: {self._cnc_store.lastCommand or '-'}"
        )
        self.status_summary.setText(summary)

    def _refresh_events(self):
        self.events_list.clear()
        for entry in self._cnc_store.events:
            line = f"[{entry['timestamp']}] {entry['level']:<7} {entry['source']}: {entry['message']}"
            item = QListWidgetItem(line)
            color = QColor('#d8e0ef')
            if entry['level'] == 'ERROR':
                color = QColor('#ff8a80')
            elif entry['level'] == 'WARNING':
                color = QColor('#ffd180')
            elif entry['level'] == 'COMMAND':
                color = QColor('#80cbc4')
            item.setForeground(color)
            self.events_list.addItem(item)
