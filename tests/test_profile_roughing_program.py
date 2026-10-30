"""Profile Roughing in a program: the rest roughing added for what one leaves,
the program's G-code built against a snapshot of the Tool Library, and the
planning worker that does both away from the GUI thread."""

import os
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QCoreApplication, QEventLoop, QTimer

from teachinlathe.conversational.gcode import build_ngc_from_program
from teachinlathe.conversational.gcode.gcode_builder import ToolsNotReady
from teachinlathe.conversational.gcode.operations.profiling.operation_input import profile_cut, with_stock
from teachinlathe.conversational.gcode.operations.profile_roughing import (
    profile_roughing_preview,
)
from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase
from teachinlathe.conversational.logic.plan_worker import BackgroundPlanner
from teachinlathe.conversational.model.data_types import Operation, ProfileRoughing
from teachinlathe.conversational.model.factories import make_default_operation, make_new_program
from teachinlathe.tooling.model.data_types import InsertSpec, SpindleDirection, ToolHolder, TurningTool
from teachinlathe.tooling.model.tool_snapshot import ToolSnapshot

CCMT_95 = TurningTool(cutting_tool_id=1, insert=InsertSpec("ccmt", "06", "02"),
                      orientation=2, front_angle=95, back_angle=5,
                      spindle_direction=SpindleDirection.M4)
VBMT_NEUTRAL = TurningTool(cutting_tool_id=3, insert=InsertSpec("vbmt", "16", "04"),
                           orientation=6, front_angle=72.5, back_angle=72.5,
                           spindle_direction=SpindleDirection.M4)
TOOLS = ToolSnapshot(holders={1: ToolHolder(tool_holder_id=1, cutting_tool_id=1),
                              3: ToolHolder(tool_holder_id=3, cutting_tool_id=3)},
                     tools={1: CCMT_95, 3: VBMT_NEUTRAL})


def _point(kind, x, z):
    keys = ("x_start", "z_start") if kind == "startPoint" else ("x_end", "z_end")
    return {"type": kind, keys[0]: x, keys[1]: z, "blend": {"type": "none"}}


#: A peak at Z-24 and a neck behind it the 95° tool cannot go down into.
NECK = [_point("startPoint", 30, 0)] + [_point("lineTo", x, z) for x, z in (
    (30, -11), (54, -24), (26, -35), (38, -45), (70, -45), (70, -50))]


@pytest.fixture
def use_case(tmp_path):
    return ConversationalUseCase(programs_dir=str(tmp_path), ini=SimpleNamespace(), tools=TOOLS)


@pytest.fixture
def program(tmp_path, use_case):
    prog = make_new_program(str(tmp_path))
    prog.operations = [Operation.from_dict({**make_default_operation(op["type"]).to_dict(), **op})
                       for op in (
        {"type": "defineProfile", "order": 1, "profile_id": 1, "profile_type": "od",
         "profile_primitives": NECK},
        {"type": "profileRoughing", "order": 2,
         "speeds_and_feeds": {"direction": "M4", "mode": "rpm", "rpm_value": 1000, "feed_rate": 0.1},
         "cutting_parameters": {"doc": 1.0, "retract": 0.5},
         "profiling_parameters": {"profile_id": 1, "x_start": 74.0, "z_start": 1.0},
         "profile_roughing_strategy": {"profiling_type": "od", "pass_type": "axial"},
         "stock_to_leave": {"radial": 0.1, "axial": 0.05}},
    )]
    assert use_case.use_tool(prog, 1, 1)
    return prog


def build(program, tmp_path, tools=TOOLS):
    with open(build_ngc_from_program(program, tools, output_dir=str(tmp_path / "ngc"))) as f:
        return f.read()


def section(ngc, number):
    """The G-code of operation #``number``."""
    marker = f"(---#{number:02d} "
    start = ngc.index(marker)
    end = ngc.find("(---#", start + len(marker))
    return ngc[start:end if end >= 0 else len(ngc)]


# ── the rest roughing ───────────────────────────────────────────────────────

def test_rest_roughing_comes_right_after_as_a_linked_copy_with_no_tool(program, use_case):
    index = use_case.add_rest_roughing(program, 1)

    assert index == 2
    rest = program.operations[2]
    assert isinstance(rest, ProfileRoughing) and rest.restMaterial
    assert rest.toolRef is None
    assert not program.operations[1].restMaterial
    assert rest.profilingParameters.profile_id == 1


def test_only_a_profile_roughing_gets_a_rest_roughing(program, use_case):
    with pytest.raises(ValueError):
        use_case.add_rest_roughing(program, 0)


def test_program_gcode_rests_with_the_second_tool(program, use_case, tmp_path):
    rest_index = use_case.add_rest_roughing(program, 1)
    use_case.use_tool(program, rest_index, 3)
    ngc = build(program, tmp_path)

    first, rest = section(ngc, 2), section(ngc, 3)
    assert "ERROR" not in ngc
    assert "( Planned for CCMT" in first and "1 region left for another tool" in first
    assert "( Planned for VBMT" in rest
    assert "M6 T1 ( Turning CCMT" in first
    assert "M6 T3 ( Turning VBMT" in rest
    assert 0 < rest.count("G1 ") < first.count("G1 ")


def test_no_gcode_while_the_rest_tool_is_still_to_be_chosen(program, use_case, tmp_path):
    use_case.add_rest_roughing(program, 1)
    with pytest.raises(ToolsNotReady) as refused:
        build(program, tmp_path)

    assert refused.value.problems == ["Operation #3 OD Profile Roughing (P1) · Rest: no tool chosen"]
    assert not (tmp_path / "ngc").exists()


def test_program_gcode_checks_tools_in_the_snapshot_it_is_given(program, tmp_path):
    assert "( Planned for CCMT" in build(program, tmp_path)
    # T1 holds another tool now: not the one the roughing was planned with
    other = ToolSnapshot(holders=TOOLS.holders, tools={1: VBMT_NEUTRAL, 3: VBMT_NEUTRAL})
    with pytest.raises(ToolsNotReady):
        build(program, tmp_path, other)


def test_snapshot_keeps_what_each_holder_has():
    holders = [SimpleNamespace(tool_holder_id=1), SimpleNamespace(tool_holder_id=2)]
    repository = SimpleNamespace(holders=holders, tool_in={1: CCMT_95}.get)
    snapshot = ToolSnapshot.of(repository)

    assert snapshot.tool_in(1) is CCMT_95
    assert snapshot.tool_in(2) is None
    assert snapshot.find_holder(2) is holders[1]
    assert snapshot.find_holder(7) is None


# ── the planning worker ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def planner():
    app = QCoreApplication.instance() or QCoreApplication([])
    worker = BackgroundPlanner()
    yield worker
    worker.stop()
    del app


def answers(planner, count, timeout_ms=60000):
    """The next ``count`` answers of ``planner``: {request id: (ok, result)}."""
    got = {}
    loop = QEventLoop()

    def on_finished(request_id, ok, result):
        got[request_id] = (ok, result)
        if len(got) >= count:
            loop.quit()

    planner.finished.connect(on_finished)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    planner.finished.disconnect(on_finished)
    return got


def _payload(program):
    """The Profile Roughing as its preview is asked for: profile and tool
    resolved, and what the worker works its stock out from."""
    return profile_cut(program, 1, program.operations[1], TOOLS), program, 1, TOOLS


def test_worker_previews_what_the_gui_would(planner, program):
    payload = _payload(program)
    request = planner.submit("preview", "profile_roughing_preview", *payload)

    ok, result = answers(planner, 1)[request]
    assert ok
    assert result == profile_roughing_preview(with_stock(*payload))


def test_worker_keeps_only_the_last_of_the_requests_waiting(planner, program):
    payload = _payload(program)
    first = planner.submit("preview", "profile_roughing_preview", *payload)
    dropped = planner.submit("preview", "profile_roughing_preview", *payload)
    last = planner.submit("preview", "profile_roughing_preview", *payload)

    got = answers(planner, 2)
    assert set(got) == {first, last}
    assert dropped not in got


def test_worker_reports_a_failed_job_and_goes_on(planner, program):
    failed = planner.submit("preview", "no_such_job")
    assert answers(planner, 1)[failed][0] is False

    request = planner.submit("preview", "profile_roughing_preview", *_payload(program))
    assert answers(planner, 1)[request][0] is True


def test_worker_generates_the_gcode_the_gui_would(planner, program, tmp_path):
    request = planner.submit("gcode", "generate_gcode", program, str(tmp_path / "worker"),
                             "program.json", TOOLS)
    ok, path = answers(planner, 1)[request]
    here = build_ngc_from_program(program, TOOLS, output_dir=str(tmp_path / "here"),
                                  source_json="program.json")

    def lines(name):
        with open(name) as f:
            return [line for line in f if "Creation Date" not in line]

    assert ok and os.path.dirname(path) == str(tmp_path / "worker")
    assert lines(path) == lines(here)


def test_worker_that_dies_answers_what_it_had_and_is_started_again(planner, program):
    request = planner.submit("preview", "profile_roughing_preview", *_payload(program))
    planner._process.kill()

    assert answers(planner, 1)[request] == (False, "the planning worker stopped")
    again = planner.submit("preview", "profile_roughing_preview", *_payload(program))
    assert answers(planner, 1)[again][0] is True
