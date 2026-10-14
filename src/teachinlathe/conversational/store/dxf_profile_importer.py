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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_BLEND = {
    "type": "none",
    "chamfer_width": 0.0,
    "fillet_radius": 0.0,
    "undercut_radius": 0.4,
    "undercut_depth": 0.4,
    "undercut_length": 2.5,
}


class DxfProfileImportError(ValueError):
    """Raised when DXF geometry cannot be converted into one profile chain."""


@dataclass(frozen=True)
class ProfilePoint:
    x: float
    z: float


@dataclass(frozen=True)
class ProfileSegment:
    type: str
    start: ProfilePoint
    end: ProfilePoint
    center: ProfilePoint | None = None
    radius: float = 0.0
    direction: str = "ccw"

    def reversed(self) -> "ProfileSegment":
        direction = self.direction
        if self.type == "arc":
            direction = "cw" if direction == "ccw" else "ccw"
        return ProfileSegment(
            type=self.type,
            start=self.end,
            end=self.start,
            center=self.center,
            radius=self.radius,
            direction=direction,
        )


def read_dxf_profile(
    filename: str | Path,
    *,
    profile_id: int = 1,
    profile_type: str = "od",
    order: int = 1,
    operation_type: str = "defineProfile",
    dxf_file_path: str | None = None,
    layer: str | None = None,
    tolerance: float = 1e-5,
) -> dict[str, Any]:
    """Read a DXF file and return a profile operation dict."""

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

    segments = _segments_from_entities(doc.modelspace(), layer=layer)
    return define_profile_from_segments(
        segments,
        profile_id=profile_id,
        profile_type=profile_type,
        order=order,
        operation_type=operation_type,
        dxf_file_path=str(path) if dxf_file_path is None and operation_type == "importDxfProfile" else dxf_file_path,
        tolerance=tolerance,
    )


def define_profile_from_segments(
    segments: Iterable[ProfileSegment],
    *,
    profile_id: int = 1,
    profile_type: str = "od",
    order: int = 1,
    operation_type: str = "defineProfile",
    dxf_file_path: str | None = None,
    tolerance: float = 1e-5,
) -> dict[str, Any]:
    """Convert profile segments into the JSON shape emitted by Define Profile."""

    prepared_segments = _extract_lathe_profile_half(list(segments), tolerance=tolerance)
    chain = _chain_segments(prepared_segments, tolerance=tolerance)
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
    if operation_type == "importDxfProfile":
        payload["dxfFilePath"] = str(dxf_file_path or "")
    return payload


def _extract_lathe_profile_half(
    segments: list[ProfileSegment],
    *,
    tolerance: float,
) -> list[ProfileSegment]:
    symmetry = _detect_symmetry_axis(segments, tolerance=tolerance)
    if symmetry is None:
        return segments

    axis_kind, axis_value = symmetry
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
                selected.append(_transform_symmetric_segment(segment, axis_kind=axis_kind, axis_value=axis_value))

    return selected or segments


def _detect_symmetry_axis(
    segments: list[ProfileSegment],
    *,
    tolerance: float,
) -> tuple[str, float] | None:
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
    scored = [
        (score, spread, kind, axis)
        for kind, axis, spread, axial_spread in candidates
        if spread > tolerance and axial_spread > tolerance
        for score in [_symmetry_score(points, axis_kind=kind, axis_value=axis, tolerance=tolerance)]
    ]
    if not scored:
        return None

    score, _spread, axis_kind, axis_value = max(scored)
    if score < 0.7:
        return None
    return axis_kind, axis_value


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


def _transform_symmetric_segment(
    segment: ProfileSegment,
    *,
    axis_kind: str,
    axis_value: float,
) -> ProfileSegment:
    return ProfileSegment(
        type=segment.type,
        start=_transform_symmetric_point(segment.start, axis_kind=axis_kind, axis_value=axis_value),
        end=_transform_symmetric_point(segment.end, axis_kind=axis_kind, axis_value=axis_value),
        center=(
            _transform_symmetric_point(segment.center, axis_kind=axis_kind, axis_value=axis_value)
            if segment.center is not None
            else None
        ),
        radius=segment.radius * 2.0,
        direction=segment.direction,
    )


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

    return [_offset_segment_z(segment, -z_offset) for segment in chain]


def _offset_segment_z(segment: ProfileSegment, delta: float) -> ProfileSegment:
    return ProfileSegment(
        type=segment.type,
        start=ProfilePoint(x=segment.start.x, z=segment.start.z + delta),
        end=ProfilePoint(x=segment.end.x, z=segment.end.z + delta),
        center=(
            ProfilePoint(x=segment.center.x, z=segment.center.z + delta)
            if segment.center is not None
            else None
        ),
        radius=segment.radius,
        direction=segment.direction,
    )


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
    center = entity.dxf.center
    radius = float(entity.dxf.radius)
    start_angle = math.radians(float(entity.dxf.start_angle))
    end_angle = math.radians(float(entity.dxf.end_angle))
    start = (
        float(center.x) + radius * math.cos(start_angle),
        float(center.y) + radius * math.sin(start_angle),
    )
    end = (
        float(center.x) + radius * math.cos(end_angle),
        float(center.y) + radius * math.sin(end_angle),
    )
    return ProfileSegment(
        type="arc",
        start=_profile_point(start),
        end=_profile_point(end),
        center=_profile_point(center),
        radius=radius,
        direction="ccw",
    )


def _lwpolyline_segments(entity: Any) -> list[ProfileSegment]:
    points = list(entity.get_points("xyb"))
    closed = bool(entity.closed)
    return _polyline_points_to_segments(points, closed=closed)


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
    return _polyline_points_to_segments(points, closed=closed)


def _polyline_points_to_segments(
    points: list[tuple[float, float, float]],
    *,
    closed: bool,
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
            segments.append(_line_segment(start_xy, end_xy))
        else:
            segments.append(_bulge_segment(start_xy, end_xy, bulge))
    return segments


def _bulge_segment(
    start_xy: tuple[float, float],
    end_xy: tuple[float, float],
    bulge: float,
) -> ProfileSegment:
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
    return ProfileSegment(
        type="arc",
        start=_profile_point(start_xy),
        end=_profile_point(end_xy),
        center=_profile_point(center_xy),
        radius=radius,
        direction="ccw" if bulge > 0 else "cw",
    )


def _chain_segments(
    segments: list[ProfileSegment],
    *,
    tolerance: float,
) -> list[ProfileSegment]:
    if not segments:
        return []

    remaining = list(segments)
    chain = [remaining.pop(0)]
    while remaining:
        current_end = chain[-1].end
        match_index = -1
        reverse = False

        for index, segment in enumerate(remaining):
            if _points_close(current_end, segment.start, tolerance):
                match_index = index
                reverse = False
                break
            if _points_close(current_end, segment.end, tolerance):
                match_index = index
                reverse = True
                break

        if match_index < 0:
            raise DxfProfileImportError("DXF entities do not form one connected profile chain.")

        segment = remaining.pop(match_index)
        chain.append(segment.reversed() if reverse else segment)

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
    print(json.dumps(payload, indent=4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
