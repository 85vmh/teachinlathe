"""What Profile Roughing will cut, for drawing on the profile canvas.

The moves come from the tool-aware plan (profiling.machining), which the
G-code is to be written from as well. All X values are diameters.
"""

from .profile_roughing import plan_profile_roughing
from .profiling.operation_input import resolve_profile
from .profiling.plan_drawing import chain_points, drawn_moves, flatten_path


def build_profile_roughing_preview(op):
    """{profile, offset, feeds, rapids, residual, warnings, error} for
    an operation dict carrying its profile in ``_resolved_profile`` and its
    tool in ``_resolved_cutting_tool``:

    profile     the finished profile, as [{x, z}]
    offset      the profile offset by stock-to-leave, as the plan keeps to it, as [{x, z}]
    feeds       the cuts, the final contour pass included, as [{x0, z0, x1, z1, pass, contour}]
    rapids      the rapid moves between them (retracts included), likewise
    residual    the material left for another tool, as [[{x, z}]]
    restOffered whether a rest roughing can be added for it: there is some,
                and a tool that cut this one - not a rest roughing still
                waiting for its tool
    warnings    what the plan could not do, as [str]
    error       why there is nothing to show, or ""

    The moves are planned by profiling.machining (plan_profile_roughing), tool
    and all; the G-code is to be written from the same plan.
    """
    plan = plan_profile_roughing(op)
    if plan.error:
        return {"profile": [], "offset": [], "feeds": [], "rapids": [],
                "residual": [], "warnings": [], "error": plan.error}
    _, profile_path = resolve_profile(op)
    feeds, rapids = drawn_moves(plan)
    return {
        "profile": flatten_path(profile_path),
        # the stock to leave as the plan keeps to it: across the profile on
        # every face, the ones turned toward the chuck too
        "offset": chain_points(plan.allowance),
        "feeds": feeds,
        "rapids": rapids,
        "residual": [chain_points(region) for region in plan.residual],
        "restOffered": bool(plan.residual and plan.tool is not None and plan.tool.known),
        "warnings": list(plan.warnings),
        "error": "",
    }
