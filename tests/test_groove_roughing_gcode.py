import sys
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
os.environ["HOME"] = "/tmp"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.gcode.operations.groove_roughing import (
    generate_groove_roughing_gcode,
)


def _op(tool_type="parting_blade", orientation=6):
    return {
        "type": "grooveRoughing",
        "is_optional_block": False,
        "speeds_and_feeds": {
            "direction": "M4",
            "mode": "rpm",
            "rpm_value": 1000,
            "feed_rate": 0.1,
        },
        "cutting_parameters": {
            "peck_depth": 3.0,
            "retract": 1.0,
            "dwell_time": 0.5,
        },
        "roughing_parameters": {
            "profile_id": 1,
            "strategy": "start_center",
            "initial_offset": 1.5,
            "afterwards_offset": 1.0,
        },
        "stock_to_leave": {
            "radial": 0.5,
            "axial": 0.2,
        },
        "stock_to_leave_enabled": True,
        "_resolved_tool": {
            "t": 1,
            "q": orientation,
            "tool_type": tool_type,
            "width": 3.0,
            "left_radius": 0.1,
            "right_radius": 0.1,
        },
        "_resolved_radial_profile": {
            "profile_id": 1,
            "profile_type": "od",
            "profile_primitives": [
                {
                    "primitive_id": 1,
                    "type": "groove",
                    "right_flank": {
                        "x_start": 40.0,
                        "z_start": -20.0,
                        "angle": 0.0,
                        "start_blend": {"type": "none"},
                    },
                    "bottom": {
                        "x_end_right": 30.0,
                        "x_end_left": 30.0,
                        "blend_right": {"type": "none"},
                        "blend_left": {"type": "none"},
                    },
                    "left_flank": {
                        "x_start": 40.0,
                        "z_start": -30.0,
                        "angle": 0.0,
                        "start_blend": {"type": "none"},
                    },
                }
            ],
        },
    }


def test_groove_roughing_start_center_generates_pecks_and_contour():
    lines = generate_groove_roughing_gcode(_op())

    assert "G97 M4 S1000" in lines
    assert "G95 F0.100" in lines
    assert "(----------Groove Roughing: Start Center P1----------)" in lines
    # the start diameter 40 + 2 x 0.5 radial stock, the blade the 1 mm
    # clearance (2 on the diameter) out from it
    assert lines[lines.index("(----------Groove Roughing Initial Center Pair----------)") + 1] == "G0 X43.000"
    assert "G0 Z-24.250" in lines
    assert "G0 Z-25.750" in lines
    # the bottom at 30, with the radial stock to leave
    assert "G1 X31.000 F0.100" in lines
    assert "(----------Groove Roughing Finish Contour Z+ to Center----------)" in lines
    assert "(----------Groove Roughing Finish Contour Z- to Center----------)" in lines


def test_groove_roughing_requires_blade_tool():
    lines = generate_groove_roughing_gcode(_op(tool_type="generic", orientation=1))

    assert lines[-1] == "( ERROR: Groove Roughing -- current tool must be a parting or grooving blade )"
