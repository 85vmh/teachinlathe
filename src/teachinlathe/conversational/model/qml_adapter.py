from dataclasses import dataclass
from typing import List

from teachinlathe.conversational.model.data_types import TurnableOperation


def build_selected_program_summary(program):
    return {
        "id": program.id,
        "name": program.header.name,
        "created_date": getattr(program.header, "created_date", ""),
        "last_edit": program.header.last_edit,
        # the work offset's P number: 1 is G54 ... 6 is G59
        "datum": int(getattr(program.header, "datum", 1) or 1),
    }


def build_details_payload(obj):
    return obj.to_dict() if hasattr(obj, "to_dict") else None


def _number(value):
    """25.0 as 25, 6.80 as 6.8."""
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def axial_tool_label(op, program, tools=None):
    """What Drilling and Tapping show of their tool, in brackets: the drill's
    diameter, (Ø25), or the tap's size, (M12 x 1mm) - the tool ``op`` cuts
    with, from the Tool Library - or (???) when that is not a drill, or a
    tap, or there is none. None for any other operation. ``tools``: where
    the tool is looked up (a ToolSnapshot), the Tool Library if not given."""
    from teachinlathe.conversational.model.data_types import Drilling, Tapping
    from teachinlathe.tooling.model.data_types import DrillingTool, TappingTool
    if not isinstance(op, (Drilling, Tapping)):
        return None
    from teachinlathe.ui.tabs.programs.backplot import tool_source
    entry = program.tool_of(op) if program is not None else None
    if entry is None:
        tool = None
    elif tools is not None:
        tool = tools.tool_in(int(entry.tool_holder_id))
    else:
        tool = tool_source.tool_in(int(entry.tool_holder_id))
    if isinstance(op, Drilling):
        if not isinstance(tool, DrillingTool) or tool.diameter <= 0:
            return "(???)"
        return f"(\u00d8{_number(tool.diameter)})"
    if not isinstance(tool, TappingTool) or tool.diameter <= 0 or tool.pitch <= 0:
        return "(???)"
    return f"(M{_number(tool.diameter)} x {_number(tool.pitch)}mm)"


def operation_title(op, program, tools=None):
    """``op``'s name as the program shows it: its display_name and, for
    Drilling and Tapping, its tool's size (axial_tool_label). ``tools``: where
    the tool is looked up, the Tool Library if not given."""
    label = axial_tool_label(op, program, tools)
    return f"{op.display_name()} {label}" if label else op.display_name()


@dataclass(frozen=True)
class OperationRow:
    """An operation as the program's list shows it: ``number`` from 1,
    ``title`` its name (operation_title), ``toolLabel`` the T number where
    the tool changes - "T?" for one that cuts with no tool chosen, "" where
    it cuts with the one before's or does not cut - and its two check boxes.
    The fields are the roles QML reads (DataclassListModel)."""
    number: int
    title: str
    toolLabel: str
    generateGcode: bool
    optionalBlock: bool


def operation_rows(program) -> List[OperationRow]:
    """The rows of ``program``'s operation list, in order."""
    rows = []
    previous_tool = None
    for index, op in enumerate(program.operations):
        tool_label = ""
        if isinstance(op, TurnableOperation):
            entry = program.tool_of(op)
            holder = entry.tool_holder_id if entry is not None else None
            if holder is None:
                tool_label = "T?"
            elif holder != previous_tool:
                tool_label = f"T{holder}"
            previous_tool = holder
        rows.append(OperationRow(number=index + 1, title=operation_title(op, program), toolLabel=tool_label,
                                 generateGcode=bool(op.generate_gcode), optionalBlock=bool(op.is_optional_block)))
    return rows
