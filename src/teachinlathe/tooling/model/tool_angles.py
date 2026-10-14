"""How an insert sits in its holder: front angle, back angle, orientation.

Both angles are measured from the horizontal line through the tip - the Z
axis - one from each side of it, turning toward the body. The two and the
insert's corner make up the straight angle: ``front + corner + back = 180``.

* corner orientations 1-4: the back angle is measured from the side of the
  Z axis the body lies on, the front from the other side. An 80 degree CCMT
  held with 5 at the back has 95 in front. Either can be chosen; the other
  follows.
* orientations 6 and 8 point the tip along X, so the tool sits square and
  the two are equal - neither is a choice: a 35 degree VBMT has 72.5 either
  side.

Directions here are as the orientation pictures draw them
(``images/lathe_control_point_N.png``): +Z to the right, +X up, angles
counter-clockwise from +Z.
"""

from __future__ import annotations

import math
from typing import NamedTuple, Optional, Tuple

Vector = Tuple[float, float]

_RIGHT, _LEFT, _UP, _DOWN = (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)


class Frame(NamedTuple):
    """The two halves of the Z axis the angles are measured from, and the
    way along X the body lies - which way both edges turn."""

    front_ray: Vector
    back_ray: Vector
    body_side: Vector


#: front + corner + back, at every orientation that has a direction.
SPAN = 180.0


def _frame(orientation: int) -> Optional[Frame]:
    """The body lies opposite the tip: orientation 2's tip points up and to
    the left, so its body runs right (the back side) and down."""
    match orientation:
        case 1:
            return Frame(front_ray=_RIGHT, back_ray=_LEFT, body_side=_DOWN)
        case 2:
            return Frame(front_ray=_LEFT, back_ray=_RIGHT, body_side=_DOWN)
        case 3:
            return Frame(front_ray=_LEFT, back_ray=_RIGHT, body_side=_UP)
        case 4:
            return Frame(front_ray=_RIGHT, back_ray=_LEFT, body_side=_UP)
        case 6:
            return Frame(front_ray=_LEFT, back_ray=_RIGHT, body_side=_DOWN)
        case 8:
            return Frame(front_ray=_LEFT, back_ray=_RIGHT, body_side=_UP)
    return None


def is_symmetric(orientation: int) -> bool:
    """Whether the orientation fixes both angles equal (6 and 8)."""
    return orientation in (6, 8)


def symmetric_angle(corner: Optional[float]) -> Optional[float]:
    """Front and back angle of a tool held square on X: half of what the
    corner leaves of 180 degrees."""
    return None if corner is None else max(0.0, (SPAN - corner) / 2.0)


def angle_span(orientation: int) -> Optional[float]:
    return None if _frame(orientation) is None else SPAN


def max_angle(corner: Optional[float], orientation: int) -> Optional[float]:
    """The most either angle can be; None when they are not coupled."""
    span = angle_span(orientation)
    if span is None or corner is None:
        return None
    return max(0.0, span - corner)


def complementary_angle(other: float, corner: Optional[float],
                        orientation: int) -> Optional[float]:
    """The back angle for a front angle, or the front for a back - the
    relation is the same both ways. None when they are not coupled: a round
    insert has no corner, and orientations 5, 7 and 9 have no span."""
    limit = max_angle(corner, orientation)
    if limit is None:
        return None
    return limit - clamp_angle(other, corner, orientation)


def clamp_angle(value: float, corner: Optional[float], orientation: int) -> float:
    limit = max_angle(corner, orientation)
    value = max(0.0, float(value))
    return value if limit is None else min(value, limit)


class EdgeGeometry(NamedTuple):
    """Directions from the tip, in degrees: the rays each angle is measured
    from, the two cutting edges, and the way the tip points."""

    front_ray: float
    front_edge: float
    back_ray: float
    back_edge: float
    tip: float


def edge_geometry(orientation: int, front: float, back: float) -> Optional[EdgeGeometry]:
    frame = _frame(orientation)
    if frame is None:
        return None
    front_edge = _turn_toward(frame.front_ray, frame.body_side, front)
    back_edge = _turn_toward(frame.back_ray, frame.body_side, back)
    into_body = (front_edge[0] + back_edge[0], front_edge[1] + back_edge[1])
    return EdgeGeometry(
        front_ray=direction_degrees(frame.front_ray), front_edge=direction_degrees(front_edge),
        back_ray=direction_degrees(frame.back_ray), back_edge=direction_degrees(back_edge),
        tip=direction_degrees((-into_body[0], -into_body[1])),
    )


def insert_rotation(orientation: int, front: float, back: float,
                    corner_direction: float) -> float:
    """Degrees to turn an insert drawing - counter-clockwise, as
    ``TurningInsertBase.orientation`` takes it - so that its cutting corner,
    which points at ``corner_direction`` in the insert's own frame, sits at
    these angles. 0 when the orientation has no direction."""
    geometry = edge_geometry(orientation, front, back)
    if geometry is None:
        return 0.0
    return (geometry.tip - corner_direction) % 360.0


def _turn_toward(ray: Vector, toward: Vector, degrees: float) -> Vector:
    rad = math.radians(degrees)
    return (ray[0] * math.cos(rad) + toward[0] * math.sin(rad),
            ray[1] * math.cos(rad) + toward[1] * math.sin(rad))


def direction_degrees(vector: Vector) -> float:
    """The direction of a vector, in degrees counter-clockwise from +Z."""
    return math.degrees(math.atan2(vector[1], vector[0])) % 360.0