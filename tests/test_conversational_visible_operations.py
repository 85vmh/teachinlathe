from types import SimpleNamespace

from teachinlathe.conversational.model.program_commands import (
    delete_visible_operation,
    duplicate_visible_operation,
    move_visible_operation,
)
from teachinlathe.conversational.model.qml_adapter import build_operations_model


def operation(op_type, tool_no=None):
    return SimpleNamespace(type=op_type, tool_no=tool_no, order=0)


def program(*operations):
    return SimpleNamespace(operations=list(operations))


def test_visible_model_hides_tool_changes_and_marks_only_new_tool():
    prog = program(
        operation("changeTool", 1), operation("facing"),
        operation("positionAt"),
        operation("changeTool", 1), operation("parting"),
        operation("changeTool", 11), operation("profileContour"),
    )

    rows = build_operations_model(prog)

    assert [row["type"] for row in rows] == ["facing", "positionAt", "parting", "profileContour"]
    assert [row["order"] for row in rows] == [1, 2, 3, 4]
    assert [row["source_index"] for row in rows] == [1, 2, 4, 6]
    assert [row["group_start_index"] for row in rows] == [0, 2, 3, 5]
    assert [row["tool_label"] for row in rows] == ["T1", "", "", "T11"]
    assert len(prog.operations) == 7


def test_visible_edits_keep_hidden_tool_change_with_its_operation():
    first = operation("facing")
    change = operation("changeTool", 11)
    second = operation("parting")
    third = operation("positionAt")
    prog = program(first, change, second, third)

    assert move_visible_operation(prog, 2, 3) == 3
    assert prog.operations == [first, third, change, second]
    assert [op.order for op in prog.operations] == [1, 2, 3, 4]

    assert duplicate_visible_operation(prog, 3) == 5
    assert [op.type for op in prog.operations] == [
        "facing", "positionAt", "changeTool", "parting", "changeTool", "parting",
    ]
    assert prog.operations[4] is not change

    assert delete_visible_operation(prog, 3)
    assert [op.type for op in prog.operations] == ["facing", "positionAt", "changeTool", "parting"]

    assert move_visible_operation(prog, 3, 0) == 1
    assert [op.type for op in prog.operations] == ["changeTool", "parting", "facing", "positionAt"]
    assert [row["tool_label"] for row in build_operations_model(prog)] == ["T11", "", ""]
