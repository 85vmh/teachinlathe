import importlib.util
import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "src" / "teachinlathe" / "widgets" / "conversational_qml" / "gcode_builder"
CONVERSATIONAL_SRC = ROOT / "src"
if str(CONVERSATIONAL_SRC) not in sys.path:
    sys.path.insert(0, str(CONVERSATIONAL_SRC))

from teachinlathe.conversational.data_types import PassType


def _load_diagonal_modules():
    for name in ["x", "x.operations", "x.operations.profiling"]:
        package = types.ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package

    module_order = [
        ("x.config", BASE / "config.py"),
        ("x.operations.profiling.geometry", BASE / "operations" / "profiling" / "geometry.py"),
        ("x.operations.profiling.context", BASE / "operations" / "profiling" / "context.py"),
        ("x.operations.profiling.diagonal", BASE / "operations" / "profiling" / "diagonal.py"),
    ]
    for fullname, path in module_order:
        spec = importlib.util.spec_from_file_location(fullname, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = module
        spec.loader.exec_module(module)

    return (
        sys.modules["x.operations.profiling.context"].RoughingContext,
        sys.modules["x.operations.profiling.diagonal"].emit_diagonal_roughing,
        sys.modules["x.operations.profiling.geometry"].StartPoint,
        sys.modules["x.operations.profiling.geometry"].ToolpathArc,
        sys.modules["x.operations.profiling.geometry"].ToolpathLine,
    )


def _debug_case():
    RoughingContext, emit_diagonal_roughing, StartPoint, ToolpathArc, ToolpathLine = _load_diagonal_modules()
    context = RoughingContext(
        x_start=15.0,
        z_start=0.0,
        doc=1.0,
        retract=0.3,
        stock_x=0.5,
        stock_z=0.1,
        optional_prefix="",
        x_safe=14.7,
        x_limit=39.5,
        x_direction=1,
        stock_x_sign=-1,
    )
    path = [
        StartPoint(x=39.5, z=0.1),
        ToolpathLine(end_x=39.5, end_z=-12.667908047326835),
        ToolpathArc(
            end_x=37.362043656699036,
            end_z=-15.54138690299029,
            center_x=36.5,
            center_z=-12.667908047326835,
            anticlockwise=False,
        ),
        ToolpathLine(end_x=30.538193505282027, end_z=-17.58854194841539),
        ToolpathArc(
            end_x=29.19415827327218,
            end_z=-18.939861870874594,
            center_x=31.11288927641472,
            center_z=-19.50419451885769,
            anticlockwise=True,
        ),
        ToolpathLine(end_x=24.65292086336391, end_z=-34.380069064562704),
        ToolpathArc(
            end_x=23.980903247358984,
            end_z=-35.0557290257923,
            center_x=23.69355536179264,
            center_z=-34.09790274057115,
            anticlockwise=False,
        ),
        ToolpathLine(end_x=15.0, end_z=-37.75),
    ]
    return context, emit_diagonal_roughing, path


def test_profile_diagonal_interior_logged_case_writes_gcode(capsys):
    context, emit_diagonal_roughing, path = _debug_case()

    lines = []
    emit_diagonal_roughing(
        lines=lines,
        context=context,
        path=path,
        x_cut_limit=39.5,
        z_cut_deepest=-37.75,
        pass_type=PassType.DIAGONAL_INTERIOR,
    )

    assert lines
    assert lines[1:6] == [
        "G0 X16.000 Z0.300",
        "G1 Z0.000",
        "G1 X15.000 Z-1.000",
        "G1 X14.700",
        "G0 X16.000 Z0.300",
    ]
    with capsys.disabled():
        print("\n--- generated diagonal interior gcode ---")
        print("\n".join(lines))


def test_profile_diagonal_exterior_logged_case_writes_gcode(capsys):
    context, emit_diagonal_roughing, path = _debug_case()

    lines = []
    emit_diagonal_roughing(
        lines=lines,
        context=context,
        path=path,
        x_cut_limit=39.5,
        z_cut_deepest=-37.75,
        pass_type=PassType.DIAGONAL_EXTERIOR,
    )

    assert lines
    assert lines[1:6] == [
        "G0 X14.700 Z-1.000",
        "G1 X15.000",
        "G1 X16.000 Z0.000",
        "G1 Z0.300",
        "G0 X14.700 Z-1.000",
    ]
    with capsys.disabled():
        print("\n--- generated diagonal exterior gcode ---")
        print("\n".join(lines))
