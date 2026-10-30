"""Groove Roughing's G-code against the groove it roughs: on every move - feed
or rapid - the blade, its corners rounded as they are, swept from where it
was to where it goes, never enters the part, nor the stock it is to be left
with. The G-code is read back move by move, for the point the blade was
touched off on - a corner or the middle of its end - so the blade is placed
as the machine places it."""

import math
import re

import pytest
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from gcode_reading import groove_cut_of
from teachinlathe.tooling.model.data_types import BladeTool, MountedTool, ZOffsetPlace
from teachinlathe.conversational.gcode.operations.groove_roughing import generate_groove_roughing_gcode
from teachinlathe.conversational.gcode.operations.profiling.groove_outline import groove_outline
from teachinlathe.conversational.gcode.operations.profiling.geometry import build_path
from teachinlathe.conversational.model.data_types import Groove, ProfilingType, radial_primitives_from
from teachinlathe.conversational.gcode.operations.profiling.shapes import minkowski, path_points

#: How far into the part or its stock a move may go, mm^2: rounding only.
MAX_OVERLAP = 1e-4

_WORD = re.compile(r"([GXZIK])(-?\d+(?:\.\d*)?)")


def _blend(kind="none", size=0.0):
    return {"type": kind, "chamfer_width": size, "fillet_radius": size}


def _groove(top=30.0, bottom=12.0, right=-20.0, left=-30.0, angle=0.0, start=None, corners=None):
    start = start or _blend()
    corners = corners or _blend()
    return {"primitive_id": 1, "type": "groove",
            "right_flank": {"x_start": top, "z_start": right, "angle": angle, "start_blend": start},
            "bottom": {"x_end_right": bottom, "x_end_left": bottom, "blend_right": corners, "blend_left": corners},
            "left_flank": {"x_start": top, "z_start": left, "angle": angle, "start_blend": start}}


GROOVES = {
    # upright flanks, sharp corners
    "plain": _groove(),
    # the Grooving tests program's: fillets at the mouth and the bottom
    "filleted": _groove(start=_blend("fillet", 1.0), corners=_blend("fillet", 1.0)),
    # flanks at 10 degrees, chamfered
    "angled": _groove(angle=10.0, start=_blend("chamfer", 1.0), corners=_blend("chamfer", 0.5)),
    # narrow: three blades wide
    "narrow": _groove(right=-24.0, left=-28.5, bottom=20.0),
}

BLADES = {
    "1.5 touched off left": {"width": 1.5, "left_radius": 0.2, "right_radius": 0.2, "control": -1},
    "1.5 touched off middle": {"width": 1.5, "left_radius": 0.2, "right_radius": 0.2, "control": 0},
    "1.5 touched off right": {"width": 1.5, "left_radius": 0.2, "right_radius": 0.2, "control": 1},
    "3 touched off left": {"width": 3.0, "left_radius": 0.5, "right_radius": 0.3, "control": -1},
}

STOCK = {"none": None, "0.5 / 0.2": (0.5, 0.2)}

CASES = [(g, b, s) for g in GROOVES for b in BLADES for s in STOCK]


def _op(groove, blade, stock, initial=1.0, afterwards=1.5, peck=5.0, clearance=1.0, profile_type="od"):
    radial, axial = stock or (0.0, 0.0)
    return {
        "type": "grooveRoughing",
        "speeds_and_feeds": {"direction": "M3", "mode": "rpm", "rpm_value": 1000, "feed_rate": 0.1},
        "cutting_parameters": {"peck_depth": peck, "retract": clearance, "dwell_time": 0.2},
        "roughing_parameters": {"profile_id": 1, "strategy": "start_center",
                                "initial_offset": initial, "afterwards_offset": afterwards},
        "stock_to_leave": {"radial": radial, "axial": axial},
        "stock_to_leave_enabled": stock is not None,
        "_resolved_tool": _mounted(blade, 8 if profile_type == "id" else 6),
        "_resolved_radial_profile": {"profile_id": 1, "profile_type": profile_type,
                                     "profile_primitives": [groove]},
    }


def _mounted(blade, orientation):
    """Blade ``blade`` (one of BLADES) as mounted, in T13."""
    return MountedTool(13, BladeTool(cutting_tool_id=13, blade_width=blade["width"],
                                     left_radius=blade["left_radius"], right_radius=blade["right_radius"],
                                     orientation=orientation),
                       ZOffsetPlace(str(blade["control"])))


def _blade_of(op):
    """The blade ``op`` cuts with, as BLADES has it."""
    mounted = op["_resolved_tool"]
    return {"width": mounted.blade.blade_width, "left_radius": mounted.blade.left_radius,
            "right_radius": mounted.blade.right_radius, "control": mounted.z_control}


def _moves(lines):
    """Every move of the G-code, [(x0, z0, x1, z1)] - X a diameter - arcs as
    short chords."""
    moves, x, z, mode = [], None, None, "G0"
    for line in lines:
        text = line.strip().lstrip("/").split("(")[0]
        words = {}
        for letter, value in _WORD.findall(text):
            if letter == "G":
                code = "G%d" % int(float(value))
                if code in ("G0", "G1", "G2", "G3"):
                    mode = code
            else:
                words[letter] = float(value)
        if "X" not in words and "Z" not in words:
            continue
        nx, nz = words.get("X", x), words.get("Z", z)
        if None not in (x, z, nx, nz):
            if mode in ("G2", "G3"):
                moves.extend(_arc(x, z, nx, nz, words.get("I", 0.0), words.get("K", 0.0)))
            else:
                moves.append((x, z, nx, nz))
        x, z = nx, nz
    return moves


def _arc(x0, z0, x1, z1, i, k, steps=16):
    """An arc from (x0, z0) to (x1, z1), its centre I (on the radius) and K
    off the start, as chords - the shorter way round."""
    cr, cz = x0 / 2 + i, z0 + k
    a0 = math.atan2(x0 / 2 - cr, z0 - cz)
    a1 = math.atan2(x1 / 2 - cr, z1 - cz)
    sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    radius = math.hypot(i, k)
    points = [(2 * (cr + radius * math.sin(a0 + sweep * n / steps)), cz + radius * math.cos(a0 + sweep * n / steps))
              for n in range(steps + 1)]
    points[0], points[-1] = (x0, z0), (x1, z1)
    return [(a[0], a[1], b[0], b[1]) for a, b in zip(points, points[1:])]


def _blade(x, z, blade, sign):
    """The blade at G-code point (x, z), in the frame the part is checked in:
    (z, r) with r turned over for ID, the blade's end down, its body up. Its
    end's middle is ``control`` half-widths off the point along Z."""
    half = blade["width"] / 2
    middle = z - blade["control"] * half
    tip = sign * x / 2
    left, right = blade["left_radius"], blade["right_radius"]
    body = 50.0
    # each half of its end rounded by its own corner's radius
    shape = [box(middle - half + left, tip, middle + half - right, tip + body),
             box(middle - half, tip + left, middle, tip + body),
             box(middle, tip + right, middle + half, tip + body)]
    if left > 0:
        shape.append(Point(middle - half + left, tip + left).buffer(left, 32))
    if right > 0:
        shape.append(Point(middle + half - right, tip + right).buffer(right, 32))
    return unary_union(shape)


def _part(op):
    """The part with the stock it is to be left with, in the checking frame:
    under the groove's profile, the bar carried on past it either side."""
    profile = op["_resolved_radial_profile"]
    sign = -1.0 if profile["profile_type"] == "id" else 1.0
    groove = next(p for p in radial_primitives_from(profile["profile_primitives"]) if isinstance(p, Groove))
    path = build_path(list(groove_outline(groove).primitives), ProfilingType(profile["profile_type"]))
    points = [(z, sign * r) for z, r in path_points(path)]
    if points[0][0] < points[-1][0]:
        points.reverse()
    (zr, rr), (zl, rl) = points[0], points[-1]
    floor = min(r for _z, r in points) - 100.0
    part = Polygon([(zr + 100, rr)] + points + [(zl - 100, rl), (zl - 100, floor), (zr + 100, floor)]).buffer(0)
    if op["stock_to_leave_enabled"]:
        radial, axial = op["stock_to_leave"]["radial"], op["stock_to_leave"]["axial"]
        part = minkowski(part, [(-axial, -radial), (axial, -radial), (axial, radial), (-axial, radial)])
    return part.buffer(-1e-3), sign


def _gouges(op):
    """The moves whose swept blade enters the part or its stock to leave:
    [(line of the move, (x0, z0, x1, z1), area)]."""
    lines = generate_groove_roughing_gcode(groove_cut_of(op))
    assert not [line for line in lines if "ERROR" in line], lines
    part, sign = _part(op)
    blade = _blade_of(op)
    found = []
    for move in _moves(lines):
        x0, z0, x1, z1 = move
        swept = unary_union([_blade(x0, z0, blade, sign), _blade(x1, z1, blade, sign)]).convex_hull
        area = swept.intersection(part).area
        if area > MAX_OVERLAP:
            found.append((move, round(area, 5)))
    return found


@pytest.mark.parametrize("groove,blade,stock", CASES)
def test_no_move_takes_the_blade_into_the_part_or_its_stock(groove, blade, stock):
    op = _op(GROOVES[groove], BLADES[blade], STOCK[stock])

    assert _gouges(op) == []


@pytest.mark.parametrize("initial,afterwards,peck", [(0.0, 1.0, 3.0), (1.0, 1.5, 5.0), (2.0, 0.5, 2.0),
                                                     (0.5, 1.0, 20.0)])
def test_no_move_goes_past_the_profile_whatever_the_steps(initial, afterwards, peck):
    """The pair of plunges in the middle backs off from the other's depth
    after each peck: with both at the bottom, that is still out of it."""
    op = _op(GROOVES["filleted"], BLADES["1.5 touched off left"], None,
             initial=initial, afterwards=afterwards, peck=peck)

    assert _gouges(op) == []


def test_no_move_goes_deeper_than_the_smallest_diameter():
    """The Grooving tests program: its bottom at 12, no stock to leave - no
    X under 12 anywhere, rapids included."""
    op = _op(GROOVES["filleted"], BLADES["1.5 touched off left"], None)
    xs = [x for move in _moves(generate_groove_roughing_gcode(groove_cut_of(op))) for x in (move[0], move[2])]

    assert min(xs) >= 12.0 - 1e-6


@pytest.mark.parametrize("groove", ["plain", "filleted"])
def test_an_id_groove_is_roughed_inside_it_too(groove):
    op = _op(dict(GROOVES[groove], right_flank=dict(GROOVES[groove]["right_flank"], x_start=12.0),
                  left_flank=dict(GROOVES[groove]["left_flank"], x_start=12.0),
                  bottom=dict(GROOVES[groove]["bottom"], x_end_right=30.0, x_end_left=30.0)),
             BLADES["1.5 touched off middle"], STOCK["0.5 / 0.2"], profile_type="id")

    assert _gouges(op) == []


@pytest.mark.parametrize("groove", ["plain", "filleted", "angled"])
@pytest.mark.parametrize("blade", ["1.5 touched off left", "1.5 touched off middle", "1.5 touched off right"])
@pytest.mark.parametrize("stock", list(STOCK))
def test_the_contours_clean_the_bottom_to_the_middle(groove, blade, stock):
    """Each side's contour runs on along the bottom past the groove's
    middle - the blade's own middle there - so the two of them clean all of
    it between them."""
    op = _op(GROOVES[groove], BLADES[blade], STOCK[stock])
    lines = generate_groove_roughing_gcode(groove_cut_of(op))
    tool = _blade_of(op)
    middle = (GROOVES[groove]["right_flank"]["z_start"] + GROOVES[groove]["left_flank"]["z_start"]) / 2
    ends = {}
    section = None
    z = None
    for line in lines:
        # the Z a line leaves out is the one before it
        found = re.search(r"Z(-?[\d.]+)", line.split("(")[0])
        z = float(found.group(1)) if found else z
        if "Finish Contour Z+" in line:
            section = "right"
        elif "Finish Contour Z-" in line:
            section = "left"
        elif section and line.startswith(("G1", "G2", "G3")):
            ends[section] = z - tool["control"] * tool["width"] / 2      # the blade's middle
    assert ends["right"] <= middle + 1e-6
    assert ends["left"] >= middle - 1e-6


@pytest.mark.parametrize("stock", list(STOCK))
def test_the_blade_starts_the_clearance_out_from_the_start_diameter(stock):
    """The start diameter is the pulley's outside with its radial stock to
    leave on it; the blade starts, and backs off to, the clearance out from
    that - on the diameter, twice the radial values."""
    op = _op(GROOVES["filleted"], BLADES["1.5 touched off middle"], STOCK[stock], clearance=1.0)
    radial = op["stock_to_leave"]["radial"] if op["stock_to_leave_enabled"] else 0.0
    first = next(move for move in _moves(generate_groove_roughing_gcode(groove_cut_of(op))))

    assert first[0] == pytest.approx(GROOVES["filleted"]["right_flank"]["x_start"] + 2 * radial + 2 * 1.0)
