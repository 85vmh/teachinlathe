"""What a program has done to its stock, operation by operation (StockModel).

Nothing of the stock need be declared. Everything starts unknown, and what
is known is only what the program makes sure of - the air its feeds leave,
where the tool went with nothing in its way - or what is declared there
(``material``: what the header's stock will say, once it can say it; none
yet). A program run on a part already made and one on a bare bar are the
same to it: each operation goes by its own parameters, and the model says
what is known to be air before it, and what is known to be material.

The stock is in (z, r) - r the radius, the part turned about the axis - Z
in the work offset the program started in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from .operations.profiling.shapes import FAR, _difference, _mirror, _on_grid, sweeps
from .operations.profiling.tool_shape import ToolShape, cutting_shape
from .toolpath import OperationPath, move_points


class StockState(Enum):
    """What is at a point of the stock."""
    MATERIAL = "material"
    AIR = "air"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StockStep:
    """The stock as operation ``index`` finds it - ``air_before``,
    ``material_before``, shapely shapes in (z, r) - and leaves it.
    ``known`` False when what it cut is not known - its moves, its tool or,
    for an optional one, whether it runs at all - and it then makes nothing
    sure: what it may have cut stays as it was."""
    index: int
    known: bool
    air_before: object
    air_after: object
    material_before: object
    material_after: object

    @property
    def cut(self):
        """What it made sure is air: its cut, where nothing was known to be air yet."""
        return self.air_after.difference(self.air_before)


@dataclass
class StockModel:
    """The stock, operation after operation (apply): known air, known
    material - ``material``, what is declared there, less what is cut - and
    everything else unknown."""
    material: object = field(default_factory=Polygon)
    air: object = field(default_factory=Polygon)
    steps: List[StockStep] = field(default_factory=list)

    def state_at(self, z: float, r: float) -> StockState:
        point = Point(z, abs(r))
        if self.air.contains(point):
            return StockState.AIR
        if self.material.contains(point):
            return StockState.MATERIAL
        return StockState.UNKNOWN

    def apply(self, path: OperationPath, tool: Optional[ToolShape]) -> StockStep:
        """Operation ``path`` cutting with ``tool`` (what of it cuts,
        tool_shape.cutting_shape; None when not known): the stock after it,
        and the step it made."""
        feeds = [move for move in path.moves if move.feed and not move.synced]
        if path.known and not feeds:
            # it cuts nothing all round - a definition, a move, a thread
            cut = Polygon()
        elif path.known and not path.optional and path.z_origin is not None and tool is not None:
            cut = _cut(feeds, tool, path.z_origin)
        else:
            cut = None
        air_before, material_before = self.air, self.material
        if cut is not None and not cut.is_empty:
            self.air = _on_grid(unary_union([self.air, cut]))
            if not self.material.is_empty:
                self.material = _difference(self.material, cut)
        step = StockStep(path.index, cut is not None, air_before, self.air, material_before, self.material)
        self.steps.append(step)
        return step


def _cut(feeds, tool: ToolShape, z_origin: float):
    """What ``tool`` going along ``feeds`` - Moves at the feed, not
    synchronized: a thread is cut, not all round - leaves air, turned about
    the axis."""
    pieces = []
    for move in feeds:
        points = [(z + z_origin, r) for z, r in move_points(move)]
        pieces.extend(sweeps(tool.outline, points))
    cut = unary_union(pieces)
    # turned about the axis: what is cut on one side of it is cut all round
    cut = unary_union([cut, _mirror(cut)]).intersection(box(-FAR, 0.0, FAR, FAR))
    return _on_grid(cut)


def program_stock(program, tools) -> List[StockStep]:
    """The stock as each of ``program``'s operations finds it and leaves it,
    nothing of it declared: a StockStep for each operation that is written.
    ``tools``: where the tools are looked up - the Tool Library, a ToolSnapshot."""
    from teachinlathe.tooling.model.data_types import MountedTool

    from .gcode_builder import program_toolpath

    path = program_toolpath(program, tools)
    model = StockModel()
    for operation in path.operations:
        mounted = MountedTool.of(tools, operation.tool_holder_id) if operation.tool_holder_id else None
        model.apply(operation, cutting_shape(mounted))
    return model.steps
