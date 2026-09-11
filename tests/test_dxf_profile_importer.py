import math

import pytest

from teachinlathe.conversational.data_types import DefineProfile, ImportDxfProfile
from teachinlathe.conversational.dxf_profile_importer import (
    DxfProfileImportError,
    ProfilePoint,
    ProfileSegment,
    _bulge_segment,
    define_profile_from_segments,
    read_dxf_profile,
)


def test_define_profile_from_connected_segments():
    payload = define_profile_from_segments(
        [
            ProfileSegment("line", ProfilePoint(30, 0), ProfilePoint(30, -10)),
            ProfileSegment("line", ProfilePoint(30, -10), ProfilePoint(25, -12)),
        ],
        profile_id=3,
        profile_type="id",
        order=7,
    )

    assert payload["order"] == 7
    assert payload["type"] == "defineProfile"
    assert payload["profile_id"] == 3
    assert payload["profile_type"] == "id"
    assert payload["profile_primitives"] == [
        {
            "primitive_id": 1,
            "type": "startPoint",
            "x_start": 30.0,
            "z_start": 0.0,
            "blend": {
                "type": "none",
                "chamfer_width": 0.0,
                "fillet_radius": 0.0,
                "undercut_radius": 0.4,
                "undercut_depth": 0.4,
                "undercut_length": 2.5,
            },
        },
        {
            "primitive_id": 2,
            "type": "lineTo",
            "x_end": 30.0,
            "z_end": -10.0,
            "angle": 0.0,
            "input": "xz",
            "blend": {
                "type": "none",
                "chamfer_width": 0.0,
                "fillet_radius": 0.0,
                "undercut_radius": 0.4,
                "undercut_depth": 0.4,
                "undercut_length": 2.5,
            },
        },
        {
            "primitive_id": 3,
            "type": "lineTo",
            "x_end": 25.0,
            "z_end": -12.0,
            "angle": 0.0,
            "input": "xz",
            "blend": {
                "type": "none",
                "chamfer_width": 0.0,
                "fillet_radius": 0.0,
                "undercut_radius": 0.4,
                "undercut_depth": 0.4,
                "undercut_length": 2.5,
            },
        },
    ]

    parsed = DefineProfile.from_dict(payload)
    assert parsed.to_dict() == payload


def test_define_profile_reverses_segments_to_build_chain():
    payload = define_profile_from_segments(
        [
            ProfileSegment("line", ProfilePoint(10, 0), ProfilePoint(20, 0)),
            ProfileSegment("line", ProfilePoint(30, 0), ProfilePoint(20, 0)),
        ],
    )

    assert payload["profile_primitives"][0]["x_start"] == 10.0
    assert payload["profile_primitives"][1]["x_end"] == 20.0
    assert payload["profile_primitives"][2]["x_end"] == 30.0


def test_import_dxf_profile_payload_keeps_file_path():
    payload = define_profile_from_segments(
        [
            ProfileSegment("line", ProfilePoint(30, 0), ProfilePoint(30, -10)),
        ],
        operation_type="importDxfProfile",
        dxf_file_path="/tmp/profile.dxf",
    )

    assert payload["type"] == "importDxfProfile"
    assert payload["dxfFilePath"] == "/tmp/profile.dxf"

    parsed = ImportDxfProfile.from_dict(payload)
    assert parsed.to_dict() == payload


def test_symmetric_full_lathe_profile_imports_only_one_half_as_diameter_profile():
    payload = define_profile_from_segments(
        [
            ProfileSegment("line", ProfilePoint(15, 0), ProfilePoint(15, -10)),
            ProfileSegment("line", ProfilePoint(-15, 0), ProfilePoint(-15, -10)),
            ProfileSegment("line", ProfilePoint(15, 0), ProfilePoint(-15, 0)),
            ProfileSegment("line", ProfilePoint(15, -10), ProfilePoint(-15, -10)),
        ]
    )

    assert payload["profile_primitives"] == [
        {
            "primitive_id": 1,
            "type": "startPoint",
            "x_start": 30.0,
            "z_start": 0.0,
            "blend": {
                "type": "none",
                "chamfer_width": 0.0,
                "fillet_radius": 0.0,
                "undercut_radius": 0.4,
                "undercut_depth": 0.4,
                "undercut_length": 2.5,
            },
        },
        {
            "primitive_id": 2,
            "type": "lineTo",
            "x_end": 30.0,
            "z_end": -10.0,
            "angle": 0.0,
            "input": "xz",
            "blend": {
                "type": "none",
                "chamfer_width": 0.0,
                "fillet_radius": 0.0,
                "undercut_radius": 0.4,
                "undercut_depth": 0.4,
                "undercut_length": 2.5,
            },
        },
    ]


def test_define_profile_rejects_disconnected_segments():
    with pytest.raises(DxfProfileImportError):
        define_profile_from_segments(
            [
                ProfileSegment("line", ProfilePoint(10, 0), ProfilePoint(20, 0)),
                ProfileSegment("line", ProfilePoint(10, -5), ProfilePoint(20, -5)),
            ]
        )


def test_bulge_segment_creates_arc():
    segment = _bulge_segment((1.0, 0.0), (0.0, 1.0), math.tan(math.radians(90) / 4.0))

    assert segment.type == "arc"
    assert segment.direction == "ccw"
    assert segment.start == ProfilePoint(x=0.0, z=1.0)
    assert segment.end == ProfilePoint(x=1.0, z=0.0)
    assert segment.center is not None
    assert segment.center.x == pytest.approx(0.0)
    assert segment.center.z == pytest.approx(0.0)
    assert segment.radius == pytest.approx(1.0)


def test_read_dxf_profile_with_ezdxf(tmp_path):
    ezdxf = pytest.importorskip("ezdxf")

    path = tmp_path / "profile.dxf"
    doc = ezdxf.new("R2000")
    msp = doc.modelspace()
    msp.add_line((0, 30), (-10, 30))
    msp.add_line((-10, 30), (-12, 25))
    doc.saveas(path)

    payload = read_dxf_profile(path, profile_id=2)

    assert payload["profile_id"] == 2
    assert payload["profile_primitives"][0]["type"] == "startPoint"
    assert payload["profile_primitives"][0]["x_start"] == 30.0
    assert payload["profile_primitives"][0]["z_start"] == 0.0
    assert payload["profile_primitives"][2]["x_end"] == 25.0
    assert payload["profile_primitives"][2]["z_end"] == -12.0
