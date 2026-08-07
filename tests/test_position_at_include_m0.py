import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.data_types import (
    MoveSequence,
    PositionAt,
    PositionDetails,
)

POSITION_AT_GENERATOR = (
    ROOT
    / "src"
    / "teachinlathe"
    / "widgets"
    / "conversational_qml"
    / "gcode_builder"
    / "operations"
    / "position_at.py"
)


def _load_position_at_generator():
    spec = importlib.util.spec_from_file_location("position_at_generator", POSITION_AT_GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generate_position_at_gcode


def test_position_at_include_m0_serializes_and_generates_pause():
    generate_position_at_gcode = _load_position_at_generator()
    details = PositionDetails(
        x_pos=12.0,
        z_pos=-5.0,
        move_sequence=MoveSequence.XZ,
        stop_spindle_before_positioning=True,
        include_m0=True,
    )
    op = PositionAt(
        order=1,
        type="positionAt",
        generate_gcode=True,
        is_optional_block=False,
        position_details=details,
    )

    assert op.to_dict()["position_details"]["include_m0"] is True
    assert op.to_dict()["position_details"]["stop_spindle_before_positioning"] is True
    assert "coordinate_type" not in op.to_dict()["position_details"]
    assert generate_position_at_gcode(op) == [
        "M5   (stop the spindle)",
        "",
        "G90  (absolute distance mode)",
        "G0 X12.000",
        "G0 Z-5.000",
        "",
        "M0   (pause program)",
    ]
