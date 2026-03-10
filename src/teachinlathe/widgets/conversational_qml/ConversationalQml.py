import json
import os
import time

from PyQt5.QtCore import QUrl, QObject, QMetaObject, Qt, QTimer, QEventLoop
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtWidgets import QProgressDialog, QApplication

from teachinlathe.conversational.data_types import Workpiece, SpindleParameters, Facing, CuttingParameters, GeometryParameters, M1Parameters, SpindleMode, \
    operation_types
from teachinlathe.widgets.conversational_qml.ProgramListModel import ProgramListModel
from teachinlathe.widgets.conversational_qml.program_loader import load_programs_from_folder
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog


def _merge_dataclass(obj, dct):
    if not isinstance(dct, dict) or obj is None:
        return
    for k, v in dct.items():
        if hasattr(obj, k):
            try:
                setattr(obj, k, v)
            except Exception:
                pass


def _deep_merge(base, patch):
    if not isinstance(base, dict) or not isinstance(patch, dict):
        return patch
    out = dict(base)
    for k, v in patch.items():
        if k in out and isinstance(out[k],  dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class ConversationalQml(QQuickWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.folder_path = "/home/cnc/Work/teachinlathe/conversational"
        self.current_program = None
        self.child_screen_item = None

        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        programs = load_programs_from_folder(self.folder_path)

        self.model = ProgramListModel(programs)
        self.engine().rootContext().setContextProperty("programsModel", self.model)

        root_path = os.path.join(self.base_dir, "Root.qml")
        self.statusChanged.connect(self.onStatusChanged)
        self.setSource(QUrl.fromLocalFile(root_path))

    def onStatusChanged(self, status):
        if status == QQuickWidget.Ready:
            self.root = self.rootObject()
            if not self.root:
                print("Failed to load Root.qml")
                return

            print("----Model count:", self.model.rowCount())

            main_url = QUrl.fromLocalFile(os.path.join(self.base_dir, "MainScreen.qml")).toString()
            self.root.loadScreen(main_url, {"programsModel": self.model, "showBack": False})

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

    def onLoaderItemChanged(self):
        sender = self.sender()
        if not sender:
            return
        item = sender.property("item")
        if item:
            self._hook_screen_item(item)

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
    def _sanitize_filename(self, name: str) -> str:
        # very simple sanitizer: keep alnum, space, dash, underscore, dot
        safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", "."))
        safe = safe.strip().replace(" ", "_")
        return safe or "program"

    def _resolve_save_path(self, prog) -> str:
        # 1) Prefer path provided by loader
        filename = getattr(prog, "filename", None)
        if filename and isinstance(filename, str) and filename.strip():
            return filename

        # 2) Fallback to folder_path + header.name/id + .json
        base_dir = getattr(self, "folder_path", os.getcwd())
        base_name = None
        # try header.name
        try:
            base_name = prog.header.name
        except Exception:
            pass
        if not base_name:
            # try id
            try:
                base_name = prog.id
            except Exception:
                base_name = "program"

        base_name = self._sanitize_filename(str(base_name))
        if not base_name.lower().endswith(".json"):
            base_name += ".json"

        return os.path.join(base_dir, base_name)

    # în _save_current_program(self):
    def _save_current_program(self):
        prog = self._get_current_program()
        if not prog:
            return

        from datetime import datetime
        try:
            if hasattr(prog, "header") and hasattr(prog.header, "last_edit"):
                prog.header.last_edit = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        data = prog.to_dict() if hasattr(prog, "to_dict") else None
        if not data:
            print("Program serialization missing (to_dict).")
            return

        filename = self._resolve_save_path(prog)
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            if not getattr(prog, "filename", None):
                prog.filename = filename
            print(f"[autosave] Program written to: {filename}")
        except Exception as e:
            print("Failed to save program:", e)
            return

        # 🔁 IMPORTANT: reîncarcă de pe disc și înlocuiește instanța în model + self.current_program
        try:
            with open(filename, "r", encoding="utf-8") as f:
                disk_data = json.load(f)
            from teachinlathe.conversational.data_types import Program
            new_prog = Program.from_dict(disk_data)
            new_prog.filename = filename

            row = getattr(self, "current_program_index", None)
            if row is not None and hasattr(self.model, "setProgramAt"):
                self.model.setProgramAt(row, new_prog)
                # păstrează *aceeași referință* ca în model
                self.current_program = self.model.get(row)
            else:
                # fallback
                self.current_program = new_prog

            # notifică last-edit în listă
            if row is not None:
                top = self.model.index(row)
                bottom = self.model.index(row)
                from teachinlathe.widgets.conversational_qml.ProgramListModel import ProgramListModel as _PLM
                self.model.dataChanged.emit(top, bottom, [_PLM.LastEditDateRole])

            # refresh operation labels in the left pane without reloading the screen
            if getattr(self, "child_screen_item", None) is not None:
                new_ops = self._build_operations_model(self.current_program)
                self.child_screen_item.setProperty("activeOpIndex", getattr(self, "current_op_index", -1))
                self.child_screen_item.setProperty("operationsModel", new_ops)
        except Exception as e:
            print("Failed to refresh in-memory program from disk:", e)

    def _hook_screen_item(self, item):
        try:
            obj_name = item.property("objectName")
        except Exception:
            obj_name = None
        if obj_name == "childScreen":
            self.child_screen_item = item

        try:
            if hasattr(item, "addNewProgramRequested"):
                item.addNewProgramRequested.connect(self.openChildScreen)
            if hasattr(item, "editProgramRequested"):
                item.editProgramRequested.connect(self.openChildScreen)
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
            if hasattr(item, "updateDefineProfile"):
                item.updateDefineProfile.connect(self.onUpdateDefineProfile)
            if hasattr(item, "teachXRequested"):
                item.teachXRequested.connect(self.onTeachX)
            if hasattr(item, "teachZRequested"):
                item.teachZRequested.connect(self.onTeachZ)
            if hasattr(item, "updateFacing"):
                item.updateFacing.connect(self.onUpdateFacing)
            if hasattr(item, "updateProfiling"):
                item.updateProfiling.connect(self.onUpdateProfiling)
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
        except Exception as e:
            print("Failed to hook screen item signals:", e)

    def _default_op_dict(self, op_type: str) -> dict:
        base = {"order": 1, "type": op_type, "generate_gcode": True, "is_optional_block": False}
        spindle_rpm = {"direction": 1, "mode": "rpm", "rpm_value": 1000}
        m1_default  = {"include_m1": False, "x_inspect": 0.0, "z_inspect": 0.0, "stop_spindle": False}

        if op_type == "changeTool":
            base.update({
                "tool_no": 1, "tool_orientation": 1, "back_angle": 0, "front_angle": 0,
                "toolchange_rules": {
                    "x_pos": 0.0, "z_pos": 0.0,
                    "coordinate_type": "absolute", "move_sequence": "xz", "stop_spindle": False,
                },
            })
        elif op_type == "facing":
            base.update({
                "spindle_parameters": spindle_rpm,
                "cutting_parameters": {"feed_rate": 0.1, "doc": 0.5, "retract": 1.0},
                "geometry_parameters": {"x_start": 0.0, "z_start": 0.0, "x_end": 0.0, "z_end": 0.0},
                "m1_parameters": m1_default,
                "z_end_becomes_new_z0": False,
            })
        elif op_type == "profiling":
            base.update({
                "spindle_parameters": spindle_rpm,
                "cutting_parameters": {"feed_rate": 0.1, "doc": 0.5, "retract": 1.0},
                "profiling_parameters": {"profile_id": 1, "x_start": 0.0, "z_start": 0.0},
                "profiling_options": {
                    "strategy": "rough",
                    "stock_to_leave_x": 0.0, "stock_to_leave_z": 0.0, "finish_spring_passes": 0,
                },
            })
        elif op_type == "threading":
            base.update({
                "spindle_parameters": {"direction": 1, "mode": "rpm", "rpm_value": 500},
                "location": "OD", "thread_type": "metric",
                "pitch": 1.0, "starts": 1,
                "major_diameter": 0.0, "minor_diameter": 0.0,
                "z_start": 0.0, "z_end": 0.0,
                "initial_doc": 0.3, "retract": 1.0, "spring_passes": 0,
                "depth_degression": 1.0, "taper_type": 0, "compound_angle": 0.0,
            })
        elif op_type == "drilling":
            base.update({
                "spindle_parameters": spindle_rpm,
                "drilling_parameters": {
                    "z_start": 0.0, "z_end": 0.0, "z_retract": 5.0, "peck_depth": 3.0, "feed_rate": 0.05,
                },
                "m1_parameters": m1_default,
            })
        elif op_type == "tapping":
            base.update({
                "spindle_parameters": {"direction": 1, "mode": "rpm", "rpm_value": 500},
                "tapping_parameters": {
                    "z_start": 0.0, "z_end": 0.0, "z_retract": 5.0, "peck_depth": 0.0, "pitch": 1.0,
                },
                "m1_parameters": m1_default,
            })
        elif op_type == "parting":
            base.update({
                "spindle_parameters": {"direction": 1, "mode": "rpm", "rpm_value": 500},
                "parting_parameters": {
                    "x_start": 0.0, "x_end": 0.0, "z_pos": 0.0,
                    "1st_feed_rate": 0.05, "2nd_feed_rate": 0.02, "2nd_feed_x_pos": 5.0,
                    "x_clearance": 1.0,
                },
                "edge_break": {"blend_type": "none", "chamfer_width": 0.0, "fillet_radius": 0.0},
            })
        elif op_type == "defineProfile":
            base.update({
                "generate_gcode": False,
                "profile_id": 1,
                "profile_primitives": [],
            })
        return base

    def onAddOperationTypeChosen(self, op_type: str, insert_index: int):
        print(f"[operations] Adding {op_type!r} at index {insert_index}")
        prog = self._get_current_program()
        if not prog:
            return
        from teachinlathe.conversational.data_types import operation_types
        if op_type not in operation_types:
            print(f"[operations] Unknown type: {op_type!r}")
            return
        try:
            op_dict = self._default_op_dict(op_type)
            new_op  = operation_types[op_type].from_dict(op_dict)
            ops     = prog.operations
            idx     = max(0, min(insert_index, len(ops)))
            ops.insert(idx, new_op)
            self._renumber_operations(ops)
            self.current_op_index = idx
            self._save_current_program()
        except Exception as e:
            print(f"[operations] Failed to create {op_type!r}: {e}")

    def onAddOperationRequested(self):
        print("[operations] Add New requested")
        # TODO: open your 'add operation' flow

    def onReorderModeToggled(self, on):
        print(f"[operations] Reorder mode: {'ON' if on else 'OFF'}")

    def _renumber_operations(self, ops):
        for i, op in enumerate(ops):
            op.order = i + 1

    def onMoveUp(self, index: int):
        prog = self._get_current_program()
        if not prog or index <= 0:
            return
        ops = prog.operations
        ops.insert(index - 1, ops.pop(index))
        self._renumber_operations(ops)
        self.current_op_index = index - 1
        self._save_current_program()

    def onMoveDown(self, index: int):
        prog = self._get_current_program()
        if not prog or index >= len(prog.operations) - 1:
            return
        ops = prog.operations
        ops.insert(index + 1, ops.pop(index))
        self._renumber_operations(ops)
        self.current_op_index = index + 1
        self._save_current_program()

    def onDeleteOperation(self, index: int):
        prog = self._get_current_program()
        if not prog or not (0 <= index < len(prog.operations)):
            return
        prog.operations.pop(index)
        self._renumber_operations(prog.operations)
        self.current_op_index = -1
        self._save_current_program()

    def onAddProfilingFinishRequested(self, index: int):
        prog = self._get_current_program()
        if not prog or not (0 <= index < len(prog.operations)):
            return
        op = prog.operations[index]
        from teachinlathe.conversational.data_types import Profiling
        if not isinstance(op, Profiling):
            return
        try:
            d = op.to_dict()
            opts = d.get("profiling_options", {}) or {}
            opts["strategy"] = "finish"
            d["profiling_options"] = opts
            new_op = Profiling.from_dict(d)
            insert_idx = index + 1
            prog.operations.insert(insert_idx, new_op)
            self._renumber_operations(prog.operations)
            self.current_op_index = insert_idx
            self._save_current_program()
        except Exception as e:
            print("[profiling] add finish failed:", e)

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
        from .gcode_builder import build_ngc_from_json
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

        return build_ngc_from_json(json_path, output_dir=gcode_dir)

    def onDetailsRequested(self, screen_item, index: int):
        self.current_op_index = index
        # Header selected
        if index == -1:
            prog = self._get_current_program()
            if not prog:
                return
            try:
                data = prog.to_dict() if hasattr(prog, "to_dict") else None
                if data:
                    screen_item.receiveDetailsData(-1, data)  # ChildScreen va încărca HeaderDetailsView.qml
            except Exception as e:
                print("receiveDetailsData(header) failed:", e)
            return

        # Normal op details
        op = self._get_current_op(index)
        if op is None:
            return
        data = op.to_dict() if hasattr(op, "to_dict") else None
        if not data:
            return
        try:
            screen_item.receiveDetailsData(index, data)
        except Exception as e:
            print("receiveDetailsData failed:", e)

    def addNewProgram(self):
        print("add new program clicked")

    def openChildScreen(self, arg=None):
        program = None
        row_index = None
        if isinstance(arg, int):
            row_index = arg
            if hasattr(self.model, "get"):
                program = self.model.get(arg)
            elif hasattr(self.model, "program_at"):
                program = self.model.program_at(arg)
            elif hasattr(self.model, "programAt"):
                program = self.model.programAt(arg)
        if program is None:
            print("openChildScreen: program not resolved from", arg)
            return

        self.current_program = program
        self.current_program_index = row_index

        selected_program = {
            "id": program.id,
            "name": program.header.name,
            "last_edit": program.header.last_edit,
        }
        operations_model = self._build_operations_model(program)

        child_url = QUrl.fromLocalFile(os.path.join(self.base_dir, "ChildScreen.qml")).toString()
        params = {
            "showBack": True,
            "selectedProgram": selected_program,
            "operationsModel": operations_model,
        }
        print("openChildScreen for:", selected_program["name"], "ops:", len(operations_model))
        self.root.loadScreen(child_url, params)

    def _build_operations_model(self, program):
        """Return a list of dicts friendly to QML with 'display_type' precomputed."""
        out = []
        ops = getattr(program, "operations", []) or []
        for op in ops:
            # base fields
            d = {
                "order": getattr(op, "order", None),
                "type": getattr(op, "type", ""),
                "generate_gcode": bool(getattr(op, "generate_gcode", False)),
                "is_optional_block": bool(getattr(op, "is_optional_block", False)),
            }
            # enrich with hints used for display name
            tool_no    = getattr(op, "tool_no", None)
            pitch      = getattr(op, "pitch", None)
            profile_id = getattr(getattr(op, "profilingParameters", None), "profile_id", None)
            if profile_id is None:
                profile_id = getattr(op, "profile_id", None)
            strategy   = getattr(getattr(op, "profilingOptions", None), "strategy", None)
            d["display_type"] = self._display_name_for_op(
                d["type"], tool_no=tool_no, pitch=pitch, profile_id=profile_id, strategy=strategy
            )
            out.append(d)
        return out

    def _display_name_for_op(self, op_type, tool_no=None, pitch=None, profile_id=None, strategy=None):
        """Map internal operation types to human readable strings."""
        t = (op_type or "").strip()
        if t == "changeTool":
            if tool_no is not None:
                return f"Tool Change (T{tool_no})"
            return "Tool Change"
        if t == "facing":
            return "Facing"
        if t == "defineProfile":
            if profile_id is not None:
                return f"Define Profile (P{profile_id})"
            return "Define Profile"
        if t == "profiling":
            if profile_id is not None and strategy is not None:
                strategy_str = strategy.value.capitalize() if hasattr(strategy, "value") else str(strategy).capitalize()
                return f"Cut Profile (P:{profile_id}, {strategy_str})"
            if profile_id is not None:
                return f"Cut Profile (P:{profile_id})"
            return "Cut Profile"
        if t == "threading":
            return f"Threading (P: {pitch})" if pitch is not None else "Threading"
        if t == "drilling":
            return "Drilling"
        if t == "tapping":
            return "Tapping"
        if t == "parting":
            return "Parting"
        # fallback
        return t or "Unknown"

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
            # Unwrap daca vine sub cheia "header"
            hdr = p.get("header", p)

            prog = self._get_current_program()
            if not prog or not hasattr(prog, "header") or prog.header is None:
                return

            header = prog.header

            if "name" in hdr:
                header.name = str(hdr["name"])
            if "units" in hdr:
                header.units = str(hdr["units"])
            if "datum" in hdr:
                try:
                    header.datum = int(hdr["datum"])
                except Exception:
                    pass
            if "last_edit" in hdr and hdr["last_edit"] is not None:
                header.last_edit = str(hdr["last_edit"])

            # nested: workpiece
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
            old_dict = op.to_dict()
            merged   = _deep_merge(old_dict, p)
            new_op   = DefineProfile.from_dict(merged)
            prog     = self._get_current_program()
            if prog:
                prog.operations[index] = new_op
            self._save_current_program()
        except Exception as e:
            print("[defineProfile] update error:", e)

    def onUpdateToolChange(self, index: int, payload):
        payload = self._to_py(payload)
        op = self._get_current_op(index)
        if op is None:
            return
        for attr in ("order", "generate_gcode", "is_optional_block",
                     "tool_no", "tool_orientation", "back_angle", "front_angle"):
            if attr in payload and hasattr(op, attr):
                try:
                    setattr(op, attr, payload[attr])
                except Exception:
                    pass
        d = payload.get("toolchange_rules")
        tcd = getattr(op, "toolchange_rules", None)
        if tcd and isinstance(d, dict):
            for attr in ("x_pos", "z_pos", "coordinate_type", "move_sequence", "stop_spindle"):
                if attr in d and hasattr(tcd, attr):
                    try:
                        setattr(tcd, attr, d[attr])
                    except Exception:
                        pass
        self._save_current_program()

    def onUpdateFacing(self, index: int, payload):
        p = self._to_py(payload) or {}
        op = self._get_current_op(index)
        from teachinlathe.conversational.data_types import Facing
        if not isinstance(op, Facing):
            return

        old_dict = op.to_dict()  # sursa de adevăr din memorie
        sp_old = (old_dict.get("spindle_parameters") or {})

        # --- Normalizează payload-ul de spindle înainte de merge ---
        sp_new = p.get("spindle_parameters")
        if isinstance(sp_new, dict):
            sp_norm = dict(sp_old)  # pornește de la ce aveai
            # 1) “mode”: dacă vine din UI, ia-l; dacă nu, inferă; altfel păstrează vechiul
            if "mode" in sp_new and sp_new["mode"]:
                sp_norm["mode"] = sp_new["mode"]
            elif "rpm_value" in sp_new and sp_new["rpm_value"] is not None:
                sp_norm["mode"] = "rpm"
            elif (sp_new.get("css_value") is not None) and (sp_new.get("css_max_speed") is not None):
                sp_norm["mode"] = "css"
            else:
                sp_norm["mode"] = sp_old.get("mode", "rpm")

            # 2) Copiază doar ce vine, restul păstrează (NU pune default aici)
            for k in ("direction", "rpm_value", "css_value", "css_max_speed"):
                if k in sp_new and sp_new[k] is not None:
                    sp_norm[k] = sp_new[k]

            # asigură-te că rămân și valorile celuilalt mod pentru UI (nu le ștergem)
            p["spindle_parameters"] = sp_norm

        # --- Merge pe tot op-ul ---
        merged = _deep_merge(old_dict, p)

        # --- Reconstruiește instanța curentă (validare într-un singur loc) ---
        cls = operation_types[merged.get("type", old_dict.get("type"))]
        new_op = cls.from_dict(merged)

        # --- Înlocuiește în listă și salvează ---
        prog = self._get_current_program()
        if prog:
            prog.operations[index] = new_op
        self._save_current_program()

    def onUpdateProfiling(self, index: int, payload):
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import Profiling
            if not isinstance(op, Profiling):
                return

            old_dict = op.to_dict()
            sp_old = (old_dict.get("spindle_parameters") or {})
            sp_new = p.get("spindle_parameters")
            if isinstance(sp_new, dict):
                sp_norm = dict(sp_old)
                if "mode" in sp_new and sp_new["mode"]:
                    sp_norm["mode"] = sp_new["mode"]
                elif "rpm_value" in sp_new and sp_new["rpm_value"] is not None:
                    sp_norm["mode"] = "rpm"
                elif (sp_new.get("css_value") is not None) and (sp_new.get("css_max_speed") is not None):
                    sp_norm["mode"] = "css"
                else:
                    sp_norm["mode"] = sp_old.get("mode", "rpm")
                for k in ("direction", "rpm_value", "css_value", "css_max_speed"):
                    if k in sp_new and sp_new[k] is not None:
                        sp_norm[k] = sp_new[k]
                p["spindle_parameters"] = sp_norm

            merged = _deep_merge(old_dict, p)
            new_op = Profiling.from_dict(merged)
            prog = self._get_current_program()
            if prog:
                prog.operations[index] = new_op
            self._save_current_program()
        except Exception as e:
            print("[profiling] update error:", e)

    def onUpdateDrilling(self, index: int, payload):
        """Drilling autosave."""
        try:
            p = self._to_py(payload) or {}
            op = self._get_current_op(index)
            from teachinlathe.conversational.data_types import Drilling
            if not isinstance(op, Drilling):
                return

            old_dict = op.to_dict()
            sp_old = (old_dict.get("spindle_parameters") or {})
            sp_new = p.get("spindle_parameters")
            if isinstance(sp_new, dict):
                sp_norm = dict(sp_old)
                if "mode" in sp_new and sp_new["mode"]:
                    sp_norm["mode"] = sp_new["mode"]
                elif "rpm_value" in sp_new and sp_new["rpm_value"] is not None:
                    sp_norm["mode"] = "rpm"
                else:
                    sp_norm["mode"] = sp_old.get("mode", "rpm")
                for k in ("direction", "rpm_value", "css_value", "css_max_speed"):
                    if k in sp_new and sp_new[k] is not None:
                        sp_norm[k] = sp_new[k]
                p["spindle_parameters"] = sp_norm

            merged = _deep_merge(old_dict, p)
            new_op = Drilling.from_dict(merged)
            prog = self._get_current_program()
            if prog:
                prog.operations[index] = new_op
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

            old_dict = op.to_dict()
            sp_old = (old_dict.get("spindle_parameters") or {})
            sp_new = p.get("spindle_parameters")
            if isinstance(sp_new, dict):
                sp_norm = dict(sp_old)
                if "mode" in sp_new and sp_new["mode"]:
                    sp_norm["mode"] = sp_new["mode"]
                elif "rpm_value" in sp_new and sp_new["rpm_value"] is not None:
                    sp_norm["mode"] = "rpm"
                elif (sp_new.get("css_value") is not None) and (sp_new.get("css_max_speed") is not None):
                    sp_norm["mode"] = "css"
                else:
                    sp_norm["mode"] = sp_old.get("mode", "rpm")
                for k in ("direction", "rpm_value", "css_value", "css_max_speed"):
                    if k in sp_new and sp_new[k] is not None:
                        sp_norm[k] = sp_new[k]
                p["spindle_parameters"] = sp_norm

            merged = _deep_merge(old_dict, p)
            new_op = Parting.from_dict(merged)
            prog = self._get_current_program()
            if prog:
                prog.operations[index] = new_op
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

            old_dict = op.to_dict()
            sp_old = (old_dict.get("spindle_parameters") or {})
            sp_new = p.get("spindle_parameters")
            if isinstance(sp_new, dict):
                sp_norm = dict(sp_old)
                if "mode" in sp_new and sp_new["mode"]:
                    sp_norm["mode"] = sp_new["mode"]
                elif "rpm_value" in sp_new and sp_new["rpm_value"] is not None:
                    sp_norm["mode"] = "rpm"
                else:
                    sp_norm["mode"] = sp_old.get("mode", "rpm")
                for k in ("direction", "rpm_value", "css_value", "css_max_speed"):
                    if k in sp_new and sp_new[k] is not None:
                        sp_norm[k] = sp_new[k]
                p["spindle_parameters"] = sp_norm

            merged = _deep_merge(old_dict, p)
            new_op = Tapping.from_dict(merged)
            prog = self._get_current_program()
            if prog:
                prog.operations[index] = new_op
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

            old_dict = op.to_dict()
            sp_old = (old_dict.get("spindle_parameters") or {})
            sp_new = p.get("spindle_parameters")
            if isinstance(sp_new, dict):
                sp_norm = dict(sp_old)
                if "mode" in sp_new and sp_new["mode"]:
                    sp_norm["mode"] = sp_new["mode"]
                elif "rpm_value" in sp_new and sp_new["rpm_value"] is not None:
                    sp_norm["mode"] = "rpm"
                else:
                    sp_norm["mode"] = sp_old.get("mode", "rpm")
                for k in ("direction", "rpm_value", "css_value", "css_max_speed"):
                    if k in sp_new and sp_new[k] is not None:
                        sp_norm[k] = sp_new[k]
                p["spindle_parameters"] = sp_norm

            merged = _deep_merge(old_dict, p)
            new_op = Threading.from_dict(merged)
            prog = self._get_current_program()
            if prog:
                prog.operations[index] = new_op
            self._save_current_program()
        except Exception as e:
            print("[threading] update error:", e)

    # Optional: handle teach buttons
    def onTeachX(self, index: int):
        # TODO: read live X from machine and push to UI
        # op = self._get_current_op(index)
        # if op and hasattr(op, "toolchange_rules"):
        #     x = getattr(op.toolchange_rules, "x_pos", 0.0)
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
