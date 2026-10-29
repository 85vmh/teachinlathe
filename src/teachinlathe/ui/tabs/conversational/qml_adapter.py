"""The open program as the Conversational screens read it: the selected
program's summary and the rows of its operation list."""

from dataclasses import dataclass
from typing import List

from teachinlathe.conversational.model.data_types import TurnableOperation
from teachinlathe.conversational.model.operation_titles import operation_title


def build_selected_program_summary(program):
    return {
        "id": program.id,
        "name": program.header.name,
        "created_date": getattr(program.header, "created_date", ""),
        "last_edit": program.header.last_edit,
        # the work offset's P number: 1 is G54 ... 6 is G59
        "datum": int(getattr(program.header, "datum", 1) or 1),
    }


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


def operation_rows(program, tools) -> List[OperationRow]:
    """The rows of ``program``'s operation list, in order; the tools they
    name looked up in ``tools`` (operation_title)."""
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
        rows.append(OperationRow(number=index + 1, title=operation_title(op, program, tools), toolLabel=tool_label,
                                 generateGcode=bool(op.generate_gcode), optionalBlock=bool(op.is_optional_block)))
    return rows
