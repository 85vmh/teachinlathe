"""The toolpath Profile Roughing makes, as it has been checked on the screen and
in the backplot (conversational/gcode/operations/profiling/planner.py): where
the passes go and how far apart, how the tool gets to them and away, the
contour, what the canvas draws of it - on the two ID profiles it was worked out
on, with the boring tool it was worked out with, in all four strategies; what
holds for any profile, on two OD ones too."""

import math
import re
import time

import pytest
from shapely.geometry import LineString, MultiLineString, Point, Polygon, box

from teachinlathe.conversational.gcode.operations import profile_roughing
from teachinlathe.conversational.gcode.operations.profile_roughing import (
    generate_profile_roughing_gcode,
    plan_profile_roughing,
)
from teachinlathe.conversational.gcode.operations.profile_roughing import (
    profile_roughing_preview,
)
from teachinlathe.conversational.gcode.operations.profiling import plan as plan_module
from teachinlathe.conversational.gcode.operations.profiling import shapes
from teachinlathe.conversational.gcode.operations.profiling.planner import _Planner
from teachinlathe.conversational.gcode.operations.profiling.shapes import MIN_AREA, sweep
from teachinlathe.tooling.model.data_types import (
    BoringTool,
    InsertSpec,
    SolidBody,
    SpindleDirection,
    TurningTool,
)

from gcode_reading import gcode_moves, profile_cut_of

M3 = SpindleDirection.M3
M4 = SpindleDirection.M4

#: T6 as the machine has it: a boring bar with a DCMT 11T304, 93° and 32° back.
DCMT_BORING = BoringTool(cutting_tool_id=5, insert=InsertSpec("dcmt", "11", "04"),
                         solid_body=SolidBody(tip_angle=50, diameter=10, max_radial_undercut=6),
                         orientation=3, front_angle=93, back_angle=32, spindle_direction=M3)
#: A 95° CCMT for OD: back angle 5°.
CCMT_95 = TurningTool(cutting_tool_id=1, insert=InsertSpec("ccmt", "06", "02"),
                      orientation=2, front_angle=95, back_angle=5, spindle_direction=M4)

PASS_TYPES = ["axial", "radial", "diagonal_interior", "diagonal_exterior"]
DIAGONAL = ["diagonal_interior", "diagonal_exterior"]


def _start(x, z=0.0, blend=None):
    return {"type": "startPoint", "x_start": x, "z_start": z, "blend": blend or {"type": "none"}}


def _line(x, z, blend=None):
    return {"type": "lineTo", "x_end": x, "z_end": z, "input": "xz", "blend": blend or {"type": "none"}}


def _fillet(radius):
    return {"type": "fillet", "fillet_radius": radius}


def id_steps():
    """'ID Profiling Axial': Ø32 at the face, rounded in, a 25° slope down to a
    wall at Z-15, Ø15 behind it, Ø10 at the end."""
    return [_start(32, blend=_fillet(1.0)), _line(32, -7, _fillet(2.0)),
            {"type": "lineTo", "x_end": 32, "z_end": -15, "angle": 25, "input": "az", "blend": {"type": "none"}},
            _line(15, -15, _fillet(2.0)), _line(15, -20), _line(10, -20)]


def id_groove():
    """'ID Profiling Test 2': Ø40 at the face, a slope to a Ø32 shoulder, a
    Ø36 groove behind it - under the shoulder - then Ø25, Ø20 at the end."""
    return [_start(40, blend=_fillet(1.0)), _line(40, -10, _fillet(2.0)), _line(32, -15),
            _line(32, -20, _fillet(1.0)), _line(36, -20, _fillet(0.5)), _line(36, -25, _fillet(0.5)),
            _line(25, -25, _fillet(1.0)), _line(25, -30), _line(20, -30)]


def od_steps():
    """OD: Ø20, a shoulder out to Ø30, a 45° chamfer up to Ø40."""
    return [_start(20), _line(20, -10, _fillet(1.0)), _line(30, -10), _line(30, -18), _line(40, -23),
            _line(40, -30)]


def od_pocket():
    """OD: Ø20, down 45° into a Ø14 pocket, a wall back to Ø20, a shoulder."""
    return [_start(20), _line(20, -5), _line(14, -8), _line(14, -15), _line(20, -15),
            _line(20, -25), _line(30, -25), _line(30, -30)]


#: name: (profile, kind, tool, X Start, Z Start, Ap, retract, stock radial, stock axial)
PROFILES = {
    "id_steps": (id_steps, "id", DCMT_BORING, 10.0, 2.0, 1.0, 0.3, 0.2, 0.5),
    "id_groove": (id_groove, "id", DCMT_BORING, 20.0, 2.0, 1.0, 0.5, 0.5, 0.2),
    "od_steps": (od_steps, "od", CCMT_95, 44.0, 1.0, 1.5, 0.5, 0.3, 0.1),
    "od_pocket": (od_pocket, "od", CCMT_95, 34.0, 1.0, 1.0, 0.5, 0.1, 0.05),
}

ID_CASES = [(p, t) for p in ("id_steps", "id_groove") for t in PASS_TYPES]
OD_CASES = [(p, t) for p in ("od_steps", "od_pocket") for t in ("axial", "radial")]
ALL_CASES = ID_CASES + OD_CASES


def operation(profile, pass_type):
    build, kind, tool, x_start, z_start, doc, retract, radial, axial = PROFILES[profile]
    return profile_cut_of({"_resolved_profile": {"profile_type": kind, "profile_primitives": build()},
            "_resolved_cutting_tool": tool,
            "profiling_parameters": {"x_start": x_start, "z_start": z_start},
            "cutting_parameters": {"doc": doc, "retract": retract},
            "stock_to_leave": {"radial": radial, "axial": axial},
            "profile_roughing_strategy": {"profiling_type": kind, "pass_type": pass_type}})


_PLANNED = {}


def planned(profile, pass_type):
    """(operation, plan, planner, seconds) for a case, planned once - the
    planner kept for what it knows: the insert, the stock to leave, the
    contour."""
    key = (profile, pass_type)
    if key not in _PLANNED:
        op = operation(profile, pass_type)
        caught = {}
        original = _Planner.plan

        def plan(self):
            caught["planner"] = self
            return original(self)

        _Planner.plan = plan
        try:
            # planned here, not taken from the cache - which keeps it after,
            # for the G-code and the preview made from the same plan
            profile_roughing._PLANS.forget(profile_roughing.roughing_plan_key(op))
            started = time.perf_counter()
            result = plan_profile_roughing(op)
            seconds = time.perf_counter() - started
        finally:
            _Planner.plan = original
        _PLANNED[key] = (op, result, caught["planner"], seconds)
    return _PLANNED[key]


def _mirrored(planner, z, r):
    """A move's point in the planner's frame, where ID is planned as OD."""
    return (z, planner.sign * r)


def _slanted(m):
    return abs(m.z1 - m.z0) > 1e-6 and abs(m.r1 - m.r0) > 1e-6


def _angle():
    """The diagonal passes' angle from the Z axis, in radians - the constant
    they are planned with (45° as these were checked on the screen)."""
    return math.radians(plan_module.DIAGONAL_ANGLE)


def _at_diagonal_angle(m):
    return (abs(m.z1 - m.z0) > 1e-6
            and abs(abs(m.r1 - m.r0) / abs(m.z1 - m.z0) - math.tan(_angle())) < 1e-6)


def _level(m):
    """Which of the parallel diagonal lines a move starts on: how far along
    the normal to them, (sin, cos) of their angle, in the planning frame
    (r is -X/2 for ID)."""
    return m.z0 * math.sin(_angle()) - m.r0 * math.cos(_angle())


def _diagonal_cuts(plan):
    """The diagonal cuts, in the order they are made."""
    return [m for m in plan.moves
            if m.feed and not m.contour and _slanted(m) and _at_diagonal_angle(m) and abs(m.z1 - m.z0) > 0.05]


def _final_contour(plan):
    last = max(m.pass_no for m in plan.moves if m.contour)
    return [m for m in plan.moves if m.contour and m.pass_no == last]


# ── it is made, and in good time ────────────────────────────────────────────

@pytest.mark.parametrize("profile,pass_type", ALL_CASES)
def test_the_plan_is_made_in_good_time(profile, pass_type):
    _op, plan, _planner, seconds = planned(profile, pass_type)

    assert not plan.error
    assert plan.moves
    # a walk that stood still - crawling along the profile a hair at a time -
    # took minutes
    assert seconds < 20.0


# ── the stock to leave ──────────────────────────────────────────────────────

@pytest.mark.parametrize("profile,pass_type", ALL_CASES)
def test_no_move_takes_the_insert_into_the_stock_to_leave(profile, pass_type):
    """Neither a cut nor a rapid - a rapid through the stock to leave would hit
    material on the machine."""
    _op, plan, planner, _s = planned(profile, pass_type)

    into = [m for m in plan.moves
            if shapes._intersection(
                sweep(planner.envelope, _mirrored(planner, m.z0, m.r0), _mirrored(planner, m.z1, m.r1)),
                planner.part_allow_inside).area >= MIN_AREA]

    assert into == []


@pytest.mark.parametrize("profile,pass_type", ALL_CASES)
def test_no_line_the_canvas_draws_goes_into_the_stock_to_leave(profile, pass_type):
    """The cuts drawn where the nose leaves its edge, not at the control point,
    which lies outside the nose where a cut ends on a slope or an arc."""
    _op, plan, planner, _s = planned(profile, pass_type)
    inside = planner.part_allow.buffer(-0.01)

    deep = []
    for m in plan.moves:
        if not m.feed:
            continue
        z0, r0, z1, r1 = m.drawn or (m.z0, m.r0, m.z1, m.r1)
        line = LineString([_mirrored(planner, z0, r0), _mirrored(planner, z1, r1)])
        if line.length > 1e-9 and not shapes._intersection(line, inside).is_empty:
            deep.append(m)

    assert deep == []


@pytest.mark.parametrize("profile,pass_type", ALL_CASES)
def test_the_contour_is_drawn_parallel_to_where_the_machine_moves(profile, pass_type):
    """Each stretch of the contour drawn parallel to its own - a wall the tool
    runs straight along drawn straight - and the stretches joined."""
    _op, plan, _planner, _s = planned(profile, pass_type)

    for m in plan.moves:
        if not (m.contour and m.drawn) or math.hypot(m.z1 - m.z0, m.r1 - m.r0) < 0.05:
            continue
        d = m.drawn
        moved = math.atan2(m.r1 - m.r0, m.z1 - m.z0)
        drawn = math.atan2(d[3] - d[1], d[2] - d[0])
        assert abs(math.remainder(drawn - moved, 2 * math.pi)) < 1e-6


# ── the 45° passes ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("profile", ["id_steps", "id_groove"])
@pytest.mark.parametrize("pass_type", DIAGONAL)
def test_45_degree_passes_are_one_depth_of_cut_apart(profile, pass_type):
    """Square to the passes, from one to the next - along X Start, along the
    profile and into an island alike; a step back is the walk turning into an
    island behind a shoulder."""
    op, plan, _planner, _s = planned(profile, pass_type)
    doc = op.op.cuttingParameters.doc
    cuts = _diagonal_cuts(plan)
    gaps = [(_level(a) - _level(b), a, b) for a, b in zip(cuts, cuts[1:])]

    assert len(gaps) > 10
    for gap, a, b in gaps:
        # or the same line again past the profile in its way: the two cut
        # apart, part between them
        same_line_on = abs(gap) < 1e-6 and max(a.z1, a.z0) > max(b.z1, b.z0) and min(a.z0, a.z1) > max(b.z0, b.z1) - 1e-6
        assert abs(gap - doc) < 1e-3 or gap < 0 or same_line_on, (gap, a, b)


@pytest.mark.parametrize("profile", ["id_steps", "id_groove"])
@pytest.mark.parametrize("pass_type,toward_z,toward_x", [("diagonal_interior", -1, -1),
                                                        ("diagonal_exterior", 1, 1)])
def test_45_degree_passes_cut_the_way_their_arrow_points(profile, pass_type, toward_z, toward_x):
    """↖ interior: toward Z- and the smaller diameter; ↘ exterior: toward Z+
    and the larger one."""
    _op, plan, _planner, _s = planned(profile, pass_type)

    for m in _diagonal_cuts(plan):
        assert math.copysign(1, m.z1 - m.z0) == toward_z
        assert math.copysign(1, m.r1 - m.r0) == toward_x


@pytest.mark.parametrize("pass_type,toward", [("diagonal_interior", "interior"),
                                             ("diagonal_exterior", "exterior")])
def test_45_degree_gcode_says_the_way_the_passes_cut(pass_type, toward):
    lines = generate_profile_roughing_gcode(operation("id_steps", pass_type))

    assert any(f"{plan_module.DIAGONAL_ANGLE:g}° Passes toward {toward}" in line for line in lines)


@pytest.mark.parametrize("pass_type", DIAGONAL)
def test_45_degree_passes_go_on_past_a_groove_they_cannot_get_out_of(pass_type):
    """In the groove under the shoulder the tool cannot come back in front of a
    pass's start: the walk goes on all the same, to the profile's end."""
    _op, plan, _planner, _s = planned("id_groove", pass_type)
    cuts = _diagonal_cuts(plan)

    # passes in the groove (Z-20..-25, beyond Ø32) and behind it (past Z-25)
    assert any(min(m.z0, m.z1) < -20.0 and 2 * max(m.r0, m.r1) > 32.0 for m in cuts)
    assert any(max(m.z0, m.z1) < -25.0 for m in cuts)


def test_45_degree_passes_cover_a_groove_the_same_either_way():
    interior = _diagonal_cuts(planned("id_groove", "diagonal_interior")[1])
    exterior = _diagonal_cuts(planned("id_groove", "diagonal_exterior")[1])

    assert len(interior) == len(exterior)


# ── how the tool gets about ─────────────────────────────────────────────────

@pytest.mark.parametrize("profile,pass_type", ID_CASES)
def test_id_rapids_move_one_axis_at_a_time(profile, pass_type):
    """For ID along X first, then along Z, never both at once - but for the
    way back alongside a 45° pass, a retract off it."""
    _op, plan, _planner, _s = planned(profile, pass_type)

    slanted = [m for m in plan.moves if not m.feed and _slanted(m)]
    if pass_type in DIAGONAL:
        assert all(_at_diagonal_angle(m) for m in slanted)
    else:
        assert slanted == []


@pytest.mark.parametrize("profile,pass_type", ID_CASES)
def test_nothing_goes_deeper_than_the_contour_runs_out_to_z_start(profile, pass_type):
    """In front of the face no pass goes past the diameter the contour runs out
    to Z Start at - behind it the profile stops them."""
    _op, plan, planner, _s = planned(profile, pass_type)
    deepest = -planner._extension_r() * 2           # the planning frame's r is -X/2 for ID

    assert max(2 * max(m.r0, m.r1) for m in plan.moves) <= deepest + 1e-6


@pytest.mark.parametrize("profile,pass_type", ID_CASES)
def test_the_contour_runs_out_to_z_start_along_the_axis(profile, pass_type):
    _op, plan, planner, _s = planned(profile, pass_type)
    chain = planner._contour_chain()

    assert chain[0][0] == pytest.approx(planner.z_start)
    assert chain[0][1] == pytest.approx(chain[1][1])


# ── the contour ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("profile,pass_type", ALL_CASES)
def test_the_last_contour_runs_the_way_the_strategy_has_it(profile, pass_type):
    """After radial and 45° passes from the back to the front, Z- to Z+; after
    axial ones from Z Start to the profile's end."""
    _op, plan, _planner, _s = planned(profile, pass_type)
    contour = _final_contour(plan)
    travel = contour[-1].z1 - contour[0].z0

    if pass_type == "axial":
        assert travel < 0
    else:
        assert travel > 0


@pytest.mark.parametrize("profile,pass_type", [(p, t) for p, t in ALL_CASES if t in ("axial", "radial")])
def test_axial_and_radial_passes_go_on_along_the_profile_to_the_pass_before(profile, pass_type):
    """A pass that ends on the profile does not leave the step to the pass
    before for the contour at the end: it goes on along the profile."""
    _op, plan, _planner, _s = planned(profile, pass_type)
    last = max(m.pass_no for m in plan.moves if m.contour)

    assert any(m.contour and m.pass_no < last for m in plan.moves)


# ── the G-code and the preview: the plan ────────────────────────────────────

@pytest.mark.parametrize("profile,pass_type", ALL_CASES)
def test_gcode_makes_the_planned_moves(profile, pass_type):
    op, plan, _planner, _s = planned(profile, pass_type)
    feeds, rapids = gcode_moves(generate_profile_roughing_gcode(op))
    moves = MultiLineString([[(m.z0, m.r0), (m.z1, m.r1)] for m in plan.moves
                             if (m.z0, m.r0) != (m.z1, m.r1)])

    assert feeds
    for move in feeds + rapids:
        for t in (0.0, 0.5, 1.0):
            z = move["z0"] + t * (move["z1"] - move["z0"])
            r = (move["x0"] + t * (move["x1"] - move["x0"])) / 2.0
            assert moves.distance(Point(z, r)) < 0.005, move


@pytest.mark.parametrize("profile,pass_type", ALL_CASES)
def test_preview_draws_the_planned_moves(profile, pass_type):
    op, plan, _planner, _s = planned(profile, pass_type)
    preview = profile_roughing_preview(op)

    assert len(preview.feeds) == sum(1 for m in plan.moves if m.feed)
    assert preview.error == ""


def test_planning_warns_when_geos_has_to_try_again(caplog):
    """A difference or an intersection GEOS cannot work out is tried again on
    the shapes mended - and said so, not passed over in silence."""
    bow = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])           # crosses itself
    square = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])

    with caplog.at_level("WARNING"):
        result = shapes._intersection(bow, square)

    assert result.area > 0
    assert any("tried again" in r.getMessage() for r in caplog.records)


def test_what_is_left_is_kept_on_the_grid():
    """Cut along the same lines again and again a shape picks up edges a hair
    apart that GEOS cannot tell crossing or not: on the grid they either meet
    or do not."""
    cut = shapes._difference(box(0, 0, 10, 10), box(1.0000000001, 1, 2.0000000004, 2))

    for x, y in cut.exterior.coords:
        assert abs(x / shapes.GRID - round(x / shapes.GRID)) < 1e-6
        assert abs(y / shapes.GRID - round(y / shapes.GRID)) < 1e-6


def test_gcode_names_the_strategy():
    lines = generate_profile_roughing_gcode(operation("id_steps", "radial"))

    assert any(re.search(r"Radial Passes", line) for line in lines)
