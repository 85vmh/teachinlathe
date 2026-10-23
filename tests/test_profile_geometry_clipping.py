"""The profile offset by the stock to leave and clipped to X Start
(profiling/geometry.py: build_shifted_path_clipped_to_x_boundary) - what
Profile Roughing's preview and Profile Contour cut against."""

from teachinlathe.conversational.gcode.operations.profiling.geometry import (
    StartPoint,
    ToolpathArc,
    ToolpathLine,
    build_shifted_path_clipped_to_x_boundary,
)


def test_clipped_arcs_keep_their_radius_in_diameter_mode():
    """An ID path with arcs, offset and clipped: every arc still starts and
    ends on its own circle - X counted on the diameter, Z on the radius."""
    path = [
        StartPoint(17.0, 0.0),
        ToolpathArc(15.006896551724137, -0.9172413793103448, 17.0, -1.0, False),
        ToolpathLine(15.0, -10.0),
        ToolpathArc(11.0, -12.0, 11.0, -10.0, True),
        ToolpathLine(10.0, -12.0),
        ToolpathArc(8.0, -13.0, 10.0, -13.0, False),
        ToolpathLine(8.0, -15.0),
    ]

    clipped = build_shifted_path_clipped_to_x_boundary(
        path, offset_x=-1.0, offset_z=0.2, x_boundary=8.0, keep_side="gte")

    current_x, current_z = clipped[0].x, clipped[0].z
    for element in clipped[1:]:
        if isinstance(element, ToolpathArc):
            start_radius = ((current_x - element.center_x) / 2.0) ** 2 + (current_z - element.center_z) ** 2
            end_radius = ((element.end_x - element.center_x) / 2.0) ** 2 + (element.end_z - element.center_z) ** 2
            assert abs(start_radius - end_radius) < 1e-4
        current_x, current_z = element.end_x, element.end_z
