"""The grooves of a Define Profile (GrooveTo) as the primitives they are drawn
and cut along - the one place that is worked out, for the G-code and the canvas.

A groove is three lines from where the profile has got to: its right flank, its
bottom and its left flank, each carrying the blend on the corner it ends. Its
top corners are between its flanks and what is either side of it in the profile:

- the start corner's blend goes on the primitive before it, which ends there;
- the end corner's is the left flank's, against the primitive after it.

With nothing that side - first after the start point, last in the profile - the
corner is against the outside along Z, as a groove of a radial profile has it
(groove_outline), and is cut here.
"""

from dataclasses import dataclass, replace
from typing import List, Tuple

from teachinlathe.conversational.model.data_types import (
    ArcTo, BlendType, GrooveTo, LineTo, ProfileBlend, ProfilePrimitive, StartPoint,
)

from .geometry import line_end
from .groove_outline import OUTSIDE_LEG, At, CornerCut, corner_cut, cut_arc, groove_points_from

_NO_BLEND = ProfileBlend(blend_type=BlendType.NONE)


@dataclass
class Expanded:
    """A primitive of a profile with its grooves expanded: the index in the
    profile of the one it was made for, and of the one whose blend it carries -
    another when a groove's start blend is on the primitive before the groove."""
    primitive: ProfilePrimitive
    source: int
    blend_source: int


def expand_grooves(primitives) -> List[Expanded]:
    """``primitives`` with every GrooveTo replaced by what it is made of (see
    the module). A groove with no primitive before it gives nothing."""
    out: List[Expanded] = []
    at = (0.0, 0.0)  # (X, a diameter; Z) where the profile has got to
    for index, primitive in enumerate(primitives):
        if isinstance(primitive, GrooveTo):
            if out:
                at = _expand_groove(primitive, index, at, index == len(primitives) - 1, out)
            continue
        at = _end_of(primitive, at)
        out.append(Expanded(primitive, index, index))
    return out


def expanded_primitives(primitives) -> list:
    """``primitives`` with every GrooveTo replaced by what it is made of."""
    return [expanded.primitive for expanded in expand_grooves(primitives)]


def _end_of(primitive: ProfilePrimitive, at: Tuple[float, float]) -> Tuple[float, float]:
    if isinstance(primitive, StartPoint):
        return float(primitive.x_start), float(primitive.z_start)
    if isinstance(primitive, LineTo):
        return line_end(primitive, *at)
    if isinstance(primitive, ArcTo):
        return float(primitive.x_end), float(primitive.z_end)
    return at


def _line(to: At, blend: ProfileBlend, groove: GrooveTo, index: int) -> Expanded:
    line = LineTo(primitive_id=groove.primitive_id, primitive_type="lineTo", x_end=to.x, z_end=to.z, blend=blend,
                  input="xz")
    return Expanded(line, index, index)


def _cut(cut: CornerCut, groove: GrooveTo, index: int) -> Expanded:
    """On along ``cut`` to its end: its arc, or a line."""
    if cut.center is not None:
        return Expanded(cut_arc(cut, groove.primitive_id), index, index)
    return _line(cut.end, _NO_BLEND, groove, index)


def _start_corner(groove: GrooveTo, index: int, p1: At, p2: At, out: List[Expanded]):
    """The groove's start blend on its corner with what comes before it."""
    blend = groove.right_flank.start_blend
    if blend.blend_type is BlendType.NONE:
        return
    before = out[-1]
    if not isinstance(before.primitive, StartPoint):
        before.primitive = replace(before.primitive, blend=blend)
        before.blend_source = index
        return
    # nothing before it but the start: the path starts where the blend does
    cut = corner_cut(p1, At(p1.z + OUTSIDE_LEG, p1.xh), p2, blend)
    if cut.start == cut.end:
        return
    before.primitive = replace(before.primitive, x_start=cut.start.x, z_start=cut.start.z, blend=_NO_BLEND)
    out.append(_cut(cut, groove, index))


def _expand_groove(groove: GrooveTo, index: int, at: Tuple[float, float], last: bool,
                   out: List[Expanded]) -> Tuple[float, float]:
    """``groove``, from ``at``, added to ``out``; where it ends."""
    bottom, left = groove.bottom, groove.left_flank
    p1, p2, p3, p4 = groove_points_from(At.on_diameter(*at), groove.right_flank.angle, bottom, left)
    _start_corner(groove, index, p1, p2, out)
    out.append(_line(p2, bottom.blend_right, groove, index))
    out.append(_line(p3, bottom.blend_left, groove, index))
    if not last:
        out.append(_line(p4, left.start_blend, groove, index))
        return p4.x, p4.z
    # nothing after it: its end corner is cut against the outside
    cut = corner_cut(p4, p3, At(p4.z - OUTSIDE_LEG, p4.xh), left.start_blend)
    out.append(_line(cut.start, _NO_BLEND, groove, index))
    if cut.start != cut.end:
        out.append(_cut(cut, groove, index))
    return p4.x, p4.z
