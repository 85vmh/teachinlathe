"""Tests for the tool library's model, its JSON files and its list models."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt6.QtCore import QCoreApplication, Qt  # noqa: E402

from teachinlathe.tooling.model.data_types import (  # noqa: E402
    BladeTool, BoringTool, CuttingTool, CuttingToolType, DrillingTool,
    HolderOrientation, ReamingTool, SpindleDirection, TappingTool, ThreadingTool,
    ToolHolder, TurningTool, TwistDirection, ZOffsetPlace, from_json, to_json,
)
from teachinlathe.core.lathe_tool_extras_data_source import (  # noqa: E402
    CUTTING_TOOLS_FILE, TOOL_HOLDERS_FILE,
)
from tool_library_fakes import TOOL_TABLE_FILE, tool_library, touch_off  # noqa: E402
from teachinlathe.core.tool_tbl_file_data_source import parse_line  # noqa: E402
from teachinlathe.ui.tabs.tool_library.tool_library_models import (  # noqa: E402
    CuttingToolCategoriesModel, ToolHolderListModel,
)


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


# The examples the file format was specified with.
USER_TOOLS = [
    {"cutting_tool_id": 1, "type": "turning",
     "insert": {"geometry": "ccmt", "size": "06", "radius": "02"},
     "orientation": 6, "front_angle": 5, "back_angle": 5, "spindle_direction": 4},
    {"cutting_tool_id": 2, "type": "boring",
     "insert": {"geometry": "ccmt", "size": "06", "radius": "02"},
     "solid_body": {"tip_angle": 50, "diameter": 5, "max_radial_undercut": 3},
     "orientation": 6, "front_angle": 5, "back_angle": 5, "spindle_direction": 4},
    {"cutting_tool_id": 3, "type": "blade", "blade_width": 3, "left_radius": 0.5,
     "right_radius": 0.5, "orientation": 6, "spindle_direction": 4},
    {"cutting_tool_id": 4, "type": "threading",
     "insert": {"geometry": "ER", "size": "16", "radius": "02"},
     "orientation": 8, "pitch": 1.5, "spindle_direction": 4},
    {"cutting_tool_id": 5, "type": "drilling", "diameter": 10, "tip_angle": 118,
     "twist_direction": "right_hand", "spindle_direction": 4},
    {"cutting_tool_id": 6, "type": "tapping", "diameter": 10, "pitch": 1.5,
     "twist_direction": "right_hand", "spindle_direction": 4},
    {"cutting_tool_id": 7, "type": "reaming", "diameter": 10,
     "spindle_direction": 4},
]

USER_HOLDER = {"tool_holder_id": 1, "orientation": "radial", "cutting_tool_id": 3,
               "x_touched": True, "z_touched": True, "z_offset_place": "-1",
               "last_loaded": None, "x_offset": 123.123, "z_offset": 123.123}


@pytest.mark.parametrize("raw", USER_TOOLS, ids=lambda raw: raw["type"])
def test_cutting_tool_round_trips(raw):
    tool = CuttingTool.from_json(raw)
    assert tool.tool_type is CuttingToolType(raw["type"])
    assert tool.to_json() == raw
    assert list(tool.to_json())[:2] == ["cutting_tool_id", "type"]


def test_cutting_tool_types_resolve_to_their_classes():
    expected = [TurningTool, BoringTool, BladeTool, ThreadingTool, DrillingTool, ReamingTool,
                TappingTool]
    assert [CuttingTool.class_for(t) for t in CuttingToolType] == expected


def test_decoded_values_are_typed():
    drill = CuttingTool.from_json(USER_TOOLS[4])
    assert drill.twist_direction is TwistDirection.RIGHT_HAND
    assert drill.spindle_direction is SpindleDirection.M4
    boring = CuttingTool.from_json(USER_TOOLS[1])
    assert boring.solid_body.diameter == 5.0
    assert boring.insert.size == "06"


def test_holder_round_trips():
    holder = from_json(ToolHolder, USER_HOLDER)
    assert holder.orientation is HolderOrientation.RADIAL
    assert holder.z_offset_place is ZOffsetPlace.LEFT
    assert to_json(holder) == USER_HOLDER


def test_mounting_zeroes_the_offsets_and_wants_a_touch_off():
    holder = from_json(ToolHolder, USER_HOLDER)
    assert holder.is_ready
    holder.mount(7)
    assert holder.cutting_tool_id == 7
    assert (holder.x_offset, holder.z_offset, holder.z_offset_place) == (0.0, 0.0, None)
    assert not (holder.x_touched or holder.z_touched)
    assert not holder.is_ready
    holder.x_touched = holder.z_touched = True
    assert holder.is_ready
    holder.mount(None)
    assert not holder.has_tool and not holder.is_ready


# ── The repository and its files ───────────────────────────────────────────


def _table(tmp_path):
    """The tool table, by T number."""
    text = (tmp_path / TOOL_TABLE_FILE).read_text(encoding="utf-8")
    return {e.t: e for e in map(parse_line, text.splitlines()) if e is not None}


def test_repository_seeds_missing_files_and_reloads_them(tmp_path):
    library = tool_library(tmp_path)
    assert (tmp_path / CUTTING_TOOLS_FILE).exists()
    assert (tmp_path / TOOL_HOLDERS_FILE).exists()
    assert all(library.tools_of(t) for t in CuttingToolType)

    reloaded = tool_library(tmp_path)
    assert reloaded.cutting_tools == library.cutting_tools
    assert reloaded.holders == library.holders


def test_the_tool_table_has_a_line_per_holder_with_a_tool(tmp_path):
    library = tool_library(tmp_path)
    assert sorted(_table(tmp_path)) == [h.tool_holder_id for h in library.holders if h.has_tool]


def test_offsets_are_read_from_the_tool_table(tmp_path):
    holder_id = next(h for h in tool_library(tmp_path).holders if h.has_tool).tool_holder_id
    touch_off(tmp_path, holder_id, 1.5, -2.25)

    holder = tool_library(tmp_path).find_holder(holder_id)
    assert holder.is_ready
    assert (holder.x_offset, holder.z_offset) == (1.5, -2.25)
    saved = json.loads((tmp_path / TOOL_HOLDERS_FILE).read_text(encoding="utf-8"))
    assert all("x_offset" not in h and "z_offset" not in h for h in saved["tool_holders"])


def test_mount_persists_and_zeroes_the_offsets(tmp_path):
    library = tool_library(tmp_path)
    holder_id = next(h for h in library.holders if h.has_tool).tool_holder_id
    touch_off(tmp_path, holder_id, 1.5, -2.25)
    library = tool_library(tmp_path)
    other = next(t for t in library.cutting_tools if library.holder_of(t.cutting_tool_id) is None)
    library.mount(holder_id, other.cutting_tool_id)

    holder = tool_library(tmp_path).find_holder(holder_id)
    assert holder.cutting_tool_id == other.cutting_tool_id
    assert not holder.is_ready
    assert (_table(tmp_path)[holder_id].x, _table(tmp_path)[holder_id].z) == (0.0, 0.0)


def test_repository_rejects_unknown_ids(tmp_path):
    library = tool_library(tmp_path)
    with pytest.raises(KeyError):
        library.mount(999, None)
    with pytest.raises(KeyError):
        library.mount(library.holders[0].tool_holder_id, 999)


def test_repository_does_not_overwrite_an_unreadable_file(tmp_path):
    broken = tmp_path / CUTTING_TOOLS_FILE
    broken.write_text("{ not json", encoding="utf-8")
    library = tool_library(tmp_path)
    assert library.cutting_tools == []
    assert broken.read_text(encoding="utf-8") == "{ not json"


def test_repository_writes_the_specified_layout(tmp_path):
    tool_library(tmp_path)
    holders = json.loads((tmp_path / TOOL_HOLDERS_FILE).read_text(encoding="utf-8"))
    tools = json.loads((tmp_path / CUTTING_TOOLS_FILE).read_text(encoding="utf-8"))
    assert set(holders) == {"tool_holders", "current_loaded_tool"}
    assert isinstance(tools, list)
    assert next(iter(tools[0].values())) == tools[0]["cutting_tool_id"]


# ── The list models ─────────────────────────────────────────────────────────


def _rows(model):
    names = {v.decode(): k for k, v in model.roleNames().items()}
    return [{name: model.data(model.index(r, 0), role) for name, role in names.items()}
            for r in range(model.rowCount())]


def test_categories_model_groups_by_type_and_folds(qt_app, tmp_path):
    library = tool_library(tmp_path)
    model = CuttingToolCategoriesModel(library)

    rows = _rows(model)
    assert [r["toolType"] for r in rows] == [t.value for t in CuttingToolType]
    assert [r["count"] for r in rows] == [len(library.tools_of(t)) for t in CuttingToolType]
    assert all(r["expanded"] for r in rows) and model.allExpanded

    model.toggle(CuttingToolType.TURNING.value)
    assert not model.categoryRow(CuttingToolType.TURNING).expanded
    assert model.rowCount() == len(CuttingToolType)
    assert not model.allExpanded and not model.allCollapsed

    model.toggle(CuttingToolType.TURNING.value)
    assert model.categoryRow(CuttingToolType.TURNING).expanded

    model.setAllExpanded(False)
    assert model.allCollapsed


def test_categories_model_knows_the_mounted_tools(qt_app, tmp_path):
    library = tool_library(tmp_path)
    model = CuttingToolCategoriesModel(library)
    assert model.mountedToolIds == sorted(h.cutting_tool_id for h in library.holders if h.has_tool)


def test_holder_model_shows_the_stored_fields(qt_app, tmp_path):
    holder_id = next(h for h in tool_library(tmp_path).holders if h.has_tool).tool_holder_id
    touch_off(tmp_path, holder_id, 1.5, -2.25)
    library = tool_library(tmp_path)
    rows = _rows(ToolHolderListModel(library))
    assert [r["holderId"] for r in rows] == [h.tool_holder_id for h in library.holders]
    assert [r["ready"] for r in rows] == [h.is_ready for h in library.holders]
    assert [r["toolId"] for r in rows] == [h.cutting_tool_id or 0 for h in library.holders]
    touched = next(r for r in rows if r["holderId"] == holder_id)
    assert (touched["xOffset"], touched["zOffset"]) == ("1.500", "-2.250")
    assert all(r["xOffset"] == "" for r in rows if r["holderId"] != holder_id)
