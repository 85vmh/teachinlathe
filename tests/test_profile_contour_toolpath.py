"""Profile Contour, planned as Profile Roughing plans the contour it finishes
with (profile_contour.py on profiling/machining.py): the tool's, compensated
for its nose, bridged over what it cannot enter, from Z Start to the profile's
end - and the G-code and the preview that plan. On the profiles the roughing's
toolpath is checked on (test_profile_roughing_toolpath.py), with and without
stock to leave."""

import math
import re

import pytest
from shapely.geometry import LineString, MultiLineString, Point

from teachinlathe.conversational.gcode.operations import profile_contour
from teachinlathe.conversational.gcode.operations.profile_contour import (
    generate_profile_contour_gcode,
    plan_profile_contour,
)
from teachinlathe.conversational.gcode.operations.profile_contour_preview import (
    build_profile_contour_preview,
)
from gcode_reading import gcode_moves
from teachinlathe.conversational.gcode.operations.profiling import machining
from teachinlathe.conversational.gcode.operations.profiling.machining import MIN_AREA, sweep

from test_profile_roughing_toolpath import PROFILES

CASES = [(p, stock) for p in PROFILES for stock in (False, True)]


def operation(profile, stock=False, tool=True):
    build, kind, cutting_tool, x_start, z_start, doc, retract, radial, axial = PROFILES[profile]
    op = {"_resolved_profile": {"profile_type": kind, "profile_primitives": build()},
          "profiling_parameters": {"x_start": x_start, "z_start": z_start},
          "cutting_parameters": {"doc": doc, "retract": retract},
          "stock_to_leave": {"radial": radial, "axial": axial},
          "stock_to_leave_enabled": stock,
          "profile_contour_strategy": {"profiling_type": kind}}
    if tool:
        op["_resolved_cutting_tool"] = cutting_tool.to_json()
    return op


_PLANNED = {}


def planned(profile, stock=False):
    """(operation, plan, planner) for a case, planned once - the planner
    kept for the stock to leave and the contour chain it knows."""
    key = (profile, stock)
    if key not in _PLANNED:
        op = operation(profile, stock)
        caught = {}
        original = machining._Planner.plan_contour_only

        def plan(self):
            caught["planner"] = self
            return original(self)

        machining._Planner.plan_contour_only = plan
        try:
            profile_contour._PLANS.clear()
            result = plan_profile_contour(op)
        finally:
            machining._Planner.plan_contour_only = original
        _PLANNED[key] = (op, result, caught["planner"])
    return _PLANNED[key]


def _mirrored(planner, z, r):
    return (z, planner.sign * r)


def _cuts(plan):
    return [m for m in plan.moves if m.feed]


# ── the contour ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("profile,stock", CASES)
def test_the_contour_is_planned_with_the_tool(profile, stock):
    _op, plan, _planner = planned(profile, stock)

    assert not plan.error
    assert plan.tool.known
    assert _cuts(plan)
    assert all(m.contour for m in _cuts(plan))


@pytest.mark.parametrize("profile,stock", CASES)
def test_no_move_takes_the_insert_into_the_part_or_its_stock_to_leave(profile, stock):
    _op, plan, planner = planned(profile, stock)

    into = [m for m in plan.moves
            if machining._intersection(
                sweep(planner.envelope, _mirrored(planner, m.z0, m.r0), _mirrored(planner, m.z1, m.r1)),
                planner.part_allow_inside).area >= MIN_AREA]

    assert into == []


@pytest.mark.parametrize("profile,stock", CASES)
def test_the_contour_runs_from_z_start_to_the_profiles_end(profile, stock):
    op, plan, planner = planned(profile, stock)
    cuts = _cuts(plan)

    assert cuts[0].z0 == pytest.approx(op["profiling_parameters"]["z_start"] + planner.retract)
    assert cuts[-1].z1 < cuts[0].z0
    assert cuts[-1].z1 == pytest.approx(min(m.z1 for m in cuts))


@pytest.mark.parametrize("profile", ["id_steps", "od_steps"])
@pytest.mark.parametrize("stock", [False, True])
def test_the_nose_touches_the_profile_offset_by_the_stock_to_leave(profile, stock):
    """Where the tool reaches all of the profile, the nose - as the canvas
    draws it - runs along the profile offset by the stock to leave: the
    control point compensated, not run along the profile itself."""
    _op, plan, planner = planned(profile, stock)
    allowance = LineString([_mirrored(planner, z, r) for z, r in plan.allowance])

    for m in _cuts(plan):
        if m.drawn is None or math.hypot(m.z1 - m.z0, m.r1 - m.r0) < 0.05:
            continue
        z0, r0, z1, r1 = m.drawn
        if min(z0, z1) > planner.profile[0][0] + planner.setup.stock_z + 0.01:
            continue                    # in front of the face: the way in along Z
        mid = Point(*_mirrored(planner, (z0 + z1) / 2, (r0 + r1) / 2))
        assert allowance.distance(mid) < 0.02, m


def test_on_a_slope_the_control_point_is_off_the_profile():
    """The nose compensated for: along the 45° chamfer the point the machine
    is programmed to is not on the profile, as it was before the contour was
    planned with the tool."""
    _op, plan, planner = planned("od_steps")
    profile = LineString(planner.profile)
    on_chamfer = [m for m in _cuts(plan)
                  if abs(abs(m.z1 - m.z0) - abs(m.r1 - m.r0)) < 1e-6 and abs(m.z1 - m.z0) > 1.0]

    assert on_chamfer
    for m in on_chamfer:
        middle = Point((m.z0 + m.z1) / 2, (m.r0 + m.r1) / 2)
        assert profile.distance(middle) > 0.05


def test_the_contour_is_bridged_over_a_groove_the_tool_cannot_enter():
    """Under the shoulder of id_groove the DCMT does not fit: the contour
    stays out of it - the insert never in the part, as above - and does not
    go to the groove's floor under the shoulder."""
    _op, plan, _planner = planned("id_groove")

    under_shoulder = [m for m in _cuts(plan) if -20.0 < m.z1 < -19.0 and 2 * m.r1 > 33.0]
    assert under_shoulder == []


def test_stock_to_leave_off_leaves_none():
    _op, plan_off, _p = planned("od_steps", False)
    _op, plan_on, _p = planned("od_steps", True)

    # with stock to leave the contour stands off the profile further
    assert min(m.r1 for m in _cuts(plan_on)) > min(m.r1 for m in _cuts(plan_off))


def test_without_a_tool_the_contour_says_so():
    profile_contour._PLANS.clear()
    plan = plan_profile_contour(operation("od_steps", tool=False))

    assert not plan.error
    assert not plan.tool.known
    assert any("No turning tool" in w for w in plan.warnings)


def test_without_a_profile_it_is_an_error():
    op = operation("od_steps")
    op["_resolved_profile"] = {"profile_type": "od", "profile_primitives": []}
    profile_contour._PLANS.clear()

    lines = generate_profile_contour_gcode(op)

    assert any("ERROR: Profile Contour" in line for line in lines)


# ── the G-code and the preview: the plan ────────────────────────────────────

@pytest.mark.parametrize("profile,stock", CASES)
def test_gcode_makes_the_planned_moves(profile, stock):
    op, plan, _planner = planned(profile, stock)
    lines = generate_profile_contour_gcode(op)
    # read from where the moves begin: after the comment naming the tool
    feeds, rapids = gcode_moves(lines, start="( Planned for")
    moves = MultiLineString([[(m.z0, m.r0), (m.z1, m.r1)] for m in plan.moves
                             if (m.z0, m.r0) != (m.z1, m.r1)])

    assert any(f"Planned for {plan.tool.label}" in line for line in lines)
    assert feeds
    for move in feeds + rapids:
        for t in (0.0, 0.5, 1.0):
            z = move["z0"] + t * (move["z1"] - move["z0"])
            r = (move["x0"] + t * (move["x1"] - move["x0"])) / 2.0
            assert moves.distance(Point(z, r)) < 0.005, move


@pytest.mark.parametrize("profile,stock", CASES)
def test_gcode_arcs_are_arcs(profile, stock):
    """No run of chords barely bent written as an arc of tens of mm - the
    profiles here have no radius over 2 mm, nor the nose."""
    op, _plan, _planner = planned(profile, stock)

    for line in generate_profile_contour_gcode(op):
        m = re.search(r"\bG[23]\b.*I(-?[\d.]+) K(-?[\d.]+)", line)
        if m:
            assert math.hypot(float(m.group(1)), float(m.group(2))) < 5.0, line


@pytest.mark.parametrize("profile,stock", CASES)
def test_preview_draws_the_planned_contour(profile, stock):
    op, plan, _planner = planned(profile, stock)
    preview = build_profile_contour_preview(op)

    assert preview["error"] == ""
    assert len(preview["feeds"]) == len(_cuts(plan))
    assert preview["offset"]
    assert preview["rapids"] == []
