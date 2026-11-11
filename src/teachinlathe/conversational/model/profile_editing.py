"""What is done to a profile's primitives as its editor edits them: a Define
Profile's (startPoint, lineTo, arcTo, grooveTo) and a Define Radial Profile's
(groove, repeat), as their dicts - the operation's JSON. Each function takes
the list and gives a new one; none changes what it is given.

A Define Profile's rules: its start point stays first; its primitives are
numbered from 1 in their order; a corner where a groove starts has one blend,
the one just edited; a new primitive starts where the one before it ends.
"""

import copy
import math

#: What a blend starts with, by its type. The G-code's defaults for a saved
#: blend that lacks a value are data_types.ProfileBlend's: an undercut's there
#: have to stay these.
BLEND_DEFAULTS = {
    "chamfer": {"chamfer_width": 1.0},
    "fillet": {"fillet_radius": 1.0},
    "undercut_din509": {"undercut_radius": 0.4, "undercut_depth": 0.4, "undercut_length": 2.5},
}

_NO_BLEND = {"type": "none"}


def renumbered(primitives):
    """``primitives`` numbered from 1 in their order."""
    out = copy.deepcopy(list(primitives or []))
    for i, primitive in enumerate(out, start=1):
        primitive["primitive_id"] = i
    return out


def _has_blend(blend):
    return bool(blend) and bool(blend.get("type")) and blend.get("type") != "none"


def _keep_one_corner_blend(primitives, index):
    """A corner before a groove has two primitives that can give it a blend:
    the one ending there and the groove starting there. The one at ``index``,
    just edited, takes it from the other."""
    item = primitives[index]
    before = primitives[index - 1] if index > 0 else None
    after = primitives[index + 1] if index + 1 < len(primitives) else None
    if item["type"] == "grooveTo" and before and _has_blend(item["right_flank"].get("start_blend")):
        if before["type"] == "grooveTo":
            before["left_flank"]["start_blend"] = dict(_NO_BLEND)
        elif before["type"] != "startPoint":
            before["blend"] = dict(_NO_BLEND)
    end_blend = item["left_flank"].get("start_blend") if item["type"] == "grooveTo" else item.get("blend")
    if item["type"] != "startPoint" and after and after["type"] == "grooveTo" and _has_blend(end_blend):
        after["right_flank"]["start_blend"] = dict(_NO_BLEND)


def with_primitive(primitives, index, primitive):
    """``primitives`` with the one at ``index`` replaced by ``primitive``."""
    out = copy.deepcopy(list(primitives))
    out[index] = copy.deepcopy(primitive)
    _keep_one_corner_blend(out, index)
    return renumbered(out)


def with_blend(primitives, index, blend_type):
    """``primitives`` with a ``blend_type`` blend at the end of the one at
    ``index``, as a new blend starts (BLEND_DEFAULTS)."""
    primitive = copy.deepcopy(primitives[index])
    primitive["blend"] = {"type": blend_type, **BLEND_DEFAULTS.get(blend_type, {})}
    return with_primitive(primitives, index, primitive)


def without_primitive(primitives, index):
    """``primitives`` without the one at ``index`` - never the start point -
    and the one selected after: the one now there, or the last."""
    if not 0 < index < len(primitives):
        return renumbered(primitives), index
    out = copy.deepcopy(list(primitives))
    del out[index]
    return renumbered(out), min(index, len(out) - 1) if out else -1


def end_of(primitives, index):
    """Where the primitive at ``index`` ends, (x, z) - x a diameter; (0, 0)
    for none."""
    x = z = 0.0
    if not 0 <= index < len(primitives):
        return x, z
    for item in primitives[:index + 1]:
        kind = item.get("type")
        if kind == "startPoint":
            x, z = float(item.get("x_start", 0) or 0), float(item.get("z_start", 0) or 0)
        elif kind == "lineTo":
            mode = str(item.get("input", "xz")).lower()
            end_x, end_z = float(item.get("x_end", 0) or 0), float(item.get("z_end", 0) or 0)
            tan = math.tan(math.radians(float(item.get("angle", 0) or 0)))
            if mode == "az":
                x, z = x + 2.0 * (end_z - z) * tan, end_z
            elif mode == "ax":
                z = z if abs(tan) < 1e-12 else z + (end_x - x) / 2.0 / tan
                x = end_x
            else:
                x, z = end_x, end_z
        elif kind == "arcTo":
            x, z = float(item.get("x_end", 0) or 0), float(item.get("z_end", 0) or 0)
        elif kind == "grooveTo":
            x, z = float(item["left_flank"]["x_start"]), float(item["left_flank"]["z_start"])
    return x, z


def new_primitive(kind, x, z, profile_type="od"):
    """A new ``kind`` primitive ("lineTo", "arcTo", "grooveTo") starting at
    (x, z): a line or an arc to there, a groove 3 wide and 2 deep on the
    radius into the part."""
    if kind == "lineTo":
        return {"type": "lineTo", "primitive_id": 0, "input": "xz", "angle": 0,
                "x_end": x, "z_end": z, "blend": dict(_NO_BLEND)}
    if kind == "grooveTo":
        bottom_x = x + 4 if profile_type == "id" else max(0.0, x - 4)
        return {"type": "grooveTo", "primitive_id": 0,
                "right_flank": {"x_start": 0, "z_start": 0, "angle": 0, "start_blend": dict(_NO_BLEND)},
                "bottom": {"x_end_right": bottom_x, "x_end_left": bottom_x,
                           "blend_right": dict(_NO_BLEND), "blend_left": dict(_NO_BLEND)},
                "left_flank": {"x_start": x, "z_start": z - 3, "angle": 0, "start_blend": dict(_NO_BLEND)}}
    return {"type": "arcTo", "primitive_id": 0, "direction": "cw", "arc_radius": 10,
            "x_end": x, "z_end": z, "x_center": 0, "z_center": 0, "blend": dict(_NO_BLEND)}


def with_new_primitive(primitives, index, kind, profile_type="od"):
    """``primitives`` with a new ``kind`` primitive at ``index`` - never
    before the start point; past the end, last - starting where the one
    before it ends; and where it went."""
    out = copy.deepcopy(list(primitives))
    at = len(out) if index < 0 or index >= len(out) else max(1, index)
    x, z = end_of(out, at - 1)
    out.insert(at, new_primitive(kind, x, z, profile_type))
    return renumbered(out), at


# ── a Define Radial Profile's ───────────────────────────────────────────────

def _empty_radial_blend():
    return {"type": "none", "chamfer_width": 0.0, "fillet_radius": 0.0}


def new_radial_primitive(kind):
    """A new radial ``kind`` primitive: a groove 5 wide at Z0, from Ø30 down
    to Ø20, or a repeat of the first one 5 along."""
    if kind == "repeat":
        return {"primitive_id": 0, "type": "repeat", "repeat_primitive_id": 1, "repeat_count": 1, "z_offset": -5.0}
    return {"primitive_id": 0, "type": "groove",
            "right_flank": {"x_start": 30.0, "z_start": 0.0, "angle": 0.0, "start_blend": _empty_radial_blend()},
            "bottom": {"x_end_right": 20.0, "x_end_left": 20.0,
                       "blend_right": _empty_radial_blend(), "blend_left": _empty_radial_blend()},
            "left_flank": {"x_start": 30.0, "z_start": -5.0, "angle": 0.0, "start_blend": _empty_radial_blend()}}


def with_radial_primitive(primitives, index, primitive):
    """A radial profile's ``primitives`` with the one at ``index`` replaced."""
    out = copy.deepcopy(list(primitives))
    out[index] = copy.deepcopy(primitive)
    return renumbered(out)


def with_new_radial_primitive(primitives, kind):
    """A radial profile's ``primitives`` with a new ``kind`` one last; and
    where it went."""
    out = copy.deepcopy(list(primitives)) + [new_radial_primitive(kind)]
    return renumbered(out), len(out) - 1


def without_radial_primitive(primitives, index):
    """A radial profile's ``primitives`` without the one at ``index``, and the
    one selected after: the one now there, or the last."""
    if not 0 <= index < len(primitives):
        return renumbered(primitives), index
    out = copy.deepcopy(list(primitives))
    del out[index]
    return renumbered(out), min(index, len(out) - 1) if out else -1
