"""What the tool in the spindle is, for the marker to draw it.

LinuxCNC's tool table knows a tool's number, offsets, orientation and a
diameter - not that T3 is a DCMT 11 or a 6.8 mm drill. The Tool Library does:
holder N is TN, with the cutting tool clamped in it. This reads that, and
turns it into a description the insert actor builds its outline from: one
of the drawings below, by the kind of tool.

A drawing is a frozen dataclass of plain values, so the backplot can compare
it from one poll to the next and redraw only when the tool changes. Its
``rotation`` is in degrees, counter-clockwise, as the Tool Library turns the
same drawing - so the marker sits as the tool's card shows it.

None when there is nothing to describe - no tool in the spindle, an empty
holder: the actor then falls back to its default insert.
"""

import logging
from dataclasses import dataclass
from typing import Optional

LOG = logging.getLogger(__name__)

#: How a blade is placed at each orientation: degrees turned and whether it
#: is mirrored top to bottom first - BladeToolView's ``_PLACEMENT``.
_BLADE_PLACEMENT = {6: (0.0, False), 5: (-90.0, False), 8: (0.0, True), 7: (90.0, False)}



class ToolDrawing:
    """What every drawing has: how far it is turned, in degrees, and whether
    it is mirrored top to bottom first."""
    rotation: Optional[float] = 0.0
    mirror_y: bool = False


@dataclass(frozen=True)
class InsertDrawing(ToolDrawing):
    """An ISO turning insert - a boring bar's too. A field left None is the
    actor's: its default insert, the tool table's nose radius, the tool
    table's orientation."""
    family: Optional[str] = None
    size_index: Optional[int] = None
    nose_radius: Optional[float] = None
    rotation: Optional[float] = None
    active_corner: int = 0


@dataclass(frozen=True)
class ThreadingDrawing(ToolDrawing):
    size: str
    pitch: float
    mirrored: bool
    rotation: float = 0.0


@dataclass(frozen=True)
class BladeDrawing(ToolDrawing):
    width: float
    left_radius: float
    right_radius: float
    #: the point its Z offset was taken on: -1 its left corner, 0 its
    #: middle, 1 its right corner
    control: int
    rotation: float = 0.0
    mirror_y: bool = False


@dataclass(frozen=True)
class DrillDrawing(ToolDrawing):
    diameter: float
    tip_angle: float
    right_hand: bool
    rotation: float = 0.0


@dataclass(frozen=True)
class ReamerDrawing(ToolDrawing):
    diameter: float
    rotation: float = 0.0


@dataclass(frozen=True)
class TapDrawing(ToolDrawing):
    diameter: float
    pitch: float
    right_hand: bool
    rotation: float = 0.0


def _repository():
    from teachinlathe.core.tool_library_repository import tool_library_repository
    return tool_library_repository()


def tool_in(tool_no):
    """The cutting tool clamped in holder ``tool_no``, or None."""
    if not tool_no or tool_no <= 0:
        return None
    return _repository().tool_in(int(tool_no))


def describe(tool_no, repository=None) -> Optional[ToolDrawing]:
    """The tool in holder ``tool_no``, as the actor draws it; None for
    none. ``repository``: where to look it up, the Tool Library if not given."""
    if not tool_no or tool_no <= 0:
        return None
    repository = repository or _repository()
    holder = repository.find_holder(int(tool_no))
    tool = repository.tool_in(int(tool_no))
    if tool is None:
        return None
    try:
        return _describe(holder, tool)
    except Exception as exc:        # bad data must not stop the plot drawing
        LOG.warning("backplot: cannot describe T%s: %s", tool_no, exc)
        return None


def _describe(holder, tool):
    from teachinlathe.tooling.model import insert_catalog, threading_catalog, tool_angles
    from teachinlathe.tooling.model.data_types import (BladeTool, DrillingTool, MountedTool,
                                                 ReamingTool, TappingTool, ThreadingTool,
                                                 TurningTool, TwistDirection)

    if isinstance(tool, ThreadingTool):
        hand = threading_catalog.hand_of(tool.insert.geometry, tool.orientation)
        size = threading_catalog.size_of(tool.insert.size)
        return ThreadingDrawing(size=size, pitch=threading_catalog.nearest_pitch(size, tool.pitch),
                                mirrored=threading_catalog.DRAWN_HAND[hand] == "L",
                                rotation=180.0 if threading_catalog.ORIENTATION[hand] == 8 else 0.0)

    if isinstance(tool, TurningTool):           # boring bars too
        insert = insert_catalog.insert_for(tool.insert)
        corner = tool_angles.direction_degrees(insert.active_tip())
        return InsertDrawing(family=insert.family, size_index=insert.size_index,
                             nose_radius=insert.nose_radius,
                             rotation=tool_angles.insert_rotation(
                                 tool.orientation, tool.front_angle, tool.back_angle, corner))

    if isinstance(tool, BladeTool):
        rotation, mirrored = _BLADE_PLACEMENT.get(tool.orientation, _BLADE_PLACEMENT[6])
        mounted = MountedTool(int(holder.tool_holder_id), tool, holder.z_offset_place)
        return BladeDrawing(width=tool.blade_width, left_radius=tool.left_radius,
                            right_radius=tool.right_radius, control=mounted.z_control,
                            rotation=rotation, mirror_y=mirrored)

    if not isinstance(tool, (DrillingTool, ReamingTool, TappingTool)) or tool.diameter <= 0:
        return None                             # nothing to draw it at
    if isinstance(tool, ReamingTool):
        return ReamerDrawing(diameter=tool.diameter)
    right_hand = tool.twist_direction is not TwistDirection.LEFT_HAND
    if isinstance(tool, DrillingTool):
        return DrillDrawing(diameter=tool.diameter, tip_angle=tool.tip_angle, right_hand=right_hand)
    return TapDrawing(diameter=tool.diameter, pitch=tool.pitch, right_hand=right_hand)
