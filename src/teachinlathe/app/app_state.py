from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot


class DomainStore(QObject):
    titleChanged = pyqtSignal()
    headerVisibleChanged = pyqtSignal()

    def __init__(self, title, header_visible=True, parent=None):
        super().__init__(parent)
        self._title = title
        self._header_visible = header_visible

    @pyqtProperty(str, notify=titleChanged)
    def title(self):
        return self._title

    @pyqtProperty(bool, notify=headerVisibleChanged)
    def headerVisible(self):
        return self._header_visible


class NavigationStore(QObject):
    currentTabChanged = pyqtSignal()
    currentTitleChanged = pyqtSignal()
    headerVisibleChanged = pyqtSignal()
    logsExpandedChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_tab = 'manual'
        self._current_title = ''
        self._header_visible = False
        self._logs_expanded = False

    @pyqtProperty(str, notify=currentTabChanged)
    def currentTab(self):
        return self._current_tab

    @pyqtProperty(str, notify=currentTitleChanged)
    def currentTitle(self):
        return self._current_title

    @pyqtProperty(bool, notify=headerVisibleChanged)
    def headerVisible(self):
        return self._header_visible

    @pyqtProperty(bool, notify=logsExpandedChanged)
    def logsExpanded(self):
        return self._logs_expanded

    def setCurrentView(self, tab_id, title, header_visible):
        if self._current_tab != tab_id:
            self._current_tab = tab_id
            self.currentTabChanged.emit()
        if self._current_title != title:
            self._current_title = title
            self.currentTitleChanged.emit()
        if self._header_visible != header_visible:
            self._header_visible = header_visible
            self.headerVisibleChanged.emit()

    @pyqtSlot()
    def toggleLogs(self):
        self.setLogsExpanded(not self._logs_expanded)

    def setLogsExpanded(self, expanded):
        expanded = bool(expanded)
        if self._logs_expanded == expanded:
            return
        self._logs_expanded = expanded
        self.logsExpandedChanged.emit()


class AppState(QObject):
    # The stores below are built once in __init__ and never replaced, so the
    # properties exposing them are declared constant. A constant property has
    # no change signal by definition - the pair that used to be declared here
    # was never emitted and never connected.

    def __init__(self, parent=None):
        super().__init__(parent)
        self._navigation_store = NavigationStore(self)
        # No title: the menu is on the left of its title bar
        self._manual_store = DomainStore('', True, self)
        self._conversational_store = DomainStore('Conversational', True, self)
        self._programs_store = DomainStore('Programs', True, self)
        self._tools_store = DomainStore('Tool Library', True, self)
        self._machine_settings_store = DomainStore('Machine Settings', True, self)
        self._stores = {
            'manual': self._manual_store,
            'conversational': self._conversational_store,
            'programs': self._programs_store,
            'tools': self._tools_store,
            'settings': self._machine_settings_store,
        }
        self.activateTab('manual')

    @pyqtProperty(QObject, constant=True)
    def navigationStore(self):
        return self._navigation_store

    @pyqtProperty(QObject, constant=True)
    def manualStore(self):
        return self._manual_store

    @pyqtProperty(QObject, constant=True)
    def conversationalStore(self):
        return self._conversational_store

    @pyqtProperty(QObject, constant=True)
    def programsStore(self):
        return self._programs_store

    @pyqtProperty(QObject, constant=True)
    def toolsStore(self):
        return self._tools_store

    @pyqtProperty(QObject, constant=True)
    def machineSettingsStore(self):
        return self._machine_settings_store

    @pyqtSlot(str)
    def activateTab(self, tab_id):
        store = self._stores.get(tab_id, self._manual_store)
        self._navigation_store.setCurrentView(tab_id, store.title, store.headerVisible)

    def storeForTab(self, tab_id):
        return self._stores.get(tab_id, self._manual_store)
