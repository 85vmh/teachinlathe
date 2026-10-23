"""What Profile Contour will cut, for drawing on the profile canvas: the same
plan its G-code is written from (plan_profile_contour). All X values are
diameters."""

from .profile_contour import plan_profile_contour
from .profiling.operation_input import resolve_profile
from .profiling.plan_drawing import chain_points, drawn_moves, flatten_path


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
    _, profile_path = resolve_profile(op)
    feeds, _rapids = drawn_moves(plan)
    return {
        "profile": flatten_path(profile_path),
        "offset": chain_points(plan.allowance),
        "feeds": feeds,
        "rapids": [],
        "warnings": list(plan.warnings),
        "error": "",
    }
