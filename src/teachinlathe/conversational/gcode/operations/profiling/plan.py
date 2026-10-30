"""What the roughing planner is given and what it gives back: the setup, the
moves, the plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from teachinlathe.conversational.model.data_types import PassType, ProfilingType

from ...toolpath import Move
from .shapes import Pt
from .tool_shape import ToolShape


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
    tool: Optional[ToolShape] = None
    warnings: List[str] = field(default_factory=list)
    error: str = ""

#: The angle the diagonal passes run at, from the Z axis, in degrees - as the
#: part has it, on the radius: 45° is as far along Z as across X/2.
DIAGONAL_ANGLE = 45.0
#: The angles a diagonal pass may run at.
DIAGONAL_ANGLE_RANGE = (30.0, 60.0)


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
    #: the diagonal passes' angle from the Z axis, in degrees
    diagonal_angle: float = DIAGONAL_ANGLE

    def __post_init__(self):
        low, high = DIAGONAL_ANGLE_RANGE
        if not low <= self.diagonal_angle <= high:
            raise ValueError(f"diagonal angle {self.diagonal_angle}° is not within {low:g}..{high:g}°")
