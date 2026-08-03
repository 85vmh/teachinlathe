import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.data_types import (  # noqa: E402
    G33Threading,
    M1Parameters,
    PredefinedPosition,
    SpindleMode,
    SpindleParameters,
    ThreadLocation,
)

BASE = SRC / "teachinlathe" / "widgets" / "conversational_qml" / "gcode_builder"


def _load_g33_threading_module():
    for name in ["g33test", "g33test.helpers", "g33test.operations"]:
        package = types.ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package

    for fullname, path in [
        ("g33test.config", BASE / "config.py"),
        ("g33test.helpers.utils", BASE / "helpers" / "utils.py"),
        ("g33test.helpers.m1", BASE / "helpers" / "m1.py"),
        ("g33test.helpers.spindle", BASE / "helpers" / "spindle.py"),
        ("g33test.operations.g33_threading", BASE / "operations" / "g33_threading.py"),
    ]:
        spec = importlib.util.spec_from_file_location(fullname, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = module
        spec.loader.exec_module(module)

    return sys.modules["g33test.operations.g33_threading"].generate_g33_threading_gcode


def _op(**overrides):
    values = {
        "order": 1,
        "type": "g33Threading",
        "generate_gcode": True,
        "is_optional_block": False,
        "spindleParameters": SpindleParameters(direction=-1, mode=SpindleMode.RPM, rpm_value=500),
        "location": ThreadLocation.OD,
        "thread_type": "g33",
        "pitch": 1.5,
        "starts": 1,
        "major_diameter": 20.0,
        "minor_diameter": 18.0,
        "z_start": 0.0,
        "z_end": -12.0,
        "initial_doc": 1.0,
        "retract": 1.0,
        "spring_passes": 0,
        "minimum_radial_increment": 0.0,
        "taper_type": 0,
        "compound_angle": 0.0,
        "m1Parameters": M1Parameters(
            include_m1=False,
            inspect_position=PredefinedPosition.G28,
            stop_spindle=False,
        ),
    }
    values.update(overrides)
    return G33Threading(**values)


def test_g33_threading_generator_emits_basic_pass_geometry():
    generate_g33_threading_gcode = _load_g33_threading_module()
    lines = generate_g33_threading_gcode(_op())

    assert lines == [
        "G97 M4 S500",
        "(G33 roughing pass 1)",
        "G0 X21.000 Z0.000",
        "G0 X18.000",
        "G33 Z-12.000 K1.500 D0.000",
        "G0 X21.000",
    ]


def test_g33_threading_generator_emits_m1_after_each_g33_for_each_start():
    generate_g33_threading_gcode = _load_g33_threading_module()
    lines = generate_g33_threading_gcode(
        _op(
            starts=2,
            initial_doc=1.0,
            m1Parameters=M1Parameters(
                include_m1=True,
                inspect_position=PredefinedPosition.G30,
                stop_spindle=False,
            ),
        )
    )

    g33_lines = [line for line in lines if line.startswith("G33 ")]
    m1_lines = [line for line in lines if line.startswith("o<m1_handling> call")]

    assert g33_lines == [
        "G33 Z-12.000 K3.000 D0.000",
        "G33 Z-12.000 K3.000 D180.000",
    ]
    assert m1_lines == [
        "o<m1_handling> call [1] [21.000] [-12.000] [-1]",
        "o<m1_handling> call [1] [21.000] [-12.000] [-1]",
    ]


def test_g33_threading_generator_completes_one_start_before_next_start():
    generate_g33_threading_gcode = _load_g33_threading_module()
    lines = generate_g33_threading_gcode(_op(starts=2, initial_doc=0.8))

    comments = [line for line in lines if line.startswith("(G33 ")]
    g33_lines = [line for line in lines if line.startswith("G33 ")]

    assert comments == [
        "(G33 roughing pass 1, start 1)",
        "(G33 roughing pass 2, start 1)",
        "(G33 roughing pass 1, start 2)",
        "(G33 roughing pass 2, start 2)",
    ]
    assert g33_lines == [
        "G33 Z-12.000 K3.000 D0.000",
        "G33 Z-12.000 K3.000 D0.000",
        "G33 Z-12.000 K3.000 D180.000",
        "G33 Z-12.000 K3.000 D180.000",
    ]
