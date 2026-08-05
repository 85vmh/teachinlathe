import importlib.util
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
BASE = SRC / "teachinlathe" / "widgets" / "conversational_qml" / "gcode_builder"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.data_types import (  # noqa: E402
    BlendType,
    DefineProfile,
    LineTo,
    ProfileBlend,
    ProfilingType,
    StartPoint,
    Workpiece,
)


def _load_define_profile_module():
    for name in ["x", "x.operations"]:
        package = types.ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package

    for fullname, path in [
        ("x.config", BASE / "config.py"),
        ("x.operations.define_profile", BASE / "operations" / "define_profile.py"),
    ]:
        spec = importlib.util.spec_from_file_location(fullname, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = module
        spec.loader.exec_module(module)

    return sys.modules["x.operations.define_profile"].generate_define_profile_gcode


def _load_profiling_geometry_module():
    for name in ["y", "y.operations", "y.operations.profiling"]:
        package = types.ModuleType(name)
        package.__path__ = []
        sys.modules[name] = package

    spec = importlib.util.spec_from_file_location(
        "y.operations.profiling.geometry",
        BASE / "operations" / "profiling" / "geometry.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["y.operations.profiling.geometry"] = module
    spec.loader.exec_module(module)
    return module


def test_define_profile_din509_undercut_uses_radius_floor_and_15_degree_ramp():
    generate_define_profile_gcode = _load_define_profile_module()
    op = DefineProfile(
        order=1,
        type="defineProfile",
        generate_gcode=True,
        is_optional_block=False,
        profile_id=7,
        profile_type=ProfilingType.OD,
        profile_primitives=[
            StartPoint(
                primitive_id=1,
                primitive_type="startPoint",
                x_start=10.0,
                z_start=0.0,
            ),
            LineTo(
                primitive_id=2,
                primitive_type="lineTo",
                x_end=10.0,
                z_end=-10.0,
                blend=ProfileBlend(
                    blend_type=BlendType.UNDERCUT_DIN509,
                    undercut_radius=1.0,
                    undercut_depth=1.0,
                    undercut_length=6.0,
                ),
            ),
            LineTo(
                primitive_id=3,
                primitive_type="lineTo",
                x_end=20.0,
                z_end=-10.0,
                blend=ProfileBlend(blend_type=BlendType.NONE),
            ),
        ],
    )

    assert generate_define_profile_gcode(op) == [
        "O7 SUB",
        "\tG0 X10.000 Z0.000",
        "\tG1 X10.000 Z-4.000",
        "\tG1 X8.000 Z-7.732",
        "\tG1 X8.000 Z-9.000",
        "\tG3 X10.000 Z-10.000 I1.000 K0.000",
        "\tG1 X20.000 Z-10.000",
        "O7 ENDSUB",
    ]


def test_profiling_render_path_includes_din509_undercut_geometry():
    geometry = _load_profiling_geometry_module()
    primitives = [
        {
            "type": "startPoint",
            "x_start": 10.0,
            "z_start": 0.0,
            "blend": {"type": "none"},
        },
        {
            "type": "lineTo",
            "x_end": 10.0,
            "z_end": -10.0,
            "blend": {
                "type": "undercut_din509",
                "undercut_radius": 1.0,
                "undercut_depth": 1.0,
                "undercut_length": 6.0,
            },
        },
        {
            "type": "lineTo",
            "x_end": 20.0,
            "z_end": -10.0,
            "blend": {"type": "none"},
        },
    ]

    segments = geometry.build_profile_segments(primitives)
    path = geometry.build_render_path(segments, "od")

    assert path[0] == geometry.StartPoint(10.0, 0.0)
    assert path[1] == geometry.ToolpathLine(10.0, -4.0)
    assert path[2].end_x == pytest.approx(8.0)
    assert path[2].end_z == pytest.approx(-7.732050807568877)
    assert path[3] == geometry.ToolpathLine(8.0, -9.0)
    assert path[4] == geometry.ToolpathArc(10.0, -10.0, 10.0, -9.0, True)
    assert path[5] == geometry.ToolpathLine(20.0, -10.0)


def test_profiling_din509_undercut_arc_is_tangent_to_obtuse_next_line():
    geometry = _load_profiling_geometry_module()
    primitives = [
        {
            "type": "startPoint",
            "x_start": 10.0,
            "z_start": 0.0,
            "blend": {"type": "none"},
        },
        {
            "type": "lineTo",
            "x_end": 10.0,
            "z_end": -10.0,
            "blend": {
                "type": "undercut_din509",
                "undercut_radius": 1.0,
                "undercut_depth": 1.0,
                "undercut_length": 6.0,
            },
        },
        {
            "type": "lineTo",
            "x_end": 20.0,
            "z_end": -5.0,
            "blend": {"type": "none"},
        },
    ]

    path = geometry.build_render_path(geometry.build_profile_segments(primitives), "od")

    assert len(path) == 6
    arc_start = path[3]
    arc = path[4]
    next_line = path[5]
    assert isinstance(arc, geometry.ToolpathArc)
    assert next_line == geometry.ToolpathLine(20.0, -5.0)

    start_radius_x = (arc_start.end_x - arc.center_x) / 2.0
    start_radius_z = arc_start.end_z - arc.center_z
    end_radius_x = (arc.end_x - arc.center_x) / 2.0
    end_radius_z = arc.end_z - arc.center_z

    incoming_floor_dir_x = 0.0
    incoming_floor_dir_z = -1.0
    next_dir_x = (next_line.end_x - arc.end_x) / 2.0
    next_dir_z = next_line.end_z - arc.end_z
    next_len = (next_dir_x ** 2 + next_dir_z ** 2) ** 0.5
    next_dir_x /= next_len
    next_dir_z /= next_len

    assert start_radius_x * incoming_floor_dir_x + start_radius_z * incoming_floor_dir_z == pytest.approx(0.0)
    assert end_radius_x * next_dir_x + end_radius_z * next_dir_z == pytest.approx(0.0)


def test_line_to_defaults_missing_input_to_xz_for_backward_compatibility():
    primitive = LineTo.from_dict({
        "type": "lineTo",
        "primitive_id": 4,
        "x_end": 12.0,
        "z_end": -8.0,
        "blend": {"type": "none"},
    })

    assert primitive.input == "xz"
    assert primitive.angle == pytest.approx(0.0)
    assert primitive.to_dict()["input"] == "xz"


def test_workpiece_defaults_missing_stock_length_for_backward_compatibility():
    workpiece = Workpiece.from_dict({
        "material": "",
        "external_diameter": 40.0,
        "internal_diameter": 0.0,
        "stickout_length": 80.0,
    })

    assert workpiece.stock_length == pytest.approx(0.0)
    assert workpiece.to_dict()["stock_length"] == pytest.approx(0.0)


def test_define_profile_resolves_angle_and_z_line_to_with_siemens_angle_convention():
    generate_define_profile_gcode = _load_define_profile_module()
    op = DefineProfile(
        order=1,
        type="defineProfile",
        generate_gcode=True,
        is_optional_block=False,
        profile_id=8,
        profile_type=ProfilingType.OD,
        profile_primitives=[
            StartPoint(
                primitive_id=1,
                primitive_type="startPoint",
                x_start=10.0,
                z_start=0.0,
            ),
            LineTo(
                primitive_id=2,
                primitive_type="lineTo",
                x_end=0.0,
                z_end=10.0,
                angle=45.0,
                input="az",
                blend=ProfileBlend(blend_type=BlendType.NONE),
            ),
        ],
    )

    assert generate_define_profile_gcode(op) == [
        "O8 SUB",
        "\tG0 X10.000 Z0.000",
        "\tG1 X30.000 Z10.000",
        "O8 ENDSUB",
    ]


def test_define_profile_resolves_angle_and_x_line_to_with_siemens_angle_convention():
    generate_define_profile_gcode = _load_define_profile_module()
    op = DefineProfile(
        order=1,
        type="defineProfile",
        generate_gcode=True,
        is_optional_block=False,
        profile_id=9,
        profile_type=ProfilingType.OD,
        profile_primitives=[
            StartPoint(
                primitive_id=1,
                primitive_type="startPoint",
                x_start=10.0,
                z_start=0.0,
            ),
            LineTo(
                primitive_id=2,
                primitive_type="lineTo",
                x_end=30.0,
                z_end=0.0,
                angle=45.0,
                input="ax",
                blend=ProfileBlend(blend_type=BlendType.NONE),
            ),
        ],
    )

    assert generate_define_profile_gcode(op) == [
        "O9 SUB",
        "\tG0 X10.000 Z0.000",
        "\tG1 X30.000 Z10.000",
        "O9 ENDSUB",
    ]


def test_profiling_geometry_resolves_angle_line_to_endpoint():
    geometry = _load_profiling_geometry_module()
    primitives = [
        {
            "type": "startPoint",
            "x_start": 10.0,
            "z_start": 0.0,
            "blend": {"type": "none"},
        },
        {
            "type": "lineTo",
            "x_end": 0.0,
            "z_end": 10.0,
            "angle": 45.0,
            "input": "az",
            "blend": {"type": "none"},
        },
    ]

    segments = geometry.build_profile_segments(primitives)

    assert segments[1].end_x == pytest.approx(30.0)
    assert segments[1].end_z == pytest.approx(10.0)
