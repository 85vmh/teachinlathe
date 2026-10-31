"""The Programs tab's view model.

Two screens over one strip of panes - the file system, and the loaded
program with its backplot - and which of them is up (``screenIndex``), or
the simulation of a file over them (``simulate``, SimulateViewModel); the
program running, completed or aborted; the app shell's header for each.
The file browser, the DRO and the tool/feed/speed row have view models of
their own, as properties of this one.

The backplot is a scene-graph item QML makes. It is told what to preview by
``previewFile`` and the preview* / gremlin* signals, which
ProgramLoadedScreen.qml passes on to it; nothing here holds it.
"""

import logging
import os

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.core.ini_repository import ini_repository
from teachinlathe.ui.common.images import image_url
from teachinlathe.ui.tabs.programs.filesystemview import FileSystemLocation, FileSystemViewModel, LocationType
from teachinlathe.ui.tabs.programs.filesystemview.FileSystemBridge import FileSystemBridge
from teachinlathe.ui.tabs.programs.ProgramRunViewModel import ProgramRunViewModel
from teachinlathe.ui.tabs.programs.simulate.SimulateViewModel import SimulateViewModel

from teachinlathe.programs.model.program_runtime import ProgramRuntimeStore
from teachinlathe.programs.model.program_stack import ProgramCallStackResolver
from teachinlathe.programs.model.programs_action_source import ProgramsActionSource
from teachinlathe.programs.model.programs_screen import ProgramsScreen
from teachinlathe.programs.model.run_time_tracker import RunTimeTracker
from teachinlathe.programs.logic.simulate_use_case import SimulateUseCase
from teachinlathe.programs.logic.final_profile_use_case import FinalProfileUseCase
from teachinlathe.programs.logic.tool_changes_use_case import ToolChangesUseCase
from teachinlathe.programs.logic.run import MachineRunSource
from teachinlathe.programs.logic.programs_use_case import ProgramsUseCase
from teachinlathe.ui.tabs.programs.ProgramsToolChangeViewModel import ProgramsToolChangeViewModel

Screen = ProgramsScreen

LOG = logging.getLogger(__name__)

USB_STICK_SUBFOLDER = "USB Stick Programs"


def program_locations(ini):
    """The folders the file browser lists, in the order it lists them."""
    return [
        FileSystemLocation("Generated Programs", ini.conversational_gcode_dir, LocationType.GENERATED),
        FileSystemLocation("USB Stick Programs",
                           os.path.join(ini.program_prefix, USB_STICK_SUBFOLDER), LocationType.USB_STICK),
        FileSystemLocation("SyncThing Programs", os.path.expanduser("~/Sync"), LocationType.SYNCTHING),
        FileSystemLocation("Home", os.path.expanduser("~"), LocationType.HOME),
    ]


class ProgramsViewModel(QObject):
    screenIndexChanged = pyqtSignal(int)
    currentFilePathChanged = pyqtSignal(str)
    currentFileContentChanged = pyqtSignal(str)
    currentFileDisplayPathChanged = pyqtSignal(str)
    finalProfileChanged = pyqtSignal()
    executionViewChanged = pyqtSignal()
    runningStateChanged = pyqtSignal()
    programCompletedStateChanged = pyqtSignal()
    # Full-screen run view transitions
    enterRunFullScreenRequested = pyqtSignal()
    exitRunFullScreenRequested = pyqtSignal()
    switchToManualRequested = pyqtSignal()
    programLoadRequested = pyqtSignal(str)
    ensureProgramLoadedRequested = pyqtSignal()
    gremlinZoomInRequested = pyqtSignal()
    gremlinZoomOutRequested = pyqtSignal()
    gremlinClearRequested = pyqtSignal()
    gremlinFitRequested = pyqtSignal()
    headerStateChanged = pyqtSignal()
    # Edit, on a generated program: the conversational program behind it.
    editConversationalProgramRequested = pyqtSignal(str)
    previewFileChanged = pyqtSignal()
    # A program about to be loaded: drop the backplot's cached preview of it.
    previewInvalidated = pyqtSignal(str)
    previewPollRequested = pyqtSignal()

    def __init__(self, shell, navigation_store, parent=None, ini=None, use_case=None):
        super().__init__(parent)
        self._shell = shell
        self._navigation_store = navigation_store
        self._preview_file = ''
        self._pending_fit_path = ''
        ini = ini_repository() if ini is None else ini
        locations = program_locations(ini)
        self._bridge = FileSystemBridge(self)
        self._runtime_store = ProgramRuntimeStore(self)
        self._call_stack_resolver = ProgramCallStackResolver(self)
        self._actions = ProgramsActionSource(self._runtime_store, self)
        self._tool_change = ProgramsToolChangeViewModel(self)
        self._screen_index = Screen.FileSystem
        self._run_tracker = RunTimeTracker(self)
        # the program loaded's next tool, for the tool box; its planner is the
        # screen's, made at the first program read
        self._planner = None
        self._tool_changes = ToolChangesUseCase(self._background_planner, self, ini=ini)
        self._machine = ProgramsUseCase(parent=self) if use_case is None else use_case
        self._program_completed = False
        self._program_completed_name = ""
        self._was_active = False
        self._run_started = False
        self._abort_requested = False
        self._execution_frames = []
        self._active_execution_file_path = ''
        self._active_execution_title = ''
        self._active_execution_content = ''
        self._active_execution_motion_line = 0
        self._main_highlight_line = 0
        self._is_execution_context_current_program = False

        self._bridge.filePathChanged.connect(self._on_file_path_changed)
        self._bridge.fileContentChanged.connect(self._on_file_content_changed)
        self._bridge.screenChangeRequested.connect(self._set_screen_index)
        self._bridge.programLoadRequested.connect(self.programLoadRequested)
        self.programLoadRequested.connect(lambda _path: self._set_program_loaded(True))
        self.ensureProgramLoadedRequested.connect(lambda: self._set_program_loaded(True))

        self._navigation_store.currentTabChanged.connect(self._on_current_tab_changed)
        self._on_current_tab_changed()

        self._runtime_store.snapshotChanged.connect(self._on_runtime_snapshot_changed)
        self._runtime_store.machineFileChanged.connect(lambda _path: self.runningStateChanged.emit())
        self._actions.stateChanged.connect(self.runningStateChanged)
        self._actions.stateChanged.connect(self._on_running_state_changed)
        self._actions.abortTriggered.connect(self._on_abort_triggered)
        self._actions.cycleStartObserved.connect(self._on_cycle_start_observed)
        # The code views grey out the M1 stops while Break on M1 is off, and
        # the "/" blocks while Skip "/" Blocks is on.
        self._actions.optionalStopAction.checkedChanged.connect(self._bridge.setOptionalStop)
        self._bridge.setOptionalStop(self._actions.optionalStopAction.checked)
        self._actions.blockDeleteAction.checkedChanged.connect(self._bridge.setBlockDelete)
        self._bridge.setBlockDelete(self._actions.blockDeleteAction.checked)
        self._actions.optionalStopAction.checkedChanged.connect(self._tool_changes.set_optional_stop)
        self._tool_changes.set_optional_stop(self._actions.optionalStopAction.checked)
        self.programLoadRequested.connect(self._tool_changes.load)
        self._runtime_store.snapshotChanged.connect(self._tool_changes.follow)

        self._bind_program_completion_hal()
        self._sync_program_completed_from_hal()
        self._refresh_execution_view()

        self._file_system = FileSystemViewModel(
            locations, self, json_folder_path=ini.conversational_json_dir)
        self._file_system.fileSelected.connect(self._bridge.selectFileByAbsolutePath)
        self._file_system.fileOpenRequested.connect(self.openFileByAbsolutePath)
        self._file_system.selectionChanged.connect(self.headerStateChanged)
        self._file_system.navigationChanged.connect(self.headerStateChanged)
        # A failed file operation is reported the way the rest of the app
        # reports one: a toast, plus an entry in the events drawer.
        self._file_system.deleteFailed.connect(lambda msg: self._shell.showToast("Delete failed: %s" % msg))
        self._file_system.copyFailed.connect(lambda msg: self._shell.showToast("Copy failed: %s" % msg))

        # one planning worker (self._planner) for the screen's simulations, its
        # parts and its tool changes, started when the first is asked for
        self._simulate = SimulateViewModel(SimulateUseCase(self, ini=ini, planner=self._background_planner), self)
        self._simulate.run.runChanged.connect(self.headerStateChanged)
        self._simulate.run.changed.connect(self.headerStateChanged)
        self._simulate.loadingChanged.connect(self.headerStateChanged)
        self._stock = []
        self._final_profile = {"state": "none", "message": "", "rings": [], "stock": [], "summary": None}
        self._final_profile_use_case = FinalProfileUseCase(self._background_planner, self, ini=ini)
        self._final_profile_use_case.ready.connect(self._on_final_profile)
        # the machine running the program loaded, as every run is shown: the
        # DRO, the spindle / feed / tool boxes, the backplot
        from teachinlathe.ui.tabs.programs.backplot.plot_source import MachineSource
        self._run = ProgramRunViewModel(
            MachineRunSource(self._runtime_store, self._actions, self._tool_changes, self), MachineSource, self)

        self.programLoadRequested.connect(self._prepare_preview_for_load)
        self.enterRunFullScreenRequested.connect(self._shell.enterProgramRunFullScreen)
        self.exitRunFullScreenRequested.connect(self._shell.exitFullScreen)
        self.switchToManualRequested.connect(lambda: self._shell.activateTab("manual"))
        self.screenIndexChanged.connect(lambda _index: self.headerStateChanged.emit())
        self.currentFilePathChanged.connect(self._on_current_file_changed)
        self._actions.stateChanged.connect(self.headerStateChanged)
        self._runtime_store.machineFileChanged.connect(self._on_machine_file_changed)
        # callLevelChanged is deliberately not connected. It used to re-fit the
        # plot to the window, but the call level changes on every subroutine
        # call and return, and every conversational operation is a subroutine -
        # so the operator's zoom and pan were thrown away at each operation
        # boundary. Stepping into a subroutine does not change the geometry on
        # screen, so there is nothing to re-fit.
        self._set_preview_file(self.currentFilePath)
        self._request_final_profile(self.currentFilePath)
        # a program LinuxCNC has loaded already, before the application started
        if self._runtime_store.snapshot.call_level == 0:
            self._tool_changes.load(self._runtime_store.snapshot.machine_file)

    def _background_planner(self):
        if self._planner is None:
            from teachinlathe.conversational.logic.plan_worker import BackgroundPlanner
            self._planner = BackgroundPlanner(self)
        return self._planner

    @pyqtProperty(QObject, constant=True)
    def actions(self):
        return self._actions

    @pyqtProperty(QObject, constant=True)
    def toolChange(self):
        return self._tool_change

    @pyqtProperty(QObject, constant=True)
    def fileSystem(self):
        return self._file_system

    @pyqtProperty(QObject, constant=True)
    def run(self):
        """The machine running the program loaded (ProgramRunViewModel)."""
        return self._run

    @pyqtProperty(QObject, constant=True)
    def simulate(self):
        return self._simulate

    @pyqtProperty("QVariant", notify=finalProfileChanged)
    def finalProfile(self):
        """The part the file shown makes (FinalProfileView): ``state`` "none"
        (not a program), "loading", "ready" or "empty" (with ``message``, why
        not), ``rings``, [[z, r], ...] in mm - the outline of what is left of
        the stock and of its holes - ``stock``, the stock it is cut from as
        the program's header has it, the same way; [] with none - and
        ``summary``, what the program is: {operations, toolChanges, duration -
        seconds, -1 when not timed}, or None until it is read."""
        return self._final_profile

    def _request_final_profile(self, path):
        from teachinlathe.ui.tabs.programs.backplot import workpiece

        bar = workpiece.for_program(path) if path else {}
        self._stock = _rings(_stock_shape(bar)) if path and path.lower().endswith(".ngc") else []
        if path and path.lower().endswith(".ngc"):
            self._set_final_profile({"state": "loading", "message": "", "rings": []})
        self._final_profile_use_case.request(path or "", bar)

    def _on_final_profile(self, path, result):
        if path != (self.currentFilePath or ""):
            return
        if result is None:
            self._set_final_profile({"state": "none", "message": "", "rings": []})
            return
        error = result.get("error", "")
        summary = None
        if "operations" in result:
            duration = result.get("duration")
            summary = {"operations": int(result["operations"]), "toolChanges": int(result["tool_changes"]),
                       "duration": float(duration) if duration is not None else -1.0}
        material = result.get("material")
        rings = _rings(material) if material is not None else []
        if rings:
            self._set_final_profile({"state": "ready", "message": error, "rings": rings}, summary)
        else:
            why = error or ("No stock for this program" if not self._stock else "Nothing left of the stock")
            self._set_final_profile({"state": "empty", "message": why, "rings": []}, summary)

    def _set_final_profile(self, profile, summary=None):
        self._final_profile = dict(profile, stock=self._stock, summary=summary)
        self.finalProfileChanged.emit()

    @pyqtProperty(bool, notify=screenIndexChanged)
    def programShown(self):
        """The loaded program, rather than the file system."""
        return self._screen_index in (Screen.ProgramLoaded, Screen.ProgramRunning)

    @pyqtProperty(bool, notify=screenIndexChanged)
    def simulateShown(self):
        return self._screen_index in (Screen.Simulate, Screen.SimulateRunning)

    @pyqtProperty(bool, notify=screenIndexChanged)
    def running(self):
        return self._screen_index in (Screen.ProgramRunning, Screen.SimulateRunning)

    @pyqtProperty(str, notify=previewFileChanged)
    def previewFile(self):
        """The file the backplot previews."""
        return self._preview_file

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

    @pyqtProperty(bool, notify=programCompletedStateChanged)
    def programCompletedVisible(self):
        return self._program_completed

    @pyqtProperty(str, notify=programCompletedStateChanged)
    def programCompletedName(self):
        return self._program_completed_name

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
        return self._main_highlight_line

    @pyqtProperty(bool, notify=runningStateChanged)
    def executionHighlightVisible(self):
        return self._execution_highlight_visible()

    @pyqtSlot(int)
    def navigateTo(self, screen):
        self._bridge.navigateTo(screen)

    @pyqtSlot()
    def showFilesScreen(self):
        self.navigateTo(Screen.FileSystem)

    @pyqtSlot(QObject)
    def attachHighlighter(self, quick_document):
        self._bridge.attachHighlighter(quick_document)

    @pyqtSlot(str)
    def openFileByAbsolutePath(self, path: str) -> None:
        """Load a file into LinuxCNC by absolute path — called from FileSystemViewModel."""
        self._bridge.openFileByAbsolutePath(path)

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
        self._sync_program_completed_from_hal()
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
    def _bind_program_completion_hal(self):
        self._machine.programCompletedChanged.connect(self._on_program_completed_changed)
        self._machine.cycleStartPressed.connect(self._on_cycle_start_pressed)
        self._machine.programAborted.connect(self._close_completed_program_screen)

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
            self._tool_changes.start_run(self._runtime_store.snapshot)
            self._set_screen_index(Screen.ProgramRunning)
            self.enterRunFullScreenRequested.emit()
        elif self._was_active and not tracking_active:
            self._run_tracker.stop()
            self._tool_changes.stop_run()
            if self._abort_requested:
                if self._screen_index == Screen.ProgramRunning:
                    self._set_screen_index(Screen.ProgramLoaded)
                    self.exitRunFullScreenRequested.emit()
            elif self._run_started:
                name = os.path.basename(self.currentFilePath or '') or 'Program'
                self._set_program_completed_name(name)
                self._sync_program_completed_from_hal()
            elif self._screen_index == Screen.ProgramRunning:
                self._set_screen_index(Screen.ProgramLoaded)
                self.exitRunFullScreenRequested.emit()
            self._abort_requested = False
            self._run_started = False
        self._was_active = tracking_active
        self._refresh_execution_view()

    def _execution_highlight_visible(self):
        return bool(self._actions.isActive)

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
    def triggerCycleStart(self):
        if self._program_completed:
            self._run_completed_program_again()
            return
        self._actions.triggerStart()

    @pyqtSlot()
    def triggerCycleAbort(self):
        if self._program_completed:
            return
        self._actions.triggerStop()

    @pyqtSlot()
    def closeCompletedProgram(self):
        """The Program Completed dialog's Cycle Abort: close the screen, as
        the machine's abort button does once the program has completed."""
        if self._program_completed:
            self._close_completed_program_screen()

    def _on_cycle_start_pressed(self):
        if self._program_completed:
            self._run_completed_program_again()

    def _set_program_loaded(self, loaded):
        self._machine.set_program_loaded(loaded)

    def _on_current_tab_changed(self):
        self._machine.set_ready_to_run(self._navigation_store.currentTab == "programs")

    def _on_program_completed_changed(self, completed):
        if completed and not self._program_completed_name:
            self._set_program_completed_name(os.path.basename(self.currentFilePath or '') or 'Program')
        self._set_program_completed_state(completed)

    def _run_completed_program_again(self):
        self._set_program_completed_state(False)
        self._set_screen_index(Screen.ProgramRunning)
        self.ensureProgramLoadedRequested.emit()
        self._actions.triggerStart()

    def _close_completed_program_screen(self):
        self._set_program_completed_state(False)
        self._run_started = False
        self._was_active = False
        self._set_screen_index(Screen.FileSystem)
        self.exitRunFullScreenRequested.emit()
        self.switchToManualRequested.emit()

    def _sync_program_completed_from_hal(self):
        self._set_program_completed_state(self._machine.program_completed)

    def _set_program_completed_name(self, name):
        name = str(name or "Program")
        if self._program_completed_name != name:
            self._program_completed_name = name
            self.programCompletedStateChanged.emit()

    def _set_program_completed_state(self, completed):
        completed = bool(completed)
        name_changed = False
        if not completed and self._program_completed_name:
            self._program_completed_name = ""
            name_changed = True
        if self._program_completed == completed:
            if name_changed:
                self.programCompletedStateChanged.emit()
            return
        self._program_completed = completed
        self.programCompletedStateChanged.emit()

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

        main_highlight_line = 0
        if self._execution_highlight_visible() and not frames and self._is_showing_machine_file(snapshot.machine_file):
            main_highlight_line = int(snapshot.motion_line or 0)

        next_signature = (
            tuple((frame['filePath'], frame['lineNumber'], frame['lineText']) for frame in frames),
            active_path,
            active_content,
            active_motion_line,
            main_highlight_line,
            bool(is_executing_current_program),
        )
        current_signature = (
            tuple((frame['filePath'], frame['lineNumber'], frame['lineText']) for frame in self._execution_frames),
            self._active_execution_file_path,
            self._active_execution_content,
            self._active_execution_motion_line,
            self._main_highlight_line,
            bool(self._is_execution_context_current_program),
        )
        if next_signature == current_signature:
            return

        self._execution_frames = frames
        self._active_execution_file_path = active_path
        self._active_execution_title = active_title
        self._active_execution_content = active_content
        self._active_execution_motion_line = active_motion_line
        self._main_highlight_line = main_highlight_line
        self._is_execution_context_current_program = is_executing_current_program
        self.executionViewChanged.emit()

    # ── the backplot ────────────────────────────────────────────────────────

    def _set_preview_file(self, path):
        path = path or ''
        if path != self._preview_file:
            self._preview_file = path
            self.previewFileChanged.emit()

    def _on_current_file_changed(self, path):
        self._set_preview_file(path)
        self.headerStateChanged.emit()
        self._request_final_profile(path)

    def _prepare_preview_for_load(self, path):
        self._pending_fit_path = os.path.abspath(path) if path else ''
        # The preview follows this file from now on, not whatever the
        # interpreter happens to have open: while the program runs it dips
        # into subroutines, and a subroutine does not parse on its own.
        self._set_preview_file(path)
        if self._pending_fit_path:
            LOG.info('Programs: invalidating preview for %s', self._pending_fit_path)
            self.previewInvalidated.emit(self._pending_fit_path)
            QTimer.singleShot(0, self._refresh_preview_after_load)
        else:
            self.gremlinClearRequested.emit()

    def _refresh_preview_after_load(self):
        snapshot = self._runtime_store.snapshot
        if self._actions.isActive or snapshot.call_level > 0:
            LOG.info('Programs: skipped preview refresh while program is active')
            self._pending_fit_path = ''
            return
        self.previewPollRequested.emit()
        self._pending_fit_path = ''
        QTimer.singleShot(150, self.gremlinFitRequested.emit)

    def _on_machine_file_changed(self, path):
        """Fit the view when a new program reaches the machine - and only then.

        The interpreter's file also changes as it steps into subroutines, and
        re-fitting on those would move the plot under the operator mid-run.
        """
        machine_path = os.path.abspath(path) if path else ''
        if not machine_path:
            return
        program = self.currentFilePath or ''
        if program and machine_path != os.path.abspath(program):
            return
        if self._pending_fit_path and machine_path != self._pending_fit_path:
            return
        QTimer.singleShot(150, self.gremlinFitRequested.emit)
        self._pending_fit_path = ''

    # ── the app shell's header ──────────────────────────────────────────────

    def getHeaderState(self):
        left_actions = []
        right_actions = []
        title = 'Machine FileSystem'
        if self._screen_index in (Screen.Simulate, Screen.SimulateRunning):
            left_actions.append({"id": "back", "text": "← Back to FileSystem", "enabled": True})
            title = f'Simulate [{self._simulate.fileName}]'
            if self._screen_index == Screen.Simulate:
                right_actions.append({
                    "id": "cycle_start",
                    "text": "Cycle Start",
                    "enabled": bool(self._simulate.ready and not self._simulate.loading),
                    "active": False,
                })
        elif self._screen_index != Screen.FileSystem:
            left_actions.append({"id": "back", "text": "← Back to FileSystem", "enabled": True})
            title = f'Loaded Program [{os.path.basename(self.currentFilePath or "") or "No file loaded"}]'
            # Cycle Start lives up here until the program is going; from then
            # on the view is full screen and Feed Hold / Resume and Cycle
            # Abort sit under the backplot. It lights with the machine's
            # cycle-start LED, so it blinks when the machine wants it pressed.
            if not self._actions.isActive:
                right_actions.append({
                    "id": "cycle_start",
                    "text": "Cycle Start",
                    "enabled": bool(self._actions.startAction.enabled),
                    "active": bool(self._actions.cycleStartLedActive),
                })
        else:
            if self._file_system.isInGeneratedPrograms:
                left_actions.append({
                    "id": "edit_program",
                    "text": "← Back to Conversational",
                    "enabled": bool(self._file_system.canEditSelectedGeneratedProgram),
                })
            right_actions.append({
                "id": "load_program",
                "text": "Load Program",
                "leadingIcon": image_url("load_program.svg"),
                "enabled": bool(self._file_system.selectedIsFile
                                and not self._file_system.isInMountedMedia),
            })
        return {
            "title": title,
            "left_actions": left_actions,
            "right_actions": right_actions,
        }

    def triggerHeaderAction(self, action_id):
        if action_id == "back":
            if self._screen_index in (Screen.Simulate, Screen.SimulateRunning):
                self._simulate.close()
                self._set_screen_index(Screen.FileSystem)
                self.exitRunFullScreenRequested.emit()
            else:
                self.showFilesScreen()
        elif action_id == "cycle_start":
            if self._screen_index == Screen.Simulate:
                self.startSimulationRun()
            else:
                self.triggerCycleStart()
        elif action_id == "load_program":
            self._file_system.openSelectedFile()
        elif action_id == "edit_program":
            json_path = self._file_system.selectedGeneratedJsonPathForEdit()
            if json_path:
                self.editConversationalProgramRequested.emit(json_path)
        elif action_id == "toggle_optional_stop":
            self._actions.setOptionalStopEnabled(not self._actions.optionalStopAction.checked)
        elif action_id == "toggle_block_delete":
            self._actions.setBlockDeleteEnabled(not self._actions.blockDeleteAction.checked)

    @pyqtProperty(bool, notify=headerStateChanged)
    def simulateAvailable(self):
        """A G-code file is selected that can be played on the Simulate
        screen: one on the machine, not on a stick."""
        return bool(self._file_system.selectedIsFile
                    and not self._file_system.isInMountedMedia
                    and self._file_system.selectedFilePath().lower().endswith(".ngc"))

    @pyqtSlot()
    def startSimulation(self):
        """The selected file played on the Simulate screen, from the machine as
        it is now - Break on M1 as it is set."""
        path = self._file_system.selectedFilePath()
        if not path:
            return
        self._simulate.open(path, self._file_system.selectedGeneratedJsonPathForEdit(),
                           bool(self._actions.optionalStopAction.checked),
                           bool(self._actions.blockDeleteAction.checked))
        self._set_screen_index(Screen.Simulate)

    @pyqtSlot()
    def startSimulationRun(self):
        """Cycle Start from the common header: start and enter the run view."""
        if not self._simulate.ready or self._simulate.loading:
            return
        self._simulate.run.cycleStart()
        self._set_screen_index(Screen.SimulateRunning)
        self.enterRunFullScreenRequested.emit()

    @pyqtSlot()
    def abortSimulationRun(self):
        """Cycle Abort in the common run bar: stop, keeping the simulation open."""
        self._simulate.run.cycleStop()
        self._set_screen_index(Screen.Simulate)
        self.exitRunFullScreenRequested.emit()

    def showFileInGeneratedPrograms(self, ngc_path):
        """A program just generated: selected in Generated Programs."""
        self.showFilesScreen()
        self._file_system.showFileInGeneratedPrograms(os.path.abspath(ngc_path))


def _rings(material):
    """Every ring of ``material`` - a shapely (z, r) shape - as [[z, r], ...],
    its outline first and then its holes, polygon by polygon."""
    rings = []
    for polygon in getattr(material, "geoms", [material]):
        if polygon.is_empty or polygon.geom_type != "Polygon":
            continue
        for ring in [polygon.exterior] + list(polygon.interiors):
            rings.append([[float(z), float(r)] for z, r in list(ring.coords)[:-1]])
    return rings


def _stock_shape(bar):
    """The stock ``bar`` - the header's workpiece, as a dict - says, as a
    shapely (z, r) shape; an empty one with none."""
    from shapely.geometry import Polygon

    from teachinlathe.conversational.gcode.stock import header_material
    from teachinlathe.conversational.model.data_types import Workpiece

    if not bar:
        return Polygon()
    try:
        return header_material(Workpiece.from_dict(dict(bar)))
    except (KeyError, TypeError, ValueError):
        return Polygon()
