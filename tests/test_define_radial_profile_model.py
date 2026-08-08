import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.data_types import Operation
from teachinlathe.conversational.factories import make_default_operation
from teachinlathe.conversational.qml_adapter import display_name_for_op


def test_define_radial_profile_roundtrip_and_display_name():
    op = make_default_operation("defineRadialProfile", order=2)
    data = op.to_dict()

    assert data["type"] == "defineRadialProfile"
    assert data["profile_id"] == 1
    assert data["profile_type"] == "od"
    assert data["profile_primitives"][0]["type"] == "groove"
    assert list(data["profile_primitives"][0].keys())[:5] == [
        "primitive_id",
        "type",
        "right_flank",
        "bottom",
        "left_flank",
    ]
    assert data["profile_primitives"][0]["bottom"]["x_end_right"] == 20.0

    loaded = Operation.from_dict(data)
    assert loaded.to_dict() == data
    assert display_name_for_op("defineRadialProfile", profile_id=1) == "Define Radial Profile (P1)"


def test_define_radial_profile_orders_groove_keys_on_load():
    data = make_default_operation("defineRadialProfile", order=2).to_dict()
    groove = data["profile_primitives"][0]
    data["profile_primitives"][0] = {
        "bottom": groove["bottom"],
        "left_flank": groove["left_flank"],
        "primitive_id": groove["primitive_id"],
        "right_flank": groove["right_flank"],
        "type": groove["type"],
    }

    loaded = Operation.from_dict(data)
    out = loaded.to_dict()["profile_primitives"][0]

    assert list(out.keys())[:5] == [
        "primitive_id",
        "type",
        "right_flank",
        "bottom",
        "left_flank",
    ]
