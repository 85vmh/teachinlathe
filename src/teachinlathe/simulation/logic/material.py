"""What a tool takes off a turned part: the one model of it, for a simulation
(program_run.ProgramRun) and for the machine's own trail as it runs
(MaterialLeft, which the backplot keeps).

The part is a shapely shape in (z, r) - r the radius - and what a tool
takes off is its cutting outline (tool_shape.cutting_shape) swept along the
move, turned about the axis (shapes.turned): what it cuts on one side it cuts
all round. Whether a rapid goes through the part is shapes.goes_through, as
the conversational G-code checks it.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

from shapely.geometry import Polygon
from shapely.ops import unary_union

from teachinlathe.conversational.gcode.operations.profiling.shapes import _difference, _on_grid, sweeps, turned
from teachinlathe.conversational.gcode.operations.profiling.tool_shape import ToolShape

Point = Tuple[float, float]


def cut(material, points: Sequence[Point], tool: Optional[ToolShape]):
    """``material`` less what ``tool`` going through ``points`` - (z, r),
    in order - takes off it; as it was with no tool or nothing to cut."""
    if tool is None or material.is_empty or len(points) < 2:
        return material
    swept = _on_grid(turned(unary_union(sweeps(tool.outline, points))))
    return _difference(material, swept) if swept.intersects(material) else material


class MaterialLeft:
    """A part as it is being cut: ``material``, from ``stock`` on, less what
    each cut takes off it (cut). ``version`` counts the cuts that changed it,
    for whatever draws it to know when to draw it again."""

    def __init__(self, stock=None):
        self.material = _on_grid(stock) if stock is not None and not stock.is_empty else Polygon()
        self.version = 0

    def cut(self, points: Sequence[Point], tool: Optional[ToolShape]) -> bool:
        """``tool`` through ``points``: whether it took anything off."""
        after = cut(self.material, points, tool)
        if after is self.material:
            return False
        self.material = after
        self.version += 1
        return True
