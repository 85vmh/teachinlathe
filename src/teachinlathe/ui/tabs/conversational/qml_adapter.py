"""The open program as the Conversational screens read it: the selected
program's summary and the rows of its operation list."""

from dataclasses import dataclass
from typing import List

from teachinlathe.conversational.gcode.operations.profiling import groove_outline as outline
from teachinlathe.conversational.model.data_types import Groove, TurnableOperation, radial_primitives_from
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
    #: a rapid of it goes through the stock: no G-code for the program
    stockProblem: bool = False


def operation_rows(program, tools, stock_problems=()) -> List[OperationRow]:
    """The rows of ``program``'s operation list, in order; the tools they
    name looked up in ``tools`` (operation_title). ``stock_problems``: the
    indexes of the operations a rapid of which goes through the stock."""
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
                                 generateGcode=bool(op.generate_gcode), optionalBlock=bool(op.is_optional_block),
                                 stockProblem=index in stock_problems))
    return rows


def _point(at) -> dict:
    return {"z": at.z, "x": at.x}


def groove_outline_payload(raw_primitives) -> dict:
    """The first groove of a radial profile - ``raw_primitives``, the
    primitives' dicts as its editor has them - as RadialProfileCanvas draws
    it (groove_outline): ``points`` P1-P4 ({z, x: diameter}), ``primitives``
    the profile primitives' dicts, and ``roles`` what each of them draws -
    {key, section}, a flank's ``from`` and ``to`` its points, a top blend's
    ``anchor`` the middle of it. All empty with no groove."""
    groove = next((p for p in radial_primitives_from(raw_primitives) if isinstance(p, Groove)), None)
    if groove is None:
        return {"points": [], "primitives": [], "roles": []}
    drawn = outline.groove_outline(groove)
    p1, p2, p3, p4 = (_point(at) for at in drawn.points)
    roles = {
        outline.START: {"key": outline.START},
        outline.RIGHT_BLEND: {"key": outline.RIGHT_BLEND, "section": "right_flank",
                              "anchor": _point(drawn.right_corner.middle)},
        outline.RIGHT_FLANK: {"key": outline.RIGHT_FLANK, "section": "right_flank", "from": p1, "to": p2},
        outline.BOTTOM: {"key": outline.BOTTOM, "section": "bottom"},
        outline.LEFT_FLANK: {"key": outline.LEFT_FLANK, "section": "left_flank", "from": p4, "to": p3},
        outline.LEFT_BLEND: {"key": outline.LEFT_BLEND, "section": "left_flank",
                             "anchor": _point(drawn.left_corner.middle)},
    }
    return {"points": [p1, p2, p3, p4],
            "primitives": [p.to_dict() for p in drawn.primitives],
            "roles": [roles[part] for part in drawn.parts]}
