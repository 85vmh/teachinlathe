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
from teachinlathe.tooling.store.tool_library_store import (  # noqa: E402
    CUTTING_TOOLS_FILE, TOOL_HOLDERS_FILE, ToolLibraryStore,
)
from teachinlathe.ui.tabs.tool_library.tool_library_models import (  # noqa: E402
    CuttingToolTreeModel, ToolHolderListModel,
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
     "orientation": 8, "spindle_direction": 4},
    {"cutting_tool_id": 5, "type": "drilling", "diameter": 10, "tip_angle": 118,
     "twist_direction": "right_hand", "spindle_direction": 4},
    {"cutting_tool_id": 6, "type": "tapping", "diameter": 10, "pitch": 1.5,
     "twist_direction": "right_hand", "spindle_direction": 4},
    {"cutting_tool_id": 7, "type": "reaming", "diameter": 10,
     "spindle_direction": 4},
]

USER_HOLDER = {"tool_holder_id": 1, "orientation": "radial", "cutting_tool_id": 3,
               "x_offset": 123.123, "z_offset": 123.123, "z_offset_place": "-1"}


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


def test_mounting_clears_the_offsets():
    holder = from_json(ToolHolder, USER_HOLDER)
    assert holder.is_ready
    holder.mount(7)
    assert holder.cutting_tool_id == 7
    assert (holder.x_offset, holder.z_offset, holder.z_offset_place) == (None, None, None)
    assert not holder.is_ready
    holder.x_offset, holder.z_offset = 1.0, 2.0
    assert holder.is_ready
    holder.mount(None)
    assert not holder.has_tool and not holder.is_ready


def test_store_seeds_missing_files_and_reloads_them(tmp_path):
    store = ToolLibraryStore(tmp_path)
    assert (tmp_path / CUTTING_TOOLS_FILE).exists()
    assert (tmp_path / TOOL_HOLDERS_FILE).exists()
    assert all(store.tools_of(t) for t in CuttingToolType)

    reloaded = ToolLibraryStore(tmp_path)
    assert reloaded.cutting_tools == store.cutting_tools
    assert reloaded.holders == store.holders


def test_store_mount_persists(tmp_path):
    store = ToolLibraryStore(tmp_path)
    ready = next(h for h in store.holders if h.is_ready)
    store.mount(ready.tool_holder_id, store.cutting_tools[-1].cutting_tool_id)

    holder = ToolLibraryStore(tmp_path).find_holder(ready.tool_holder_id)
    assert holder.cutting_tool_id == store.cutting_tools[-1].cutting_tool_id
    assert holder.x_offset is None and holder.z_offset is None


def test_store_rejects_unknown_ids(tmp_path):
    store = ToolLibraryStore(tmp_path)
    with pytest.raises(KeyError):
        store.mount(999, None)
    with pytest.raises(KeyError):
        store.mount(store.holders[0].tool_holder_id, 999)


def test_store_does_not_overwrite_an_unreadable_file(tmp_path):
    broken = tmp_path / CUTTING_TOOLS_FILE
    broken.write_text("{ not json", encoding="utf-8")
    store = ToolLibraryStore(tmp_path)
    assert store.cutting_tools == []
    assert broken.read_text(encoding="utf-8") == "{ not json"


def test_store_writes_the_specified_layout(tmp_path):
    ToolLibraryStore(tmp_path)
    holders = json.loads((tmp_path / TOOL_HOLDERS_FILE).read_text(encoding="utf-8"))
    tools = json.loads((tmp_path / CUTTING_TOOLS_FILE).read_text(encoding="utf-8"))
    assert set(holders) == {"tool_holders"}
    assert isinstance(tools, list)
    assert next(iter(tools[0].values())) == tools[0]["cutting_tool_id"]


def _rows(model):
    names = {v.decode(): k for k, v in model.roleNames().items()}
    return [{name: model.data(model.index(r, 0), role) for name, role in names.items()}
            for r in range(model.rowCount())]


def test_tree_model_groups_by_type_and_folds(qt_app, tmp_path):
    store = ToolLibraryStore(tmp_path)
    model = CuttingToolTreeModel(store)

    headers = [r for r in _rows(model) if r["isHeader"]]
    assert [h["toolType"] for h in headers] == [t.value for t in CuttingToolType]
    assert [h["count"] for h in headers] == [len(store.tools_of(t)) for t in CuttingToolType]
    assert model.rowCount() == len(CuttingToolType) + len(store.cutting_tools)

    model.toggle(CuttingToolType.TURNING.value)
    turning = len(store.tools_of(CuttingToolType.TURNING))
    assert model.rowCount() == len(CuttingToolType) + len(store.cutting_tools) - turning
    assert not model.headerRow(CuttingToolType.TURNING).expanded

    model.toggle(CuttingToolType.TURNING.value)
    assert model.rowCount() == len(CuttingToolType) + len(store.cutting_tools)


def test_holder_model_shows_the_stored_fields(qt_app, tmp_path):
    store = ToolLibraryStore(tmp_path)
    rows = _rows(ToolHolderListModel(store))
    assert [r["holderId"] for r in rows] == [h.tool_holder_id for h in store.holders]
    assert [r["ready"] for r in rows] == [h.is_ready for h in store.holders]
    assert "tool_holder_id:\u00a01" in rows[0]["text"]
    assert all(bool(r["toolText"]) == h.has_tool for r, h in zip(rows, store.holders))
