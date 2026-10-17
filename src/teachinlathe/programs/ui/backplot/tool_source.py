"""What the tool in the spindle is, for the marker to draw it.

LinuxCNC's tool table knows a tool's number, offsets, orientation and a
diameter - not that T3 is a DCMT 11 or a 6.8 mm drill. The Tool Library does:
holder N is TN, with the cutting tool clamped in it. This reads that, and
turns it into a plain description the insert actor builds its outline from.

The description is a dict of plain values, so the backplot can compare it
from one poll to the next and redraw only when the tool changes. Its
``rotation`` is in degrees, counter-clockwise, as the Tool Library turns the
same drawing - so the marker sits as the tool's card shows it.

Empty when there is nothing to describe - no library, no tool in the
spindle, an empty holder: the actor then falls back to its default insert.
"""

import logging

LOG = logging.getLogger(__name__)

#: The Tool Library's store, set once at start-up by the main window.
_store = None

#: How a blade is placed at each orientation: degrees turned and whether it
#: is mirrored top to bottom first - BladeToolView's ``_PLACEMENT``.
_BLADE_PLACEMENT = {6: (0.0, False), 5: (-90.0, False), 8: (0.0, True), 7: (90.0, False)}

#: Which point of a blade the Z offset was taken from: -1, 0 or 1.
_BLADE_CONTROL = {"-1": -1, "0": 0, "1": 1}


def set_store(store):
    global _store
    _store = store


def tool_in(tool_no):
    """The cutting tool clamped in holder ``tool_no``, or None."""
    if _store is None or not tool_no or tool_no <= 0:
        return None
    holder = _store.find_holder(int(tool_no))
    return _store.find_tool(holder.cutting_tool_id) if holder is not None else None


def describe(tool_no):
    """The tool in holder ``tool_no``, as the actor draws it; ``{}`` for
    none."""
    if _store is None or not tool_no or tool_no <= 0:
        return {}
    holder = _store.find_holder(int(tool_no))
    if holder is None:
        return {}
    tool = _store.find_tool(holder.cutting_tool_id)
    if tool is None:
        return {}
    try:
        return _describe(holder, tool)
    except Exception as exc:        # bad data must not stop the plot drawing
        LOG.warning("backplot: cannot describe T%s: %s", tool_no, exc)
        return {}


def _describe(holder, tool):
    from teachinlathe.tooling.model import insert_catalog, threading_catalog, tool_angles
    from teachinlathe.tooling.model.data_types import (BladeTool, DrillingTool, ReamingTool,
                                                 TappingTool, ThreadingTool, TurningTool,
                                                 TwistDirection)

    if isinstance(tool, ThreadingTool):
        hand = threading_catalog.hand_of(tool.insert.geometry, tool.orientation)
        size = threading_catalog.size_of(tool.insert.size)
        return {"kind": "threading", "size": size,
                "pitch": threading_catalog.nearest_pitch(size, tool.pitch),
                "mirrored": threading_catalog.DRAWN_HAND[hand] == "L",
                "rotation": 180.0 if threading_catalog.ORIENTATION[hand] == 8 else 0.0}

    if isinstance(tool, TurningTool):           # boring bars too
        insert = insert_catalog.insert_for(tool.insert)
        corner = tool_angles.direction_degrees(insert.active_tip())
        return {"kind": "insert", "family": insert.family,
                "size_index": insert.size_index, "nose_radius": insert.nose_radius,
                "rotation": tool_angles.insert_rotation(
                    tool.orientation, tool.front_angle, tool.back_angle, corner)}

    if isinstance(tool, BladeTool):
        rotation, mirrored = _BLADE_PLACEMENT.get(tool.orientation, _BLADE_PLACEMENT[6])
        place = holder.z_offset_place.value if holder.z_offset_place is not None else "0"
        return {"kind": "blade", "width": tool.blade_width,
                "left_radius": tool.left_radius, "right_radius": tool.right_radius,
                "control": _BLADE_CONTROL.get(place, 0),
                "rotation": rotation, "mirror_y": mirrored}

    if getattr(tool, "diameter", 0.0) <= 0:
        return {}                               # nothing to draw it at
    right_hand = getattr(tool, "twist_direction", None) is not TwistDirection.LEFT_HAND
    # the M code the spindle turns the tool with: 3 or 4
    spindle = int(tool.spindle_direction)
    if isinstance(tool, DrillingTool):
        return {"kind": "drill", "diameter": tool.diameter,
                "tip_angle": tool.tip_angle, "right_hand": right_hand, "rotation": 0.0,
                "spindle_direction": spindle}
    if isinstance(tool, ReamingTool):
        return {"kind": "reamer", "diameter": tool.diameter, "rotation": 0.0,
                "spindle_direction": spindle}
    if isinstance(tool, TappingTool):
        return {"kind": "tap", "diameter": tool.diameter, "pitch": tool.pitch,
                "right_hand": right_hand, "rotation": 0.0, "spindle_direction": spindle}
    return {}
