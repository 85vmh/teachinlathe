"""What the conversational editor does to programs, without any screen.

Creating, opening, saving, duplicating and deleting programs; adding,
moving and editing their operations; turning one into G-code; and what the
editor's screens ask about a program - the profile an operation cuts, the
tool in by then, a preview of the cut. The view model calls this and keeps
only what is on screen.

Every edit is on the Program it is given. Saving it is a separate call, so
the view model decides when an edit is done.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

from teachinlathe.conversational.model.data_types import (
    AfterLastOperation,
    DefineProfile,
    DefineRadialProfile,
    Drilling,
    Facing,
    G33Threading,
    GrooveFinishing,
    GrooveRoughing,
    Header,
    Knurling,
    Parting,
    PredefinedPosition,
    ProfileContour,
    ProfileRoughing,
    Profiling,
    Program,
    Tapping,
    Threading,
    Workpiece,
    operation_types,
)
from teachinlathe.conversational.model.program_commands import (
    add_profiling_finish,
    create_new_program,
    delete_operation,
    delete_program_file,
    duplicate_operation,
    duplicate_program,
    insert_default_operation,
    move_operation,
)
from teachinlathe.conversational.model.qml_adapter import build_details_payload
from teachinlathe.conversational.model.updaters import (
    apply_cutting_update,
    apply_define_profile_update,
    apply_define_radial_profile_update,
    apply_drilling_update,
    apply_edge_break_update,
    apply_g33_threading_update,
    apply_geometry_update,
    apply_groove_finishing_cutting_update,
    apply_groove_finishing_parameters_update,
    apply_groove_roughing_cutting_update,
    apply_groove_roughing_parameters_update,
    apply_knurling_cutting_update,
    apply_m1_update,
    apply_operation_update,
    apply_parting_update,
    apply_position_details_update,
    apply_predefined_position_update,
    apply_profile_contour_strategy_update,
    apply_profile_roughing_strategy_update,
    apply_profiling_options_update,
    apply_profiling_parameters_update,
    apply_stock_to_leave_update,
    apply_tapping_update,
    apply_threading_update,
    apply_turnable_operation_update,
)
from teachinlathe.conversational.store.program_loader import load_programs_from_folder
from teachinlathe.conversational.store.program_store import save_program_to_disk
from teachinlathe.core.ini_repository import ini_repository

log = logging.getLogger(__name__)

#: Where the conversational programs are kept, one JSON file each.
PROGRAMS_DIR = "/home/cnc/Work/teachinlathe/conversational"

#: Where the DXF import screen looks for drawings, under [DISPLAY] PROGRAM_PREFIX
#: beside the conversational G-code and JSON folders.
DXF_PROFILE_SUBFOLDER = "DXF Profiles"

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def _set_if_given(op, payload, key, attr, convert):
    if key in payload and payload[key] is not None:
        setattr(op, attr, convert(payload[key]))


class ConversationalUseCase:
    def __init__(self, programs_dir: str = PROGRAMS_DIR, ini=None) -> None:
        self.programs_dir = programs_dir
        self._ini = ini_repository() if ini is None else ini
        # The edit each operation type takes, and the class it must be.
        self._updaters = {
            "changeTool": (None, self._update_tool_change),
            "positionAt": (None, self._update_position_at),
            "defineProfile": (DefineProfile, apply_define_profile_update),
            "defineRadialProfile": (DefineRadialProfile, apply_define_radial_profile_update),
            "facing": (Facing, self._update_facing),
            "profiling": (Profiling, self._update_profiling),
            "knurling": (Knurling, self._update_knurling),
            "profileRoughing": (ProfileRoughing, self._update_profile_roughing),
            "profileContour": (ProfileContour, self._update_profile_contour),
            "grooveRoughing": (GrooveRoughing, self._update_groove_roughing),
            "grooveFinishing": (GrooveFinishing, self._update_groove_finishing),
            "drilling": (Drilling, self._update_drilling),
            "parting": (Parting, self._update_parting),
            "tapping": (Tapping, self._update_tapping),
            "threading": (Threading, self._update_threading),
            "g33Threading": (G33Threading, self._update_g33_threading),
        }

    @property
    def dxf_profiles_dir(self) -> str:
        return os.path.join(self._ini.program_prefix, DXF_PROFILE_SUBFOLDER)

    # ── programs ────────────────────────────────────────────────────────────

    def load_programs(self) -> list[Program]:
        return load_programs_from_folder(self.programs_dir)

    def create_program(self) -> Program:
        program = create_new_program(self.programs_dir)
        save_program_to_disk(program, self.programs_dir)
        return program

    def duplicate_program(self, program: Program, existing_names) -> Program:
        new_program = duplicate_program(program, self.programs_dir, existing_names)
        save_program_to_disk(new_program, self.programs_dir)
        return new_program

    def delete_program(self, program: Program) -> None:
        delete_program_file(program)

    def load_program_file(self, json_path: str) -> Program:
        with open(json_path, "r", encoding="utf-8") as handle:
            program = Program.from_dict(json.load(handle))
        program.filename = json_path
        return program

    def save(self, program: Program) -> str:
        """Writes the program, stamped with when it was last edited."""
        now = datetime.now().strftime(TIMESTAMP_FORMAT)
        if not program.header.created_date:
            program.header.created_date = now
        program.header.last_edit = now
        return save_program_to_disk(program, self.programs_dir)

    def remember_last_operation(self, program: Program, op_index: int) -> None:
        """Stores the order of the open operation (0 for the header) so the
        program reopens there. Not an edit, so last_edit is left alone."""
        op = self.operation(program, op_index)
        last_operation = int(getattr(op, "order", 0) or 0) if op is not None else 0
        if program.header.last_operation == last_operation:
            return
        program.header.last_operation = last_operation
        try:
            save_program_to_disk(program, self.programs_dir)
        except Exception as e:
            log.error("failed to save the last operation: %s", e)

    @staticmethod
    def last_operation_index(program: Program) -> int:
        """Index of the operation whose order the header remembers, or -1 (header)."""
        last_operation = program.header.last_operation
        if last_operation:
            for i, op in enumerate(program.operations):
                if getattr(op, "order", None) == last_operation:
                    return i
        return -1

    def generate_gcode(self, program: Program) -> str:
        """Writes the program's G-code, and the copy of the program the
        Programs tab opens again for editing. Returns the .ngc path."""
        from teachinlathe.conversational.gcode import build_ngc_from_program

        gcode_dir, json_path = self.export_program(program)
        return build_ngc_from_program(program, output_dir=gcode_dir, source_json=json_path)

    def gcode_job(self, program: Program):
        """What building the program's G-code away from the application
        takes (plan_worker's ``generate_gcode``): the program, written out
        as for generate_gcode, and the Tool Library as it is now."""
        from teachinlathe.core.tool_library_repository import tool_library_repository
        from teachinlathe.tooling.model.tool_snapshot import ToolSnapshot

        gcode_dir, json_path = self.export_program(program)
        return program, gcode_dir, json_path, ToolSnapshot.of(tool_library_repository())

    def export_program(self, program: Program):
        """Writes the copy of the program the Programs tab opens again for
        editing; returns (the G-code folder, that copy's path)."""
        json_dir = self._ini.conversational_json_dir
        gcode_dir = self._ini.conversational_gcode_dir
        base_name = program.header.name or program.id or "program"
        base_name = "".join(c for c in str(base_name) if c.isalnum() or c in ("-", "_", " ")).strip()
        base_name = base_name.replace(" ", "_")
        current_json_path = os.path.abspath(program.filename or "")
        if current_json_path and os.path.dirname(current_json_path) == os.path.abspath(json_dir):
            json_path = current_json_path
        else:
            json_path = os.path.join(json_dir, base_name + ".json")

        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as handle:
            handle.write(program.to_json())

        # Deliberately not touching program.filename: that is the authoritative
        # path in programs_dir, the only place load_programs() reads at
        # startup. Repointing it here sent every later autosave into the
        # export folder, so edits made after generating G-code disappeared on
        # restart. The exported copy is passed as source_json instead, so the
        # .ngc still carries the ( Program: <file>.json ) comment that the
        # Programs screen reads to enable Edit.
        return gcode_dir, json_path

    # ── operations ──────────────────────────────────────────────────────────

    @staticmethod
    def operation(program: Optional[Program], index: int):
        if program is None or not (0 <= index < len(program.operations)):
            return None
        return program.operations[index]

    @staticmethod
    def is_operation_type(op_type: str) -> bool:
        return op_type in operation_types

    def insert_operation(self, program: Program, op_type: str, index: int) -> int:
        return insert_default_operation(program, op_type, index)

    def move_operation(self, program: Program, from_index: int, to_index: int) -> bool:
        return move_operation(program, from_index, to_index) is not None

    def delete_operation(self, program: Program, index: int) -> bool:
        return bool(delete_operation(program, index))

    def duplicate_operation(self, program: Program, index: int) -> int:
        """A copy of the operation, right after it. Returns where it went."""
        return duplicate_operation(program, index, index + 1)

    def add_profiling_finish(self, program: Program, index: int) -> int:
        return add_profiling_finish(program, index)

    def add_rest_roughing(self, program: Program, index: int) -> int:
        """For what the Profile Roughing at ``index`` leaves: right after it,
        a Change Tool with no tool chosen yet and a copy of the roughing set
        to rest material. Returns where the copy went."""
        source = self.operation(program, index)
        if not isinstance(source, ProfileRoughing):
            raise ValueError(f"operation {index} is not a Profile Roughing")
        change_index = insert_default_operation(program, "changeTool", index + 1)
        program.operations[change_index].tool_no = 0
        rest_index = duplicate_operation(program, index, change_index + 1)
        program.operations[rest_index].restMaterial = True
        return rest_index

    def use_tool_before(self, program: Program, op_index: int, tool_no: int,
                        toolchange_position: str = "G28") -> Optional[int]:
        """Have the operation at ``op_index`` cut with tool ``tool_no``: the
        Change Tool right above it changes to it, or one is put in right
        above it - going to ``toolchange_position`` ("G28" or "G30") for the
        change. Returns the operation's index afterwards, or None."""
        if op_index < 0 or tool_no <= 0:
            return None
        ops = program.operations
        try:
            position = PredefinedPosition(str(toolchange_position).upper())
        except ValueError:
            position = PredefinedPosition.G28
        if op_index > 0 and getattr(ops[op_index - 1], "type", "") == "changeTool":
            change = ops[op_index - 1]
        else:
            change = ops[insert_default_operation(program, "changeTool", op_index)]
            op_index += 1
        change.tool_no = int(tool_no)
        change.toolchange_position = position
        return op_index

    def set_generate_gcode(self, program: Program, index: int, checked: bool) -> bool:
        op = self.operation(program, index)
        if op is None:
            return False
        op.generate_gcode = bool(checked)
        return True

    def set_optional_block(self, program: Program, index: int, checked: bool) -> bool:
        op = self.operation(program, index)
        if op is None:
            return False
        op.is_optional_block = bool(checked)
        return True

    def update_operation(self, program: Program, op_type: str, index: int, payload: dict) -> bool:
        """Applies what an operation's editor sent. False when the operation
        at ``index`` is not one of ``op_type``."""
        op_class, update = self._updaters[op_type]
        op = self.operation(program, index)
        if op is None or (op_class is not None and not isinstance(op, op_class)):
            return False
        update(op, payload)
        if op_type in ("profileRoughing", "profileContour"):
            self._follow_profile_type(program, op, index)
        return True

    def update_header(self, program: Program, payload: dict) -> None:
        hdr = payload.get("header", payload)
        header = program.header

        if "name" in hdr:
            header.name = str(hdr["name"])
        if hdr.get("created_date") is not None:
            header.created_date = str(hdr["created_date"])
        if "units" in hdr:
            header.units = str(hdr["units"])
        if "datum" in hdr:
            try:
                header.datum = Header.datum_from_value(hdr["datum"])
            except Exception:
                pass
        if hdr.get("last_edit") is not None:
            header.last_edit = str(hdr["last_edit"])
        if hdr.get("after_last_operation") is not None:
            try:
                header.after_last_operation = AfterLastOperation(str(hdr["after_last_operation"]).lower())
            except ValueError:
                pass

        wp_payload = hdr.get("workpiece")
        if isinstance(wp_payload, dict):
            wp = header.workpiece
            if wp is None:
                wp = Workpiece(material="", external_diameter=0.0,
                               internal_diameter=0.0, stickout_length=0.0, stock_length=0.0)
            if "material" in wp_payload:
                wp.material = str(wp_payload["material"])
            for key in ("external_diameter", "internal_diameter", "stickout_length", "stock_length"):
                if key in wp_payload:
                    try:
                        setattr(wp, key, float(wp_payload[key]))
                    except Exception:
                        pass
            header.workpiece = wp

    def import_dxf_profile(self, program: Program, op_index: int, dxf_file_path: str) -> bool:
        """Reads the drawing into the Define Profile at ``op_index``. Raises
        when the drawing cannot be read; False when there is no such profile."""
        from teachinlathe.conversational.store.dxf_profile_importer import read_dxf_profile

        op = self.operation(program, op_index)
        if not isinstance(op, DefineProfile):
            return False
        payload = read_dxf_profile(str(dxf_file_path), **self._dxf_target(op, dxf_file_path))
        apply_define_profile_update(op, payload)
        if hasattr(op, "dxfFilePath"):
            op.dxfFilePath = str(dxf_file_path)
        return True

    def preview_dxf_profile(self, program: Program, op_index: int, dxf_file_path: str) -> dict:
        """The profile the drawing would give the Define Profile at ``op_index``."""
        try:
            from teachinlathe.conversational.store.dxf_profile_importer import read_dxf_profile

            op = self.operation(program, op_index)
            if not isinstance(op, DefineProfile):
                return {"ok": False, "error": "No DXF profile operation is active."}
            target = self._dxf_target(op, dxf_file_path)
            payload = read_dxf_profile(str(dxf_file_path), **target)
            return {
                "ok": True,
                "error": "",
                "profileType": payload.get("profile_type", target["profile_type"]),
                "primitives": payload.get("profile_primitives", []),
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "profileType": "od", "primitives": []}

    @staticmethod
    def _dxf_target(op, dxf_file_path):
        profile_type = getattr(op, "profile_type", "od")
        return {
            "profile_id": int(getattr(op, "profile_id", 1) or 1),
            "profile_type": profile_type.value if hasattr(profile_type, "value") else str(profile_type or "od"),
            "order": int(getattr(op, "order", 1) or 1),
            "operation_type": "importDxfProfile",
            "dxf_file_path": str(dxf_file_path),
        }

    # ── what the editor's screens show ──────────────────────────────────────

    def details_payload(self, program: Program, index: int) -> Optional[dict]:
        """What the details pane shows for the header (-1) or an operation."""
        if index == -1:
            return build_details_payload(program)
        op = self.operation(program, index)
        if op is None:
            return None
        data = self.with_workpiece(program, build_details_payload(op))
        if not data:
            return None
        # the way the tool in by then turns - the last Change Tool's - which
        # is the only way the operation's spindle may turn: 3 (M3), 4 (M4),
        # 0 with none
        try:
            from teachinlathe.ui.tabs.programs.backplot import tool_source
            change = self.change_tool_before(program, index)
            tool = tool_source.tool_in(int(change.tool_no)) if change is not None else None
            data["_tool_spindle_direction"] = int(tool.spindle_direction) if tool is not None else 0
        except Exception as e:
            log.error("tool spindle direction failed: %s", e)
        if getattr(op, "type", "") == "changeTool":
            # The tool already in by then: changing to it again is no change.
            previous = self.change_tool_before(program, index)
            data["previous_tool_no"] = int(previous.tool_no) if previous is not None else 0
        return data

    def operation_payload(self, program: Program, index: int) -> dict:
        """An operation as its editor gets it, with the workpiece for profiles."""
        op = self.operation(program, index)
        return self.with_workpiece(program, build_details_payload(op)) if op is not None else {}

    @staticmethod
    def with_workpiece(program: Optional[Program], payload):
        """A profile's payload carries the program's workpiece, for the drawing."""
        if not isinstance(payload, dict) or payload.get("type") not in ("defineProfile", "importDxfProfile"):
            return payload
        workpiece = program.header.workpiece if program is not None else None
        if workpiece is not None and hasattr(workpiece, "to_dict"):
            enriched = dict(payload)
            enriched["workpiece"] = workpiece.to_dict()
            return enriched
        return payload

    @staticmethod
    def workpiece(program: Optional[Program]) -> dict:
        """The program header's workpiece, as its dict, or {}."""
        workpiece = program.header.workpiece if program is not None else None
        return workpiece.to_dict() if workpiece is not None and hasattr(workpiece, "to_dict") else {}

    @staticmethod
    def resolve_profile_type(program: Optional[Program], profile_id, before_index=None):
        """The ProfilingType of the DefineProfile with the given id, or None."""
        if program is None or not profile_id:
            return None
        operations = program.operations
        if before_index is not None and before_index >= 0:
            operations = operations[:before_index]
        for op in operations:
            if isinstance(op, DefineProfile) and int(op.profile_id) == int(profile_id):
                return op.profile_type
        return None

    def last_profile_before(self, program: Optional[Program], before_index: int) -> dict:
        """The last DefineProfile above ``before_index``, as its details payload, or {}."""
        if program is None:
            return {}
        for op in reversed(program.operations[:max(before_index, 0)]):
            if isinstance(op, DefineProfile):
                return self.with_workpiece(program, build_details_payload(op)) or {}
        return {}

    @staticmethod
    def change_tool_before(program: Optional[Program], before_index: int):
        """The last Change Tool above ``before_index``, or None."""
        if program is None:
            return None
        return next((o for o in reversed(program.operations[:max(before_index, 0)])
                     if getattr(o, "type", "") == "changeTool"), None)

    def tool_before(self, program: Optional[Program], before_index: int) -> dict:
        """The tool the last Change Tool above ``before_index`` puts in, as
        the backplot describes it (ui/tabs/programs/backplot/tool_source.py) with
        its ``tool_no``, or {} with none."""
        from teachinlathe.ui.tabs.programs.backplot import tool_source
        change = self.change_tool_before(program, before_index)
        if change is None:
            return {}
        tool = dict(tool_source.describe(int(change.tool_no)) or {})
        tool["tool_no"] = int(change.tool_no)
        return tool

    @staticmethod
    def facing_preview(op_data: dict) -> dict:
        """What a Facing would cut with ``op_data``; see build_facing_preview."""
        from teachinlathe.conversational.gcode.operations.facing_preview import build_facing_preview
        return build_facing_preview(op_data)

    def profile_roughing_preview(self, program, op_index: int, op_data: dict) -> dict:
        """What the Profile Roughing at ``op_index`` would cut with ``op_data``,
        against the last profile above it; see build_profile_roughing_preview.
        Worked out here, on the caller's thread - the editor has it done in
        the planning worker (plan_worker) instead."""
        from teachinlathe.conversational.gcode.operations.profile_roughing_preview import (
            build_profile_roughing_preview,
        )
        return build_profile_roughing_preview(self.resolve_profile_roughing(program, op_index, op_data))

    def resolve_profile_roughing(self, program, op_index: int, op_data: dict) -> dict:
        """``op_data`` with all its preview needs from the program: the
        profile, the tool - and for rest material the roughings above it.
        Plain values only, so it can go to the planning worker as it is."""
        op_data = dict(op_data)
        op_data["_resolved_profile"] = self.last_profile_before(program, op_index)
        op_data["_resolved_cutting_tool"] = self.cutting_tool_before(program, op_index)
        if op_data.get("rest_material"):
            op_data["_resolved_previous_roughing"] = self.roughings_before(program, op_index)
        return op_data

    def roughings_before(self, program: Optional[Program], before_index: int) -> list:
        """The Profile Roughings above ``before_index`` that cut the same
        profile as the one there, in order, each as an operation dict with its
        profile and tool resolved - what a rest roughing starts from."""
        if program is None:
            return []
        ops = program.operations
        own = ops[before_index] if 0 <= before_index < len(ops) else None
        profile_id = int(getattr(getattr(own, "profilingParameters", None), "profile_id", 0) or 0)
        out = []
        for index, op in enumerate(ops[:max(before_index, 0)]):
            if not isinstance(op, ProfileRoughing):
                continue
            if int(getattr(op.profilingParameters, "profile_id", 0) or 0) != profile_id:
                continue
            data = op.to_dict()
            data["_resolved_profile"] = self.last_profile_before(program, index)
            data["_resolved_cutting_tool"] = self.cutting_tool_before(program, index)
            out.append(data)
        return out

    def cutting_tool_before(self, program: Optional[Program], before_index: int) -> dict:
        """The cutting tool the last Change Tool above ``before_index`` puts
        in, as the Tool Library stores it (CuttingTool.to_json); {} with none."""
        change = self.change_tool_before(program, before_index)
        if change is None:
            return {}
        from teachinlathe.ui.tabs.programs.backplot import tool_source
        try:
            tool = tool_source.tool_in(int(change.tool_no))
        except Exception:
            return {}
        return tool.to_json() if tool is not None else {}

    def profile_contour_preview(self, program, op_index: int, op_data: dict) -> dict:
        """What the Profile Contour at ``op_index`` would cut with ``op_data``,
        against the last profile above it; see build_profile_contour_preview."""
        from teachinlathe.conversational.gcode.operations.profile_contour_preview import (
            build_profile_contour_preview,
        )
        op_data["_resolved_profile"] = self.last_profile_before(program, op_index)
        return build_profile_contour_preview(op_data)

    # ── the edit each operation type takes ──────────────────────────────────

    @staticmethod
    def _update_tool_change(op, p):
        apply_operation_update(op, p)
        for key in ("tool_no", "tool_orientation", "back_angle", "front_angle"):
            _set_if_given(op, p, key, key, int)
        apply_predefined_position_update(op, p, "toolchange_position")

    @staticmethod
    def _update_position_at(op, p):
        apply_operation_update(op, p)
        apply_position_details_update(getattr(op, "position_details", None), p.get("position_details"))

    @staticmethod
    def _update_facing(op, p):
        apply_turnable_operation_update(op, p)
        apply_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
        apply_geometry_update(op.geometryParameters, p.get("geometry_parameters"))
        apply_m1_update(op.m1Parameters, p.get("m1_parameters"))
        _set_if_given(op, p, "z_end_becomes_new_z0", "zEndBecomesNewZ0", bool)

    @staticmethod
    def _update_profiling(op, p):
        apply_turnable_operation_update(op, p)
        apply_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
        apply_profiling_parameters_update(op.profilingParameters, p.get("profiling_parameters"))
        apply_profiling_options_update(op.profilingOptions, p.get("profiling_options"))

    @staticmethod
    def _update_knurling(op, p):
        apply_turnable_operation_update(op, p)
        apply_knurling_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
        apply_geometry_update(op.geometryParameters, p.get("geometry_parameters"))
        apply_m1_update(op.m1Parameters, p.get("m1_parameters"))

    @staticmethod
    def _update_profile_roughing(op, p):
        apply_turnable_operation_update(op, p)
        apply_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
        apply_profiling_parameters_update(op.profilingParameters, p.get("profiling_parameters"))
        apply_profile_roughing_strategy_update(op.profileRoughingStrategy, p.get("profile_roughing_strategy"))
        apply_stock_to_leave_update(op.stockToLeave, p.get("stock_to_leave"))
        apply_m1_update(op.m1Parameters, p.get("m1_parameters"))
        _set_if_given(op, p, "rest_material", "restMaterial", bool)

    @staticmethod
    def _update_profile_contour(op, p):
        apply_turnable_operation_update(op, p)
        apply_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
        apply_profiling_parameters_update(op.profilingParameters, p.get("profiling_parameters"))
        apply_profile_contour_strategy_update(op.profileContourStrategy, p.get("profile_contour_strategy"))
        apply_stock_to_leave_update(op.stockToLeave, p.get("stock_to_leave"))
        _set_if_given(op, p, "stock_to_leave_enabled", "stockToLeaveEnabled", bool)

    def _follow_profile_type(self, program, op, index):
        """A roughing or contour pass cuts OD or ID as the profile it follows is."""
        profile_id = int(getattr(op.profilingParameters, "profile_id", 0) or 0)
        resolved_type = self.resolve_profile_type(program, profile_id, index)
        if resolved_type is None:
            return
        if isinstance(op, ProfileRoughing):
            op.profileRoughingStrategy.profiling_type = resolved_type
        else:
            op.profileContourStrategy.profiling_type = resolved_type

    @staticmethod
    def _update_groove_roughing(op, p):
        apply_turnable_operation_update(op, p)
        apply_groove_roughing_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
        apply_groove_roughing_parameters_update(op.roughingParameters, p.get("roughing_parameters"))
        apply_stock_to_leave_update(op.stockToLeave, p.get("stock_to_leave"))
        _set_if_given(op, p, "stock_to_leave_enabled", "stockToLeaveEnabled", bool)
        apply_m1_update(op.m1Parameters, p.get("m1_parameters"))

    @staticmethod
    def _update_groove_finishing(op, p):
        apply_turnable_operation_update(op, p)
        apply_groove_finishing_cutting_update(op.cuttingParameters, p.get("cutting_parameters"))
        apply_groove_finishing_parameters_update(op.finishingParameters, p.get("finishing_parameters"))

    @staticmethod
    def _update_drilling(op, p):
        apply_turnable_operation_update(op, p)
        apply_drilling_update(op.drillingParameters, p.get("drilling_parameters"))
        apply_m1_update(op.m1Parameters, p.get("m1_parameters"))

    @staticmethod
    def _update_parting(op, p):
        apply_turnable_operation_update(op, p)
        apply_parting_update(op.partingParameters, p.get("parting_parameters"))
        apply_edge_break_update(op.edgeBreak, p.get("edge_break"))

    @staticmethod
    def _update_tapping(op, p):
        apply_turnable_operation_update(op, p)
        apply_tapping_update(op.tappingParameters, p.get("tapping_parameters"))
        apply_m1_update(op.m1Parameters, p.get("m1_parameters"))

    @staticmethod
    def _update_threading(op, p):
        apply_turnable_operation_update(op, p)
        apply_threading_update(op, p)

    @staticmethod
    def _update_g33_threading(op, p):
        apply_turnable_operation_update(op, p)
        apply_g33_threading_update(op, p)
        apply_m1_update(op.m1Parameters, p.get("m1_parameters"))
