import json
import logging
import os
from datetime import datetime

from teachinlathe.conversational.model.data_types import (
    AfterLastOperation,
    DefineProfile,
    DefineRadialProfile,
    Drilling,
    Facing,
    G33Threading,
    GrooveFinishing,
    GrooveRoughing,
    ImportDxfProfile,
    Knurling,
    Parting,
    PositionAt,
    ProfileContour,
    ProfileRoughing,
    Profiling,
    Program,
    Tapping,
    Threading,
)
from teachinlathe.conversational.logic import program_tools
from teachinlathe.conversational.model.operation_titles import operation_title
from teachinlathe.tooling.model.tool_titles import list_title

from .operations import (
    drilling_toolpath, facing_toolpath, g33_threading_toolpath, generate_define_profile_gcode,
    generate_knurling_gcode, groove_finishing_toolpath, groove_roughing_toolpath,
    generate_profiling_gcode, parting_toolpath, position_at_toolpath, tapping_toolpath,
    profile_contour_toolpath, profile_roughing_toolpath,
    generate_threading_gcode,
)
from .toolpath import GcodeEmitter

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


def _define_profile_needs_subroutine(profile_id, operations):
    if not profile_id:
        return False

    for op in operations:
        if not isinstance(op, Profiling):
            continue
        if not bool(getattr(op, "generate_gcode", True)):
            continue
        params = getattr(op, "profilingParameters", None)
        if params and int(params.profile_id or 0) == profile_id:
            return True

    return False



def _holder_of(program, op):
    """The T number of the tool ``op`` cuts with, 0 with none."""
    tool = program.tool_of(op)
    return int(tool.tool_holder_id) if tool is not None else 0


# Where a program's tools are looked up, ``tools`` here: anything with
# tool_in(holder), find_holder(holder) - the Tool Library, a ToolSnapshot.
# The caller gives it: nothing here reaches for the Tool Library itself.


def _resolve_tap_pitch(program, op, tools):
    """The pitch of the tap ``op`` cuts with, from ``tools``; None when it
    is not a tap or cannot be found."""
    from teachinlathe.tooling.model.data_types import TappingTool
    tool_no = _holder_of(program, op)
    if not tool_no:
        return None
    tool = tools.tool_in(tool_no)
    if not isinstance(tool, TappingTool) or tool.pitch <= 0:
        return None
    return float(tool.pitch)


class ToolsNotReady(ValueError):
    """The program's tools are not all as chosen: no G-code until they are."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def build_ngc_from_program(program: Program, tools, output_dir=None, output_path=None, source_json=None):
    """Writes the program's .ngc and returns its path, its tools looked up
    in ``tools``. Raises ToolsNotReady, writing nothing, while an operation
    that cuts has no tool or one ``tools`` no longer has as it was."""
    problems = program_tools.not_ready(program, tools)
    if problems:
        raise ToolsNotReady(problems)
    return _build_ngc(program, tools, output_dir, output_path, source_json)


def _build_ngc(program, tools, output_dir, output_path, source_json):
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

    path = program_toolpath(program, tools, program_name)
    with open(ngc_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(path.lines))

    return ngc_path


def program_toolpath(program: Program, tools, program_name: str = "") -> GcodeEmitter:
    """``program`` written on one GcodeEmitter: its G-code (``lines``) and,
    operation by operation, what each moves (``operations``, an
    OperationPath each). Where the machine is is carried from one operation
    to the next, but for what is not known there: after a tool change, an
    optional operation, and an operation whose moves are not on the emitter.
    Tools are looked up in ``tools``, as build_ngc_from_program looks them up."""
    path = GcodeEmitter()
    path.code("( Generated by TeachInLathe Conversational)")
    path.code(_format_comment(f"Program: {program_name or program.header.name}"))
    path.code(_format_comment(f"Creation Date: {_format_creation_date(datetime.now())}"))
    path.code("G21  (mm)")
    path.code("G7   (diameter mode)")
    path.code("G90  (absolute distance mode)")
    path.code("G95  (feed per rev)")
    path.code("G18  (ZX plane)")
    path.code(f"{program.header.datum_code}  (workpiece coordinate offset)")
    path.blank()

    operations = program.operations
    # the T number in the spindle so far; 0 before the first tool change
    loaded_tool = 0
    for index, op in enumerate(operations, 1):
        if not bool(op.generate_gcode):
            continue

        op_display = operation_title(op, program, tools)
        path.code(_format_comment(f"----------Operation #{index}: {op_display}----------") + "\n")

        # a tool change where the tool differs from the one before. Never a
        # "/" block, even for an optional operation: skipped, the operations
        # after it would cut with the wrong tool.
        tool = program.tool_of(op) if program_tools.needs_tool(op) else None
        if tool is not None and tool.tool_holder_id != loaded_tool:
            # G28/G30 (toolchange_position) are kept on the tool but not used: M6
            # goes to the machine's tool change position
            path.tool_change(tool.tool_holder_id, list_title(tools.tool_in(tool.tool_holder_id)))
            path.blank()
            loaded_tool = tool.tool_holder_id

        with path.operation(index - 1, bool(op.is_optional_block), loaded_tool if tool else 0):
            _write_operation(path, op, program, index - 1, tools)
        path.blank()
    path.blank()
    path.code_comment("M5", "stop the spindle")
    path.blank()
    after_last = _after_last_operation(program.header)
    if after_last.gcode:
        path.code_comment(after_last.gcode, "rapid move to predefined position")
        path.forget_position()
    path.code_comment("M30", "end program")
    return path


def _write_operation(path, op, program, op_index, tools):
    """Operation ``op``, at ``op_index`` of ``program``, onto ``path``, by
    the writer of its class (_WRITERS); its tools looked up in ``tools``."""
    writer = _WRITERS.get(type(op))
    if writer is None:
        path.foreign([_format_comment(f"TODO: no G-code for {type(op).__name__}")])
        return
    writer(path, op, program, op_index, tools)


# ── how each operation is written onto the program's emitter ───────────────
# Every writer is (path, op, program, op_index, tools). An operation whose generator
# is on the emitter writes its moves onto it; the others give their lines,
# which the emitter takes as they are (GcodeEmitter.foreign).

def _on_emitter(toolpath):
    """For a generator on the emitter: toolpath(op, path, program)."""
    return lambda path, op, program, op_index, tools: toolpath(op, path, program)


def _lines(generator):
    """For a generator of lines from the operation alone."""
    return lambda path, op, program, op_index, tools: path.foreign(generator(op))


def _cut_on_emitter(toolpath):
    """For a Profile Roughing's or Contour's generator on the emitter, from
    what it is cut against in the program (a ProfileCut): toolpath(cut, path)."""
    from .operations.profiling.operation_input import profile_cut
    return lambda path, op, program, op_index, tools: toolpath(profile_cut(program, op_index, op, tools), path)


def _groove_on_emitter(toolpath):
    """For a Groove Roughing's or Finishing's generator on the emitter, from
    what it is cut against in the program (a GrooveCut): toolpath(cut, path)."""
    from .operations.profiling.operation_input import groove_cut
    return lambda path, op, program, op_index, tools: toolpath(groove_cut(program, op_index, op, tools), path)


def _write_tapping(path, op, program, op_index, tools):
    # the tap's pitch, from the tool
    tapping_toolpath(op, path, _resolve_tap_pitch(program, op, tools))


def _write_define_profile(path, op, program, op_index, tools):
    # a profile G70/G71 cuts is a subroutine of the program; any other is
    # drawn by the operations that cut it
    if _define_profile_needs_subroutine(int(op.profile_id or 0), program.operations):
        path.foreign(generate_define_profile_gcode(op))
    else:
        path.code("; The drawn profile is represented in the custom profiling section.")


def _write_radial_profile(path, op, program, op_index, tools):
    path.code("; The radial profile is represented in the conversational JSON.")


#: The writer of each operation class.
_WRITERS = {
    Facing: _on_emitter(facing_toolpath),
    Drilling: _on_emitter(drilling_toolpath),
    PositionAt: _on_emitter(position_at_toolpath),
    Knurling: _lines(generate_knurling_gcode),
    Profiling: _lines(generate_profiling_gcode),
    Threading: _lines(generate_threading_gcode),
    G33Threading: _on_emitter(g33_threading_toolpath),
    Parting: _on_emitter(parting_toolpath),
    ProfileRoughing: _cut_on_emitter(profile_roughing_toolpath),
    ProfileContour: _cut_on_emitter(profile_contour_toolpath),
    GrooveRoughing: _groove_on_emitter(groove_roughing_toolpath),
    GrooveFinishing: _groove_on_emitter(groove_finishing_toolpath),
    Tapping: _write_tapping,
    DefineProfile: _write_define_profile,
    ImportDxfProfile: _write_define_profile,
    DefineRadialProfile: _write_radial_profile,
}


def build_ngc_from_json(json_path, tools, output_dir=None):
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

    return build_ngc_from_program(program, tools, output_path=output_path)
