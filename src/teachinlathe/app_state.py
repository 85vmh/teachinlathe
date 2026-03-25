import logging
from datetime import datetime

from PyQt5.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.plugins import getPlugin

STATUS = getPlugin('status')


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


class StoreLogHandler(logging.Handler):
    def __init__(self, cnc_store):
        super().__init__()
        self._cnc_store = cnc_store
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()
        self._cnc_store.addEvent(record.levelname, record.name, message)


class CncStore(QObject):
    eventsChanged = pyqtSignal()
    taskModeChanged = pyqtSignal()
    machineStateChanged = pyqtSignal()
    activeFileChanged = pyqtSignal()
    lastCommandChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events = []
        self._max_events = 500
        self._task_mode = ''
        self._machine_state = ''
        self._active_file = ''
        self._last_command = ''

        self._log_handler = StoreLogHandler(self)
        self._log_handler.setLevel(logging.INFO)
        root_logger = logging.getLogger()
        if not any(isinstance(h, StoreLogHandler) for h in root_logger.handlers):
            root_logger.addHandler(self._log_handler)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self.refreshStatus)
        self._poll_timer.start()

        self.addEvent('INFO', 'app', 'CNC store initialized')
        self.refreshStatus()

    @pyqtProperty('QVariantList', notify=eventsChanged)
    def events(self):
        return list(self._events)

    @pyqtProperty(str, notify=taskModeChanged)
    def taskMode(self):
        return self._task_mode

    @pyqtProperty(str, notify=machineStateChanged)
    def machineState(self):
        return self._machine_state

    @pyqtProperty(str, notify=activeFileChanged)
    def activeFile(self):
        return self._active_file

    @pyqtProperty(str, notify=lastCommandChanged)
    def lastCommand(self):
        return self._last_command

    @pyqtSlot(str)
    def submitCommand(self, command_text):
        command_text = (command_text or '').strip()
        if not command_text:
            return
        self._last_command = command_text
        self.lastCommandChanged.emit()
        self.addEvent('COMMAND', 'mdi', command_text)
        try:
            issue_mdi(command_text)
        except Exception as exc:
            self.addEvent('ERROR', 'mdi', str(exc))

    @pyqtSlot()
    def clearEvents(self):
        if not self._events:
            return
        self._events = []
        self.eventsChanged.emit()

    def addEvent(self, level, source, message):
        entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'level': str(level),
            'source': str(source),
            'message': str(message),
        }
        self._events.append(entry)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
        self.eventsChanged.emit()

    def refreshStatus(self):
        try:
            stat = getattr(STATUS, 'stat', None)
            if stat is not None:
                stat.poll()
        except Exception:
            stat = None

        task_mode = ''
        machine_state = ''
        active_file = ''

        try:
            task_mode = str(getattr(getattr(STATUS, 'task_mode', None), 'value', '')) or str(getattr(stat, 'task_mode', ''))
        except Exception:
            task_mode = ''
        try:
            machine_state = str(getattr(getattr(STATUS, 'state', None), 'value', '')) or str(getattr(stat, 'state', ''))
        except Exception:
            machine_state = ''
        try:
            active_file = str(getattr(getattr(STATUS, 'file', None), 'value', '')) or str(getattr(stat, 'file', ''))
        except Exception:
            active_file = ''

        if self._task_mode != task_mode:
            self._task_mode = task_mode
            self.taskModeChanged.emit()
        if self._machine_state != machine_state:
            self._machine_state = machine_state
            self.machineStateChanged.emit()
        if self._active_file != active_file:
            self._active_file = active_file
            self.activeFileChanged.emit()


class AppState(QObject):
    navigationStoreChanged = pyqtSignal()
    cncStoreChanged = pyqtSignal()
    manualStoreChanged = pyqtSignal()
    conversationalStoreChanged = pyqtSignal()
    programsStoreChanged = pyqtSignal()
    toolsStoreChanged = pyqtSignal()
    machineSettingsStoreChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._navigation_store = NavigationStore(self)
        self._cnc_store = CncStore(self)
        self._manual_store = DomainStore('Manual Turning', False, self)
        self._conversational_store = DomainStore('Conversational', True, self)
        self._programs_store = DomainStore('Programs', True, self)
        self._tools_store = DomainStore('Tools & Offsets', True, self)
        self._machine_settings_store = DomainStore('Machine Settings', True, self)
        self._stores = {
            'manual': self._manual_store,
            'conversational': self._conversational_store,
            'programs': self._programs_store,
            'tools': self._tools_store,
            'settings': self._machine_settings_store,
        }
        self.activateTab('manual')

    @pyqtProperty(QObject, notify=navigationStoreChanged, constant=True)
    def navigationStore(self):
        return self._navigation_store

    @pyqtProperty(QObject, notify=cncStoreChanged, constant=True)
    def cncStore(self):
        return self._cnc_store

    @pyqtProperty(QObject, notify=manualStoreChanged, constant=True)
    def manualStore(self):
        return self._manual_store

    @pyqtProperty(QObject, notify=conversationalStoreChanged, constant=True)
    def conversationalStore(self):
        return self._conversational_store

    @pyqtProperty(QObject, notify=programsStoreChanged, constant=True)
    def programsStore(self):
        return self._programs_store

    @pyqtProperty(QObject, notify=toolsStoreChanged, constant=True)
    def toolsStore(self):
        return self._tools_store

    @pyqtProperty(QObject, notify=machineSettingsStoreChanged, constant=True)
    def machineSettingsStore(self):
        return self._machine_settings_store

    @pyqtSlot(str)
    def activateTab(self, tab_id):
        store = self._stores.get(tab_id, self._manual_store)
        self._navigation_store.setCurrentView(tab_id, store.title, store.headerVisible)

    def storeForTab(self, tab_id):
        return self._stores.get(tab_id, self._manual_store)
