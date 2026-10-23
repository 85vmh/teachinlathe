"""What Profile Contour will cut, for drawing on the profile canvas: the same
plan its G-code is written from (plan_profile_contour). All X values are
diameters."""

from .profile_contour import plan_profile_contour
from .profile_roughing import _resolve_profile
from .profile_roughing_preview import flatten_path


def build_profile_contour_preview(op):
    """{profile, offset, feeds, rapids, warnings, error} for an operation dict
    carrying its profile in ``_resolved_profile`` and its tool in
    ``_resolved_cutting_tool``, as build_profile_roughing_preview gives them
    for roughing:

    profile     the finished profile, as [{x, z}]
    offset      the profile offset by stock-to-leave, as [{x, z}]
    feeds       the contour - in along Z from Z Start to where the profile
                begins, then along it - drawn where the nose touches, as
                [{x0, z0, x1, z1, pass, contour}]
    rapids      always empty: only the cut is drawn
    warnings    what the plan could not do, as [str]
    error       why there is nothing to show, or ""
    """
    plan = plan_profile_contour(op)
    if plan.error:
        return {"profile": [], "offset": [], "feeds": [], "rapids": [], "warnings": [], "error": plan.error}
    _, profile_path = _resolve_profile(op)
    feeds = []
    for move in plan.moves:
        if not move.feed:
            continue
        z0, r0, z1, r1 = move.drawn or (move.z0, move.r0, move.z1, move.r1)
        feeds.append({"x0": 2 * r0, "z0": z0, "x1": 2 * r1, "z1": z1,
                      "pass": move.pass_no, "contour": move.contour})
    return {
        "profile": flatten_path(profile_path),
        "offset": [{"x": 2 * r, "z": z} for z, r in plan.allowance],
        "feeds": feeds,
        "rapids": [],
        "warnings": list(plan.warnings),
        "error": "",
    }
