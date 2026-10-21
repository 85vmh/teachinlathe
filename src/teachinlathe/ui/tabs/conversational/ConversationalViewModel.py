"""The Conversational tab's view model.

What is on screen - the list of programs, the program open in the editor,
the operation selected in it, the profile editor that may be over it - and
the header the app shell shows for each. What is done to a program is
ConversationalUseCase's.

Which screens are open is ``screens``, bottom to top:

    programs -> program -> profileEditor
                        -> radialProfileEditor
                        -> dxfImport -> profileEditor

ConversationalTabRoot.qml keeps a StackView in step with it, binds the
screens to the properties here and connects their signals to the slots.
The selected operation's editor has a view model of its own, ``editor``
(OperationEditorViewModel.py). Nothing here holds a QML item.
"""

import logging
import os
import time

from PyQt6.QtCore import (QCoreApplication, QEventLoop, QObject, QTimer, pyqtProperty, pyqtSignal,
                          pyqtSlot)

from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase
from teachinlathe.conversational.model.data_types import Program
from teachinlathe.conversational.model.qml_adapter import build_operations_model, build_selected_program_summary
from teachinlathe.core.positions_bridge import PositionsBridge
from teachinlathe.ui.common.touchable_input.numpad_dialog_viewmodel import NumpadDialogViewModel
from teachinlathe.ui.tabs.conversational.OperationEditorViewModel import EMPTY_PREVIEW, editor_for
from teachinlathe.ui.tabs.conversational.ProgramListModel import ProgramListModel
from teachinlathe.ui.tabs.programs.filesystemview import FileSystemLocation, FileSystemViewModel, LocationType
from teachinlathe.ui.tabs.tool_library.ManualToolsViewModel import TouchedOffToolsModel

LOG = logging.getLogger(__name__)

PROGRAMS = "programs"
PROGRAM = "program"
PROFILE_EDITOR = "profileEditor"
RADIAL_PROFILE_EDITOR = "radialProfileEditor"
DXF_IMPORT = "dxfImport"
# Shown over the program, full screen but for the title bar.
EDITOR_SCREENS = (PROFILE_EDITOR, RADIAL_PROFILE_EDITOR, DXF_IMPORT)

# The generation progress dialog stays up at least this long, so it is seen.
GCODE_PROGRESS_MIN_S = 0.3


def to_py(obj):
    """Convert QJSValue / nested JS structures to Python dict/list."""
    try:
        if hasattr(obj, "toVariant"):
            obj = obj.toVariant()
    except Exception:
        pass
    if isinstance(obj, dict):
        return {k: to_py(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_py(x) for x in obj]
    return obj


class ConversationalViewModel(QObject):
    headerStateChanged = pyqtSignal()
    screensChanged = pyqtSignal()
    programChanged = pyqtSignal()
    # Its own signal, sent before programChanged: the operation list goes back
    # to the header row whenever its model changes, then to activeOpIndex - so
    # activeOpIndex has to be in place before the list is.
    activeOpIndexChanged = pyqtSignal()
    editorChanged = pyqtSignal()
    facingMirrorChanged = pyqtSignal()
    gcodeGenerationStarted = pyqtSignal()
    gcodeGenerationFinished = pyqtSignal()
    #: The header's Import DXF: the import screen imports the drawing it shows.
    importDxfRequested = pyqtSignal()
    dxfImportFailed = pyqtSignal(str)
    # A program's G-code was written, at this path: it is shown in Programs.
    gcodeGenerated = pyqtSignal(str)

    def __init__(self, shell=None, parent=None, use_case: ConversationalUseCase = None):
        super().__init__(parent)
        self.use_case = ConversationalUseCase() if use_case is None else use_case
        self._shell = shell
        self._screens = [PROGRAMS]
        self._facing_mirror = True
        self._full_screen = False
        self._editor_title = ""
        self._dxf_selected_path = ""
        self._editor = None
        # The editor before this one, kept until the next: the screen it was
        # on may still hold it while it moves to the new one.
        self._retired_editor = None
        self.current_program = None
        self.current_program_index = None
        self.current_op_index = -1

        self.model = ProgramListModel(self.use_case.load_programs())

        self._numpad_view_model = NumpadDialogViewModel(self, persist=False)
        # The machine's position, for the Teach buttons; app_window publishes it.
        self.positionsBridge = PositionsBridge(self)
        # The tools a program can change to, for the editors' tool pickers.
        self.touched_off_tools = TouchedOffToolsModel(parent=self)

        dxf_profile_folder = self.use_case.dxf_profiles_dir
        os.makedirs(dxf_profile_folder, exist_ok=True)
        self._dxf_file_system_view_model = FileSystemViewModel(
            [FileSystemLocation("DXF Profiles", dxf_profile_folder, LocationType.HOME)],
            self,
            file_extensions=(".dxf",),
            file_filter_label="DXF",
            allow_file_filter_toggle=False,
            mounted_media_exclusive=True,
            show_recursive_folder_file_counts=True,
        )
        self._dxf_file_system_view_model.selectionChanged.connect(self.headerStateChanged)

    # ── what the screens bind to ────────────────────────────────────────────

    @pyqtProperty("QStringList", notify=screensChanged)
    def screens(self):
        return list(self._screens)

    @pyqtProperty(QObject, constant=True)
    def programsModel(self):
        return self.model

    @pyqtProperty(QObject, constant=True)
    def numpadViewModel(self):
        # Conversational never persists last_value (only the manual tab does).
        return self._numpad_view_model

    @pyqtProperty(QObject, constant=True)
    def dxfFileSystemViewModel(self):
        """The DXF Profiles folder, for the import screen."""
        return self._dxf_file_system_view_model

    @pyqtProperty(str, notify=programChanged)
    def selectedProgramId(self):
        return self.current_program.id if self.current_program is not None else ""

    @pyqtProperty("QVariant", notify=programChanged)
    def selectedProgram(self):
        if self.current_program is None:
            return None
        return build_selected_program_summary(self.current_program)

    @pyqtProperty("QVariantList", notify=programChanged)
    def operationsModel(self):
        if self.current_program is None:
            return []
        return build_operations_model(self.current_program)

    @pyqtProperty(int, notify=activeOpIndexChanged)
    def activeOpIndex(self):
        return self.current_op_index

    @pyqtProperty(QObject, notify=editorChanged)
    def editor(self):
        """The selected operation's editor (or the header's), or None."""
        return self._editor

    # Facing's canvas mirrored or not: on whenever a program is opened, then as
    # the operator leaves it for every Facing of that program.
    def _get_facing_mirror(self):
        return self._facing_mirror

    def _set_facing_mirror(self, on):
        on = bool(on)
        if on != self._facing_mirror:
            self._facing_mirror = on
            self.facingMirrorChanged.emit()

    facingMirror = pyqtProperty(bool, _get_facing_mirror, _set_facing_mirror, notify=facingMirrorChanged)

    # ── the screen stack ────────────────────────────────────────────────────

    @property
    def _top(self):
        return self._screens[-1]

    def _set_screens(self, screens):
        self._screens = list(screens)
        self.screensChanged.emit()
        if self._top != DXF_IMPORT:
            self._dxf_selected_path = ""
        full_screen = self._top in EDITOR_SCREENS
        if full_screen != self._full_screen and self._shell is not None:
            if full_screen:
                self._shell.enterContentFullScreen()
            else:
                self._shell.exitFullScreen()
        self._full_screen = full_screen
        if self._top == PROGRAM:
            # The program may have changed under the editor that was over it.
            self._program_changed()
            QTimer.singleShot(0, lambda: self.showDetails(self.current_op_index))
        self.headerStateChanged.emit()

    def _push(self, screen):
        self._set_screens(self._screens + [screen])

    def _pop_to(self, screen):
        self._set_screens(self._screens[:self._screens.index(screen) + 1])

    @pyqtSlot()
    def back(self):
        if len(self._screens) > 1:
            self._set_screens(self._screens[:-1])

    def _done(self):
        # A profile read from a drawing goes back past the import screen.
        if self._top == PROFILE_EDITOR and DXF_IMPORT in self._screens:
            self._pop_to(PROGRAM)
        else:
            self.back()

    # ── the app shell's header ──────────────────────────────────────────────

    def getHeaderState(self):
        left_actions = []
        right_actions = []
        if self._top in EDITOR_SCREENS:
            title = "Import DXF Profile" if self._top == DXF_IMPORT else self._editor_title
            left_actions.append({"id": "back", "text": "← Back", "enabled": True})
            if self._top == DXF_IMPORT:
                right_actions.append({"id": "import_dxf", "text": "Import DXF",
                                      "enabled": bool(self._dxf_selected_path)})
            else:
                right_actions.append({"id": "done", "text": "Done", "enabled": True})
        elif self._top == PROGRAM:
            program_name = self.current_program.header.name if self.current_program is not None else ""
            title = f"Editing: {program_name}" if program_name else "Creating New Program"
            left_actions.append({"id": "back", "text": "← Back to Programs", "enabled": True})
            operations = self.current_program.operations if self.current_program is not None else []
            right_actions.append({"id": "build_gcode", "text": "Generate GCode", "enabled": bool(operations)})
        else:
            title = "Conversational Programs"
            right_actions.append({"id": "create_new", "text": "Create New", "enabled": True})

        return {
            "title": title,
            "left_actions": left_actions,
            "right_actions": right_actions,
        }

    def triggerHeaderAction(self, action_id):
        if action_id == "back":
            self.back()
        elif action_id == "done":
            self._done()
        elif action_id == "import_dxf":
            self.importDxfRequested.emit()
        elif action_id == "create_new":
            self.addNewProgram()
        elif action_id == "build_gcode":
            self.generateGcode()

    @pyqtSlot(str)
    def setDxfSelectedPath(self, path):
        self._dxf_selected_path = str(path or "")
        self.headerStateChanged.emit()

    # ── the program list ────────────────────────────────────────────────────

    @pyqtSlot()
    def addNewProgram(self):
        try:
            program = self.use_case.create_program()
        except Exception as e:
            LOG.error("failed to create a program: %s", e)
            return
        self._open_program(program, self.model.appendProgram(program))

    @pyqtSlot("QVariant")
    def openProgram(self, arg):
        """A program in the list, by its row (or the Program itself)."""
        arg = to_py(arg)
        if isinstance(arg, float) and arg.is_integer():
            arg = int(arg)
        if isinstance(arg, int):
            program, row_index = self.model.get(arg), arg
        elif isinstance(arg, Program):
            program = arg
            row_index = self.model._programs.index(arg) if arg in self.model._programs else None
        else:
            program, row_index = None, None
        if program is None:
            LOG.error("openProgram: program not resolved from %r", arg)
            return
        self._open_program(program, row_index)

    def openProgramFile(self, json_path: str):
        """Edit, from the Programs tab: the program behind a generated file."""
        json_path = os.path.abspath(json_path or "")
        if not json_path or not os.path.isfile(json_path):
            LOG.error("openProgramFile: missing JSON %s", json_path)
            return
        try:
            program = self.use_case.load_program_file(json_path)
        except Exception as e:
            LOG.error("openProgramFile: failed to load %s: %s", json_path, e)
            return

        row_index = self.model.indexOfFilename(json_path)
        if row_index >= 0:
            self.model.setProgramAt(row_index, program)
        else:
            row_index = self.model.appendProgram(program)
        self._open_program(program, row_index if row_index >= 0 else None)

    def _open_program(self, program, row_index):
        self.current_program = program
        self.current_program_index = row_index
        self.current_op_index = self.use_case.last_operation_index(program)
        self._set_facing_mirror(True)
        LOG.info("opening %s, %d operations", program.header.name, len(program.operations))
        # A fresh editor, whatever was open before.
        if self._screens != [PROGRAMS]:
            self._set_screens([PROGRAMS])
        self._push(PROGRAM)

    @pyqtSlot(int)
    def deleteProgram(self, row_index):
        program = self.model.get(row_index)
        if not program:
            return
        try:
            self.use_case.delete_program(program)
        except Exception as e:
            LOG.error("failed to delete the program file: %s", e)
            return

        self.model.removeProgramAt(row_index)
        if self.current_program_index == row_index:
            self.current_program = None
            self.current_program_index = None
            self.current_op_index = -1
            self._set_editor(None)
        elif self.current_program_index is not None and row_index < self.current_program_index:
            self.current_program_index -= 1

    @pyqtSlot(int)
    def duplicateProgram(self, row_index):
        program = self.model.get(row_index)
        if not program:
            return
        existing_names = {candidate.header.name for candidate in self.model._programs}
        try:
            new_program = self.use_case.duplicate_program(program, existing_names)
        except Exception as e:
            LOG.error("failed to duplicate the program: %s", e)
            return
        self.model.appendProgram(new_program)

    # ── the program open in the editor ──────────────────────────────────────

    def _save_current_program(self):
        prog = self.current_program
        if not prog:
            return
        try:
            filename = self.use_case.save(prog)
            LOG.debug("program written to %s", filename)
        except Exception as e:
            LOG.error("failed to save the program: %s", e)
            return

        if self.current_program_index is not None:
            self.model.setProgramAt(self.current_program_index, prog)
        self._program_changed()
        self.headerStateChanged.emit()

    def _program_changed(self):
        self.activeOpIndexChanged.emit()
        self.programChanged.emit()

    @pyqtSlot(int)
    def showDetails(self, index):
        """The operation list selected the header (-1) or an operation."""
        # The list stays under a profile editor and, as its model changes
        # with every save, selects the header and back: not a selection.
        if self._top in EDITOR_SCREENS:
            return
        self.current_op_index = index
        self._set_editor(index)

    def _set_editor(self, index):
        operation = None
        if self.current_program is not None and index is not None:
            operation = self.use_case.details_payload(self.current_program, index)
        editor = editor_for(self, self.current_program, index, operation, self) if operation else None
        if self._retired_editor is not None:
            self._retired_editor.deleteLater()
        self._retired_editor, self._editor = self._editor, editor
        self.editorChanged.emit()

    @pyqtSlot()
    def generateGcode(self):
        prog = self.current_program
        if not prog:
            LOG.warning("generate G-code: no program open")
            return
        self.use_case.remember_last_operation(prog, self.current_op_index)
        self.gcodeGenerationStarted.emit()
        QCoreApplication.processEvents()

        start = time.monotonic()
        path = None
        try:
            path = self.use_case.generate_gcode(prog)
            LOG.info("G-code generated: %s", path)
        except Exception as e:
            LOG.error("G-code generation failed: %s", e)
        finally:
            elapsed = time.monotonic() - start
            if elapsed < GCODE_PROGRESS_MIN_S:
                loop = QEventLoop()
                QTimer.singleShot(int((GCODE_PROGRESS_MIN_S - elapsed) * 1000), loop.quit)
                loop.exec()
            self.gcodeGenerationFinished.emit()

        if path:
            self.gcodeGenerated.emit(path)

    @pyqtSlot(int, bool)
    def setGenerateGcode(self, index, checked):
        if self.use_case.set_generate_gcode(self.current_program, index, checked):
            self.current_op_index = index
            self._save_current_program()

    @pyqtSlot(int, bool)
    def setOptionalBlock(self, index, checked):
        if self.use_case.set_optional_block(self.current_program, index, checked):
            self.current_op_index = index
            self._save_current_program()

    @pyqtSlot(str, int)
    def addOperation(self, op_type, insert_index):
        prog = self.current_program
        if not prog:
            return
        if not self.use_case.is_operation_type(op_type):
            LOG.error("unknown operation type %r", op_type)
            return
        try:
            idx = self.use_case.insert_operation(prog, op_type, insert_index)
        except Exception as e:
            LOG.error("failed to add %r: %s", op_type, e)
            return
        self.current_op_index = idx
        self._save_current_program()
        # The profiles are drawn as soon as they are added.
        open_editor = {
            "defineProfile": self.open_profile_editor,
            "importDxfProfile": self._open_dxf_import,
            "defineRadialProfile": self.open_radial_profile_editor,
        }.get(op_type)
        if open_editor is not None:
            QTimer.singleShot(0, lambda: open_editor(idx))

    @pyqtSlot(int, int)
    def moveOperation(self, from_index, to_index):
        """Dragged from one place to another; the selection stays on the operation it was on."""
        prog = self.current_program
        if not prog or not self.use_case.move_operation(prog, from_index, to_index):
            return
        current = self.current_op_index
        if current == from_index:
            self.current_op_index = to_index
        elif from_index < current <= to_index:
            self.current_op_index = current - 1
        elif to_index <= current < from_index:
            self.current_op_index = current + 1
        self._save_current_program()

    @pyqtSlot(int)
    def deleteOperation(self, index):
        prog = self.current_program
        if not prog or not self.use_case.delete_operation(prog, index):
            return
        # the one above it, or the header for the first
        self.current_op_index = index - 1
        self._save_current_program()

    @pyqtSlot(int)
    def duplicateOperation(self, index):
        """A copy of the operation, right after it; the selection stays where it was."""
        prog = self.current_program
        if not prog:
            return
        try:
            new_index = self.use_case.duplicate_operation(prog, index)
        except IndexError as e:
            LOG.error("duplicate operation failed: %s", e)
            return
        if self.current_op_index >= new_index:
            self.current_op_index += 1
        self._save_current_program()

    # ── what the operation editors ask of the tab ───────────────────────────

    def update_operation(self, op_type, index, payload):
        """An operation's editor changed a value: autosave."""
        if self.current_program is None:
            return
        try:
            updated = self.use_case.update_operation(self.current_program, op_type, index, to_py(payload) or {})
        except Exception as e:
            LOG.error("%s update failed: %s", op_type, e)
            return
        if updated:
            self._save_current_program()

    def update_header(self, payload):
        if self.current_program is None:
            return
        try:
            self.use_case.update_header(self.current_program, to_py(payload) or {})
        except Exception as e:
            LOG.error("header update failed: %s", e)
            return
        self._save_current_program()

    def use_tool_before(self, op_index, tool_no, toolchange_position):
        if self.current_program is None:
            return
        new_index = self.use_case.use_tool_before(self.current_program, op_index, tool_no, toolchange_position)
        if new_index is None:
            return
        self.current_op_index = new_index
        self._save_current_program()
        # The operation moved down, under its new Change Tool: a new editor.
        QTimer.singleShot(0, lambda: self.showDetails(new_index))

    def add_profiling_finish(self, index):
        prog = self.current_program
        if not prog:
            return
        try:
            self.current_op_index = self.use_case.add_profiling_finish(prog, index)
        except Exception as e:
            LOG.error("add profiling finish failed: %s", e)
            return
        self._save_current_program()

    @staticmethod
    def preview(build, op_data):
        """A cut preview from an editor's draft, or an empty one with the error."""
        try:
            return build(to_py(op_data) or {})
        except Exception as e:
            LOG.error("preview failed: %s", e)
            return dict(EMPTY_PREVIEW, error=str(e))

    # ── the profile editors ─────────────────────────────────────────────────

    def _open_editor(self, op_index, screen, title=""):
        self.current_op_index = int(op_index)
        # The operation as it is now, for the screen about to show it.
        self._set_editor(self.current_op_index)
        self._editor_title = title
        self._push(screen)

    def open_profile_editor(self, op_index):
        op_data = self.use_case.operation_payload(self.current_program, op_index)
        type_str = "ID" if str(op_data.get("profile_type", "od")).lower() == "id" else "OD"
        op_order = op_data.get("order", "")
        self._open_editor(op_index, PROFILE_EDITOR,
                          f"Define {type_str} Profile Op #{op_order}" if op_order else f"Define {type_str} Profile")

    def open_radial_profile_editor(self, op_index):
        op_order = self.use_case.operation_payload(self.current_program, op_index).get("order", "")
        self._open_editor(op_index, RADIAL_PROFILE_EDITOR,
                          f"Define Radial Profile Op #{op_order}" if op_order else "Define Radial Profile")

    def _open_dxf_import(self, op_index):
        self._open_editor(op_index, DXF_IMPORT)

    def import_dxf_profile(self, op_index, dxf_file_path):
        """The drawing chosen on the import screen: read into the profile,
        then shown in the profile editor."""
        if self.current_program is None:
            return
        try:
            if not self.use_case.import_dxf_profile(self.current_program, op_index, dxf_file_path):
                return
        except Exception as e:
            LOG.error("DXF import failed: %s", e)
            self.dxfImportFailed.emit(str(e))
            return
        self.current_op_index = op_index
        self._save_current_program()
        self.open_profile_editor(op_index)
