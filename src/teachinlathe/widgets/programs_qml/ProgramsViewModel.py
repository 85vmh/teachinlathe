import os

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.widgets.programs_qml.filesystemview.FileSystemBridge import FileSystemBridge, load_or_reload_program

from teachinlathe.data.program_runtime import ProgramRuntimeStore
from teachinlathe.data.program_stack import ProgramCallStackResolver
from teachinlathe.data.programs_action_source import ProgramsActionSource
from teachinlathe.data.programs_screen import ProgramsScreen
from teachinlathe.data.run_time_tracker import RunTimeTracker, format_duration

Screen = ProgramsScreen


class ProgramsViewModel(QObject):
    screenIndexChanged = pyqtSignal(int)
    currentFilePathChanged = pyqtSignal(str)
    currentFileContentChanged = pyqtSignal(str)
    currentFileDisplayPathChanged = pyqtSignal(str)
    executionViewChanged = pyqtSignal()
    runningStateChanged = pyqtSignal()
    # Full-screen run view transitions
    enterRunFullScreenRequested = pyqtSignal()
    exitRunFullScreenRequested = pyqtSignal()
    # name, movement, toolchange, total (pre-formatted strings)
    programCompleted = pyqtSignal(str, str, str, str)
    programLoadRequested = pyqtSignal(str)
    ensureProgramLoadedRequested = pyqtSignal()
    gremlinZoomInRequested = pyqtSignal()
    gremlinZoomOutRequested = pyqtSignal()
    gremlinClearRequested = pyqtSignal()
    gremlinFitRequested = pyqtSignal()

    def __init__(self, folders, parent=None):
        super().__init__(parent)
        self._bridge = FileSystemBridge(folders, self)
        self._runtime_store = ProgramRuntimeStore(self)
        self._call_stack_resolver = ProgramCallStackResolver(self)
        self._actions = ProgramsActionSource(self._runtime_store, self)
        self._screen_index = Screen.FileSystem
        self._run_tracker = RunTimeTracker(self)
        self._was_active = False
        self._run_started = False
        self._abort_requested = False
        self._execution_frames = []
        self._active_execution_file_path = ''
        self._active_execution_title = ''
        self._active_execution_content = ''
        self._active_execution_motion_line = 0
        self._is_execution_context_current_program = False

        self._bridge.filePathChanged.connect(self._on_file_path_changed)
        self._bridge.fileContentChanged.connect(self._on_file_content_changed)
        self._bridge.screenChangeRequested.connect(self._set_screen_index)
        self._bridge.programLoadRequested.connect(self.programLoadRequested)

        self._runtime_store.snapshotChanged.connect(self._on_runtime_snapshot_changed)
        self._runtime_store.machineFileChanged.connect(lambda _path: self.runningStateChanged.emit())
        self._actions.stateChanged.connect(self.runningStateChanged)
        self._actions.stateChanged.connect(self._on_running_state_changed)
        self._actions.abortTriggered.connect(self._on_abort_triggered)
        self._actions.cycleStartObserved.connect(self._on_cycle_start_observed)

        self._refresh_execution_view()

    @property
    def bridge(self):
        return self._bridge

    @property
    def runtime_store(self):
        return self._runtime_store

    @pyqtProperty(QObject, constant=True)
    def actions(self):
        return self._actions

    @pyqtProperty('QVariantList', constant=True)
    def folderNames(self):
        return self._bridge.folderNames

    @pyqtProperty(int, notify=screenIndexChanged)
    def screenIndex(self):
        return self._screen_index

    @pyqtProperty(str, notify=currentFilePathChanged)
    def currentFilePath(self):
        return self._bridge.currentFilePath

    @pyqtProperty(str, notify=currentFileContentChanged)
    def currentFileContent(self):
        return self._bridge._current_content

    @pyqtProperty(str, notify=currentFileDisplayPathChanged)
    def currentFileDisplayPath(self):
        return self.currentFilePath or 'No file loaded'

    @pyqtProperty(bool, notify=executionViewChanged)
    def hasExecutionStack(self):
        return bool(self._execution_frames and self._active_execution_content)

    @pyqtProperty('QVariantList', notify=executionViewChanged)
    def executionFrames(self):
        return list(self._execution_frames)

    @pyqtProperty(str, notify=executionViewChanged)
    def activeExecutionFilePath(self):
        return self._active_execution_file_path

    @pyqtProperty(str, notify=executionViewChanged)
    def activeExecutionTitle(self):
        return self._active_execution_title

    @pyqtProperty(str, notify=executionViewChanged)
    def activeExecutionContent(self):
        return self._active_execution_content

    @pyqtProperty(int, notify=executionViewChanged)
    def activeExecutionMotionLine(self):
        return self._active_execution_motion_line

    @pyqtProperty(int, notify=executionViewChanged)
    def mainHighlightLine(self):
        snapshot = self._runtime_store.snapshot
        if self.hasExecutionStack:
            return 0
        if not self._is_showing_machine_file(snapshot.machine_file):
            return 0
        return int(snapshot.motion_line or 0)

    @pyqtProperty(bool, notify=currentFilePathChanged)
    def hasCurrentFile(self):
        return bool(self.currentFilePath)

    @pyqtProperty(bool, notify=screenIndexChanged)
    def isGremlinScreen(self):
        return self._screen_index == Screen.ProgramLoaded

    @pyqtSlot(int)
    def navigateTo(self, screen):
        self._bridge.navigateTo(screen)

    @pyqtSlot()
    def showFilesScreen(self):
        self.navigateTo(Screen.FileSystem)

    @pyqtSlot()
    def showGremlinScreen(self):
        self.navigateTo(Screen.ProgramLoaded)

    @pyqtSlot(str, result='QVariantList')
    def getFiles(self, folder_name):
        return self._bridge.getFiles(folder_name)

    @pyqtSlot(str, str, result='QVariantList')
    def getFilesInPath(self, folder_name, relative_path):
        return self._bridge.getFilesInPath(folder_name, relative_path)

    @pyqtSlot(str, result=str)
    def getFolderPath(self, folder_name):
        return self._bridge.getFolderPath(folder_name)

    @pyqtSlot(str, str)
    def selectFile(self, folder_name, relative_path):
        self._bridge.selectFile(folder_name, relative_path)

    @pyqtSlot(str, str)
    def openFile(self, folder_name, relative_path):
        self._bridge.openFile(folder_name, relative_path)

    @pyqtSlot(QObject)
    def attachHighlighter(self, quick_document):
        self._bridge.attachHighlighter(quick_document)

    @pyqtSlot(str)
    def openFileByAbsolutePath(self, path: str) -> None:
        """Load a file into LinuxCNC by absolute path — called from FileSystemViewModel."""
        self._bridge.openFileByAbsolutePath(path)

    @pyqtSlot()
    def openCurrentFileInMachine(self):
        file_path = self.currentFilePath
        if not file_path:
            return

        folder_name = None
        relative_path = None
        for candidate_name, candidate_path in self._bridge._folders:
            candidate_root = os.path.abspath(candidate_path)
            if file_path == candidate_root or file_path.startswith(candidate_root + os.sep):
                folder_name = candidate_name
                relative_path = file_path[len(candidate_root):].lstrip(os.sep)
                break

        if folder_name is not None and relative_path is not None:
            self._bridge.openFile(folder_name, relative_path)
            return

        self.programLoadRequested.emit(file_path)
        load_or_reload_program(file_path)
        self._bridge.navigateTo(Screen.ProgramLoaded)

    @pyqtSlot()
    def zoomGremlinIn(self):
        self.gremlinZoomInRequested.emit()

    @pyqtSlot()
    def zoomGremlinOut(self):
        self.gremlinZoomOutRequested.emit()

    @pyqtSlot()
    def clearGremlinPlot(self):
        self.gremlinClearRequested.emit()

    @pyqtSlot()
    def requestGremlinFit(self):
        self.gremlinFitRequested.emit()

    def _on_file_path_changed(self, path):
        self._run_started = False
        self._was_active = False
        self.currentFilePathChanged.emit(path)
        self.currentFileDisplayPathChanged.emit(self.currentFileDisplayPath)
        self._refresh_execution_view()

    def _on_file_content_changed(self, content):
        self.currentFileContentChanged.emit(content)
        self._refresh_execution_view()

    def _on_runtime_snapshot_changed(self, _snapshot):
        self.runningStateChanged.emit()
        self._refresh_execution_view()

    def _set_screen_index(self, screen):
        screen = int(screen or 0)
        if self._screen_index == screen:
            return
        self._screen_index = screen
        self.screenIndexChanged.emit(self._screen_index)

    # ── Running full-screen state machine ─────────────────────────────
    def _on_abort_triggered(self):
        self._abort_requested = True
        self._run_started = False
        if self._screen_index == Screen.ProgramRunning:
            self._set_screen_index(Screen.ProgramLoaded)
            self.exitRunFullScreenRequested.emit()

    def _on_cycle_start_observed(self):
        if self._has_loaded_program_for_run():
            self._run_started = True
            self._on_running_state_changed()

    def _on_running_state_changed(self):
        active = self._actions.isActive
        loaded = self._has_loaded_program_for_run()
        tracking_active = active and loaded and self._run_started
        if tracking_active and not self._was_active:
            self._abort_requested = False
            self._run_tracker.start()
            self._set_screen_index(Screen.ProgramRunning)
            self.enterRunFullScreenRequested.emit()
        elif self._was_active and not tracking_active:
            movement, toolchange, total = self._run_tracker.stop()
            if self._abort_requested:
                if self._screen_index == Screen.ProgramRunning:
                    self._set_screen_index(Screen.ProgramLoaded)
                    self.exitRunFullScreenRequested.emit()
            elif self._run_started:
                name = os.path.basename(self.currentFilePath or '') or 'Program'
                self.programCompleted.emit(
                    name,
                    format_duration(movement),
                    format_duration(toolchange),
                    format_duration(total),
                )
            elif self._screen_index == Screen.ProgramRunning:
                self._set_screen_index(Screen.ProgramLoaded)
                self.exitRunFullScreenRequested.emit()
            self._abort_requested = False
            self._run_started = False
        self._was_active = tracking_active

    def _has_loaded_program_for_run(self):
        snapshot = self._runtime_store.snapshot
        if not snapshot.machine_file:
            return False
        if not os.path.isfile(snapshot.machine_file):
            return False
        if self.currentFilePath and self._is_showing_machine_file(snapshot.machine_file):
            return True
        return bool(self.currentFilePath and os.path.isfile(self.currentFilePath))

    @pyqtSlot()
    def runDone(self):
        """'Done' on the completion popup: leave full screen back to Loaded."""
        self._set_screen_index(Screen.ProgramLoaded)
        self.exitRunFullScreenRequested.emit()

    @pyqtSlot()
    def runAgain(self):
        """'Run Again' on the completion popup: start the program once more."""
        self.ensureProgramLoadedRequested.emit()
        self._actions.triggerStart()

    def _is_showing_machine_file(self, machine_file=''):
        editor_path = os.path.abspath(self.currentFilePath) if self.currentFilePath else ''
        runtime_path = os.path.abspath(machine_file) if machine_file else ''
        return bool(editor_path and runtime_path and editor_path == runtime_path)

    def _is_executing_current_program(self, snapshot):
        if self._is_showing_machine_file(snapshot.machine_file):
            return True

        editor_path = os.path.abspath(self.currentFilePath) if self.currentFilePath else ''
        if not editor_path:
            return False

        if self._actions.isActive and snapshot.call_level > 0 and snapshot.call_stack:
            return True

        return any(
            os.path.abspath(frame.filename) == editor_path
            for frame in snapshot.call_stack
            if frame.filename
        )

    def _refresh_execution_view(self):
        snapshot = self._runtime_store.snapshot
        frames = []
        active_path = ''
        active_title = ''
        active_content = ''
        active_motion_line = 0

        is_executing_current_program = self._is_executing_current_program(snapshot)
        if is_executing_current_program and snapshot.call_level > 0:
            stack_view = self._call_stack_resolver.build_view(snapshot)
            if stack_view is not None:
                for frame in stack_view.frames:
                    frames.append({
                        'filePath': frame.file_path,
                        'title': os.path.basename(frame.file_path) or 'Unknown file',
                        'content': frame.content,
                        'lineNumber': int(frame.line_number or 0),
                        'lineText': self._call_stack_resolver.get_line_text(frame.content, frame.line_number),
                    })
                active_path = stack_view.active_file_path
                active_title = os.path.basename(active_path) or 'Subroutine'
                active_content = stack_view.active_content
                active_motion_line = int(stack_view.motion_line or 0)

        next_signature = (
            tuple((frame['filePath'], frame['lineNumber'], frame['lineText']) for frame in frames),
            active_path,
            active_content,
            active_motion_line,
            int(snapshot.motion_line or 0),
            bool(is_executing_current_program),
        )
        current_signature = (
            tuple((frame['filePath'], frame['lineNumber'], frame['lineText']) for frame in self._execution_frames),
            self._active_execution_file_path,
            self._active_execution_content,
            self._active_execution_motion_line,
            self.mainHighlightLine,
            bool(self._is_execution_context_current_program),
        )
        if next_signature == current_signature:
            return

        self._execution_frames = frames
        self._active_execution_file_path = active_path
        self._active_execution_title = active_title
        self._active_execution_content = active_content
        self._active_execution_motion_line = active_motion_line
        self._is_execution_context_current_program = is_executing_current_program
        self.executionViewChanged.emit()
