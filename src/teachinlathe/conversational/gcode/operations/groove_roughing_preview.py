"""What Groove Roughing will cut, for drawing on the profile canvas: the
pecks of the G-code it writes (generate_groove_roughing_gcode), read back -
so the drawing is the program, peck for peck, along the blade's middle - its
finish contour on the contour itself, not where the blade's corners are
compensated to, and the groove's profile offset by the stock to leave. All X
values are diameters."""

import re

from .groove_roughing import (
    ROUNDING,
    SAME_MM,
    _blade_control,
    _blade_start_x,
    _blade_width,
    _cut_path,
    _first_groove,
    _groove_path,
    _profile_bounds_from_path,
    _reverse_path,
    _split_path_at_z,
    _start_x,
    _stock_allowance,
    generate_groove_roughing_gcode,
)
from .profiling.geometry import StartPoint, ToolpathArc
from .profiling.plan_drawing import _arc_points, flatten_path

#: How far from its own plunge toward the other a peck's number in the pair
#: in the middle is put: near enough to say whose it is, far enough from the
#: other's number at the same depth.
ORDER_BY_ITS_PLUNGE = 0.25

_WORD = re.compile(r"([GXZIK])(-?\d+(?:\.\d*)?)")
#: The comment a groove generator ends with when it cannot cut: why, after the "--".
_ERROR = re.compile(r"^/?\( ERROR: .*? -- (.*) \)$")
_CONTOUR = "Finish Contour"

#: What a groove preview has with nothing to show; each adds its own keys.
EMPTY = {"profile": [], "offset": [], "feeds": [], "rapids": [], "residual": [], "warnings": [], "error": ""}


def groove_path(op):
    """(path, profile_type, error) of the groove the op carries in
    ``_resolved_radial_profile``: its profile, from its Z+ end, and "" - or
    None and why not."""
    profile = op.get("_resolved_radial_profile", {}) or {}
    profile_type = str(profile.get("profile_type", "od")).lower()
    if not _first_groove(profile):
        return None, profile_type, "no radial profile with a groove above this operation"
    path = _groove_path(profile)
    if path is None:
        return None, profile_type, "the radial profile does not make a groove"
    return path, profile_type, ""


def gcode_error(lines):
    """Why a groove generator's ``lines`` cut nothing, or ""."""
    for line in lines:
        found = _ERROR.match(line.strip())
        if found:
            return found.group(1)
    return ""


def _moves(lines):
    """(feeds, rapids) of G-code ``lines``, each [{x0, z0, x1, z1}]; arcs as
    short lines. A feed also carries ``pass``, counting the cuts from 0 - a
    cut being the feeds between two rapids - and ``contour``, true from the
    finish contour's comment on."""
    feeds, rapids = [], []
    x = z = None
    mode = "G0"
    pass_no, last_feed = -1, False
    contour = False
    for line in lines:
        text = line.strip().lstrip("/").strip()
        if _CONTOUR in text:
            contour = True
        if not text or text.startswith("("):
            continue
        words = dict()
        for letter, value in _WORD.findall(text.split("(")[0]):
            if letter == "G":
                code = "G" + str(int(float(value)))
                if code in ("G0", "G1", "G2", "G3"):
                    mode = code
            else:
                words[letter] = float(value)
        if "X" not in words and "Z" not in words:
            continue
        new_x = words.get("X", x)
        new_z = words.get("Z", z)
        if x is not None and z is not None and new_x is not None and new_z is not None:
            if mode == "G0":
                if (x, z) != (new_x, new_z):
                    rapids.append({"x0": x, "z0": z, "x1": new_x, "z1": new_z})
                last_feed = False
            else:
                if not last_feed:
                    pass_no += 1
                last_feed = True
                points = [(new_x, new_z)]
                if mode in ("G2", "G3"):
                    # as emit_toolpath writes them: G2 for an anticlockwise
                    # ToolpathArc, I on the radius
                    arc = ToolpathArc(new_x, new_z, x + 2 * words.get("I", 0.0), z + words.get("K", 0.0),
                                      mode == "G2")
                    points = _arc_points(x, z, arc) + points
                px, pz = x, z
                for qx, qz in points:
                    feeds.append({"x0": px, "z0": pz, "x1": qx, "z1": qz, "pass": pass_no, "contour": contour})
                    px, pz = qx, qz
        x, z = new_x, new_z
    return feeds, rapids


def _from_start(feed, start_x, profile_type):
    """``feed`` from the start diameter ``start_x`` on - the part of it in the
    air above it cut off - or None when it is all in the air."""
    outside = (lambda x: x < start_x - ROUNDING) if profile_type == "id" else (lambda x: x > start_x + ROUNDING)
    if outside(feed["x0"]) and outside(feed["x1"]):
        return None
    if outside(feed["x0"]) and abs(feed["x1"] - feed["x0"]) > ROUNDING:
        t = (start_x - feed["x0"]) / (feed["x1"] - feed["x0"])
        feed["z0"] = feed["z0"] + t * (feed["z1"] - feed["z0"])
        feed["x0"] = start_x
    return feed


def _peck(feeds, peck_depth, plunges):
    """One whole peck, to point at Peck Depth from: {z, from, to} - on the
    first plunge after the two in the middle, toward Z+, or failing it the
    next that has two pecks one after the other a Peck Depth apart, from the
    end of the one to the end of the next - or None."""
    if peck_depth <= 0:
        return None
    by_z = {}
    for f in feeds:
        if abs(f["z1"] - f["z0"]) < SAME_MM:
            by_z.setdefault(round(f["z0"], 6), []).append(f["x1"])
    for z in [round(p, 6) for p in plunges[2:] + plunges[:2]]:
        ends = by_z.get(z, [])
        for a, b in zip(ends, ends[1:]):
            if abs(abs(b - a) - peck_depth) < SAME_MM:
                return {"z": z, "from": a, "to": b}
    return None


def _contour_feeds(path, cut_path, first_pass):
    """The finish contour as the G-code cuts it, on the contour - the profile
    with the stock to leave (``cut_path``) - not compensated: from the right
    flank's start to the groove's middle, then from the left one's. Each a
    pass of its own, from ``first_pass``, its arrows along it."""
    _x_min, _x_max, z_min, z_max = _profile_bounds_from_path(path)
    z_plus, z_minus = _split_path_at_z(cut_path, (z_min + z_max) / 2.0)
    feeds = []
    for n, section in enumerate((z_plus, _reverse_path(z_minus))):
        if not section or not isinstance(section[0], StartPoint):
            continue
        points = flatten_path(section)
        for a, b in zip(points, points[1:]):
            feeds.append({"x0": a["x"], "z0": a["z"], "x1": b["x"], "z1": b["z"],
                          "pass": first_pass + n, "contour": True, "arrows": "along"})
    return feeds


def build_groove_roughing_preview(op):
    """{profile, offset, feeds, rapids, plunges, peck, order, startDiameter,
    bladeX, error} for a
    Groove Roughing dict carrying its radial profile in
    ``_resolved_radial_profile`` and its tool in ``_resolved_tool``, as
    ProfileCanvas draws a roughing:

    profile     the groove's profile, as [{x, z}]
    offset      it offset by the stock to leave, as [{x, z}]; [] with none
    feeds       the cuts - the pecks, the finish contour - as [{x0, z0, x1, z1, pass,
                contour, arrows, endTick}]: a peck's ``arrows`` "end", its arrow
                where it ends, and ``endTick`` the half-width (mm) of the line
                across there; the contour's "along", arrows along it
    rapids      the rapid moves between them, likewise
    plunges     the Z of each plunge, in the order they are made
    peck        one whole peck, for its dimension: {z, from, to}, or None
    order       the pecks of the two plunges in the middle, made each in
                turn, numbered in that order: [{n, z, x, x0}] - between them, a
                ORDER_BY_ITS_PLUNGE of the way from its own, at the depth it goes to (``x``)
                from ``x0``
    startDiameter  the plunges' start: the pulley's outside with its radial
                stock to leave on it
    bladeX      where the blade starts: the clearance out from it
    error       why there is nothing to show, or ""
    """
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    empty = dict(EMPTY, plunges=[], peck=None, order=[], startDiameter=None, bladeX=None)
    path, profile_type, error = groove_path(op)
    if path is None:
        return dict(empty, error=error)

    stock = op.get("stock_to_leave", {}) or {}
    stock_on = bool(op.get("stock_to_leave_enabled", False))
    radial = abs(float(stock.get("radial", 0.0) or 0.0)) if stock_on else 0.0
    axial = abs(float(stock.get("axial", 0.0) or 0.0)) if stock_on else 0.0

    lines = generate_groove_roughing_gcode(op)
    error = gcode_error(lines)
    feeds, rapids = ([], []) if error else _moves(lines)
    # the G-code is written for the point the blade was touched off on; the
    # pecks are drawn down its middle
    tool = op.get("_resolved_tool")
    half_width = _blade_width(tool) / 2.0
    z_control = _blade_control(tool) * half_width
    for f in feeds:
        f["z0"] -= z_control
        f["z1"] -= z_control
    # the pecks, each with its arrow where it ends - the depth it goes to -
    # from the start diameter on, the pulley's largest with its radial stock
    # to leave: what the G-code feeds through above it is air; the contour
    # drawn on the contour
    start_x = _start_x(path, profile_type, radial)
    feeds = [f for f in (_from_start(dict(f, arrows="end"), start_x, profile_type)
                         for f in feeds if not f["contour"]) if f]
    plunges = []
    for f in feeds:
        if not any(abs(f["z0"] - z) < SAME_MM for z in plunges):
            plunges.append(f["z0"])
    peck = _peck(feeds, abs(float((op.get("cutting_parameters") or {}).get("peck_depth", 0) or 0)), plunges)
    # the two plunges in the middle are made a peck at a time each in turn:
    # each peck's place in that order, between them by its own plunge -
    # ORDER_BY_ITS_PLUNGE of the way to the other, so two at the same depth
    # stay apart - at the depth it goes to
    order = []
    if len(plunges) > 1:
        for f in feeds:
            for own, other in ((plunges[0], plunges[1]), (plunges[1], plunges[0])):
                if abs(f["z1"] - own) < SAME_MM:
                    order.append({"n": len(order) + 1, "z": own + (other - own) * ORDER_BY_ITS_PLUNGE, "x": f["x1"],
                                  "x0": f["x0"]})
    # where each peck ends, a line across as wide as the blade
    for f in feeds:
        f["endTick"] = half_width
    if not error:
        feeds += _contour_feeds(path, _cut_path(path, profile_type, radial, axial),
                                max([f["pass"] for f in feeds] + [-1]) + 1)
    # from where the blade starts - the clearance out from the start
    # diameter - down its middle to the start diameter, for the first two
    # plunges, the blade's and its outline's on the canvas; not the G-code's
    # rapids: the backing off and in of the pecks, and the moves between them
    # inside the groove, are not drawn
    clearance = abs(float((op.get("cutting_parameters") or {}).get("retract", 0) or 0))
    blade_x = _blade_start_x(start_x, profile_type, clearance)
    rapids = [{"x0": blade_x, "z0": z, "x1": start_x, "z1": z} for z in plunges[:2]] if clearance > 0 else []
    return dict(empty,
                startDiameter=start_x,
                bladeX=blade_x,
                plunges=plunges,
                peck=peck,
                order=order,
                profile=flatten_path(path),
                offset=[{"x": x, "z": z} for z, x in _stock_allowance(path, profile_type, radial, axial)],
                feeds=feeds,
                rapids=rapids,
                error=error)
