"""What Groove Finishing will cut, for drawing on the profile canvas: the
groove's profile, the stock the Groove Roughing above left on it - what the
finishing takes off - and the contour its strategy goes along, on the profile
itself, not where the blade's corners are compensated to. All X values are
diameters."""

from .groove_finishing import generate_groove_finishing_gcode, roughing_stock
from .groove_roughing import (
    _blade_start_x,
    _blade_width,
    _profile_bounds_from_path,
    _reverse_path,
    _split_path_at_z,
    _start_x,
    _stock_allowance,
)
from .groove_roughing_preview import EMPTY, gcode_error, groove_path
from .profiling.geometry import StartPoint
from .profiling.plan_drawing import flatten_path


def _passes(path, center_z, strategy, overlap):
    """The profile as the strategy goes along it, a list of passes, each
    [{x, z}]: toward the centre, each side ``overlap`` past the middle, as
    the blade's middle goes; toward the left,
    the Z+ side down and on along the bottom and up the Z- side; toward the
    right, the other way round."""
    z_plus, _rest = _split_path_at_z(path, center_z - overlap)
    _rest, z_minus = _split_path_at_z(path, center_z + overlap)
    if strategy == "towards_left":
        sections = [path]
    elif strategy == "towards_right":
        sections = [_reverse_path(path)]
    else:
        sections = [z_plus, _reverse_path(z_minus)]
    return [flatten_path(section) for section in sections if section and isinstance(section[0], StartPoint)]


def build_groove_finishing_preview(op):
    """{profile, offset, feeds, rapids, start, startDiameter, error} for a
    Groove Finishing dict carrying its radial profile in
    ``_resolved_radial_profile``, its tool in ``_resolved_tool`` and the
    stock the roughing above left in ``_resolved_roughing_stock``, as
    ProfileCanvas draws a roughing:

    profile     the groove's profile, as [{x, z}]
    offset      it offset by the stock the roughing left, as [{x, z}]; []
                with none
    feeds       the contour, as [{x0, z0, x1, z1, pass, contour, arrows}],
                its arrows along it
    rapids      from where the blade starts over to above each pass's start,
                and down to it
    start       where the blade starts, {x, z}: over the groove's middle, the
                clearance out from the start diameter
    startDiameter  the pulley's outside with the stock the roughing left on it
    error       why there is nothing to show, or ""
    """
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    empty = dict(EMPTY, start=None, startDiameter=None)
    path, profile_type, error = groove_path(op)
    if path is None:
        return dict(empty, error=error)

    radial, axial = roughing_stock(op)
    offset = [{"x": x, "z": z} for z, x in _stock_allowance(path, profile_type, radial, axial)]

    error = gcode_error(generate_groove_finishing_gcode(op))

    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    center_z = (z_min + z_max) / 2.0
    clearance = abs(float((op.get("cutting_parameters") or {}).get("retract", 0) or 0))
    start_x = _start_x(path, profile_type, radial)
    blade_x = _blade_start_x(start_x, profile_type, clearance)
    empty = dict(empty, profile=flatten_path(path), offset=offset, start={"x": blade_x, "z": center_z},
                 startDiameter=start_x)
    if error:
        return dict(empty, error=error)

    strategy = str((op.get("finishing_parameters") or {}).get("strategy", "towards_center")).lower()
    feeds, rapids = [], []
    # toward the centre, each side half the blade's width past the middle
    half_width = _blade_width(op.get("_resolved_tool") or {}) / 2.0
    for n, points in enumerate(_passes(path, center_z, strategy, half_width)):
        first = points[0]
        rapids.append({"x0": blade_x, "z0": center_z, "x1": blade_x, "z1": first["z"]})
        rapids.append({"x0": blade_x, "z0": first["z"], "x1": first["x"], "z1": first["z"]})
        for a, b in zip(points, points[1:]):
            feeds.append({"x0": a["x"], "z0": a["z"], "x1": b["x"], "z1": b["z"],
                          "pass": n, "contour": True, "arrows": "along"})
    return dict(empty, feeds=feeds, rapids=rapids)
