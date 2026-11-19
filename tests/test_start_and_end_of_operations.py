"""Where an operation places the tool before it starts and after it is done,
how it retracts off its cuts, and what is - and is not - left for the contour
or another tool: Turning, Profile Roughing / Contour, Turning-Finish, G33
Threading, as the program's G-code has them."""

from types import SimpleNamespace

import pytest

from teachinlathe.conversational.gcode import build_ngc_from_program
from teachinlathe.conversational.gcode.config import RETRACT_OF_AP, retract_of
from teachinlathe.conversational.gcode.operations.g33_threading import generate_g33_threading_gcode
from teachinlathe.conversational.gcode.operations.profile_roughing import plan_profile_roughing
from teachinlathe.conversational.gcode.operations.profiling.operation_input import (
    common_config,
    profile_cut,
    roughing_start_point,
    turning_start_point,
)
from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase
from teachinlathe.conversational.model.data_types import Operation
from teachinlathe.conversational.model.factories import make_default_operation, make_new_program
from teachinlathe.tooling.model.data_types import InsertSpec, SpindleDirection, ToolHolder, TurningTool
from teachinlathe.tooling.model.tool_snapshot import ToolSnapshot

from gcode_reading import profile_cut_of

CCMT_95 = TurningTool(cutting_tool_id=1, insert=InsertSpec("ccmt", "09", "04"), orientation=2,
                      front_angle=95, back_angle=5, spindle_direction=SpindleDirection.M3)
VBMT_93 = TurningTool(cutting_tool_id=2, insert=InsertSpec("vbmt", "11", "02"), orientation=2,
                      front_angle=93, back_angle=52, spindle_direction=SpindleDirection.M3)
DCMT_97 = TurningTool(cutting_tool_id=3, insert=InsertSpec("dcmt", "11", "04"), orientation=2,
                      front_angle=97, back_angle=28, spindle_direction=SpindleDirection.M3)
TOOLS = ToolSnapshot(holders={1: ToolHolder(tool_holder_id=1, cutting_tool_id=1),
                              2: ToolHolder(tool_holder_id=2, cutting_tool_id=2)},
                     tools={1: CCMT_95, 2: VBMT_93})


def _point(kind, x, z, blend=None):
    keys = ("x_start", "z_start") if kind == "startPoint" else ("x_end", "z_end")
    return {"type": kind, keys[0]: x, keys[1]: z, "blend": blend or {"type": "none"}}


#: Ø20 to Z-20, a shoulder out to Ø40, Ø40 to Z-30.
STEP = [_point("startPoint", 20, 0), _point("lineTo", 20, -20), _point("lineTo", 40, -20),
        _point("lineTo", 40, -30)]

ROUGHING = {"type": "profileRoughing",
            "speeds_and_feeds": {"direction": "M3", "mode": "rpm", "rpm_value": 1000, "feed_rate": 0.2},
            "cutting_parameters": {"doc": 1.5, "retract": 2.0},
            "profiling_parameters": {"profile_id": 1, "x_start": 44.0, "z_start": 1.0},
            "profile_roughing_strategy": {"profiling_type": "od", "pass_type": "axial"},
            "stock_to_leave": {"radial": 0.3, "axial": 0.1}}

TURNING = {"type": "turning",
           "speeds_and_feeds": {"direction": "M3", "mode": "rpm", "rpm_value": 1000, "feed_rate": 0.2},
           "cutting_parameters": {"ap": 1.5, "tool_clearance": 3.0},
           "geometry_parameters": {"x_start": 50.0, "z_start": 0.0, "x_end": 10.0, "z_end": -25.0,
                                   "start_blend": {"type": "none"}, "shoulder_blend": {"type": "none"}},
           "stock_to_leave": {"radial": 1.0, "axial": 0.5},
           "profile_roughing_strategy": {"profiling_type": "od", "pass_type": "axial"}}


def _operation(data, order):
    return Operation.from_dict({**make_default_operation(data["type"]).to_dict(), **data, "order": order})


def _program(tmp_path, operations, tools_of, after_last="do_nothing"):
    """A program of ``operations`` (dicts), each cutting one with the holder
    ``tools_of`` gives it by index."""
    use_case = ConversationalUseCase(programs_dir=str(tmp_path), ini=SimpleNamespace(), tools=TOOLS)
    program = make_new_program(str(tmp_path))
    program.operations = [_operation(op, k + 1) for k, op in enumerate(operations)]
    program.header.after_last_operation = after_last
    for index, holder in tools_of.items():
        assert use_case.use_tool(program, index, holder)
    return program


def _build(program, tmp_path):
    with open(build_ngc_from_program(program, TOOLS, output_dir=str(tmp_path / "ngc"))) as f:
        return f.read()


def _section(ngc, number):
    marker = f"(---#{number:02d} "
    start = ngc.index(marker)
    end = ngc.find("(---#", start + len(marker))
    return ngc[start:end if end >= 0 else ngc.index("M5 ")]


def _motion(section):
    return [line for line in section.splitlines() if line.startswith(("G0", "G1", "G2", "G3"))]


def _profile():
    return {"type": "defineProfile", "profile_id": 1, "profile_type": "od", "profile_primitives": STEP}


# ── back to the start point when nothing follows with the same tool ─────────

@pytest.mark.parametrize("after_last", ["do_nothing", "g28"])
def test_the_last_roughing_goes_back_to_its_start_x_then_z_before_m5(tmp_path, after_last):
    """X out first, then Z - with the spindle on, before M5 - whatever the
    header does after the last operation."""
    ngc = _build(_program(tmp_path, [_profile(), ROUGHING], {1: 1}, after_last), tmp_path)
    motion = _motion(_section(ngc, 2))

    # the start point: P1 plus the tool clearance - X44 + 2 x 2, Z1 + 2
    assert motion[-2:] == ["G0 X48.000", "G0 Z3.000"]
    assert ngc.index("back to the start point") < ngc.index("M5 ")


def test_a_roughing_another_one_follows_with_the_same_tool_stays_where_it_ends(tmp_path):
    ngc = _build(_program(tmp_path, [_profile(), ROUGHING, ROUGHING], {1: 1, 2: 1}), tmp_path)

    assert "back to the start point" not in _section(ngc, 2)
    assert "back to the start point" in _section(ngc, 3)


def test_a_roughing_another_tool_follows_goes_back_to_its_start(tmp_path):
    ngc = _build(_program(tmp_path, [_profile(), ROUGHING, ROUGHING], {1: 1, 2: 2}), tmp_path)

    assert "back to the start point" in _section(ngc, 2)


def test_a_turning_finish_toward_z_minus_goes_back_along_z_first(tmp_path):
    """From the shoulder's largest diameter, nothing in front of it: Z, then X."""
    finish = {"type": "turningFinish", "parent_order": 1, "p1_x": 50.0, "p1_z": 0.0,
              "finishing_direction": "towards_z_minus",
              "speeds_and_feeds": {"direction": "M3", "mode": "rpm", "rpm_value": 1000, "feed_rate": 0.1}}
    ngc = _build(_program(tmp_path, [TURNING, finish], {0: 1, 1: 2}), tmp_path)
    motion = _motion(_section(ngc, 2))

    assert motion[-3] == "G1 X50.000"
    assert motion[-2:] == ["G0 Z0.500", "G0 X51.000"]


# ── Turning: P1 plus the tool clearance ─────────────────────────────────────

def test_turning_starts_and_ends_at_p1_plus_the_tool_clearance(tmp_path):
    program = _program(tmp_path, [TURNING], {0: 1})
    op = program.operations[0]
    plan = plan_profile_roughing(profile_cut(program, 0, op, TOOLS))

    assert turning_start_point(op) == (56.0, 3.0)
    start = plan.moves[0]
    assert (2 * start.r0, start.z0) == (56.0, 3.0)
    # the passes from P1Z plus the clearance, the material from P1X: none
    # through the air over it
    passes = [m for m in plan.moves if m.feed and not m.contour and m.r0 == m.r1 and m.z1 < m.z0]
    assert passes and all(m.z0 == pytest.approx(3.0) for m in passes)
    assert max(2 * m.r0 for m in passes) < 50.0
    assert not plan.residual


# ── Profile Roughing: P1 plus the tool clearance, off each cut by a part of Ap ─

def test_profile_roughing_starts_at_p1_plus_the_tool_clearance_and_retracts_by_its_part_of_ap(tmp_path):
    program = _program(tmp_path, [_profile(), ROUGHING], {1: 1})
    op = program.operations[1]
    cut = profile_cut(program, 1, op, TOOLS)
    config = common_config(cut, op.profileRoughingStrategy.profiling_type)

    assert config["start_point"] == (48.0, 3.0)
    assert config["z_start"] == 1.0
    assert config["retract"] == pytest.approx(1.5 * RETRACT_OF_AP["profileRoughing"])
    assert retract_of("turning", 3.0) == pytest.approx(3.0 * RETRACT_OF_AP["turning"])


def test_an_id_roughing_starts_the_clearance_toward_the_axis():
    assert roughing_start_point(10.0, 2.0, 0.3, is_id=True) == (pytest.approx(9.4), pytest.approx(2.3))
    assert roughing_start_point(10.0, 2.0, 0.3, is_id=False) == (pytest.approx(10.6), pytest.approx(2.3))


# ── what is left ────────────────────────────────────────────────────────────

def test_a_chamfer_at_the_start_the_tool_fits_into_is_not_left():
    """The nose on the chamfer lies lower than what it touches: the contour
    starts where its edge crosses the start's diameter, not over the top of
    the chamfer, leaving it for another tool."""
    chamfer = {"type": "chamfer", "chamfer_width": 1.0}
    cut = profile_cut_of({
        "_resolved_profile": {"profile_type": "od", "profile_primitives": [
            _point("startPoint", 13, 0, chamfer), _point("lineTo", 13, -12), _point("lineTo", 30, -12),
            _point("lineTo", 30, -20)]},
        "_resolved_cutting_tool": VBMT_93,
        "profiling_parameters": {"x_start": 34.0, "z_start": 1.0},
        "cutting_parameters": {"doc": 1.5, "retract": 0.5},
        "stock_to_leave": {"radial": 0.5, "axial": 0.2},
        "profile_roughing_strategy": {"profiling_type": "od", "pass_type": "axial"}})
    plan = plan_profile_roughing(cut)

    assert not plan.error
    assert plan.residual == []


def test_what_the_passes_leave_against_the_end_is_not_a_pocket():
    """A 97° tool's leaning edge leaves a sliver against the end of the
    profile, over its last diameter: the bar's face behind the profile, not a
    pocket to go back for."""
    cut = profile_cut_of({
        "_resolved_profile": {"profile_type": "od", "profile_primitives": [
            _point("startPoint", 10, 0), _point("lineTo", 10, -40), _point("lineTo", 20, -45),
            _point("lineTo", 20, -50)]},
        "_resolved_cutting_tool": DCMT_97,
        "profiling_parameters": {"x_start": 30.0, "z_start": 0.0},
        "cutting_parameters": {"doc": 1.0, "retract": 2.0},
        "stock_to_leave": {"radial": 0.5, "axial": 0.2},
        "profile_roughing_strategy": {"profiling_type": "od", "pass_type": "axial"}})
    plan = plan_profile_roughing(cut)

    assert not any(m.pocket and min(m.z0, m.z1) < -46.0 for m in plan.moves)
    assert plan.residual == []


# ── G33: a left-hand thread is left at Z End ────────────────────────────────

def _thread(location, z_start, z_end):
    data = make_default_operation("g33Threading").to_dict()
    data.update({"location": location, "z_start": z_start, "z_end": z_end, "pitch": 1.5,
                 "major_diameter": 20.0 if location == "OD" else 22.0,
                 "minor_diameter": 18.2 if location == "OD" else 20.2,
                 "initial_doc": 0.2, "retract": 1.0})
    return Operation.from_dict(data)


@pytest.mark.parametrize("location,safe_x", [("OD", "X21.000"), ("ID", "X19.200")])
def test_a_left_hand_thread_is_left_at_z_end(location, safe_x):
    """Z Start behind Z End: out to the safe diameter after the last pass,
    then to Z End - not back along the thread to Z Start, in the part."""
    lines = generate_g33_threading_gcode(_thread(location, -25.0, 1.0))

    assert lines[-2:] == [f"G0 {safe_x}", "G0 Z1.000"]


def test_a_right_hand_thread_goes_back_to_z_start():
    lines = generate_g33_threading_gcode(_thread("OD", 1.0, -25.0))

    assert lines[-2] == "G0 X21.000"
    assert lines[-1].startswith("G0 Z0.5")
