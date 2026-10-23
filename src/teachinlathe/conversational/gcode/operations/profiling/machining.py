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

The planner is split by what each part does - see planner.py; this module
keeps the names it always had, for those who import them from here.
"""

from .planner import _Planner, plan_contour, plan_leftover, plan_roughing  # noqa: F401
from .shapes import (  # noqa: F401
    Pt,
    FAR,
    ARC_TOLERANCE,
    TOLERANCE,
    MIN_AREA,
    MIN_CUT,
    minkowski,
    sweep,
    path_points,
    _arc_points,
    GRID,
    _on_grid,
    _round,
    _difference,
    _intersection,
    _mirror,
    _simplify,
)
from .tool_shape import (  # noqa: F401
    CLEARANCE_DEGREES,
    NOSE_SEGMENTS,
    EDGE_REACH,
    ToolShape,
    insert_tool_shape,
    square_tool,
    _control_point,
    _swung,
)
from .plan import (  # noqa: F401
    Move,
    RoughingPlan,
    RoughingSetup,
)
from .shapes import log  # noqa: F401
