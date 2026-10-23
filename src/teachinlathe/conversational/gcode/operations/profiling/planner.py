"""The roughing planner put together: its state and checks (planner_base), how
the tool gets about (moves), the profile's edge (edge), and the strategies -
axial and radial passes, 45° passes, pockets, the contour - each in its own
module. See machining.py for what it plans against."""

from __future__ import annotations

from typing import Optional

from .axial_radial import AxialRadialPasses
from .diagonal_passes import DiagonalPasses
from .edge import Edge
from .final_contour import FinalContour
from .moves import Moves
from .plan import RoughingPlan, RoughingSetup
from .planner_base import PlannerBase
from .pockets import Pockets
from .tool_shape import ToolShape


class _Planner(AxialRadialPasses, DiagonalPasses, Pockets, FinalContour, Edge, Moves, PlannerBase):
    """Plans one Profile Roughing - see plan_roughing."""


def plan_roughing(setup: RoughingSetup, profile_path, tool: Optional[ToolShape],
                  stock_before=None, rest: bool = False,
                  sliver_radius: float = 0.0) -> RoughingPlan:
    """The moves of a Profile Roughing against ``profile_path`` - the finished
    profile as build_render_path gives it - with ``tool`` (None: square_tool).

    ``stock_before`` is the material there is to cut, as a shapely shape in
    (z, r); by default from X Start to the profile's smallest diameter (OD) or
    its largest (ID), from Z Start back. ``rest``: what is left by another
    roughing - the contour then runs only where there is material - and
    ``sliver_radius`` the nose radius of the tool that left it: what that
    nose's corners and the slivers between its passes leave is not cut again.
    """
    return _Planner(setup, profile_path, tool, stock_before, rest, sliver_radius).plan()


def plan_leftover(setup: RoughingSetup, profile_path, stock_before,
                  nose_radius: float = 0.0) -> RoughingPlan:
    """No moves, only what there is to cut - for a rest roughing that has no
    tool yet. ``nose_radius``: the last tool's, whose corners are not counted
    as left over."""
    return _Planner(setup, profile_path, None, stock_before, True, nose_radius)._result()
