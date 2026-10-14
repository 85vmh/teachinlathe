"""Tests for the turning-tool editor: the angle rules, the insert catalogue,
the editor's view model and the tab's navigation around it."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt6.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.tooling.model import insert_catalog, tool_angles  # noqa: E402
from teachinlathe.tooling.model.data_types import (  # noqa: E402
    CuttingToolType, InsertSpec, SpindleDirection, TurningTool,
)
from teachinlathe.tooling.store.tool_library_store import (  # noqa: E402
    CUTTING_TOOLS_FILE, ToolLibraryStore,
)
from teachinlathe.tooling.ui.ToolsTabViewModel import (  # noqa: E402
    HeaderAction, ToolsTabViewModel,
)
from teachinlathe.tooling.ui.TurningToolEditorViewModel import (  # noqa: E402
    TURNING_ORIENTATIONS, TurningToolEditorViewModel, new_turning_tool,
)


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


# ── Angles ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("corner, orientation, front, back", [
    (80, 2, 5, 5),          # CCMT, the example the rule was given with
    (55, 2, 3, 32),         # DCMT
    (35, 3, 5, 50),         # VBMT in a corner
    (35, 6, 72.5, 72.5),    # VBMT held neutral
    (80, 8, 5, 95),
])
def test_back_angle_follows_front(corner, orientation, front, back):
    assert tool_angles.complementary_angle(front, corner, orientation) == pytest.approx(back)
    assert tool_angles.complementary_angle(back, corner, orientation) == pytest.approx(front)


def test_angles_are_clamped_to_what_fits():
    assert tool_angles.complementary_angle(20, 80, 2) == 0
    assert tool_angles.complementary_angle(-3, 80, 2) == 10
    assert tool_angles.clamp_angle(50, 80, 2) == 10


def test_round_inserts_and_undirected_orientations_are_not_coupled():
    assert tool_angles.complementary_angle(5, None, 2) is None
    for orientation in (5, 7, 9):
        assert tool_angles.complementary_angle(5, 80, orientation) is None
        assert tool_angles.insert_rotation(orientation, 5, 5, 0) == 0


@pytest.mark.parametrize("orientation, tip", [
    (1, 45), (2, 135), (3, 225), (4, 315), (6, 90), (8, 270),
])
def test_symmetric_tool_points_where_the_picture_does(orientation, tip):
    """Equal angles put the tip on the diagonal - or the axis, for 6 and 8 -
    that the orientation picture shows."""
    clearance = 5 if orientation <= 4 else 50
    assert tool_angles.insert_rotation(orientation, clearance, clearance, 0) == pytest.approx(tip)


def test_edges_leave_their_axes_by_the_angles():
    geometry = tool_angles.edge_geometry(2, 3, 32)
    # Front from the X axis (down), back from the Z axis (right), both
    # turning into the body.
    assert geometry.front_ray == 270 and geometry.front_edge == pytest.approx(273)
    assert geometry.back_ray == 0 and geometry.back_edge == pytest.approx(328)


# ── Insert catalogue ────────────────────────────────────────────────────────


def test_corner_angles_come_from_the_drawn_outline():
    angles = {family: insert_catalog.corner_angle(InsertSpec(family.lower(), "", ""))
              for family in insert_catalog.families()}
    assert angles == {"CCMT": 80, "DCMT": 55, "VBMT": 35, "TCMT": 60,
                      "WNMG": 80, "SNMG": 90, "RCMT": None}


def test_spec_round_trips_through_the_catalogue():
    spec = insert_catalog.make_spec("DCMT", 1, 0.8)
    assert spec == InsertSpec("dcmt", "11", "08")
    assert insert_catalog.family_of(spec) == "DCMT"
    assert insert_catalog.size_index_of(spec) == 1
    assert insert_catalog.nose_radius_of(spec) == 0.8


def test_spec_lookup_ignores_case_and_falls_back():
    assert insert_catalog.family_of(InsertSpec("CcMt", "09", "04")) == "CCMT"
    assert insert_catalog.size_index_of(InsertSpec("ccmt", "99", "04")) == 0
    assert insert_catalog.family_of(InsertSpec("xyz", "", "")) == insert_catalog.families()[0]


# ── Editor ──────────────────────────────────────────────────────────────────


def _editor(**fields):
    tool = TurningTool(cutting_tool_id=7, insert=InsertSpec("ccmt", "09", "04"),
                       orientation=2, front_angle=5, back_angle=5)
    for name, value in fields.items():
        setattr(tool, name, value)
    return TurningToolEditorViewModel(tool, is_new=False)


def test_editor_titles(qt_app):
    assert _editor().title == "Edit Turning Tool #7"
    assert TurningToolEditorViewModel(new_turning_tool(3), is_new=True).title == "New Turning Tool"


def test_new_tool_starts_consistent(qt_app):
    tool = new_turning_tool(3)
    corner = insert_catalog.corner_angle(tool.insert)
    assert tool.front_angle + corner + tool.back_angle == pytest.approx(90)


def test_editor_couples_the_angles(qt_app):
    editor = _editor()
    editor.setFrontAngle(2)
    assert editor.backAngle == pytest.approx(8)
    editor.setBackAngle(9)
    assert editor.frontAngle == pytest.approx(1)


def test_changing_the_insert_keeps_front_and_recomputes_back(qt_app):
    editor = _editor()
    editor.setFamily(insert_catalog.families().index("DCMT"))
    assert (editor.frontAngle, editor.backAngle) == (5, 30)
    editor.setOrientation(6)
    assert (editor.frontAngle, editor.backAngle) == (5, 120)


def test_family_change_keeps_size_position_clamped(qt_app):
    editor = _editor(insert=InsertSpec("ccmt", "16", "04"))      # 4th CCMT size
    editor.setFamily(insert_catalog.families().index("VBMT"))      # has three
    assert editor.sizeCodes == ["11", "16", "22"] and editor.sizeIndex == 2
    assert editor.result().insert == InsertSpec("vbmt", "22", "04")


def test_round_insert_leaves_angles_independent(qt_app):
    editor = _editor()
    editor.setFamily(insert_catalog.families().index("RCMT"))
    assert not editor.anglesCoupled
    editor.setFrontAngle(12)
    editor.setBackAngle(40)
    assert (editor.frontAngle, editor.backAngle) == (12, 40)


def test_inconsistent_stored_angles_are_fixed_on_open(qt_app):
    editor = _editor(orientation=6)                  # 5 + 80 + 5 is not 180
    assert (editor.frontAngle, editor.backAngle) == (5, 95)


def test_only_turning_orientations_are_taken(qt_app):
    editor = _editor()
    editor.setOrientation(7)
    assert editor.orientation == 2
    assert editor.allowedOrientations == TURNING_ORIENTATIONS


def test_editor_works_on_a_copy(qt_app):
    tool = TurningTool(cutting_tool_id=1, insert=InsertSpec("ccmt", "06", "02"),
                       orientation=2, front_angle=5, back_angle=5)
    editor = TurningToolEditorViewModel(tool, is_new=False)
    editor.setFrontAngle(1)
    editor.setClockwise(True)
    assert tool.front_angle == 5 and tool.spindle_direction is SpindleDirection.M4
    assert editor.result().spindle_direction is SpindleDirection.M3


# ── Tab navigation and saving ───────────────────────────────────────────────


def _saved_tools(tmp_path):
    return json.loads((tmp_path / CUTTING_TOOLS_FILE).read_text(encoding="utf-8"))


def test_edit_save_writes_and_closes(qt_app, tmp_path):
    tab = ToolsTabViewModel(ToolLibraryStore(tmp_path))
    tab.editCuttingTool(1)
    assert tab.getHeaderState()["title"] == "Edit Turning Tool #1"
    tab.editor.setFrontAngle(2)
    tab.triggerHeaderAction(HeaderAction.SAVE.value)

    assert tab.editor is None and tab.getHeaderState() == {}
    saved = next(t for t in _saved_tools(tmp_path) if t["cutting_tool_id"] == 1)
    assert (saved["front_angle"], saved["back_angle"]) == (2, 8)


def test_back_discards(qt_app, tmp_path):
    tab = ToolsTabViewModel(ToolLibraryStore(tmp_path))
    before = _saved_tools(tmp_path)
    tab.addCuttingTool(CuttingToolType.TURNING.value)
    tab.editor.setFrontAngle(1)
    tab.triggerHeaderAction(HeaderAction.BACK.value)
    assert tab.editor is None
    assert _saved_tools(tmp_path) == before


def test_add_save_appends_a_new_tool(qt_app, tmp_path):
    store = ToolLibraryStore(tmp_path)
    tab = ToolsTabViewModel(store)
    new_id = store.next_cutting_tool_id()
    turning_before = len(store.tools_of(CuttingToolType.TURNING))
    tab.addCuttingTool(CuttingToolType.TURNING.value)
    assert tab.getHeaderState()["title"] == "New Turning Tool"
    tab.triggerHeaderAction(HeaderAction.SAVE.value)

    reloaded = ToolLibraryStore(tmp_path)
    assert reloaded.find_tool(new_id).tool_type is CuttingToolType.TURNING
    assert len(reloaded.tools_of(CuttingToolType.TURNING)) == turning_before + 1
    header = tab.cuttingToolsModel.headerRow(CuttingToolType.TURNING)
    assert header.count == turning_before + 1


def test_an_unknown_tool_opens_no_editor(qt_app, tmp_path):
    store = ToolLibraryStore(tmp_path)
    tab = ToolsTabViewModel(store)
    tab.editCuttingTool(999)
    assert tab.editor is None
    tab.editCuttingTool(store.tools_of(CuttingToolType.BORING)[0].cutting_tool_id)
    assert tab.editor is not None and tab.editor.toolType == "boring"


# ── One tool, one holder ────────────────────────────────────────────────────


def test_mounting_a_tool_moves_it_out_of_its_old_holder(tmp_path):
    store = ToolLibraryStore(tmp_path)
    old = next(h for h in store.holders if h.is_ready)
    empty = next(h for h in store.holders if not h.has_tool)
    tool_id = old.cutting_tool_id

    store.mount(empty.tool_holder_id, tool_id)

    reloaded = ToolLibraryStore(tmp_path)
    assert reloaded.find_holder(empty.tool_holder_id).cutting_tool_id == tool_id
    moved_from = reloaded.find_holder(old.tool_holder_id)
    assert not moved_from.has_tool and moved_from.x_offset is None
    assert [h.tool_holder_id for h in reloaded.holders
            if h.cutting_tool_id == tool_id] == [empty.tool_holder_id]
