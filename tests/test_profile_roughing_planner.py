"""Tool-aware Profile Roughing (conversational/gcode/operations/profiling/planner.py):
what the insert can reach, the moves that reach it, what is left for another tool,
and the G-code that has the machine make the same moves."""

import math
import re

import pytest

from teachinlathe.conversational.model.data_types import ProfilingType
from shapely.geometry import LineString, Point, Polygon

from teachinlathe.conversational.gcode.operations.profile_roughing import (
    generate_profile_roughing_gcode,
    plan_profile_roughing,
)
from teachinlathe.conversational.gcode.operations.profile_roughing import (
    profile_roughing_preview,
)
from teachinlathe.conversational.gcode.operations.profiling.shapes import MIN_AREA, TOLERANCE, path_points, sweep
from teachinlathe.conversational.gcode.operations.profiling.tool_shape import insert_tool_shape
from teachinlathe.conversational.gcode.operations.profiling.operation_input import resolve_profile
from teachinlathe.tooling.model.data_types import (
    BoringTool,
    InsertSpec,
    SolidBody,
    SpindleDirection,
    TurningTool,
)

from gcode_reading import gcode_moves, profile_cut_of

M4 = SpindleDirection.M4

#: A 95° CCMT: back angle 5° - goes down no slope steeper than that.
CCMT_95 = TurningTool(cutting_tool_id=1, insert=InsertSpec("ccmt", "06", "02"),
                      orientation=2, front_angle=95, back_angle=5, spindle_direction=M4)
#: A 35° VBMT held neutral: 72.5° either side - plunges into pockets.
VBMT_NEUTRAL = TurningTool(cutting_tool_id=3, insert=InsertSpec("vbmt", "16", "04"),
                           orientation=6, front_angle=72.5, back_angle=72.5, spindle_direction=M4)
#: A boring tool held for ID, 95° and 5° back.
CCMT_BORING = TurningTool(cutting_tool_id=41, insert=InsertSpec("ccmt", "06", "02"),
                          orientation=3, front_angle=95, back_angle=5, spindle_direction=M4)
#: A solid boring bar whose tip points the wrong way for these profiles.
BORING_BAR = BoringTool(cutting_tool_id=4, insert=InsertSpec("ccmt", "06", "02"),
                        solid_body=SolidBody(tip_angle=50, diameter=5, max_radial_undercut=3),
                        orientation=6, front_angle=5, back_angle=5, spindle_direction=M4)

STOCK_X, STOCK_Z = 0.1, 0.05


def _start(x, z=0.0):
    return {"type": "startPoint", "x_start": x, "z_start": z, "blend": {"type": "none"}}


def _line(x, z, blend=None):
    return {"type": "lineTo", "x_end": x, "z_end": z, "blend": blend or {"type": "none"}}


def pocket():
    """Ø20, down 45° into a Ø14 pocket, a vertical wall back to Ø20, a shoulder."""
    return [_start(20), _line(20, -5), _line(14, -8), _line(14, -15), _line(20, -15),
            _line(20, -25), _line(30, -25), _line(30, -30)]


def neck():
    """A peak at Z-24 and, behind it, a neck down to Ø26 - the 'Undercut ccmt' shape."""
    return [_start(30), _line(30, -11), _line(54, -24), _line(26, -35), _line(38, -45),
            _line(70, -45), _line(70, -50)]


def din509():
    """Ø10 into a shoulder with a DIN 509 relief."""
    relief = {"type": "undercut_din509", "undercut_radius": 1.0, "undercut_depth": 1.0,
              "undercut_length": 6.0}
    return [_start(10), _line(10, -10, relief), _line(20, -10), _line(20, -20)]


def bore():
    """ID: Ø30, out to a Ø36 recess, back to Ø30, then down to Ø20."""
    return [_start(30), _line(30, -5), _line(36, -8), _line(36, -14), _line(30, -14),
            _line(30, -22), _line(20, -22), _line(20, -28)]


def steps():
    """Two diameters and a shoulder: nothing any 95° tool cannot reach."""
    return [_start(20), _line(20, -10), _line(30, -10), _line(30, -20)]


PROFILES = {"pocket": (pocket, "od", 34.0), "neck": (neck, "od", 74.0), "steps": (steps, "od", 34.0),
            "din509": (din509, "od", 24.0), "bore": (bore, "id", 16.0)}


def operation(profile, tool=CCMT_95, pass_type="axial", doc=1.0, **extra):
    build, kind, x_start = PROFILES[profile]
    op = {"_resolved_profile": {"profile_type": kind, "profile_primitives": build()},
          "profiling_parameters": {"x_start": x_start, "z_start": 1.0},
          "cutting_parameters": {"doc": doc, "retract": 0.5},
          "stock_to_leave": {"radial": STOCK_X, "axial": STOCK_Z},
          "profile_roughing_strategy": {"profiling_type": kind, "pass_type": pass_type},
          **extra}
    if tool is not None:
        op["_resolved_cutting_tool"] = tool
    return profile_cut_of(op)


def finished_part(op):
    """The finished part, in (z, r): under the profile for OD, over it for ID."""
    path = resolve_profile(op)
    points = path_points(path)
    far = -50.0 if op.profile.profile_type is ProfilingType.OD else 100.0
    return Polygon(points + [(points[-1][0] - 50.0, points[-1][1]), (points[-1][0] - 50.0, far),
                             (points[0][0], far)]).buffer(0)


def inside(regions, z, r):
    return any(Polygon(region).contains(Point(z, r)) for region in regions)


# ── the insert ──────────────────────────────────────────────────────────────

def test_insert_is_hung_from_the_nose_tangent_points():
    shape = insert_tool_shape(CCMT_95)

    assert min(r for _z, r in shape.outline) == pytest.approx(0.0, abs=1e-3)
    assert min(z for z, _r in shape.outline) == pytest.approx(0.0, abs=1e-3)
    assert shape.nose_radius == pytest.approx(0.2)


def test_insert_edges_are_carried_on_as_the_holder():
    envelope = Polygon(insert_tool_shape(CCMT_95).envelope)

    def at(degrees, distance=50.0):
        a = math.radians(degrees)
        return Point(distance * math.cos(a), distance * math.sin(a))

    # far beyond the 6 mm insert, between its edges: the holder's room
    assert envelope.contains(at(20))
    assert envelope.contains(at(60))
    # under the back edge (5°, less the clearance) and before the front edge: clear
    assert not envelope.contains(at(0))
    assert not envelope.contains(at(100))


def test_only_turning_tools_have_an_insert_shape():
    assert insert_tool_shape(BORING_BAR) is not None
    assert insert_tool_shape(None) is None


# ── what the plan does not do ───────────────────────────────────────────────

CASES = [("pocket", CCMT_95, "axial"), ("pocket", VBMT_NEUTRAL, "axial"),
         ("pocket", CCMT_95, "radial"), ("pocket", CCMT_95, "diagonal_exterior"),
         ("neck", CCMT_95, "axial"), ("neck", VBMT_NEUTRAL, "axial"),
         ("din509", CCMT_95, "axial"), ("bore", CCMT_BORING, "axial"),
         ("pocket", None, "axial")]


@pytest.mark.parametrize("profile,tool,pass_type", CASES)
def test_no_move_touches_the_finished_part_nor_cuts_into_the_stock_to_leave(profile, tool, pass_type):
    op = operation(profile, tool, pass_type)
    plan = plan_profile_roughing(op)
    assert not plan.error
    assert plan.moves
    part = finished_part(op)
    # the insert itself - its edges' extension stands for the holder, which
    # may pass over the part's shoulders
    outline = plan.tool.outline
    touching = [m for m in plan.moves
                if sweep(outline, (m.z0, m.r0), (m.z1, m.r1)).intersection(
                    part.buffer(-TOLERANCE)).area > MIN_AREA]
    into_stock = [m for m in plan.moves if m.feed
                  and sweep(outline, (m.z0, m.r0), (m.z1, m.r1)).intersection(
                      part.buffer(min(STOCK_X, STOCK_Z) - 0.01)).area > MIN_AREA]
    assert touching == []
    assert into_stock == []


@pytest.mark.parametrize("profile,tool,pass_type", CASES)
def test_passes_never_go_over_the_same_ground_twice(profile, tool, pass_type):
    plan = plan_profile_roughing(operation(profile, tool, pass_type))
    runs = {}
    for m in plan.moves:
        if m.feed and not m.contour and abs(m.r1 - m.r0) < 1e-6 and abs(m.z1 - m.z0) > TOLERANCE:
            runs.setdefault(round(m.r0, 4), []).append(sorted((m.z0, m.z1)))
    for level, spans in runs.items():
        spans.sort()
        for (_a0, a1), (b0, _b1) in zip(spans, spans[1:]):
            assert b0 >= a1 - TOLERANCE, f"two passes over Z{b0:.3f}..{a1:.3f} at R{level}"


def test_tool_does_not_go_down_slopes_steeper_than_its_back_angle():
    plan = plan_profile_roughing(operation("neck", CCMT_95))
    for m in plan.moves:
        if m.feed and m.z1 < m.z0 - TOLERANCE and m.r1 < m.r0:
            descent = math.degrees(math.atan2(m.r0 - m.r1, m.z0 - m.z1))
            assert descent <= CCMT_95.back_angle + 0.1


# ── what is left for another tool ───────────────────────────────────────────

def test_neck_behind_a_peak_is_left_to_another_tool():
    plan = plan_profile_roughing(operation("neck", CCMT_95))

    assert plan.warnings == ["1 region left for another tool"]
    # the whole neck, its bottom and the back of the peak
    assert inside(plan.residual, -35.0, 14.0)
    assert inside(plan.residual, -30.0, 22.0)
    assert inside(plan.residual, -42.0, 19.0)


def test_steep_pocket_is_left_by_a_back_angle_too_small_for_it():
    plan = plan_profile_roughing(operation("pocket", CCMT_95))

    assert inside(plan.residual, -11.0, 7.5)
    assert inside(plan.residual, -6.0, 9.5)
    # over it, nothing goes deeper than the back angle lets it from its edge
    # at Z-5: Ø20 less 10 mm at 5°
    assert all(min(m.r0, m.r1) >= 10.0 - 10.0 * math.tan(math.radians(5.0)) for m in plan.moves
               if m.feed and -15.0 < min(m.z0, m.z1) and max(m.z0, m.z1) < -5.0)


def test_insert_that_fits_is_plunged_into_the_pocket():
    plan = plan_profile_roughing(operation("pocket", VBMT_NEUTRAL))

    assert any(m.pocket for m in plan.moves)
    # down to its Ø14 floor and its stock to leave
    assert min(min(m.r0, m.r1) for m in plan.moves if m.feed) == pytest.approx(7.0 + STOCK_X)
    assert not inside(plan.residual, -11.0, 7.5)


def test_din509_relief_floor_is_left_by_a_5_degree_back_angle():
    plan = plan_profile_roughing(operation("din509", CCMT_95))

    assert len(plan.residual) == 1
    z_min, r_min, z_max, r_max = Polygon(plan.residual[0]).bounds
    # the relief's floor, under Ø10 between its taper and the shoulder
    assert -10.0 <= z_min and z_max <= -4.0
    assert 4.0 <= r_min and r_max <= 5.0 + STOCK_X + TOLERANCE


def test_id_is_planned_mirrored_and_comes_back_on_the_right_side():
    plan = plan_profile_roughing(operation("bore", CCMT_BORING))

    assert not plan.error
    # every move inside the bore: under Ø36, over the Ø16 start less the retract
    assert all(7.5 - TOLERANCE <= r <= 18.0 for m in plan.moves for r in (m.r0, m.r1))
    # the recess behind the Ø30 entry, as the tool comes in through it
    assert inside(plan.residual, -12.0, 17.5)


def test_tool_held_the_wrong_way_round_is_an_error():
    plan = plan_profile_roughing(operation("bore", BORING_BAR))

    assert "check the tool's orientation" in plan.error
    assert plan.moves == []


def test_without_a_tool_only_what_any_tool_reaches_is_roughed():
    plan = plan_profile_roughing(operation("pocket", None))

    assert plan.warnings[0].startswith("No turning tool chosen")
    assert not any(m.pocket for m in plan.moves)
    assert inside(plan.residual, -11.0, 7.5)


# ── rest material ───────────────────────────────────────────────────────────

def rest_operation(tool):
    source = operation("neck", CCMT_95)
    # its own start and stock are the source's: these must not count
    rest = operation("neck", tool, doc=0.5, rest_material=True,
                     _resolved_previous_roughing=[source],
                     profiling_parameters={"x_start": 999.0, "z_start": 50.0},
                     stock_to_leave={"radial": 2.0, "axial": 2.0})
    return source, rest


def area(regions):
    return sum(Polygon(region).area for region in regions)


def test_rest_roughing_cuts_only_what_the_roughing_above_left():
    source, rest = rest_operation(VBMT_NEUTRAL)
    before = plan_profile_roughing(source)
    plan = plan_profile_roughing(rest)

    assert not plan.error
    assert area(plan.residual) < area(before.residual) / 4
    # within a depth of cut and a retract of it
    left = [Polygon(region).buffer(1.0) for region in before.residual]
    cutting = [m for m in plan.moves if m.feed]
    assert cutting
    assert all(any(region.contains(Point(m.z1, m.r1)) for region in left) for m in cutting)
    # and to the source's stock to leave
    part = finished_part(source)
    assert all(sweep(plan.tool.outline, (m.z0, m.r0), (m.z1, m.r1)).intersection(
        part.buffer(STOCK_Z - 0.01)).area <= MIN_AREA for m in cutting)


def test_rest_roughing_without_its_tool_shows_what_is_left():
    source, rest = rest_operation(None)
    plan = plan_profile_roughing(rest)

    assert plan.moves == []
    assert plan.warnings[0].startswith("Choose the tool to cut what is left")
    assert area(plan.residual) == pytest.approx(area(plan_profile_roughing(source).residual), rel=0.05)


def test_rest_roughing_without_a_roughing_above_is_an_error():
    rest = operation("neck", VBMT_NEUTRAL, rest_material=True, _resolved_previous_roughing=[])

    assert plan_profile_roughing(rest).error


# ── the preview ─────────────────────────────────────────────────────────────

def test_preview_offers_a_rest_roughing_for_what_is_left():
    preview = profile_roughing_preview(operation("neck", CCMT_95))

    assert preview.rest_offered is True
    assert preview.warnings == ("1 region left for another tool",)
    assert preview.feeds and preview.rapids and preview.residual
    assert not profile_roughing_preview(operation("steps", CCMT_95)).rest_offered


# ── the G-code ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("profile,tool,pass_type", CASES)
def test_gcode_makes_the_planned_moves(profile, tool, pass_type):
    op = operation(profile, tool, pass_type)
    plan = plan_profile_roughing(op)
    feeds, _rapids = gcode_moves(generate_profile_roughing_gcode(op))
    planned = [LineString([(m.z0, m.r0), (m.z1, m.r1)]) for m in plan.moves if m.feed]

    assert feeds
    for f in feeds:
        for t in (0.0, 0.5, 1.0):
            z = f["z0"] + t * (f["z1"] - f["z0"])
            r = (f["x0"] + t * (f["x1"] - f["x0"])) / 2.0
            assert min(line.distance(Point(z, r)) for line in planned) < 0.005


def test_contour_corners_are_arcs_in_the_gcode():
    lines = generate_profile_roughing_gcode(operation("neck", CCMT_95))

    assert any(re.match(r"\s*G[23]\b", line) for line in lines)


@pytest.mark.parametrize("profile,tool,pass_type", CASES + [("neck", None, "axial")])
def test_gcode_comments_are_never_nested(profile, tool, pass_type):
    for line in generate_profile_roughing_gcode(operation(profile, tool, pass_type)):
        depth = 0
        for char in line:
            depth += {"(": 1, ")": -1}.get(char, 0)
            assert 0 <= depth <= 1, line


def test_gcode_stops_for_inspection_after_each_pass():
    op = operation("neck", CCMT_95, m1_parameters={"include_m1": True, "inspect_position": "G28",
                                                    "stop_spindle": False})
    plan = plan_profile_roughing(op)
    lines = generate_profile_roughing_gcode(op)

    assert sum(line == "M1 P1 (Pause and move to G28)" for line in lines) == sum(m.pass_end for m in plan.moves)


def test_rest_roughing_without_its_tool_has_no_moves_in_the_gcode():
    _source, rest = rest_operation(None)
    feeds, rapids = gcode_moves(generate_profile_roughing_gcode(rest))

    assert feeds == [] and rapids == []
