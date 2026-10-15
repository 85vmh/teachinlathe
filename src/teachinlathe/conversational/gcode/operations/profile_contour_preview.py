"""What Profile Contour will cut, for drawing on the profile canvas.

Uses the same setup as generate_profile_contour_gcode and reads the moves from
the G-code it generates, so the preview shows what the machine will do. All X
values are diameters.
"""

from .profile_contour import (
    _resolve_profile,
    build_contour_setup,
    generate_profile_contour_gcode,
    parse_profile_contour_config,
)
from .profile_roughing_preview import _CONTOUR_START, flatten_path, gcode_moves


def build_profile_contour_preview(op):
    """{profile, offset, feeds, rapids, error} for an operation dict carrying
    its profile in ``_resolved_profile``, as build_profile_roughing_preview
    gives them for roughing:

    profile     the finished profile, as [{x, z}]
    offset      the profile offset by stock-to-leave, clipped to X Start, as [{x, z}]
    feeds       the contour's cuts - the feed along Z to where the profile
                begins, then the profile - as [{x0, z0, x1, z1, pass, contour}]
    rapids      always empty: only the cut is drawn
    error       why there is nothing to show, or ""
    """
    config = parse_profile_contour_config(op)
    _, contour_path, error = build_contour_setup(op, config)
    if error:
        return {"profile": [], "offset": [], "feeds": [], "rapids": [], "error": error}
    _, profile_path = _resolve_profile(op)
    feeds, _ = gcode_moves(generate_profile_contour_gcode(op), start=_CONTOUR_START)
    return {
        "profile": flatten_path(profile_path),
        "offset": flatten_path(contour_path),
        "feeds": feeds,
        "rapids": [],
        "error": "",
    }
