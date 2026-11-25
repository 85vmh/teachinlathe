import math

import pytest

from teachinlathe.conversational.model.data_types import DefineProfile, ImportDxfProfile
from teachinlathe.conversational.store.dxf_profile_importer import (
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


def test_import_dxf_profile_payload_keeps_no_file_path():
    # the drawing is nothing to the profile once read: not where it was either
    payload = define_profile_from_segments(
        [
            ProfileSegment("line", ProfilePoint(30, 0), ProfilePoint(30, -10)),
        ],
        operation_type="importDxfProfile",
    )

    assert payload["type"] == "importDxfProfile"
    assert "dxfFilePath" not in payload

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
    # counter-clockwise in the DXF's (X, Y) is clockwise to the profile,
    # whose (Z, X) are the DXF's (X, Y): its angle about the centre grows there
    assert segment.direction == "cw"
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


# ---------------------------------------------------------------------------
# The profile imported goes through the drawing: every point of every DXF arc
# and line, as ezdxf itself places it, is on the profile as the G-code reads it
# (geometry.arc_x_at_z for an arc). Nothing here repeats the importer's own
# reasoning about directions, axes or mirroring.
# ---------------------------------------------------------------------------

GROOVE_HALF_ANGLE = math.degrees(math.asin(5.837 / 10.0))


def _roller_dxf(path):
    """A roller like a real one drawn in SolidWorks: both halves of a
    Ø50 x 60 part about the DXF's X axis, R1 at both ends and one V groove
    with an R10 bottom in its middle - so it is as symmetric about its middle
    as about its axis - with its end faces and the groove's silhouette lines
    across the axis. The upper half, the one imported, has every kind of arc:
    its corners are ARCs mirrored by their extrusion (-Z), its groove's bottom
    a bulged LWPOLYLINE; the lower half has plain ARCs."""
    import ezdxf
    from ezdxf.math import OCS

    doc = ezdxf.new("R2000")
    msp = doc.modelspace()
    gx = 10.0 * math.sin(math.radians(GROOVE_HALF_ANGLE))          # 5.837
    gy = 23.0 - 10.0 * math.cos(math.radians(GROOVE_HALF_ANGLE))   # 14.88
    for (a, b) in [((-1, 25), (-18, 25)), ((-18, 25), (-30 + gx, gy)),
                   ((-30 - gx, gy), (-42, 25)), ((-42, 25), (-59, 25))]:
        msp.add_line(a, b)
        msp.add_line((a[0], -a[1]), (b[0], -b[1]))
    # the upper corners: in an OCS whose X is the drawing's -X
    mirrored = {"extrusion": (0, 0, -1)}
    assert OCS((0, 0, -1)).to_wcs((1, 2, 0)).isclose((-1, 2, 0))
    msp.add_arc((1, 24), 1, 90, 180, dxfattribs=mirrored)    # (0, 24) - (-1, 25)
    msp.add_arc((59, 24), 1, 0, 90, dxfattribs=mirrored)     # (-59, 25) - (-60, 24)
    # the upper groove's bottom: from right to left, dipping down to Y 13
    bulge = -math.tan(math.radians(2 * GROOVE_HALF_ANGLE) / 4.0)
    msp.add_lwpolyline([(-30 + gx, gy, bulge), (-30 - gx, gy, 0)], format="xyb")
    # the lower half's arcs, plain
    msp.add_arc((-1, -24), 1, 270, 360)
    msp.add_arc((-59, -24), 1, 180, 270)
    msp.add_arc((-30, -23), 10, 90 - GROOVE_HALF_ANGLE, 90 + GROOVE_HALF_ANGLE)
    # across the axis: the end faces and the silhouette lines
    msp.add_line((0, 24), (0, -24))
    msp.add_line((-60, -24), (-60, 24))
    for x in (-1, -18, -42, -59):
        msp.add_line((x, 25), (x, -25))
    for x in (-30 + gx, -30 - gx):
        msp.add_line((x, gy), (x, -gy))
    doc.saveas(path)
    return doc


def _traced(entity):
    """Points of the entity, exactly on it, in the drawing's coordinates
    (ezdxf takes an arc's out of its OCS)."""
    kind = entity.dxftype()
    if kind == "LINE":
        start, end = entity.dxf.start, entity.dxf.end
        return [start, start.lerp(end, 0.5), end]
    if kind == "LWPOLYLINE":
        return [p for part in entity.virtual_entities() for p in _traced(part)]
    return list(entity.flattening(0.05))


def _on_profile(primitives, x, z, tol=1e-6):
    """Whether (x, z) - X a diameter - is on the profile as the G-code reads it."""
    from teachinlathe.conversational.gcode.operations.profiling.geometry import arc_x_at_z

    at_x, at_z = primitives[0]["x_start"], primitives[0]["z_start"]
    for p in primitives[1:]:
        ex, ez = p["x_end"], p["z_end"]
        if p["type"] == "arcTo":
            xs = arc_x_at_z(at_x, at_z, ex, ez, p["x_center"], p["z_center"],
                            p["direction"] == "ccw", z)
            if any(abs(candidate - x) <= tol for candidate in xs):
                return True
        else:
            dz, dx = ez - at_z, ex - at_x
            length = math.hypot(dz, dx)
            t = min(1.0, max(0.0, ((z - at_z) * dz + (x - at_x) * dx) / (length * length)))
            if math.hypot(at_z + t * dz - z, at_x + t * dx - x) <= tol:
                return True
        at_x, at_z = ex, ez
    return False


def test_imported_roller_goes_through_every_point_of_its_upper_half(tmp_path):
    pytest.importorskip("ezdxf")
    path = tmp_path / "roller.dxf"
    doc = _roller_dxf(path)

    primitives = read_dxf_profile(path)["profile_primitives"]

    assert [p["arc_radius"] for p in primitives if p["type"] == "arcTo"] == pytest.approx([1.0, 10.0, 1.0])
    checked = 0
    for entity in doc.modelspace():
        for point in _traced(entity):
            # the upper half, but for the lines across the axis
            if point.y > 1e-6 and not (entity.dxftype() == "LINE"
                                       and entity.dxf.start.x == entity.dxf.end.x):
                checked += 1
                assert _on_profile(primitives, 2 * point.y, point.x), (
                    f"{entity.dxftype()} point (X{2 * point.y:.4f} Z{point.x:.4f}) is not on the profile")
    assert checked > 20
