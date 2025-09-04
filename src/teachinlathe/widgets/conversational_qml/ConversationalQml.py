from PyQt5.QtCore import QUrl, QObject, QMetaObject, Qt
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtQuickWidgets import QQuickWidget
# from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog  # adjust import
import json, os

from teachinlathe.widgets.conversational_qml.program_loader import load_programs_from_folder
from teachinlathe.widgets.conversational_qml.ProgramListModel import ProgramListModel
from teachinlathe.widgets.smart_numpad_dialog import SmartNumPadDialog


# If you can import your datatypes module, do it and reuse .to_dict()
# from teachinlathe.widgets.conversational.datatypes import Program as DProgram

class ConversationalQml(QQuickWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.folder_path = "/home/cnc/Work/teachinlathe/conversational"
        self.current_program = None

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

    def _get_current_op(self, index):
        prog = self._get_current_program()
        if not prog or not hasattr(prog, "operations"):
            return None
        if index < 0 or index >= len(prog.operations):
            return None
        return prog.operations[index]

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

    # REPLACE your _save_current_program with this version
    def _save_current_program(self):
        """Serialize and write current program to its JSON file (in the original folder if possible)."""
        prog = self._get_current_program()
        if not prog:
            return

        # update last_edit in memory before serialization (optional but useful for UI)
        try:
            from datetime import datetime
            if hasattr(prog, "header") and hasattr(prog.header, "last_edit"):
                prog.header.last_edit = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass

        # collect data
        data = prog.to_dict() if hasattr(prog, "to_dict") else None
        if not data:
            print("Program serialization missing (to_dict).")
            return

        # resolve path
        filename = self._resolve_save_path(prog)
        try:
            # ensure parent directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            # cache the filename on the object if it wasn't set
            try:
                if not getattr(prog, "filename", None):
                    prog.filename = filename
            except Exception:
                pass
            print(f"[autosave] Program written to: {filename}")
        except Exception as e:
            print("Failed to save program:", e)

        # notify the list model that last_edit changed (refresh row)
        try:
            row = getattr(self, "current_program_index", None)
            if row is not None:
                top = self.model.index(row)
                bottom = self.model.index(row)
                # Only last-edit role for minimal refresh
                from teachinlathe.widgets.conversational_qml.ProgramListModel import ProgramListModel as _PLM
                self.model.dataChanged.emit(top, bottom, [_PLM.LastEditDateRole])
        except Exception as e:
            print("Failed to emit dataChanged:", e)

    def _hook_screen_item(self, item):
        """Connect expected QML signals from the loaded screen."""
        try:
            if hasattr(item, "addNewProgramRequested"):
                item.addNewProgramRequested.connect(self.openChildScreen)
            if hasattr(item, "editProgramRequested"):
                item.editProgramRequested.connect(self.openChildScreen)  # gets row index
            if hasattr(item, "backRequested"):
                item.backRequested.connect(self.goBack)
            if hasattr(item, "toggleGenerateGcode"):
                item.toggleGenerateGcode.connect(self.onToggleGenerateGcode)
            if hasattr(item, "toggleOptionalBlock"):
                item.toggleOptionalBlock.connect(self.onToggleOptionalBlock)
            # in _hook_screen_item(self, item):
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
            if hasattr(item, "openNumPadRequested"):
                item.openNumPadRequested.connect(self.onOpenNumPadRequested)
            print("Screen signals connected.")
        except Exception as e:
            print("Failed to hook screen item signals:", e)

    def onDetailsRequested(self, screen_item, index: int):
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
        if t == "odThread":
            return f"OD Thread (P: {pitch})" if pitch is not None else "OD Thread"
        if t == "idThread":
            return f"ID Thread (P: {pitch})" if pitch is not None else "ID Thread"
        if t == "drilling":
            return "Drilling"
        if t == "tapping":
            return "Tapping"
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

    def _get_current_op(self, index):
        if self.current_program is None:
            return None
        ops = getattr(self.current_program, "operations", [])
        if not (0 <= index < len(ops)):
            return None
        return ops[index]

    # def onDetailsRequested(self, screen_item, index: int):
    #     """Build a full dict for the selected operation and push it into ChildScreen."""
    #     op = self._get_current_op(index)
    #     if op is None:
    #         return
    #     # Prefer dataclass .to_dict() for exact schema
    #     if hasattr(op, "to_dict"):
    #         data = op.to_dict()
    #     else:
    #         # fallback: minimal
    #         data = {
    #             "order": getattr(op, "order", 0),
    #             "type": getattr(op, "type", ""),
    #             "generate_gcode": bool(getattr(op, "generate_gcode", False)),
    #             "is_optional_block": bool(getattr(op, "is_optional_block", False)),
    #         }
    #         # hydrate nested if available
    #         tcd = getattr(op, "toolchange_details", None)
    #         if tcd:
    #             data["toolchange_details"] = {
    #                 "x_pos": getattr(tcd, "x_pos", 0.0),
    #                 "z_pos": getattr(tcd, "z_pos", 0.0),
    #                 "coordinate_type": getattr(tcd, "coordinate_type", "absolute"),
    #                 "move_sequence": getattr(tcd, "move_sequence", "xz"),
    #                 "stop_spindle": bool(getattr(tcd, "stop_spindle", False)),
    #             }
    #         # top-level tool props
    #         for k in ("tool_no", "tool_orientation", "back_angle", "front_angle"):
    #             if hasattr(op, k):
    #                 data[k] = getattr(op, k)
    #
    #     # Call the QML method to load + apply data
    #     try:
    #         screen_item.receiveDetailsData(index, data)
    #     except Exception as e:
    #         print("receiveDetailsData failed:", e)

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
        d = payload.get("toolchange_details")
        tcd = getattr(op, "toolchange_details", None)
        if tcd and isinstance(d, dict):
            for attr in ("x_pos", "z_pos", "coordinate_type", "move_sequence", "stop_spindle"):
                if attr in d and hasattr(tcd, attr):
                    try:
                        setattr(tcd, attr, d[attr])
                    except Exception:
                        pass
        self._save_current_program()

    def onUpdateFacing(self, index: int, payload):
        payload = self._to_py(payload)
        op = self._get_current_op(index)
        if op is None or getattr(op, "type", "") != "facing":
            return
        for attr in ("order", "generate_gcode", "is_optional_block",
                     "css_value", "max_speed", "feed_rate", "doc", "retract",
                     "x_start", "z_start", "x_end", "z_end", "z_end_becomes_new_z0"):
            if attr in payload and hasattr(op, attr):
                try:
                    setattr(op, attr, payload[attr])
                except Exception:
                    pass
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

    # Optional: handle teach buttons
    def onTeachX(self, index: int):
        # TODO: read live X from machine and push to UI
        # op = self._get_current_op(index)
        # if op and hasattr(op, "toolchange_details"):
        #     x = getattr(op.toolchange_details, "x_pos", 0.0)
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
        """Open SmartNumPadDialog and write the chosen value back into the QML field."""
        # robust read of 'settingName' from QML Item
        setting_name = None
        try:
            setting_name = fake_edit_text.property("settingName")
        except Exception:
            pass
        if setting_name is None:
            setting_name = getattr(fake_edit_text, 'settingName', None)

        # try to set numpadActive guard to avoid double-open
        try:
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
