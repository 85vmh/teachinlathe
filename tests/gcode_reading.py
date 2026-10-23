"""The moves of generated G-code read back, for the tests to check them
against the plan they were written from."""

import re

from teachinlathe.conversational.gcode.operations.profiling.plan_drawing import _arc_points
from teachinlathe.conversational.gcode.operations.profiling.geometry import ToolpathArc

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
