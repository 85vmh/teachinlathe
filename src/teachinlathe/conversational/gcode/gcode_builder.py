import json
import logging
import os
from datetime import datetime

from teachinlathe.conversational.model.data_types import (
    AfterLastOperation,
    DefineProfile,
    DefineRadialProfile,
    Program,
)
from teachinlathe.conversational.logic import program_tools
from teachinlathe.conversational.model.qml_adapter import display_name_for_op, axial_tool_label

from .operations import OPERATION_GENERATORS
from .operations.change_tool import generate_change_tool_gcode

log = logging.getLogger(__name__)


def _after_last_operation(header):
    """What the program does after the last operation, tolerating a raw string."""
    value = getattr(header, "after_last_operation", AfterLastOperation.DO_NOTHING)
    if isinstance(value, AfterLastOperation):
        return value
    try:
        return AfterLastOperation(str(value).lower())
    except ValueError:
        return AfterLastOperation.DO_NOTHING


def _safe_program_name(program):
    if isinstance(program, Program):
        name = getattr(program.header, "name", None) or program.id
    else:
        header = program.get("header", {}) if isinstance(program, dict) else {}
        name = header.get("name", program.get("id", "program"))
    safe = "".join(c for c in str(name) if c.isalnum() or c in ("-", "_", " ")).strip()
    return safe.replace(" ", "_")


def _format_creation_date(dt: datetime) -> str:
    return f"{dt.day} {dt.strftime('%b %Y, %H:%M:%S')}"


def _format_comment(text: str) -> str:
    clean = str(text).replace("(", "").replace(")", "")
    return f"( {clean} )"


def _code_comment(code: str, comment: str) -> str:
    return f"{code}{' ' * max(1, 5 - len(code))}({comment})"



def _define_profile_needs_subroutine(profile_id, operations):
    if not profile_id:
        return False

    for op in operations:
        if getattr(op, "type", None) != "profiling":
            continue
        if not bool(getattr(op, "generate_gcode", True)):
            continue
        params = getattr(op, "profilingParameters", None)
        if params and int(params.profile_id or 0) == profile_id:
            return True

    return False



def _resolve_profile_operation(profile_id, operations, before_index=None):
    if not profile_id:
        return None
    search_ops = operations
    if before_index is not None and before_index >= 0:
        search_ops = operations[:before_index]
    for op in search_ops:
        if isinstance(op, DefineProfile) and int(op.profile_id) == profile_id:
            return op
    return None


def _resolve_radial_profile_operation(profile_id, operations, before_index=None):
    if not profile_id:
        return None
    search_ops = operations
    if before_index is not None and before_index >= 0:
        search_ops = operations[:before_index]
    for op in search_ops:
        if isinstance(op, DefineRadialProfile) and int(op.profile_id) == profile_id:
            return op
    return None


def _resolve_groove_roughing_stock(profile_id, operations, before_index=None):
    """The stock the last Groove Roughing of radial profile ``profile_id``
    above ``before_index`` leaves - what a Groove Finishing takes off - as
    {"radial", "axial"}; both 0 with none, or none left."""
    search_ops = operations
    if before_index is not None and before_index >= 0:
        search_ops = operations[:before_index]
    for op in reversed(search_ops):
        if (getattr(op, "type", None) == "grooveRoughing"
                and int(getattr(op.roughingParameters, "profile_id", 0) or 0) == profile_id):
            if not getattr(op, "stockToLeaveEnabled", False):
                break
            return {"radial": abs(float(op.stockToLeave.stockToLeaveX or 0.0)),
                    "axial": abs(float(op.stockToLeave.stockToLeaveZ or 0.0))}
    return {"radial": 0.0, "axial": 0.0}


def _holder_of(program, op):
    """The T number of the tool ``op`` cuts with, 0 with none."""
    tool = program.tool_of(op)
    return int(tool.tool_holder_id) if tool is not None else 0


#: Where tools are looked up while a program is built: a ToolSnapshot when
#: building away from the application (plan_worker), else the Tool Library.
_TOOLS = None


def _tools():
    if _TOOLS is not None:
        return _TOOLS
    from teachinlathe.core.tool_library_repository import tool_library_repository
    return tool_library_repository()


def _resolve_mounted_tool(tool_no):
    """The tool in holder ``tool_no`` as mounted (a MountedTool) - what a
    groove operation cuts with - from the Tool Library; None with none."""
    if not tool_no:
        return None
    from teachinlathe.tooling.model.data_types import MountedTool
    try:
        return MountedTool.of(_tools(), int(tool_no))
    except Exception as exc:
        log.warning("Tool lookup failed for T%s: %s", tool_no, exc)
        return None


def _resolve_cutting_tool(tool_no):
    """The cutting tool in holder ``tool_no`` - what Profile Roughing plans
    its moves with; None with none."""
    if not tool_no:
        return None
    try:
        return _tools().tool_in(int(tool_no))
    except Exception as exc:
        log.warning("Tool lookup failed for T%s: %s", tool_no, exc)
        return None


def _resolve_tap_pitch(program, op):
    """The pitch of the tap ``op`` cuts with, from the Tool Library; None
    when it is not a tap or cannot be found."""
    from teachinlathe.tooling.model.data_types import TappingTool
    tool_no = _holder_of(program, op)
    if not tool_no:
        return None
    tool = _tools().tool_in(tool_no)
    if not isinstance(tool, TappingTool) or tool.pitch <= 0:
        return None
    return float(tool.pitch)


def _build_operation_payload(op, program, op_index=None):
    payload = op.to_dict()
    if op.type in ("profileRoughing", "profileContour"):
        profile_id = int(getattr(op.profilingParameters, "profile_id", 0) or 0)
        profile_op = _resolve_profile_operation(profile_id, program.operations, op_index)
        payload["_resolved_profile"] = profile_op.to_dict() if profile_op else {}
        # the insert both plan with
        payload["_resolved_cutting_tool"] = _resolve_cutting_tool(_holder_of(program, op))
    if op.type == "profileRoughing":
        if getattr(op, "restMaterial", False):
            # what it starts from: the roughings of the same profile above it
            profile_id = int(getattr(op.profilingParameters, "profile_id", 0) or 0)
            payload["_resolved_previous_roughing"] = [
                _build_operation_payload(prev, program, index)
                for index, prev in enumerate(program.operations[:op_index or 0])
                if prev.type == "profileRoughing"
                and int(getattr(prev.profilingParameters, "profile_id", 0) or 0) == profile_id]
    if op.type in ("grooveRoughing", "grooveFinishing"):
        if op.type == "grooveFinishing":
            profile_id = int(getattr(op.finishingParameters, "profile_id", 0) or 0)
        else:
            profile_id = int(getattr(op.roughingParameters, "profile_id", 0) or 0)
        profile_op = _resolve_radial_profile_operation(profile_id, program.operations, op_index)
        payload["_resolved_radial_profile"] = profile_op.to_dict() if profile_op else {}
        if op.type == "grooveFinishing":
            payload["_resolved_roughing_stock"] = _resolve_groove_roughing_stock(
                profile_id, program.operations, op_index)
        payload["_resolved_tool"] = _resolve_mounted_tool(_holder_of(program, op))
    return payload


def _display_name_for_operation(op, program=None):
    op_type = getattr(op, "type", "")
    pitch = getattr(op, "pitch", None)
    profile_id = getattr(getattr(op, "profilingParameters", None), "profile_id", None)
    if profile_id is None:
        profile_id = getattr(getattr(op, "roughingParameters", None), "profile_id", None)
    if profile_id is None:
        profile_id = getattr(getattr(op, "finishingParameters", None), "profile_id", None)
    if profile_id is None:
        profile_id = getattr(op, "profile_id", None)
    strategy = getattr(getattr(op, "profilingOptions", None), "strategy", None)
    profiling_type = getattr(getattr(op, "profileRoughingStrategy", None), "profiling_type", None)
    if profiling_type is None:
        profiling_type = getattr(getattr(op, "profileContourStrategy", None), "profiling_type", None)
    if profiling_type is not None and hasattr(profiling_type, "value"):
        profiling_type = profiling_type.value
    profile_type = getattr(op, "profile_type", None)
    return display_name_for_op(
        op_type,
        pitch=pitch,
        profile_id=profile_id,
        strategy=strategy,
        profiling_type=profiling_type,
        profile_type=profile_type,
        tool_label=axial_tool_label(op, program) if program is not None else None,
        rest=bool(getattr(op, "restMaterial", False)),
    )



class ToolsNotReady(ValueError):
    """The program's tools are not all as chosen: no G-code until they are."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def build_ngc_from_program(program: Program, output_dir=None, output_path=None, source_json=None,
                           tools=None):
    """Writes the program's .ngc and returns its path. ``tools``: a
    ToolSnapshot to look tools up in instead of the Tool Library. Raises
    ToolsNotReady, writing nothing, while an operation that cuts has no tool
    or one the Tool Library no longer has as it was."""
    global _TOOLS
    _TOOLS = tools
    try:
        problems = program_tools.not_ready(program, _tools())
        if problems:
            raise ToolsNotReady(problems)
        return _build_ngc(program, output_dir, output_path, source_json)
    finally:
        _TOOLS = None


def _build_ngc(program, output_dir, output_path, source_json):
    if not isinstance(program, Program):
        raise TypeError("build_ngc_from_program expects a parsed Program")

    # The ( Program: <file>.json ) comment is what the Programs screen reads to
    # re-open a generated .ngc for editing, so it must name the JSON sitting in
    # the export folder. Callers that export a copy pass it as source_json;
    # program.filename stays pointed at the authoritative program file.
    source_name = source_json or getattr(program, "filename", "") or ""
    program_name = os.path.basename(source_name) or getattr(program.header, "name", program.id)
    safe_name = _safe_program_name(program)

    if output_path:
        ngc_path = output_path
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
    else:
        target_dir = output_dir or os.getcwd()
        os.makedirs(target_dir, exist_ok=True)
        ngc_path = os.path.join(target_dir, safe_name + ".ngc")

    lines = []
    lines.append("( Generated by TeachInLathe Conversational)")
    lines.append(_format_comment(f"Program: {program_name}"))
    lines.append(_format_comment(f"Creation Date: {_format_creation_date(datetime.now())}"))
    lines.append("G21  (mm)")
    lines.append("G7   (diameter mode)")
    lines.append("G90  (absolute distance mode)")
    lines.append("G95  (feed per rev)")
    lines.append("G18  (ZX plane)")
    lines.append(f"{program.header.datum_code}  (workpiece coordinate offset)")
    lines.append("")

    datum = int(program.header.datum)
    operations = program.operations
    # the T number in the spindle so far; 0 before the first tool change
    loaded_tool = 0
    for index, op in enumerate(operations, 1):
        if not bool(op.generate_gcode):
            continue

        op_display = _display_name_for_operation(op, program)
        lines.append(_format_comment(f"----------Operation #{index}: {op_display}----------") + "\n")

        # a tool change where the tool differs from the one before. Never a
        # "/" block, even for an optional operation: skipped, the operations
        # after it would cut with the wrong tool.
        tool = program.tool_of(op) if program_tools.needs_tool(op) else None
        if tool is not None and tool.tool_holder_id != loaded_tool:
            lines.extend(generate_change_tool_gcode(tool.tool_holder_id, tool.toolchange_position))
            lines.append("")
            loaded_tool = tool.tool_holder_id

        if op.type in ("defineProfile", "importDxfProfile"):
            if not _define_profile_needs_subroutine(int(op.profile_id or 0), operations):
                lines.append("; The drawn profile is represented in the custom profiling section.")
                lines.append("")
                continue
        if op.type == "defineRadialProfile":
            lines.append("; The radial profile is represented in the conversational JSON.")
            lines.append("")
            continue

        generator = OPERATION_GENERATORS.get(op.type)
        if generator:
            if op.type in ("profileRoughing", "profileContour", "grooveRoughing", "grooveFinishing"):
                lines.extend(generator(_build_operation_payload(op, program, index - 1)))
            elif op.type == "facing":
                lines.extend(generator(op, datum=datum))
            elif op.type == "tapping":
                lines.extend(generator(op, pitch=_resolve_tap_pitch(program, op)))
            else:
                lines.extend(generator(op))
        else:
            lines.append(f"( TODO: gcode generator for type={op.type} )")
        lines.append("")
    lines.append("")
    lines.append(_code_comment("M5", "stop the spindle"))
    lines.append("")
    after_last = _after_last_operation(program.header)
    if after_last.gcode:
        lines.append(_code_comment(after_last.gcode, "rapid move to predefined position"))
    lines.append(_code_comment("M30", "end program"))

    with open(ngc_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return ngc_path



def build_ngc_from_json(json_path, output_dir=None):
    if not json_path or not os.path.isfile(json_path):
        raise FileNotFoundError(f"Program JSON not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as handle:
        program_dict = json.load(handle)

    program = Program.from_dict(program_dict)
    program.filename = json_path

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, os.path.splitext(os.path.basename(json_path))[0] + ".ngc")
    else:
        output_path = os.path.splitext(json_path)[0] + ".ngc"

    return build_ngc_from_program(program, output_path=output_path)
