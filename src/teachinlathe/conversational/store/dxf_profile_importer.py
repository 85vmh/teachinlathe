"""Import 2D DXF geometry as a Define Profile operation payload.

The importer assumes the DXF is drawn in the lathe profile plane:
DXF X maps to profile Z, DXF Y maps to profile X.
If the DXF contains a complete lathe section, the importer detects the
centerline symmetry axis and keeps only one half. The radial distance from
that centerline is converted to the X diameter used by TeachInLathe.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, NamedTuple


#: How far apart two points may be and still be the same one (mm).
DEFAULT_TOLERANCE = 1e-5

#: The share of a drawing's points with a mirror image across an axis for the
#: drawing to be taken as symmetric about it (_symmetry_score).
MIN_SYMMETRY_SCORE = 0.7

DEFAULT_BLEND = {
    "type": "none",
    "chamfer_width": 0.0,
    "fillet_radius": 0.0,
    "undercut_radius": 0.4,
    "undercut_depth": 0.4,
    "undercut_length": 2.5,
}


class DxfProfileImportError(ValueError):
    """Raised when DXF geometry cannot be converted into one profile chain.
    ``symmetry_ambiguous``: the drawing is symmetric both ways, and turned
    (``profile_from_segments``) it may give one."""

    def __init__(self, message: str, *, symmetry_ambiguous: bool = False):
        super().__init__(message)
        self.symmetry_ambiguous = symmetry_ambiguous


@dataclass(frozen=True)
class ProfilePoint:
    x: float
    z: float


@dataclass(frozen=True)
class ProfileSegment:
    """A line, or an arc from ``start`` to ``end`` about ``center`` through
    ``mid``, a point halfway along it.

    An arc keeps no direction: every step from the DXF to the profile (axes
    swapped, a half mirrored, reversed to chain) moves its points, and its
    direction is read from them at the end (``direction``) - a direction
    carried along instead has to be flipped by each of those steps, and was
    not."""
    type: str
    start: ProfilePoint
    end: ProfilePoint
    center: ProfilePoint | None = None
    radius: float = 0.0
    mid: ProfilePoint | None = None

    @property
    def direction(self) -> str:
        """The arc's direction as the profile model has it: clockwise when
        its angle about the centre grows in the (Z, X) plane (the
        convention of ``groove_outline.cut_corner``)."""
        if self.center is None or self.mid is None:
            raise DxfProfileImportError("An arc without its centre or a point along it.")
        c = self.center
        cross = ((self.start.z - c.z) * (self.mid.x - c.x)
                 - (self.start.x - c.x) * (self.mid.z - c.z))
        return "cw" if cross > 0 else "ccw"

    def reversed(self) -> "ProfileSegment":
        return replace(self, start=self.end, end=self.start)

    def mapped(self, fn) -> "ProfileSegment":
        """The segment with ``fn`` applied to each of its points; the radius
        stays (only X is a diameter, and the radius is as it is drawn)."""
        return replace(
            self,
            start=fn(self.start),
            end=fn(self.end),
            center=fn(self.center) if self.center is not None else None,
            mid=fn(self.mid) if self.mid is not None else None,
        )


@dataclass(frozen=True)
class DxfProfile:
    """What a drawing gives a profile: its primitives, and whether the
    drawing is symmetric about both its horizontal and its vertical middle -
    so that it does not say which is the lathe's axis (``profile_from_segments``)."""
    primitives: list
    symmetry_ambiguous: bool = False


def read_dxf_segments(filename: str | Path, *, layer: str | None = None) -> list[ProfileSegment]:
    """The lines and arcs of a DXF file's model space (of ``layer`` alone, if given)."""
    try:
        import ezdxf
        from ezdxf import recover
    except ImportError as exc:
        raise DxfProfileImportError(
            "DXF import requires the 'ezdxf' Python package."
        ) from exc

    path = Path(filename)
    try:
        doc = ezdxf.readfile(path)
    except ezdxf.DXFStructureError:
        doc, auditor = recover.readfile(path)
        if auditor.has_errors:
            raise DxfProfileImportError(f"DXF file could not be recovered: {path}")
    return _segments_from_entities(doc.modelspace(), layer=layer)


def read_dxf_profile(
    filename: str | Path,
    *,
    profile_id: int = 1,
    profile_type: str = "od",
    order: int = 1,
    operation_type: str = "defineProfile",
    layer: str | None = None,
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict[str, Any]:
    """Read a DXF file and return a profile operation dict."""
    return define_profile_from_segments(
        read_dxf_segments(filename, layer=layer),
        profile_id=profile_id,
        profile_type=profile_type,
        order=order,
        operation_type=operation_type,
        tolerance=tolerance,
    )


def profile_from_segments(
    segments: Iterable[ProfileSegment],
    *,
    quarter_turns: int = 0,
    tolerance: float = DEFAULT_TOLERANCE,
) -> DxfProfile:
    """The Define Profile primitives of a drawing's segments.

    The drawing is first turned ``quarter_turns`` times 90° counter-clockwise
    (negative: clockwise). Its axis is the one it is symmetric about: when it
    is symmetric about both its horizontal and its vertical middle (a plain
    shaft drawn whole, a roller the same at both ends), the drawing does not
    say which is the axis - the horizontal one is taken, and
    ``symmetry_ambiguous`` says so: turning the drawing makes the other one
    the axis, or the part's other end Z0."""

    segments = list(segments)
    for _ in range(quarter_turns % 4):
        # (X, Y) -> (-Y, X) in the drawing, whose (X, Y) are a point's (z, x)
        segments = [segment.mapped(lambda p: ProfilePoint(x=p.z, z=-p.x)) for segment in segments]
    symmetry = _detect_symmetry_axis(segments, tolerance=tolerance)
    ambiguous = symmetry is not None and symmetry.ambiguous
    prepared_segments = _extract_lathe_profile_half(segments, symmetry=symmetry, tolerance=tolerance)
    try:
        chain = _chain_segments(prepared_segments, tolerance=tolerance)
    except DxfProfileImportError as exc:
        # about the axis taken it is no profile: turned, it may be one
        raise DxfProfileImportError(
            f"{exc} Turn the drawing for its other axis." if ambiguous else str(exc),
            symmetry_ambiguous=ambiguous) from exc
    chain = _normalize_profile_chain(chain, tolerance=tolerance)
    if not chain:
        raise DxfProfileImportError("No profile geometry found in DXF.")

    primitives: list[dict[str, Any]] = [
        {
            "primitive_id": 1,
            "type": "startPoint",
            "x_start": _clean_float(chain[0].start.x),
            "z_start": _clean_float(chain[0].start.z),
            "blend": dict(DEFAULT_BLEND),
        }
    ]

    for index, segment in enumerate(chain, start=2):
        if segment.type == "line":
            primitives.append(
                {
                    "primitive_id": index,
                    "type": "lineTo",
                    "x_end": _clean_float(segment.end.x),
                    "z_end": _clean_float(segment.end.z),
                    "angle": 0.0,
                    "input": "xz",
                    "blend": dict(DEFAULT_BLEND),
                }
            )
            continue

        if segment.type == "arc" and segment.center is not None:
            primitives.append(
                {
                    "primitive_id": index,
                    "type": "arcTo",
                    "direction": segment.direction,
                    "x_end": _clean_float(segment.end.x),
                    "z_end": _clean_float(segment.end.z),
                    "x_center": _clean_float(segment.center.x),
                    "z_center": _clean_float(segment.center.z),
                    "arc_radius": _clean_float(segment.radius),
                    "blend": dict(DEFAULT_BLEND),
                }
            )
            continue

        raise DxfProfileImportError(f"Unsupported profile segment: {segment.type!r}")

    return DxfProfile(primitives, symmetry_ambiguous=ambiguous)


def define_profile_from_segments(
    segments: Iterable[ProfileSegment],
    *,
    profile_id: int = 1,
    profile_type: str = "od",
    order: int = 1,
    operation_type: str = "defineProfile",
    tolerance: float = DEFAULT_TOLERANCE,
) -> dict[str, Any]:
    """Convert profile segments into the JSON shape emitted by Define Profile."""
    primitives = profile_from_segments(segments, tolerance=tolerance).primitives

    profile_type = str(profile_type or "od").lower()
    if profile_type not in {"od", "id"}:
        profile_type = "od"
    if operation_type not in {"defineProfile", "importDxfProfile"}:
        raise DxfProfileImportError(f"Unsupported profile operation type: {operation_type!r}")

    payload = {
        "order": int(order),
        "type": operation_type,
        "generate_gcode": True,
        "is_optional_block": False,
        "profile_id": int(profile_id),
        "profile_type": profile_type,
        "profile_primitives": primitives,
    }
    return payload


def _extract_lathe_profile_half(
    segments: list[ProfileSegment],
    *,
    symmetry: Symmetry | None,
    tolerance: float,
) -> list[ProfileSegment]:
    if symmetry is None:
        return segments

    axis_kind, axis_value = symmetry.kind, symmetry.value
    side = _preferred_profile_side(segments, axis_kind=axis_kind, axis_value=axis_value, tolerance=tolerance)
    selected: list[ProfileSegment] = []
    for segment in segments:
        start_side = _signed_axis_distance(segment.start, axis_kind, axis_value)
        end_side = _signed_axis_distance(segment.end, axis_kind, axis_value)
        if abs(start_side) <= tolerance and abs(end_side) <= tolerance:
            continue
        if start_side * side >= -tolerance and end_side * side >= -tolerance:
            mid_side = (start_side + end_side) / 2.0
            if abs(mid_side) > tolerance or abs(start_side) > tolerance or abs(end_side) > tolerance:
                selected.append(segment.mapped(
                    lambda p: _transform_symmetric_point(p, axis_kind=axis_kind, axis_value=axis_value)))

    return selected or segments


class Symmetry(NamedTuple):
    """The axis a drawing is symmetric about: ("x", its Y) for a horizontal
    one, ("z", its X) for a vertical one; ``ambiguous``: symmetric about the
    other one as well."""
    kind: str
    value: float
    ambiguous: bool


def _detect_symmetry_axis(
    segments: list[ProfileSegment],
    *,
    tolerance: float,
) -> Symmetry | None:
    """The axis the drawing is symmetric about (the horizontal one when it is
    symmetric about both), or None."""
    points = _segment_reference_points(segments)
    if len(points) < 4:
        return None

    x_values = [p.x for p in points]
    z_values = [p.z for p in points]
    x_spread = max(x_values) - min(x_values)
    z_spread = max(z_values) - min(z_values)
    candidates = [
        ("x", (min(x_values) + max(x_values)) / 2.0, x_spread, z_spread),
        ("z", (min(z_values) + max(z_values)) / 2.0, z_spread, x_spread),
    ]
    symmetric = [
        (kind, axis)
        for kind, axis, spread, axial_spread in candidates
        if spread > tolerance and axial_spread > tolerance
        and _symmetry_score(points, axis_kind=kind, axis_value=axis, tolerance=tolerance) >= MIN_SYMMETRY_SCORE
    ]
    if not symmetric:
        return None
    # Symmetric both ways (a roller with the same groove at each end), the
    # axis is the one drawn along the DXF's X, the lathe's Z, as every DXF is
    # read here: halving it about its middle instead leaves the end faces and
    # the silhouette lines crossing the axis, which form no chain. Turning the
    # drawing (quarter_turns) makes the other one horizontal.
    axis_kind, axis_value = symmetric[0]
    return Symmetry(axis_kind, axis_value, len(symmetric) > 1)


def _segment_reference_points(segments: list[ProfileSegment]) -> list[ProfilePoint]:
    points: list[ProfilePoint] = []
    for segment in segments:
        points.append(segment.start)
        points.append(segment.end)
        if segment.center is not None:
            points.append(segment.center)
    return points


def _symmetry_score(
    points: list[ProfilePoint],
    *,
    axis_kind: str,
    axis_value: float,
    tolerance: float,
) -> float:
    if not points:
        return 0.0

    matched = 0
    for point in points:
        mirror = (
            ProfilePoint(x=2.0 * axis_value - point.x, z=point.z)
            if axis_kind == "x"
            else ProfilePoint(x=point.x, z=2.0 * axis_value - point.z)
        )
        if any(_points_close(mirror, candidate, tolerance) for candidate in points):
            matched += 1
    return matched / len(points)


def _preferred_profile_side(
    segments: list[ProfileSegment],
    *,
    axis_kind: str,
    axis_value: float,
    tolerance: float,
) -> float:
    positive = 0
    negative = 0
    for segment in segments:
        for point in (segment.start, segment.end):
            distance = _signed_axis_distance(point, axis_kind, axis_value)
            if distance > tolerance:
                positive += 1
            elif distance < -tolerance:
                negative += 1
    return 1.0 if positive >= negative else -1.0


def _signed_axis_distance(point: ProfilePoint, axis_kind: str, axis_value: float) -> float:
    value = point.x if axis_kind == "x" else point.z
    return value - axis_value


def _transform_symmetric_point(
    point: ProfilePoint,
    *,
    axis_kind: str,
    axis_value: float,
) -> ProfilePoint:
    if axis_kind == "x":
        return ProfilePoint(x=2.0 * abs(point.x - axis_value), z=point.z)
    return ProfilePoint(x=2.0 * abs(point.z - axis_value), z=point.x)


def _normalize_profile_chain(
    chain: list[ProfileSegment],
    *,
    tolerance: float,
) -> list[ProfileSegment]:
    if not chain:
        return []

    start_z = chain[0].start.z
    end_z = chain[-1].end.z
    if start_z < end_z - tolerance:
        chain = [segment.reversed() for segment in reversed(chain)]

    z_values = [segment.start.z for segment in chain] + [segment.end.z for segment in chain]
    z_offset = max(z_values)
    if abs(z_offset) <= tolerance:
        return chain

    return [segment.mapped(lambda p: ProfilePoint(x=p.x, z=p.z - z_offset)) for segment in chain]


def _segments_from_entities(modelspace: Any, *, layer: str | None) -> list[ProfileSegment]:
    segments: list[ProfileSegment] = []
    unsupported: set[str] = set()

    for entity in modelspace:
        if layer and getattr(entity.dxf, "layer", None) != layer:
            continue

        entity_type = entity.dxftype()
        if entity_type == "LINE":
            segments.append(_line_segment(entity.dxf.start, entity.dxf.end))
        elif entity_type == "ARC":
            segments.append(_arc_segment(entity))
        elif entity_type == "LWPOLYLINE":
            segments.extend(_lwpolyline_segments(entity))
        elif entity_type == "POLYLINE":
            segments.extend(_polyline_segments(entity))
        elif entity_type in {"CIRCLE", "ELLIPSE", "SPLINE"}:
            unsupported.add(entity_type)

    if unsupported:
        names = ", ".join(sorted(unsupported))
        raise DxfProfileImportError(f"Unsupported DXF entities for profile import: {names}")

    return segments


def _line_segment(start: Any, end: Any) -> ProfileSegment:
    return ProfileSegment("line", _profile_point(start), _profile_point(end))


def _arc_segment(entity: Any) -> ProfileSegment:
    """A DXF ARC: counter-clockwise from its start angle to its end angle in
    its own coordinate system (OCS), which is the drawing's mirrored when
    its extrusion points down (-Z) - so its points are taken to the drawing's
    (WCS), and its direction read from them."""
    center = entity.dxf.center
    radius = float(entity.dxf.radius)
    start_angle = math.radians(float(entity.dxf.start_angle))
    end_angle = math.radians(float(entity.dxf.end_angle))
    sweep = (end_angle - start_angle) % (2.0 * math.pi)
    mid_angle = start_angle + sweep / 2.0
    ocs = _entity_ocs(entity)
    cx, cy = float(center.x), float(center.y)
    cz = float(center.z) if hasattr(center, "z") else 0.0

    def at(angle: float) -> tuple[float, float]:
        return _to_wcs(ocs, (cx + radius * math.cos(angle), cy + radius * math.sin(angle), cz))

    return ProfileSegment(
        type="arc",
        start=_profile_point(at(start_angle)),
        end=_profile_point(at(end_angle)),
        center=_profile_point(_to_wcs(ocs, (cx, cy, cz))),
        radius=radius,
        mid=_profile_point(at(mid_angle)),
    )


def _entity_ocs(entity: Any) -> Any:
    """The entity's own coordinate system (OCS), where it has one."""
    return entity.ocs() if hasattr(entity, "ocs") else None


def _to_wcs(ocs: Any, point: tuple[float, float, float]) -> tuple[float, float]:
    if ocs is None:
        return point[0], point[1]
    wcs = ocs.to_wcs(point)
    return float(wcs[0]), float(wcs[1])


def _lwpolyline_segments(entity: Any) -> list[ProfileSegment]:
    """Its points are in its own coordinate system (OCS), mirrored when
    its extrusion points down; ``_bulge_segment`` takes them to the drawing's."""
    points = list(entity.get_points("xyb"))
    closed = bool(entity.closed)
    ocs = _entity_ocs(entity)
    elevation = float(entity.dxf.get("elevation", 0.0) or 0.0)
    return _polyline_points_to_segments(points, closed=closed, ocs=ocs, elevation=elevation)


def _polyline_segments(entity: Any) -> list[ProfileSegment]:
    vertices = list(entity.vertices)
    points = [
        (
            float(vertex.dxf.location.x),
            float(vertex.dxf.location.y),
            float(vertex.dxf.get("bulge", 0.0) or 0.0),
        )
        for vertex in vertices
    ]
    closed = bool(entity.is_closed)
    # a 2D polyline's vertices are in its OCS, a 3D one's in the drawing's
    ocs = entity.ocs() if getattr(entity, "is_2d_polyline", False) else None
    return _polyline_points_to_segments(points, closed=closed, ocs=ocs)


def _polyline_points_to_segments(
    points: list[tuple[float, float, float]],
    *,
    closed: bool,
    ocs: Any = None,
    elevation: float = 0.0,
) -> list[ProfileSegment]:
    if len(points) < 2:
        return []

    segments: list[ProfileSegment] = []
    count = len(points)
    limit = count if closed else count - 1
    for index in range(limit):
        current = points[index]
        next_point = points[(index + 1) % count]
        start_xy = (float(current[0]), float(current[1]))
        end_xy = (float(next_point[0]), float(next_point[1]))
        bulge = float(current[2] or 0.0)
        if abs(bulge) < 1e-12:
            segments.append(_line_segment(_to_wcs(ocs, (*start_xy, elevation)),
                                          _to_wcs(ocs, (*end_xy, elevation))))
        else:
            segments.append(_bulge_segment(start_xy, end_xy, bulge, ocs=ocs, elevation=elevation))
    return segments


def _bulge_segment(
    start_xy: tuple[float, float],
    end_xy: tuple[float, float],
    bulge: float,
    *,
    ocs: Any = None,
    elevation: float = 0.0,
) -> ProfileSegment:
    """An arc of a polyline, counter-clockwise from ``start_xy`` to ``end_xy``
    (in the polyline's OCS) when ``bulge`` is positive."""
    sx, sy = start_xy
    ex, ey = end_xy
    dx = ex - sx
    dy = ey - sy
    chord = math.hypot(dx, dy)
    if chord <= 1e-12:
        raise DxfProfileImportError("Polyline contains a zero-length bulge segment.")

    radius = chord * (1.0 + bulge * bulge) / (4.0 * abs(bulge))
    center_offset = chord * (1.0 - bulge * bulge) / (4.0 * bulge)
    mid_x = (sx + ex) / 2.0
    mid_y = (sy + ey) / 2.0
    left_x = -dy / chord
    left_y = dx / chord
    center_xy = (
        mid_x + left_x * center_offset,
        mid_y + left_y * center_offset,
    )
    # halfway along the arc: off the chord's middle by the sagitta, to the
    # right of the chord when the arc goes counter-clockwise
    sagitta = bulge * chord / 2.0
    arc_mid_xy = (mid_x - left_x * sagitta, mid_y - left_y * sagitta)

    def wcs(xy: tuple[float, float]) -> ProfilePoint:
        return _profile_point(_to_wcs(ocs, (xy[0], xy[1], elevation)))

    return ProfileSegment(
        type="arc",
        start=wcs(start_xy),
        end=wcs(end_xy),
        center=wcs(center_xy),
        radius=radius,
        mid=wcs(arc_mid_xy),
    )


def _chain_segments(
    segments: list[ProfileSegment],
    *,
    tolerance: float,
) -> list[ProfileSegment]:
    if not segments:
        return []

    # The first segment may be anywhere along the profile (the DXF lists them
    # in any order): the chain grows from its end, then from its start.
    remaining = list(segments)
    chain = [remaining.pop(0)]
    while remaining:
        current_end = chain[-1].end
        current_start = chain[0].start
        for index, segment in enumerate(remaining):
            if _points_close(current_end, segment.start, tolerance):
                chain.append(remaining.pop(index))
                break
            if _points_close(current_end, segment.end, tolerance):
                chain.append(remaining.pop(index).reversed())
                break
            if _points_close(current_start, segment.end, tolerance):
                chain.insert(0, remaining.pop(index))
                break
            if _points_close(current_start, segment.start, tolerance):
                chain.insert(0, remaining.pop(index).reversed())
                break
        else:
            raise DxfProfileImportError("DXF entities do not form one connected profile chain.")

    return chain


def _profile_point(point: Any) -> ProfilePoint:
    if hasattr(point, "x") and hasattr(point, "y"):
        dxf_x = float(point.x)
        dxf_y = float(point.y)
    else:
        dxf_x = float(point[0])
        dxf_y = float(point[1])
    return ProfilePoint(x=dxf_y, z=dxf_x)


def _points_close(a: ProfilePoint, b: ProfilePoint, tolerance: float) -> bool:
    return abs(a.x - b.x) <= tolerance and abs(a.z - b.z) <= tolerance


def _clean_float(value: float) -> float:
    if abs(value) < 1e-12:
        return 0.0
    rounded = round(float(value), 6)
    if rounded == int(rounded):
        return float(int(rounded))
    return rounded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convert DXF profile geometry to profile JSON.")
    parser.add_argument("dxf_file")
    parser.add_argument("--profile-id", type=int, default=1)
    parser.add_argument("--profile-type", choices=("od", "id"), default="od")
    parser.add_argument("--operation-type", choices=("defineProfile", "importDxfProfile"), default="defineProfile")
    parser.add_argument("--order", type=int, default=1)
    parser.add_argument("--layer", default=None)
    args = parser.parse_args(argv)

    payload = read_dxf_profile(
        args.dxf_file,
        profile_id=args.profile_id,
        profile_type=args.profile_type,
        order=args.order,
        operation_type=args.operation_type,
        layer=args.layer,
    )
    # This CLI's stdout is the JSON result consumed by callers, not a log.
    sys.stdout.write(json.dumps(payload, indent=4) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
