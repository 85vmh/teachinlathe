"""The moves of generated G-code read back, for the tests to check them
against the plan they were written from."""

import re

from teachinlathe.conversational.gcode.operations.profiling.plan_drawing import _arc_points
from teachinlathe.conversational.gcode.operations.profiling.geometry import ToolpathArc
from teachinlathe.conversational.gcode.operations.profiling.operation_input import GrooveCut, ProfileCut
from teachinlathe.conversational.model.data_types import Operation, StockToLeave
from teachinlathe.conversational.model.factories import make_default_operation

_ROUGHING_START = "(----------Profiling Type:"
_CONTOUR_START = "( Contour with StockToLeave"
_MOTION = re.compile(
    r"^/?\s*(G[0-3])?\s*(?:X(-?[\d.]+))?\s*(?:Z(-?[\d.]+))?\s*(?:I(-?[\d.]+))?\s*(?:K(-?[\d.]+))?"
)


def gcode_moves(lines, start=_ROUGHING_START):
    """The moves of generated G-code ``lines`` from the comment that begins
    with ``start`` on, as (feeds, rapids), each [{x0, z0, x1, z1}]; arcs come
    as short lines. A feed also carries ``pass``, counting the passes from 0,
    a pass being the feeds between two rapids, and ``contour``, true from the
    contour pass's comment on.
    """
    feeds, rapids = [], []
    pass_no = -1
    last_mode = None
    in_moves = in_contour = False
    mode = None
    x = z = None
    for line in lines:
        text = line.strip()
        if text.startswith(start):
            in_moves = True
        if text.startswith(_CONTOUR_START):
            in_contour = True
        if not in_moves or not text or text.startswith("(") or "o<" in text:
            continue
        match = _MOTION.match(text)
        if not match or (match.group(2) is None and match.group(3) is None):
            continue
        mode = match.group(1) or mode
        new_x = float(match.group(2)) if match.group(2) is not None else x
        new_z = float(match.group(3)) if match.group(3) is not None else z
        if x is not None and z is not None and new_x is not None and new_z is not None:
            if mode == "G0":
                rapids.append({"x0": x, "z0": z, "x1": new_x, "z1": new_z})
            else:
                if last_mode != "G1":
                    pass_no += 1
                points = [(new_x, new_z)]
                if mode in ("G2", "G3"):
                    # as emit_toolpath writes them: G2 for an anticlockwise
                    # ToolpathArc, I on the radius
                    arc = ToolpathArc(new_x, new_z,
                                      x + 2 * float(match.group(4) or 0), z + float(match.group(5) or 0),
                                      mode == "G2")
                    points = _arc_points(x, z, arc) + points
                px, pz = x, z
                for qx, qz in points:
                    feeds.append({"x0": px, "z0": pz, "x1": qx, "z1": qz,
                                  "pass": pass_no, "contour": in_contour})
                    px, pz = qx, qz
            last_mode = "G1" if mode != "G0" else "G0"
        x, z = new_x, new_z
    return feeds, rapids


def profile_cut_of(fixture):
    """A test's Profile Roughing or Contour as it is cut (a ProfileCut), from
    ``fixture``: the parts of the operation's dict it sets - the rest the new
    operation's - and what it is cut against: ``_resolved_profile`` ({profile_type,
    profile_primitives}), ``_resolved_cutting_tool`` (a CuttingTool, or None)
    and ``_resolved_previous_roughing`` (fixtures or ProfileCuts)."""
    data = dict(fixture)
    resolved = data.pop("_resolved_profile", None)
    tool = data.pop("_resolved_cutting_tool", None)
    previous = data.pop("_resolved_previous_roughing", [])
    op_type = "profileContour" if "profile_contour_strategy" in data else "profileRoughing"
    op_data = make_default_operation(op_type).to_dict()
    for key, value in data.items():
        op_data[key] = {**op_data[key], **value} if isinstance(op_data.get(key), dict) else value
    profile = None
    if resolved is not None:
        profile_data = make_default_operation("defineProfile").to_dict()
        profile_data.update(profile_type=resolved["profile_type"],
                            profile_primitives=resolved["profile_primitives"])
        profile = Operation.from_dict(profile_data)
    return ProfileCut(Operation.from_dict(op_data), profile, tool,
                      tuple(p if isinstance(p, ProfileCut) else profile_cut_of(p) for p in previous))


def groove_cut_of(fixture):
    """A test's Groove Roughing or Finishing as it is cut (a GrooveCut), from
    ``fixture``: the parts of the operation's dict it sets - "type" saying
    which, the rest the new operation's - and what it is cut against:
    ``_resolved_radial_profile`` (the radial profile's dict, or what of it the
    test sets), ``_resolved_tool`` (a MountedTool, or None) and, for a
    finishing, ``_resolved_roughing_stock`` ({radial, axial})."""
    data = dict(fixture)
    resolved = data.pop("_resolved_radial_profile", None)
    tool = data.pop("_resolved_tool", None)
    stock = data.pop("_resolved_roughing_stock", None)
    op_type = data.pop("type", "grooveRoughing")
    op_data = make_default_operation(op_type).to_dict()
    for key, value in data.items():
        op_data[key] = {**op_data[key], **value} if isinstance(op_data.get(key), dict) else value
    profile = None
    if resolved:
        profile_data = {**make_default_operation("defineRadialProfile").to_dict(), **resolved}
        profile = Operation.from_dict(profile_data)
    roughing_stock = (StockToLeave(stock["radial"], stock["axial"])
                      if stock and (stock["radial"] or stock["axial"]) else None)
    return GrooveCut(Operation.from_dict(op_data), profile, tool, roughing_stock)
