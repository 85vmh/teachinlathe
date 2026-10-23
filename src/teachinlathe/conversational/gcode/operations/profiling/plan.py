"""What the roughing planner is given and what it gives back: the setup, the
moves, the plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from teachinlathe.conversational.model.data_types import PassType, ProfilingType

from .shapes import Pt
from .tool_shape import ToolShape


@dataclass
class Move:
    """One straight move of the control point, in (z, r) as the machine has
    them (not mirrored). ``feed`` False is a rapid."""
    z0: float
    r0: float
    z1: float
    r1: float
    feed: bool
    pass_no: int = -1
    contour: bool = False
    pocket: bool = False
    #: the last move of a pass, its retract included: where an M1 stop goes
    pass_end: bool = False
    #: a contour move as the profile drawing shows it, (z0, r0, z1, r1): where
    #: the nose touches - along the profile and its stock - rather than the
    #: compensated point the machine is programmed to
    drawn: Optional[Tuple[float, float, float, float]] = None

@dataclass
class RoughingPlan:
    moves: List[Move] = field(default_factory=list)
    #: the profile offset by the stock to leave, from its start to its end, as
    #: (z, r) points: the line the contour keeps to
    allowance: List[Pt] = field(default_factory=list)
    #: what is left to cut once the operation is done, beyond the stock to
    #: leave: (z, r) outlines, as the machine has them
    residual: List[List[Pt]] = field(default_factory=list)
    #: the material before the operation, less the stock to leave
    to_remove: object = None
    #: the material once the operation is done, as a shapely shape in (z, r)
    remaining_stock: object = None
    tool: Optional[ToolShape] = None
    warnings: List[str] = field(default_factory=list)
    error: str = ""

@dataclass(frozen=True)
class RoughingSetup:
    x_start: float
    z_start: float
    doc: float
    retract: float
    stock_x: float
    stock_z: float
    profiling_type: ProfilingType
    pass_type: PassType
