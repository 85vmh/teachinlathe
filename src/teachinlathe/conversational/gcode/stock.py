"""What a program has done to its stock, operation by operation (StockModel).

Nothing of the stock need be declared. Everything starts unknown, and what
is known is only what the program makes sure of - the air its feeds leave,
where the tool went with nothing in its way - or what is declared there
(``material``: the header's bar or tube, header_material, when it says one).
A program run on a part already made and one on a bare bar are the same to
it: each operation goes by its own parameters, and the model says what is
known to be air before it, and what is known to be material.

A rapid that would go through known material is what the model is for: a
StockStep keeps the ones of its operation (``rapids_into_material``), and the
G-code is not generated while there is one (gcode_builder.RapidsIntoMaterial).
The other is what an operation that plans its cuts starts from (StockBefore):
a Profile Roughing does not cut the air an operation above it left, a Groove
Finishing starts out of the material there is. In a program's toolpath it
follows the operations as they are written (ProgramStock); for one operation
on its own - its editor - it is worked out from those above it (stock_before).

The stock is in (z, r) - r the radius, the part turned about the axis - Z
in the work offset the program started in.
"""

from __future__ import annotations

import dataclasses
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from shapely.affinity import translate
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from .operations.profiling.shapes import _difference, _on_grid, goes_through, sweeps, turned
from .operations.profiling.tool_shape import ToolShape, cutting_shape
from .toolpath import Move, OperationPath, move_points


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
    sure: what it may have cut stays as it was, and where material is is no
    longer known after it. ``rapids_into_material``: its rapids that go
    through material known to be there when they are made."""
    index: int
    known: bool
    air_before: object
    air_after: object
    material_before: object
    material_after: object
    rapids_into_material: Tuple[Move, ...] = ()

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
        hits = _rapids_into(self.material, path, tool)
        if cut is None:
            # what it cut is not known: nor, then, where material is left
            self.material = Polygon()
        elif not cut.is_empty:
            self.air = _on_grid(unary_union([self.air, cut]))
            if not self.material.is_empty:
                self.material = _difference(self.material, cut)
        step = StockStep(path.index, cut is not None, air_before, self.air, material_before, self.material,
                         tuple(hits))
        self.steps.append(step)
        return step


def header_material(workpiece):
    """The material the header's workpiece says is there, in (z, r): the bar
    - or the tube, its bore left out - from its face at Z0 back as long as
    it is (stock_length, else what sticks out of the chuck). Nothing when the
    header does not say its diameter and length."""
    if workpiece is None:
        return Polygon()
    outer = float(workpiece.external_diameter or 0.0) / 2.0
    bore = min(max(0.0, float(workpiece.internal_diameter or 0.0) / 2.0), outer)
    length = float(workpiece.stock_length or 0.0) or float(workpiece.stickout_length or 0.0)
    if outer <= 0 or length <= 0 or bore >= outer:
        return Polygon()
    return box(-length, bore, 0.0, outer)


def _rapids_into(material, path: OperationPath, tool: Optional[ToolShape]) -> List[Move]:
    """The rapids of ``path`` that go through ``material``, as it is when
    each is made: less what the operation's feeds before it cut. ``tool``
    None: the control point's line, and only until it feeds - what it cuts
    then is not known."""
    if material.is_empty or not path.known or path.z_origin is None:
        return []
    z_origin = path.z_origin
    hits, pending = [], []          # pending: feeds not taken off ``material`` yet
    for move in path.moves:
        if move.feed:
            if tool is None:
                return hits
            if not move.synced:
                pending.append(move)
            continue
        points = [(z + z_origin, r) for z, r in move_points(move)]
        outline = tool.outline if tool is not None else None
        if not goes_through(material, points, outline):
            continue
        if pending:
            material = _difference(material, _cut(pending, tool, z_origin))
            pending = []
            if not goes_through(material, points, outline):
                continue
        hits.append(move)
    return hits


def _cut(feeds, tool: ToolShape, z_origin: float):
    """What ``tool`` going along ``feeds`` - Moves at the feed, not
    synchronized: a thread is cut, not all round - leaves air, turned about
    the axis."""
    pieces = []
    for move in feeds:
        points = [(z + z_origin, r) for z, r in move_points(move)]
        pieces.extend(sweeps(tool.outline, points))
    return _on_grid(turned(unary_union(pieces)))


@dataclass(frozen=True)
class StockBefore:
    """The stock as an operation finds it, in its own coordinates - Z as its
    G-code has it, r the radius: the air known there (``air``) and the
    material (``material``), shapely shapes; the rest is not known."""
    air: object = field(default_factory=Polygon)
    material: object = field(default_factory=Polygon)

    def key(self) -> str:
        """It as a plan's key has it: the same stock, the same key."""
        return hashlib.sha1(self.air.wkb + b"|" + self.material.wkb).hexdigest()


class ProgramStock:
    """The stock along a program as its toolpath is written
    (gcode_builder.program_toolpath): the operations are handed over as they
    are written (add) and applied to the model only once something asks -
    the stock an operation finds (before), the steps (steps) - so a program
    nothing asks it of costs nothing."""

    def __init__(self, material, tools):
        self.model = StockModel(material=material)
        self._tools = tools
        self._pending: List[OperationPath] = []
        self._shapes: Dict[int, Optional[ToolShape]] = {}

    def add(self, operation: OperationPath):
        self._pending.append(operation)

    def _catch_up(self):
        for operation in self._pending:
            self.model.apply(operation, self._shape(operation.tool_holder_id))
        self._pending = []

    def _shape(self, tool_holder_id: int) -> Optional[ToolShape]:
        """What cuts of the tool in holder ``tool_holder_id``, once for each."""
        from teachinlathe.tooling.model.data_types import MountedTool

        if tool_holder_id not in self._shapes:
            self._shapes[tool_holder_id] = (cutting_shape(MountedTool.of(self._tools, tool_holder_id))
                                            if tool_holder_id else None)
        return self._shapes[tool_holder_id]

    def before(self, z_origin: Optional[float]) -> StockBefore:
        """The stock the next operation finds, its Z0 at ``z_origin``; none of
        it known when where that is is not."""
        self._catch_up()
        if z_origin is None:
            return StockBefore()
        return StockBefore(translate(self.model.air, -z_origin), translate(self.model.material, -z_origin))

    @property
    def steps(self) -> List[StockStep]:
        self._catch_up()
        return self.model.steps


def program_stock(program, tools, path=None) -> List[StockStep]:
    """The stock as each of ``program``'s operations finds it and leaves it,
    from the material its header says is there (header_material): a
    StockStep for each operation that is written. ``tools``: where the tools
    are looked up - the Tool Library, a ToolSnapshot. ``path``: the program's
    toolpath (gcode_builder.program_toolpath), when it is already made."""
    from .gcode_builder import program_toolpath

    if path is None:
        path = program_toolpath(program, tools)
    return path.stock.steps


def rapids_text(moves) -> str:
    """What is wrong with ``moves``, rapids through the stock, for the
    operator: the first, where it goes, and how many more."""
    move, more = moves[0], len(moves) - 1
    return (f"rapid from X{2 * move.r0:.3f} Z{move.z0:.3f} to X{2 * move.r1:.3f} Z{move.z1:.3f} "
            f"goes through the stock" + (f" ({more} more)" if more else ""))


def operations_with_rapids_into_material(program, tools) -> List[int]:
    """The indexes of ``program``'s operations a rapid of which goes through
    the material there is: the ones its G-code is refused for."""
    return [step.index for step in program_stock(program, tools) if step.rapids_into_material]


def stock_key(program, op_index: int, tools) -> str:
    """What the stock the operation at ``op_index`` of ``program`` finds
    depends on: the header, the operations above it, and the tools of the
    program as ``tools`` has them."""
    from .operations.profiling.plan_cache import plan_key

    holders = [tool.tool_holder_id for tool in program.tools]
    return plan_key(header=program.header.to_dict(),
                    above=[op.to_dict() for op in program.operations[:max(op_index, 0)]],
                    tools=[(h, tools.find_holder(h), tools.tool_in(h)) for h in holders])


#: The stock an operation finds, by stock_key: an editor asks for it again
#: and again while what is above it stays as it is.
_BEFORE: Dict[str, StockBefore] = {}
_BEFORE_KEPT = 16


def stock_before(program, op_index: int, tools) -> StockBefore:
    """The stock the operation at ``op_index`` of ``program`` finds - from
    the toolpath of those above it - for an operation on its own, as its
    editor has it; the one worked out already while they stay the same."""
    from .gcode_builder import program_toolpath

    key = stock_key(program, op_index, tools)
    found = _BEFORE.get(key)
    if found is None:
        above = dataclasses.replace(program, operations=list(program.operations[:max(op_index, 0)]))
        path = program_toolpath(above, tools)
        found = path.stock.before(path.z_origin)
        _BEFORE[key] = found
        while len(_BEFORE) > _BEFORE_KEPT:
            _BEFORE.pop(next(iter(_BEFORE)))
    return found
