import json
import os

from PyQt5.QtCore import QUrl, QObject, QMetaObject, Qt
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtQuickWidgets import QQuickWidget

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
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
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
            if hasattr(item, "reorderModeToggled"):
                item.reorderModeToggled.connect(self.onReorderModeToggled)
            if hasattr(item, "addOperationTypeChosen"):
                item.addOperationTypeChosen.connect(self.onAddOperationTypeChosen)
            print("Screen signals connected.")
        except Exception as e:
            print("Failed to hook screen item signals:", e)

    def onAddOperationTypeChosen(self, op_type: str):
        print(f"[operations] User picked: {op_type}")

        prog = self._get_current_program()
        if not prog:
            return

        #   new_op = Operation(type=op_type, order=len(prog.operations)+1)
        #   prog.operations.append(new_op)
        #   self._save_current_program()
        self._refresh_child_operations()

    def _refresh_child_operations(self):
        print("Refreshing child operations...")

    def onAddOperationRequested(self):
        print("[operations] Add New requested")
        # TODO: open your 'add operation' flow

    def onReorderModeToggled(self, on):
        print(f"[operations] Reorder mode: {'ON' if on else 'OFF'}")
        # TODO: enable drag-reorder in the ListView when you implement it

    def onGenerateGcodeRequested(self):
        """Called from ChildScreen when user clicks 'Generate GCode' on the top bar."""
        prog = getattr(self, "current_program", None)
        if not prog:
            print("[gcode] No current program selected.")
            return
        try:
            path = self.generate_gcode_for_program(prog)
            print(f"[gcode] Generated: {path}")
        except Exception as e:
            print("[gcode] Generation failed:", e)

    def generate_gcode_for_program(self, program):
        """Very basic placeholder: writes a .ngc next to the JSON.
        Replace this with your real generator."""
        # decide output path
        json_path = getattr(program, "filename", None)
        if not json_path or not os.path.isabs(json_path):
            # fall back to folder_path/header.name
            base_dir = getattr(self, "folder_path", os.getcwd())
            base_name = getattr(getattr(program, "header", None), "name", getattr(program, "id", "program"))
            base_name = "".join(c for c in str(base_name) if c.isalnum() or c in ("-", "_", " ")).strip().replace(" ", "_")
            json_path = os.path.join(base_dir, base_name + ".json")

        base_no_ext, _ = os.path.splitext(json_path)
        ngc_path = base_no_ext + ".ngc"

        # TODO: replace this with your real generator
        lines = []
        lines.append("( Generated by ConversationalQml placeholder )")
        lines.append(f"( Program: {getattr(getattr(program, 'header', None), 'name', program.id)} )")
        lines.append(f"( Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} )")
        lines.append("G21  (mm)")
        lines.append("G90  (absolute)")
        lines.append("G94  (feed per min)")
        lines.append("G18  (ZX plane)")
        lines.append("")

        # just enumerate ops as comments for now
        try:
            ops = getattr(program, "operations", [])
            for i, op in enumerate(ops, 1):
                t = getattr(op, "type", "unknown")
                lines.append(f"( OP#{i} type={t} )")
                # You would insert real motion blocks per op type here
        except Exception:
            pass

        lines.append("")
        lines.append("M30")

        with open(ngc_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return ngc_path

    def onDetailsRequested(self, screen_item, index: int):
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
            tool_no = getattr(op, "tool_no", None)
            pitch = getattr(op, "pitch", None)
            d["display_type"] = self._display_name_for_op(d["type"], tool_no=tool_no, pitch=pitch)
            out.append(d)
        return out

    def _display_name_for_op(self, op_type, tool_no=None, pitch=None):
        """Map internal operation types to human readable strings."""
        t = (op_type or "").strip()
        if t == "changeTool":
            if tool_no is not None:
                return f"Tool Change (T{tool_no})"
            return "Tool Change"
        if t == "facing":
            return "Facing"
        if t == "define_profile":
            return "Define Profile"
        if t == "profiling":
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
        self._save_current_program()

    def onToggleOptionalBlock(self, index: int, checked: bool):
        op = self._get_current_op(index)
        if not op:
            return
        try:
            setattr(op, "is_optional_block", bool(checked))
        except Exception:
            pass
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
        payload = self._to_py(payload)
        op = self._get_current_op(index)
        if op is None or getattr(op, "type", "") != "profiling":
            return
        for attr in ("order", "generate_gcode", "is_optional_block",
                     "css_value", "max_speed", "feed_rate", "profileId",
                     "x_start", "z_start", "doc", "retract"):
            if attr in payload and hasattr(op, attr):
                try:
                    setattr(op, attr, payload[attr])
                except Exception:
                    pass
        if "strategy" in payload:
            try:
                from teachinlathe.widgets.conversational_qml.data_types import Strategy  # adjust import
                op.strategy = Strategy[payload["strategy"].upper()]
            except Exception:
                pass
        if "stock_to_leave" in payload:
            stl = payload["stock_to_leave"]
            if stl is None:
                op.stock_to_leave = None
            elif isinstance(stl, dict):
                try:
                    op.stock_to_leave = {"x": float(stl.get("x", 0.0)),
                                         "z": float(stl.get("z", 0.0))}
                except Exception:
                    pass
        if "spring_passes" in payload:
            sp = payload["spring_passes"]
            op.spring_passes = None if (sp is None) else int(sp)
        self._save_current_program()

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
        """Threading autosave (odată cu noile câmpuri)."""
        try:
            payload = self._to_py(payload)
            op = self._get_current_op(index)
            if op is None or getattr(op, "type", "") != "threading":
                return

            # câmpuri simple
            for attr in ("order", "generate_gcode", "is_optional_block",
                         "spindle_rpm", "thread_type", "pitch", "starts",
                         "major_diameter", "minor_diameter",
                         "z_start", "z_end", "initial_doc", "retract", "spring_passes"):
                if attr in payload and hasattr(op, attr):
                    setattr(op, attr, payload[attr])

            # location (enum)
            if "location" in payload:
                loc = payload["location"]
                if isinstance(loc, str):
                    try:
                        op.location = ThreadLocation[loc]  # "OD"/"ID"
                    except Exception:
                        try:
                            op.location = ThreadLocation(loc)
                        except Exception:
                            op.location = ThreadLocation.OD
                elif isinstance(loc, ThreadLocation):
                    op.location = loc

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
