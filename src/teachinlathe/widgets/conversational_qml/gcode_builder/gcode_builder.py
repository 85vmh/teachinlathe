import json
import os
from datetime import datetime

from teachinlathe.conversational.data_types import (
    AfterLastOperation,
    DefineProfile,
    DefineRadialProfile,
    Program,
)
from teachinlathe.conversational.qml_adapter import display_name_for_op
from teachinlathe.widgets.tool_library.tool_entry import ToolType, make_tool
from teachinlathe.widgets.tool_library.tool_extras_store import ToolExtrasStore
from teachinlathe.widgets.tool_library.tool_table_file import parse_tbl

from .operations import OPERATION_GENERATORS



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


def _resolve_previous_tool_change(operations, before_index=None):
    search_ops = operations
    if before_index is not None and before_index >= 0:
        search_ops = operations[:before_index]
    for op in reversed(search_ops):
        if getattr(op, "type", None) == "changeTool":
            return op
    return None


def _tool_table_path():
    try:
        from qtpyvcp.utilities.info import Info
        return Info().getToolTableFile()
    except Exception:
        return ""


def _resolve_tool_payload(tool_no, fallback_orientation=0):
    if not tool_no:
        return {}
    path = _tool_table_path()
    if not path or not os.path.isfile(path):
        return {"t": int(tool_no), "q": int(fallback_orientation or 0)}
    try:
        extras_store = ToolExtrasStore(path)
        for base in parse_tbl(path):
            if int(base.t) != int(tool_no):
                continue
            extras = extras_store.get(base.t)
            try:
                tool_type = ToolType(extras.get("tool_type", ToolType.GENERIC.value))
            except ValueError:
                tool_type = ToolType.GENERIC
            tool = make_tool(base, tool_type, extras)
            return tool.to_display_dict()
    except Exception as exc:
        print(f"[gcode_builder] tool lookup failed for T{tool_no}: {exc}")
    return {"t": int(tool_no), "q": int(fallback_orientation or 0)}



def _build_operation_payload(op, program, op_index=None):
    payload = op.to_dict()
    if op.type in ("profileRoughing", "profileContour"):
        profile_id = int(getattr(op.profilingParameters, "profile_id", 0) or 0)
        profile_op = _resolve_profile_operation(profile_id, program.operations, op_index)
        payload["_resolved_profile"] = profile_op.to_dict() if profile_op else {}
    if op.type in ("grooveRoughing", "grooveFinishing"):
        if op.type == "grooveFinishing":
            profile_id = int(getattr(op.finishingParameters, "profile_id", 0) or 0)
        else:
            profile_id = int(getattr(op.roughingParameters, "profile_id", 0) or 0)
        profile_op = _resolve_radial_profile_operation(profile_id, program.operations, op_index)
        payload["_resolved_radial_profile"] = profile_op.to_dict() if profile_op else {}
        tool_change = _resolve_previous_tool_change(program.operations, op_index)
        if tool_change is not None:
            payload["_resolved_tool_change"] = tool_change.to_dict()
            payload["_resolved_tool"] = _resolve_tool_payload(
                getattr(tool_change, "tool_no", 0),
                getattr(tool_change, "tool_orientation", 0),
            )
    return payload


def _display_name_for_operation(op):
    op_type = getattr(op, "type", "")
    tool_no = getattr(op, "tool_no", None)
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
        tool_no=tool_no,
        pitch=pitch,
        profile_id=profile_id,
        strategy=strategy,
        profiling_type=profiling_type,
        profile_type=profile_type,
    )



def build_ngc_from_program(program: Program, output_dir=None, output_path=None, source_json=None):
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
    lines.append("")

    datum = int(program.header.datum)
    operations = program.operations
    for index, op in enumerate(operations, 1):
        if not bool(op.generate_gcode):
            continue

        op_display = _display_name_for_operation(op)
        lines.append(_format_comment(f"----------Operation #{index}: {op_display}----------") + "\n")

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
