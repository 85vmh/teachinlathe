import json
import os
import re
import time
from datetime import datetime

from PyQt5.QtCore import QUrl, QObject, QMetaObject, Qt, QTimer, QEventLoop, pyqtSignal
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtWidgets import QProgressDialog, QApplication

from teachinlathe.conversational.data_types import Header, Program, Workpiece, operation_types
from teachinlathe.conversational.program_commands import (
    add_profiling_finish,
    create_new_program,
    delete_operation,
    delete_program_file,
    duplicate_operation,
    duplicate_program,
    insert_default_operation,
    move_operation_down,
    move_operation_up,
)
from teachinlathe.conversational.program_store import resolve_save_path, save_program_to_disk
from teachinlathe.conversational.qml_adapter import build_details_payload, build_operations_model, build_selected_program_summary
from teachinlathe.conversational.updaters import (
    apply_cutting_update,
    apply_define_profile_update,
    apply_drilling_update,
    apply_edge_break_update,
    apply_geometry_update,
    apply_knurling_cutting_update,
    apply_m1_update,
    apply_operation_update,
    apply_parting_update,
    apply_profiling_options_update,
    apply_profiling_parameters_update,
    apply_predefined_position_update,
    apply_position_details_update,
    apply_roughing_strategy_update,
    apply_tapping_update,
    apply_threading_update,
    apply_turnable_operation_update,
)
from teachinlathe.widgets.conversational_qml.ProgramListModel import ProgramListModel
from teachinlathe.widgets.conversational_qml.program_loader import load_programs_from_folder
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog


class ConversationalQml(QQuickWidget):
    headerStateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.folder_path = "/home/cnc/Work/teachinlathe/conversational"
        self.current_program = None
        self.current_program_index = None
        self.current_op_index = -1
        self.child_screen_item = None
        self._app_state = None

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        programs = load_programs_from_folder(self.folder_path)

        self.model = ProgramListModel(programs)
        self.engine().rootContext().setContextProperty("programsModel", self.model)

        root_path = os.path.join(self.base_dir, "Root.qml")
        self.statusChanged.connect(self.onStatusChanged)
        self.setSource(QUrl.fromLocalFile(root_path))

    def setAppState(self, app_state):
        self._app_state = app_state
        try:
            self.engine().rootContext().setContextProperty("appState", app_state)
            self.engine().rootContext().setContextProperty("cncStore", getattr(app_state, "cncStore", None))
            self.engine().rootContext().setContextProperty("navigationStore", getattr(app_state, "navigationStore", None))
        except Exception as e:
            print("setAppState failed:", e)

    def onStatusChanged(self, status):
        if status == QQuickWidget.Ready:
            self.root = self.rootObject()
            if not self.root:
                print("Failed to load Root.qml")
                return

            print("----Model count:", self.model.rowCount())

            main_url = QUrl.fromLocalFile(os.path.join(self.base_dir, "MainScreen.qml")).toString()
            self.root.loadScreen(main_url, {"programsModel": self.model, "showBack": False, "selectedProgramId": ""})

            loader = self.root.findChild(QQuickItem, "loader") or self.root.findChild(QObject, "loader")
            if loader is None:
                print("Failed to find Loader object with objectName 'loader'")
                return

            try:
                loader.itemChanged.connect(self.onLoaderItemChanged)
            except Exception as e:
                print("Failed to connect itemChanged:", e)

            current_item = loader.property("item")
            if current_item:
                self._hook_screen_item(current_item)
            QTimer.singleShot(0, self._emit_header_state_changed)

    def onLoaderItemChanged(self):
        sender = self.sender()
        if not sender:
            return
        item = sender.property("item")
        if item:
            self._hook_screen_item(item)
        self._emit_header_state_changed()

    def _current_loader_item(self):
        if not hasattr(self, "root") or self.root is None:
            return None
        loader = self.root.findChild(QQuickItem, "loader") or self.root.findChild(QObject, "loader")
        if loader is None:
            return None
        return loader.property("item")

    def _emit_header_state_changed(self):
        self.headerStateChanged.emit()

    def getHeaderState(self):
        title = "Conversational"
        left_actions = []
        right_actions = []
        item = self._current_loader_item()
        object_name = None
        if item is not None:
            try:
                object_name = item.property("objectName")
            except Exception:
                object_name = None

        if object_name == "childScreen":
            program_name = ""
            try:
                program_name = getattr(getattr(self.current_program, "header", None), "name", "") or ""
            except Exception:
                program_name = ""
            title = f"Editing: {program_name}" if program_name else "Creating New Program"
            can_go_back = False
            try:
                can_go_back = bool(self.root.canGoBack())
            except Exception:
                can_go_back = False
            if can_go_back:
                left_actions.append({"id": "back", "text": "Back to Programs", "enabled": True})
            operations = getattr(self.current_program, "operations", []) or []
            right_actions.append({"id": "build_gcode", "text": "Build GCode Program", "enabled": bool(operations)})
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
            self.goBack()
        elif action_id == "create_new":
            self.addNewProgram()
        elif action_id == "build_gcode":
            self.onGenerateGcodeRequested()

    def _to_py(self, obj):
        """Convert QJSValue / nested JS structures to Python dict/list."""
        try:
            if hasattr(obj, 'toVariant'):
                obj = obj.toVariant()
        except Exception:
            pass
        if isinstance(obj, dict):
            return {k: self._to_py(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._to_py(x) for x in obj]
        return obj

    def _get_current_program(self):
        # make sure you set self.current_program when you open ChildScreen
        return getattr(self, "current_program", None)

    # ADD this helper in class ConversationalQml
    def _save_current_program(self):
        prog = self._get_current_program()
        if not prog:
            return

        try:
            if hasattr(prog, "header") and hasattr(prog.header, "created_date") and not prog.header.created_date:
                prog.header.created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(prog, "header") and hasattr(prog.header, "last_edit"):
                prog.header.last_edit = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        data = prog.to_dict() if hasattr(prog, "to_dict") else None
        if not data:
            print("Program serialization missing (to_dict).")
            return

        try:
            filename = save_program_to_disk(prog, self.folder_path)
            print(f"[autosave] Program written to: {filename}")
        except Exception as e:
            print("Failed to save program:", e)
            return

        row = getattr(self, "current_program_index", None)
        if row is not None and hasattr(self.model, "setProgramAt"):
            self.model.setProgramAt(row, prog)
            top = self.model.index(row)
            bottom = self.model.index(row)
            from teachinlathe.widgets.conversational_qml.ProgramListModel import ProgramListModel as _PLM
            self.model.dataChanged.emit(top, bottom, [_PLM.LastEditDateRole])

        self.current_program = prog

        if getattr(self, "child_screen_item", None) is not None:
            new_ops = build_operations_model(self.current_program)
            self.child_screen_item.setProperty("activeOpIndex", getattr(self, "current_op_index", -1))
            self.child_screen_item.setProperty("operationsModel", new_ops)

        self._emit_header_state_changed()

    def _hook_screen_item(self, item):
        try:
            obj_name = item.property("objectName")
        except Exception:
            obj_name = None
        if obj_name == "childScreen":
            self.child_screen_item = item

        try:
            if hasattr(item, "addNewProgramRequested"):
                item.addNewProgramRequested.connect(self.addNewProgram)
            if hasattr(item, "editProgramRequested"):
                item.editProgramRequested.connect(self.openChildScreen)
            if hasattr(item, "deleteProgramRequested"):
                item.deleteProgramRequested.connect(self.onDeleteProgramRequested)
            if hasattr(item, "duplicateProgramRequested"):
                item.duplicateProgramRequested.connect(self.onDuplicateProgramRequested)
            if hasattr(item, "backRequested"):
                item.backRequested.connect(self.goBack)
            if hasattr(item, "toggleGenerateGcode"):
                item.toggleGenerateGcode.connect(self.onToggleGenerateGcode)
            if hasattr(item, "toggleOptionalBlock"):
                item.toggleOptionalBlock.connect(self.onToggleOptionalBlock)
            if hasattr(item, "detailsRequested"):
                item.detailsRequested.connect(lambda idx, it=item: self.onDetailsRequested(it, idx))
            if hasattr(item, "updateToolChange"):
                item.updateToolChange.connect(self.onUpdateToolChange)
            if hasattr(item, "updatePositionAt"):
                item.updatePositionAt.connect(self.onUpdatePositionAt)
            if hasattr(item, "updateDefineProfile"):
                item.updateDefineProfile.connect(self.onUpdateDefineProfile)
            if hasattr(item, "teachXRequested"):
                item.teachXRequested.connect(self.onTeachX)
            if hasattr(item, "teachZRequested"):
                item.teachZRequested.connect(self.onTeachZ)
            if hasattr(item, "updateFacing"):
                item.updateFacing.connect(self.onUpdateFacing)
            if hasattr(item, "updateKnurling"):
                item.updateKnurling.connect(self.onUpdateKnurling)
            if hasattr(item, "updateProfiling"):
                item.updateProfiling.connect(self.onUpdateProfiling)
            if hasattr(item, "updateCustomProfiling"):
                item.updateCustomProfiling.connect(self.onUpdateCustomProfiling)
            if hasattr(item, "updateProfileBoring"):
                item.updateProfileBoring.connect(self.onUpdateProfileBoring)
            if hasattr(item, "updateDrilling"):
                item.updateDrilling.connect(self.onUpdateDrilling)
            if hasattr(item, "updateThreading"):
                item.updateThreading.connect(self.onUpdateThreading)
            if hasattr(item, "updateParting"):
                item.updateParting.connect(self.onUpdateParting)
            if hasattr(item, "updateTapping"):
                item.updateTapping.connect(self.onUpdateTapping)
            if hasattr(item, "openNumPadRequested"):
                item.openNumPadRequested.connect(self.onOpenNumPadRequested)
            if hasattr(item, "generateGcodeRequested"):
                item.generateGcodeRequested.connect(self.onGenerateGcodeRequested)
            if hasattr(item, "updateHeader"):
                item.updateHeader.connect(self.onUpdateHeader)
            if hasattr(item, "addOperationRequested"):
                item.addOperationRequested.connect(self.onAddOperationRequested)
            if hasattr(item, "addProfilingFinishRequested"):
                item.addProfilingFinishRequested.connect(self.onAddProfilingFinishRequested)
            if hasattr(item, "reorderModeToggled"):
                item.reorderModeToggled.connect(self.onReorderModeToggled)
            if hasattr(item, "moveUpRequested"):
                item.moveUpRequested.connect(self.onMoveUp)
            if hasattr(item, "moveDownRequested"):
                item.moveDownRequested.connect(self.onMoveDown)
            if hasattr(item, "deleteOperationRequested"):
                item.deleteOperationRequested.connect(self.onDeleteOperation)
            if hasattr(item, "addOperationTypeChosen"):
                item.addOperationTypeChosen.connect(self.onAddOperationTypeChosen)
            print("Screen signals connected.")
            if obj_name == "childScreen" and self.current_op_index == -1:
                QTimer.singleShot(0, lambda: self.onDetailsRequested(item, -1))
        except Exception as e:
            print("Failed to hook screen item signals:", e)

    def onGenerateGcodeRequested(self):
        """Called from ChildScreen when user clicks 'Generate GCode' on the top bar."""
        prog = getattr(self, "current_program", None)
        if not prog:
            print("[gcode] No current program selected.")
            return
        progress = QProgressDialog("Generating G-Code...", None, 0, 0, self)
        progress.setWindowTitle("Generate G-Code")
        progress.setWindowModality(Qt.ApplicationModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.show()
        QApplication.processEvents()

        start = time.monotonic()
        path = None
        try:
            path = self.generate_gcode_for_program(prog)
            print(f"[gcode] Generated: {path}")
        except Exception as e:
            print("[gcode] Generation failed:", e)
        finally:
            elapsed = time.monotonic() - start
            if elapsed < 1.0:
                loop = QEventLoop()
                QTimer.singleShot(int((1.0 - elapsed) * 1000), loop.quit)
                loop.exec_()
            progress.close()

        if path:
            try:
                mw = self.window()
                if mw and hasattr(mw, "showGeneratedProgram"):
                    mw.showGeneratedProgram(path)
            except Exception as e:
                print("[gcode] showGeneratedProgram failed:", e)

    def generate_gcode_for_program(self, program):
        from .gcode_builder import build_ngc_from_program
        from teachinlathe import mainwindow as mw

        base_dir = getattr(mw, "CONVERSATIONAL_OUTPUT_BASE", None) \
            or getattr(mw, "CONVERSATIONAL_GCODE_BASE", None) \
            or getattr(self, "folder_path", os.getcwd())
        json_dir = os.path.join(base_dir, "Conversational Json")
        gcode_dir = os.path.join(base_dir, "Conversational Gcode")
        base_name = getattr(getattr(program, "header", None), "name", getattr(program, "id", "program"))
        base_name = "".join(c for c in str(base_name) if c.isalnum() or c in ("-", "_", " ")).strip()
        base_name = base_name.replace(" ", "_")
        json_path = os.path.join(json_dir, base_name + ".json")

        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as handle:
            handle.write(program.to_json())

        return build_ngc_from_program(program, output_dir=gcode_dir)

    def onDetailsRequested(self, screen_item, index: int):
        self.current_op_index = index
        if index == -1:
            prog = self._get_current_program()
            if not prog:
                return
            try:
                data = build_details_payload(prog)
                if data:
                    screen_item.receiveDetailsData(-1, data)
            except Exception as e:
                print("receiveDetailsData(header) failed:", e)
            return

        op = self._get_current_op(index)
        if op is None:
            return
        data = build_details_payload(op)
        if not data:
            return
        try:
            screen_item.receiveDetailsData(index, data)
        except Exception as e:
            print("receiveDetailsData failed:", e)

    def addNewProgram(self):
        try:
            program = create_new_program(self.folder_path)
            save_program_to_disk(program, self.folder_path)
        except Exception as e:
            print("Failed to create program:", e)
            return

        row_index = self.model.appendProgram(program) if hasattr(self.model, "appendProgram") else None
        self.current_op_index = -1
        self.openChildScreen(row_index if row_index is not None else program)

    def onDeleteProgramRequested(self, row_index: int):
        if row_index is None or row_index < 0:
            return
        program = self.model.get(row_index) if hasattr(self.model, "get") else None
        if not program:
            return

        try:
            delete_program_file(program)
        except Exception as e:
            print("Failed to delete program file:", e)
            return

        if hasattr(self.model, "removeProgramAt"):
            self.model.removeProgramAt(row_index)

        if self.current_program_index == row_index:
            self.current_program = None
            self.current_program_index = None
            self.current_op_index = -1
        elif self.current_program_index is not None and row_index < self.current_program_index:
            self.current_program_index -= 1

    def onDuplicateProgramRequested(self, row_index: int):
        program = self.model.get(row_index) if hasattr(self.model, "get") else None
        if not program:
            return

        existing_names = set()
        if hasattr(self.model, "_programs"):
            existing_names = {
                getattr(getattr(candidate, "header", None), "name", "")
                for candidate in self.model._programs
            }

        try:
            new_program = duplicate_program(program, self.folder_path, existing_names)
            save_program_to_disk(new_program, self.folder_path)
        except Exception as e:
            print("Failed to duplicate program:", e)
            return

        if hasattr(self.model, "appendProgram"):
            self.model.appendProgram(new_program)

    def onAddOperationTypeChosen(self, op_type: str, insert_index: int):
        print(f"[operations] Adding {op_type!r} at index {insert_index}")
        prog = self._get_current_program()
        if not prog:
            return
        try:
            if op_type == "__duplicate__":
                idx = duplicate_operation(prog, self.current_op_index, insert_index)
            else:
                if op_type not in operation_types:
                    print(f"[operations] Unknown type: {op_type!r}")
                    return
                idx = insert_default_operation(prog, op_type, insert_index)
            self.current_op_index = idx
            self._save_current_program()
        except Exception as e:
            print(f"[operations] Failed to create {op_type!r}: {e}")

    def onAddOperationRequested(self):
        print("[operations] Add New requested")

    def onReorderModeToggled(self, on):
        print(f"[operations] Reorder mode: {'ON' if on else 'OFF'}")

    def onMoveUp(self, index: int):
        prog = self._get_current_program()
        if not prog:
            return
        new_index = move_operation_up(prog, index)
        if new_index is None:
            return
        self.current_op_index = new_index
        self._save_current_program()

    def onMoveDown(self, index: int):
        prog = self._get_current_program()
        if not prog:
            return
        new_index = move_operation_down(prog, index)
        if new_index is None:
            return
        self.current_op_index = new_index
        self._save_current_program()

    def onDeleteOperation(self, index: int):
        prog = self._get_current_program()
        if not prog or not delete_operation(prog, index):
            return
        self.current_op_index = -1
        self._save_current_program()

    def onAddProfilingFinishRequested(self, index: int):
        prog = self._get_current_program()
        if not prog:
            return
        try:
            insert_idx = add_profiling_finish(prog, index)
            self.current_op_index = insert_idx
            self._save_current_program()
        except Exception as e:
            print("[profiling] add finish failed:", e)

    def openChildScreen(self, arg=None):
        program = None
        row_index = None
        if hasattr(arg, "toVariant"):
            try:
                arg = arg.toVariant()
            except Exception:
                pass
        if isinstance(arg, float) and arg.is_integer():
            arg = int(arg)
        if isinstance(arg, int):
            row_index = arg
            if hasattr(self.model, "get"):
                program = self.model.get(arg)
            elif hasattr(self.model, "program_at"):
                program = self.model.program_at(arg)
            elif hasattr(self.model, "programAt"):
                program = self.model.programAt(arg)
        elif isinstance(arg, Program):
            program = arg
            if hasattr(self.model, "_programs"):
                try:
                    row_index = self.model._programs.index(arg)
                except ValueError:
                    row_index = None
        if program is None:
            print("openChildScreen: program not resolved from", arg)
            return

        self.current_program = program
        self.current_program_index = row_index
        self.current_op_index = -1

        selected_program = build_selected_program_summary(program)
        operations_model = build_operations_model(program)

        try:
            if hasattr(self, "root") and hasattr(self.root, "_currentParams") and isinstance(self.root._currentParams, dict):
                self.root._currentParams["selectedProgramId"] = program.id
        except Exception:
            pass

        child_url = QUrl.fromLocalFile(os.path.join(self.base_dir, "ChildScreen.qml")).toString()
        params = {
            "showBack": True,
            "selectedProgram": selected_program,
            "operationsModel": operations_model,
        }
        print("openChildScreen for:", selected_program["name"], "ops:", len(operations_model))
        self.root.loadScreen(child_url, params)
        QTimer.singleShot(0, self._emit_header_state_changed)

    def onToggleGenerateGcode(self, index: int, checked: bool):
        op = self._get_current_op(index)
        if not op:
            return
        try:
            setattr(op, "generate_gcode", bool(checked))
        except Exception:
            pass
        self.current_op_index = index
        self._save_current_program()

    def onToggleOptionalBlock(self, index: int, checked: bool):
        op = self._get_current_op(index)
        if not op:
            return
        try:
            setattr(op, "is_optional_block", bool(checked))
        except Exception:
            pass
        self.current_op_index = index
        self._save_current_program()

    # def _get_current_op(self, index):
    #     prog = self._get_current_program()
    #     if not prog or not hasattr(prog, "operations"):
    #         return None
    #     if index < 0 or index >= len(prog.operations):
    #         return None
    #     return prog.operations[index]

    def _get_current_op(self, index):
        if self.current_program is None:
            return None
        ops = getattr(self.current_program, "operations", [])
        if not (0 <= index < len(ops)):
            return None
        return ops[index]

    def onUpdateHeader(self, payload):
        try:
            p = self._to_py(payload) or {}
            hdr = p.get("header", p)

            prog = self._get_current_program()
            if not prog or not hasattr(prog, "header") or prog.header is None:
                return

            header = prog.header

            if "name" in hdr:
                header.name = str(hdr["name"])
            if "created_date" in hdr and hdr["created_date"] is not None:
                header.created_date = str(hdr["created_date"])
            if "units" in hdr:
                header.units = str(hdr["units"])
            if "datum" in hdr:
                try:
                    header.datum = int(hdr["datum"])
                except Exception:
                    pass
            if "last_edit" in hdr and hdr["last_edit"] is not None:
                header.last_edit = str(hdr["last_edit"])

            wp_payload = hdr.get("workpiece")
            if isinstance(wp_payload, dict):
                wp = header.workpiece
                if wp is None:
                    wp = Workpiece(material="", external_diameter=0.0,
                                   internal_diameter=0.0, stickout_length=0.0)
                if "material" in wp_payload:
                    wp.material = str(wp_payload["material"])
                if "external_diameter" in wp_payload:
                    try:
                        wp.external_diameter = float(wp_payload["external_diameter"])
                    except Exception:
                        pass
                if "internal_diameter" in wp_payload:
                    try:
                        wp.internal_diameter = float(wp_payload["internal_diameter"])
                    except Exception:
                        pass
                if "stickout_length" in wp_payload:
                    try:
                        wp.stickout_length = float(wp_payload["stickout_length"])
                    except Exception:
                        pass
                header.workpiece = wp

            self._save_current_program()
            self._emit_header_state_changed()

        except Exception as e:
            print("[header] update error:", e)

    def onUpdateDefineProfile(self, index: int, payload):
        """Define Profile autosave."""
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import DefineProfile
            if not isinstance(op, DefineProfile):
                return
            apply_define_profile_update(op, p)
            self._save_current_program()
        except Exception as e:
            print("[defineProfile] update error:", e)

    def onUpdateToolChange(self, index: int, payload):
        payload = self._to_py(payload) or {}
        op = self._get_current_op(index)
        if op is None:
            return
        apply_operation_update(op, payload)
        setattr(op, "tool_no", int(payload["tool_no"])) if "tool_no" in payload and payload["tool_no"] is not None else None
        setattr(op, "tool_orientation", int(payload["tool_orientation"])) if "tool_orientation" in payload and payload["tool_orientation"] is not None else None
        setattr(op, "back_angle", int(payload["back_angle"])) if "back_angle" in payload and payload["back_angle"] is not None else None
        setattr(op, "front_angle", int(payload["front_angle"])) if "front_angle" in payload and payload["front_angle"] is not None else None
        apply_predefined_position_update(op, payload, "toolchange_position")
        self._save_current_program()

    def onUpdatePositionAt(self, index: int, payload):
        payload = self._to_py(payload) or {}
        op = self._get_current_op(index)
        if op is None:
            return
        apply_operation_update(op, payload)
        apply_position_details_update(getattr(op, "position_details", None), payload.get("position_details"))
        self._save_current_program()

    def onUpdateFacing(self, index: int, payload):
        p = self._to_py(payload) or {}
        op = self._get_current_op(index)
        from teachinlathe.conversational.data_types import Facing
        if not isinstance(op, Facing):
            return

        apply_turnable_operation_update(op, p)
        apply_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
        apply_geometry_update(op.geometryParameters, p.get("geometry_parameters"))
        apply_m1_update(op.m1Parameters, p.get("m1_parameters"))
        setattr(op, "zEndBecomesNewZ0", bool(p["z_end_becomes_new_z0"])) if "z_end_becomes_new_z0" in p and p["z_end_becomes_new_z0"] is not None else None
        self._save_current_program()

    def onUpdateProfiling(self, index: int, payload):
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import Profiling
            if not isinstance(op, Profiling):
                return

            apply_turnable_operation_update(op, p)
            apply_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
            apply_profiling_parameters_update(op.profilingParameters, p.get("profiling_parameters"))
            apply_profiling_options_update(op.profilingOptions, p.get("profiling_options"))
            self._save_current_program()
        except Exception as e:
            print("[profiling] update error:", e)

    def onUpdateKnurling(self, index: int, payload):
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import Knurling
            if not isinstance(op, Knurling):
                return

            apply_turnable_operation_update(op, p)
            apply_knurling_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
            apply_geometry_update(op.geometryParameters, p.get("geometry_parameters"))
            apply_m1_update(op.m1Parameters, p.get("m1_parameters"))
            self._save_current_program()
        except Exception as e:
            print("[knurling] update error:", e)

    def onUpdateCustomProfiling(self, index: int, payload):
        self.onUpdateProfiling(index, payload)

    def onUpdateProfileBoring(self, index: int, payload):
        """Profile Boring autosave."""
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import ProfileBoring
            if not isinstance(op, ProfileBoring):
                return

            apply_turnable_operation_update(op, p)
            apply_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
            apply_profiling_parameters_update(op.profilingParameters, p.get("profiling_parameters"))
            apply_profiling_options_update(op.profilingOptions, p.get("profiling_options"))
            apply_roughing_strategy_update(op.roughingStrategy, p.get("roughing_strategy"))
            apply_m1_update(op.m1Parameters, p.get("m1_parameters"))
            self._save_current_program()
        except Exception as e:
            print("[profileBoring] update error:", e)

    def onUpdateDrilling(self, index: int, payload):
        """Drilling autosave."""
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import Drilling
            if not isinstance(op, Drilling):
                return

            apply_turnable_operation_update(op, p)
            apply_drilling_update(op.drillingParameters, p.get("drilling_parameters"))
            apply_m1_update(op.m1Parameters, p.get("m1_parameters"))
            self._save_current_program()
        except Exception as e:
            print("[drilling] update error:", e)

    def onUpdateParting(self, index: int, payload):
        """Parting autosave."""
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import Parting
            if not isinstance(op, Parting):
                return

            apply_turnable_operation_update(op, p)
            apply_parting_update(op.partingParameters, p.get("parting_parameters"))
            apply_edge_break_update(op.edgeBreak, p.get("edge_break"))
            self._save_current_program()
        except Exception as e:
            print("[parting] update error:", e)

    def onUpdateTapping(self, index: int, payload):
        """Tapping autosave."""
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import Tapping
            if not isinstance(op, Tapping):
                return

            apply_turnable_operation_update(op, p)
            apply_tapping_update(op.tappingParameters, p.get("tapping_parameters"))
            apply_m1_update(op.m1Parameters, p.get("m1_parameters"))
            self._save_current_program()
        except Exception as e:
            print("[tapping] update error:", e)

    def onUpdateThreading(self, index: int, payload):
        """Threading autosave."""
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import Threading
            if not isinstance(op, Threading):
                return

            apply_turnable_operation_update(op, p)
            apply_threading_update(op, p)
            self._save_current_program()
        except Exception as e:
            print("[threading] update error:", e)

    # Optional: handle teach buttons
    def onTeachX(self, index: int):
        # TODO: read live X from machine and push to UI
        # op = self._get_current_op(index)
        # if op and hasattr(op, "position_details"):
        #     x = getattr(op.position_details, "x_pos", 0.0)
        #     # You can send it back to QML by re-emitting receiveDetailsData with updated dict,
        #     # or call a small method on the details item if you keep a reference.
        pass

    def onTeachZ(self, index: int):
        # Similar to onTeachX for Z
        pass

    def onOpenNumPadRequested(self, field):
        """Called from QML when a NumpadField was tapped."""
        try:
            self.openNumPad(field)
        except Exception as e:
            print("openNumPad failed:", e)

    def openNumPad(self, fake_edit_text, on_value_selected_callback=None):
        """Open SmartNumPadDialog and manage focus/highlight on the QML field."""
        setting_name = None
        try:
            setting_name = fake_edit_text.property("settingName")
        except Exception:
            pass
        if setting_name is None:
            setting_name = getattr(fake_edit_text, 'settingName', None)

        try:
            fake_edit_text.setProperty("focus", True)
            try:
                QMetaObject.invokeMethod(fake_edit_text, 'forceActiveFocus', Qt.QueuedConnection)
            except Exception:
                pass
            fake_edit_text.setProperty("numpadActive", True)
        except Exception:
            pass

        dialog = SmartNumPadDialog(setting_name)

        def handle_value(value):
            self.setSelectedValue(fake_edit_text, value)
            if on_value_selected_callback:
                on_value_selected_callback(value)

        try:
            dialog.valueSelected.connect(handle_value)
            dialog.exec_()
        finally:
            try:
                fake_edit_text.setProperty("numpadActive", False)
            except Exception:
                pass
            try:
                QMetaObject.invokeMethod(fake_edit_text, 'defocus', Qt.QueuedConnection)
            except Exception:
                try:
                    fake_edit_text.setProperty("focus", False)
                except Exception:
                    pass

    def setSelectedValue(self, field, value):
        """Write a value back into a QML field.
        Prefers a 'commit(value)' method (like NumpadField), else tries 'value', else 'text'."""
        # 1) Try direct attribute call
        try:
            if hasattr(field, 'commit'):
                field.commit(value)  # QML method exposed
                return
        except Exception:
            pass
        # 2) Try meta-object invoke
        try:
            QMetaObject.invokeMethod(field, 'commit', Qt.QueuedConnection, value)
            return
        except Exception:
            pass
        # 3) Try to set 'value' property
        try:
            if field.property("value") is not None:
                field.setProperty("value", value)
                return
        except Exception:
            pass
        # 4) Fallback: set 'text'
        try:
            field.setProperty("text", str(value))
        except Exception as e:
            print("setSelectedValue fallback failed:", e)

    def goBack(self):
        print("back button clicked")
        self.root.goBack()
        QTimer.singleShot(0, self._emit_header_state_changed)
