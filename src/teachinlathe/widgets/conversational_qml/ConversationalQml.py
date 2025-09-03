import os
from PyQt5.QtCore import QUrl, QObject
from PyQt5.QtQuick import QQuickItem
from PyQt5.QtQuickWidgets import QQuickWidget

from teachinlathe.widgets.conversational.program_loader import load_programs_from_folder
from teachinlathe.widgets.conversational_qml.ProgramListModel import ProgramListModel

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

            print("Screen signals connected.")
        except Exception as e:
            print("Failed to hook screen item signals:", e)

    def addNewProgram(self):
        print("add new program clicked")

    def openChildScreen(self, arg=None):
        """arg is expected to be the row index; fallback supported."""
        program = None
        if isinstance(arg, int):
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

    def onToggleGenerateGcode(self, index, checked):
        """Update Python model when 'Generate GCode' is toggled in QML."""
        if self.current_program is None:
            return
        if not (0 <= index < len(self.current_program.operations)):
            return
        try:
            op = self.current_program.operations[index]
            if hasattr(op, "generate_gcode"):
                op.generate_gcode = bool(checked)
                print(f"[toggle] op#{index} generate_gcode -> {checked}")
        except Exception as e:
            print("Failed to update generate_gcode:", e)

    def onToggleOptionalBlock(self, index, checked):
        """Update Python model when 'OptionalBlock' is toggled in QML."""
        if self.current_program is None:
            return
        if not (0 <= index < len(self.current_program.operations)):
            return
        try:
            op = self.current_program.operations[index]
            if hasattr(op, "is_optional_block"):
                op.is_optional_block = bool(checked)
                print(f"[toggle] op#{index} is_optional_block -> {checked}")
        except Exception as e:
            print("Failed to update is_optional_block:", e)

    def _get_current_op(self, index):
        if self.current_program is None:
            return None
        ops = getattr(self.current_program, "operations", [])
        if not (0 <= index < len(ops)):
            return None
        return ops[index]

    def onDetailsRequested(self, screen_item, index: int):
        """Build a full dict for the selected operation and push it into ChildScreen."""
        op = self._get_current_op(index)
        if op is None:
            return
        # Prefer dataclass .to_dict() for exact schema
        if hasattr(op, "to_dict"):
            data = op.to_dict()
        else:
            # fallback: minimal
            data = {
                "order": getattr(op, "order", 0),
                "type": getattr(op, "type", ""),
                "generate_gcode": bool(getattr(op, "generate_gcode", False)),
                "is_optional_block": bool(getattr(op, "is_optional_block", False)),
            }
            # hydrate nested if available
            tcd = getattr(op, "toolchange_details", None)
            if tcd:
                data["toolchange_details"] = {
                    "x_pos": getattr(tcd, "x_pos", 0.0),
                    "z_pos": getattr(tcd, "z_pos", 0.0),
                    "coordinate_type": getattr(tcd, "coordinate_type", "absolute"),
                    "move_sequence": getattr(tcd, "move_sequence", "xz"),
                    "stop_spindle": bool(getattr(tcd, "stop_spindle", False)),
                }
            # top-level tool props
            for k in ("tool_no", "tool_orientation", "back_angle", "front_angle"):
                if hasattr(op, k):
                    data[k] = getattr(op, k)

        # Call the QML method to load + apply data
        try:
            screen_item.receiveDetailsData(index, data)
        except Exception as e:
            print("receiveDetailsData failed:", e)

    def onUpdateToolChange(self, index: int, payload: dict):
        """Write the edited values back to the ChangeTool dataclass."""
        op = self._get_current_op(index)
        if op is None:
            return
        # Top-level fields
        for attr in ("order", "generate_gcode", "is_optional_block", "tool_no", "tool_orientation", "back_angle", "front_angle"):
            if attr in payload and hasattr(op, attr):
                try:
                    setattr(op, attr, payload[attr])
                except Exception:
                    pass
        # Nested toolchange_details
        tcd = getattr(op, "toolchange_details", None)
        if tcd and isinstance(payload.get("toolchange_details"), dict):
            d = payload["toolchange_details"]
            for attr in ("x_pos", "z_pos", "coordinate_type", "move_sequence", "stop_spindle"):
                if attr in d and hasattr(tcd, attr):
                    try:
                        setattr(tcd, attr, d[attr])
                    except Exception:
                        pass
        print(f"[save] ToolChange updated at index {index}: T{getattr(op, 'tool_no', '?')}")

    def onUpdateFacing(self, index: int, payload: dict):
        op = self._get_current_op(index)
        if op is None:
            return
        # only if it's actually a Facing
        if getattr(op, "type", "") != "facing":
            return
        # copy fields if present
        for attr in ("order", "generate_gcode", "is_optional_block",
                     "css_value", "max_speed", "feed_rate", "doc", "retract",
                     "x_start", "z_start", "x_end", "z_end", "z_end_becomes_new_z0"):
            if attr in payload and hasattr(op, attr):
                try:
                    setattr(op, attr, payload[attr])
                except Exception:
                    pass
        print(f"[save] Facing updated at index {index}")

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

    def goBack(self):
        print("back button clicked")
        self.root.goBack()
