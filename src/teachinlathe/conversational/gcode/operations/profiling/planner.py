"""Tool-aware profile roughing: what the tool can reach, and the moves that reach it.

The tool is the insert in the holder, at its real size and nose radius, turned
the way the backplot turns it (``tool_source._describe`` + ``insert_tool._build``)
and hung from its control point. Everything is planned against one shape, the
*obstacle*: the set of positions the control point must never enter, which is
the finished part, grown by the stock to leave, swept by the tool turned round
(a Minkowski sum). Outside it the insert touches neither the part nor the
stock left on it, so

* a pass runs from the stock face until it meets the obstacle - the first
  thing in its way, not the deepest point of the profile at that diameter,
  which is what cut through the finished diameter in front of a DIN 509
  relief;
* the contour pass is the obstacle's edge: the profile offset by the nose
  radius, and bridged over a pocket the insert does not fit into;
* a pocket - material the passes from the face cannot reach - is cut only
  where the insert can be plunged into it, and is otherwise left, as residual
  material for another operation with another tool.

Geometry is in radius space: z, and r = X / 2. ID is planned as OD with r
mirrored (r -> -r), tool and all, and mirrored back: the material then always
lies below the profile and the tool comes from above.

What is not modelled: the holder. The insert stands for it with its two
cutting edges carried on, past their ends, as straight lines (``EDGE_REACH``):
the lead and the back angle the tool is set at. So the tool goes down no slope
steeper than its back angle, and is never taken to fit into a neck behind a
peak because the insert alone is short enough to - what the holder behind it
would not. A holder wider than those lines can still hit a shoulder.

Put together here from its state and checks (planner_base), how the tool gets
about (moves), the profile's edge (edge), and the strategies - axial and radial
passes, 45° passes, pockets, the contour - each in its own module.
"""

from __future__ import annotations

from typing import Optional

from shapely.geometry import Polygon

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
    profile as geometry.build_path gives it - with ``tool`` (None: square_tool).

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


def plan_contour(setup: RoughingSetup, profile_path, tool: Optional[ToolShape]) -> RoughingPlan:
    """Profile Contour: the contour alone, from Z Start along the profile -
    offset by the stock to leave, compensated for the nose, bridged over what
    ``tool`` cannot enter - with the material roughed already: what is there
    of it is the part and its stock to leave, which no rapid may cross."""
    return _Planner(setup, profile_path, tool, Polygon(), False, 0.0).plan_contour_only()
