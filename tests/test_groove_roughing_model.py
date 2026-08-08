import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.data_types import GrooveRoughing, Operation
from teachinlathe.conversational.factories import make_default_operation
from teachinlathe.conversational.qml_adapter import display_name_for_op


def test_groove_roughing_default_roundtrip_and_json_shape():
    op = make_default_operation("grooveRoughing", order=5)
    assert isinstance(op, GrooveRoughing)

    data = op.to_dict()

    assert data["order"] == 5
    assert data["type"] == "grooveRoughing"
    assert data["spindle_parameters"] == {
        "direction": -1,
        "mode": "rpm",
        "rpm_value": 1000,
    }
    assert data["cutting_parameters"] == {
        "feed_rate": 0.1,
        "peck_depth": 3.0,
        "retract": 1.0,
        "dwell_time": 0.5,
    }
    assert data["roughing_parameters"] == {
        "profile_id": 1,
        "strategy": "start_center",
        "initial_offset": 1.5,
        "afterwards_offset": 1.0,
    }
    assert data["stock_to_leave"] == {
        "radial": 0.5,
        "axial": 0.2,
    }
    assert data["stock_to_leave_enabled"] is False
    assert data["m1_parameters"] == {
        "include_m1": False,
        "inspect_position": "G28",
        "stop_spindle": False,
    }

    loaded = Operation.from_dict(data)
    assert loaded.to_dict() == data
    assert display_name_for_op("grooveRoughing", profile_id=1) == "Groove Roughing (P1)"
