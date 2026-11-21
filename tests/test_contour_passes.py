"""A Profile Contour and a Turning-Finish in several passes: the stock each
pass leaves, the way back to P1 and the Pause to Inspect after every pass (the
G-code), the initial stock they inherit from the operation they follow and keep
to it until it is edited (ConversationalUseCase.complete_operations), and the
Profile Contour Profile Roughing adds for what it leaves (add_profile_contour).

What is pinned down here:

* Pass k of N leaves the initial stock times (N - k) / N, on X and on Z apart:
  the last pass on the profile. The count is a whole number from 1 to
  MAX_PASSES_COUNT.
* After every pass - the last too - the contour goes back to P1 along Z first,
  then X, and makes its M1 there.
* A contour inherits the stock to leave of the nearest Profile Roughing above
  it on its profile that is not on rest material; a Turning-Finish, of the
  Turning it finishes. An edit of the initial stock makes it the operator's.
* Add Profile Contour puts it after the roughing and its rest roughings, with
  the roughing's profile, tool and side, finishing toward Z+ after radial
  passes and toward Z- after any other; a roughing has a contour once one
  takes its stock.
"""

import re
from types import SimpleNamespace

import pytest

from teachinlathe.conversational.gcode.operations.profile_contour import generate_profile_contour_gcode
from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase
from teachinlathe.conversational.model.data_types import (
    MAX_PASSES_COUNT, FinishingDirection, ProfileContour, ProfilingType, passes_count,
)
from teachinlathe.conversational.model.factories import make_new_program
from teachinlathe.conversational.model.program_commands import add_profile_contour

from gcode_reading import profile_cut_of
from test_profile_roughing_toolpath import PROFILES
from test_start_and_end_of_operations import ROUGHING, TOOLS, TURNING, _operation, _profile

STOCK = (0.6, 0.3)


# ── the passes ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("value, count", [
    (None, 1), ("", 1), (0, 1), (-3, 1), (1, 1), (2.7, 2), ("4", 4),
    (MAX_PASSES_COUNT, MAX_PASSES_COUNT), (MAX_PASSES_COUNT + 5, MAX_PASSES_COUNT),
])
def test_a_passes_count_is_a_whole_number_from_one_to_the_most(value, count):
    assert passes_count(value) == count


def _contour_gcode(passes, include_m1=True, kind="od_steps"):
    build, profiling_type, tool, x_start, z_start, *_ = PROFILES[kind]
    cut = profile_cut_of({
        "_resolved_profile": {"profile_type": profiling_type, "profile_primitives": build()},
        "_resolved_cutting_tool": tool,
        "profiling_parameters": {"x_start": x_start, "z_start": z_start},
        "initial_stock_to_leave": {"radial": STOCK[0], "axial": STOCK[1]},
        "passes_count": passes,
        "m1_parameters": {"include_m1": include_m1, "inspect_position": "g28"},
        "profile_contour_strategy": {"profiling_type": profiling_type}})
    return generate_profile_contour_gcode(cut), (x_start, z_start)


@pytest.mark.parametrize("passes", [1, 2, 3, 5])
def test_each_pass_leaves_its_share_of_the_initial_stock(passes):
    lines, _p1 = _contour_gcode(passes)
    left = [(float(r), float(a)) for r, a in
            re.findall(r"StockToLeave\[radial=([-\d.]+) axial=([-\d.]+)\]", "\n".join(lines))]

    assert left == [pytest.approx((STOCK[0] * (passes - k) / passes, STOCK[1] * (passes - k) / passes), abs=1e-3)
                    for k in range(1, passes + 1)]
    assert left[-1] == pytest.approx((0.0, 0.0))
    if passes > 1:
        assert sum("Pass " in line and f" of {passes}:" in line for line in lines) == passes


@pytest.mark.parametrize("kind", ["od_steps", "id_steps"])
def test_after_every_pass_it_goes_back_to_p1_along_z_then_x_and_stops_there(kind):
    lines, (x_start, z_start) = _contour_gcode(3, kind=kind)
    motion_or_stop = [line.strip() for line in lines if line.strip().startswith(("G0", "G1", "G2", "G3", "M1"))]
    stops = [i for i, line in enumerate(motion_or_stop) if line.startswith("M1")]

    assert len(stops) == 3
    for i in stops:
        # the rapids after the last cut; no X move when the pass ends on P1's X (id_steps ends at Ø10)
        start = i
        while motion_or_stop[start - 1].startswith("G0"):
            start -= 1
        home = motion_or_stop[start:i]
        assert home[0] == f"G0 Z{z_start:.3f}"
        assert home[1:] in ([], [f"G0 X{x_start:.3f}"])
        if not home[1:]:
            assert motion_or_stop[start - 1].startswith("G1 X") and motion_or_stop[start - 1].endswith(f"X{x_start:.3f}")


def test_without_a_pause_to_inspect_it_still_goes_back_after_every_pass():
    lines, (x_start, z_start) = _contour_gcode(2, include_m1=False)
    motion = [line.strip() for line in lines if line.strip().startswith(("G0", "G1", "G2", "G3", "M1"))]

    assert not any(line.startswith("M1") for line in motion)
    assert sum(1 for a, b in zip(motion, motion[1:])
               if (a, b) == (f"G0 Z{z_start:.3f}", f"G0 X{x_start:.3f}")) == 2


# ── the initial stock, inherited ────────────────────────────────────────

def _use_case(tmp_path):
    return ConversationalUseCase(programs_dir=str(tmp_path), ini=SimpleNamespace(), tools=TOOLS)


def _program(tmp_path, operations):
    program = make_new_program(str(tmp_path))
    program.operations = [_operation(op, k + 1) for k, op in enumerate(operations)]
    return program


def _roughing(radial, axial, rest=False, pass_type="axial", profile_id=1):
    return {**ROUGHING, "rest_material": rest, "stock_to_leave": {"radial": radial, "axial": axial},
            "profiling_parameters": {**ROUGHING["profiling_parameters"], "profile_id": profile_id},
            "profile_roughing_strategy": {"profiling_type": "od", "pass_type": pass_type}}


def _contour(profile_id=1, inherited=True, stock=(0.0, 0.0)):
    return {"type": "profileContour", "initial_stock_inherited": inherited,
            "initial_stock_to_leave": {"radial": stock[0], "axial": stock[1]},
            "profiling_parameters": {"profile_id": profile_id, "x_start": 44.0, "z_start": 1.0}}


def _stock_of(op):
    return (op.initialStockToLeave.stockToLeaveX, op.initialStockToLeave.stockToLeaveZ)


def test_a_contour_inherits_the_stock_of_the_roughing_above_it_on_its_profile(tmp_path):
    use_case = _use_case(tmp_path)
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2), _roughing(0.9, 0.9, profile_id=2),
                                  _contour()])

    assert use_case.complete_operations(program)
    assert _stock_of(program.operations[3]) == (0.4, 0.2)
    assert program.operations[3].stockInherited


def test_a_rest_roughing_is_not_where_a_contour_inherits_from(tmp_path):
    use_case = _use_case(tmp_path)
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2), _roughing(0.7, 0.7, rest=True), _contour()])

    use_case.complete_operations(program)
    assert use_case.inherited_stock_source(program, 3) is program.operations[1]
    assert _stock_of(program.operations[3]) == (0.4, 0.2)


def test_the_inherited_stock_follows_the_roughing(tmp_path):
    use_case = _use_case(tmp_path)
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2), _contour()])
    use_case.complete_operations(program)

    use_case.update_operation(program, "profileRoughing", 1, {"stock_to_leave": {"radial": 0.5, "axial": 0.25}})
    use_case.complete_operations(program)
    assert _stock_of(program.operations[2]) == (0.5, 0.25)


def test_an_edited_initial_stock_is_the_operators_and_stays(tmp_path):
    use_case = _use_case(tmp_path)
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2), _contour()])
    use_case.complete_operations(program)

    use_case.update_operation(program, "profileContour", 2, {"initial_stock_to_leave": {"radial": 1.0, "axial": 0.0}})
    assert not program.operations[2].stockInherited
    use_case.update_operation(program, "profileRoughing", 1, {"stock_to_leave": {"radial": 0.5, "axial": 0.25}})
    assert not use_case.complete_operations(program)
    assert _stock_of(program.operations[2]) == (1.0, 0.0)


def test_editing_the_passes_count_keeps_the_stock_inherited(tmp_path):
    use_case = _use_case(tmp_path)
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2), _contour()])
    use_case.complete_operations(program)

    use_case.update_operation(program, "profileContour", 2, {"passes_count": MAX_PASSES_COUNT + 3})
    assert program.operations[2].passesCount == MAX_PASSES_COUNT
    assert program.operations[2].stockInherited


def test_a_turning_finish_inherits_the_stock_of_the_turning_it_finishes(tmp_path):
    use_case = _use_case(tmp_path)
    finish = {"type": "turningFinish", "parent_order": 1, "p1_x": 50.0, "p1_z": 0.0,
              "initial_stock_inherited": True}
    program = _program(tmp_path, [TURNING, finish])

    use_case.complete_operations(program)
    assert _stock_of(program.operations[1]) == (1.0, 0.5)


# ── Add Profile Contour ─────────────────────────────────────────────────

@pytest.mark.parametrize("pass_type, direction", [
    ("axial", FinishingDirection.TOWARDS_Z_MINUS),
    ("radial", FinishingDirection.TOWARDS_Z_PLUS),
    ("diagonal_interior", FinishingDirection.TOWARDS_Z_MINUS),
])
def test_add_profile_contour_takes_the_roughings_profile_tool_and_stock(tmp_path, pass_type, direction):
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2, pass_type=pass_type)])
    roughing = program.operations[1]
    roughing.toolRef = "tool-1"

    index = add_profile_contour(program, 1)
    contour = program.operations[index]

    assert index == 2 and isinstance(contour, ProfileContour)
    assert contour.profilingParameters.to_dict() == roughing.profilingParameters.to_dict()
    assert contour.profilingParameters is not roughing.profilingParameters
    assert contour.toolRef == "tool-1"
    assert contour.profileContourStrategy.profiling_type is ProfilingType.OD
    assert contour.profileContourStrategy.finishing_direction is direction
    assert _stock_of(contour) == (0.4, 0.2) and contour.stockInherited
    assert [op.order for op in program.operations] == [1, 2, 3]


def test_add_profile_contour_goes_after_the_roughings_rest_roughings(tmp_path):
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2), _roughing(0.4, 0.2, rest=True),
                                  _roughing(0.4, 0.2, rest=True), _roughing(0.4, 0.2, profile_id=2)])

    assert add_profile_contour(program, 1) == 4


def test_add_profile_contour_is_only_for_a_profile_roughing(tmp_path):
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2)])

    with pytest.raises(TypeError):
        add_profile_contour(program, 0)
    with pytest.raises(TypeError):
        add_profile_contour(program, 5)


def test_a_roughing_has_a_contour_once_one_takes_its_stock(tmp_path):
    use_case = _use_case(tmp_path)
    program = _program(tmp_path, [_profile(), _roughing(0.4, 0.2), _roughing(0.4, 0.2, rest=True),
                                  _roughing(0.4, 0.2, profile_id=2)])
    assert not any(use_case.has_profile_contour(program, i) for i in (1, 2, 3))

    add_profile_contour(program, 1)

    # the roughing, and its rest roughing, whose stock the contour takes off too
    assert use_case.has_profile_contour(program, 1)
    assert use_case.has_profile_contour(program, 2)
    # not the roughing of another profile, nor what is not a roughing
    assert not use_case.has_profile_contour(program, 4)
    assert not use_case.has_profile_contour(program, 0)
