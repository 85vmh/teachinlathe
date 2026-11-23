"""A new operation starts with the settings of the last one of its type the
operator edited (model.operation_defaults, ConversationalUseCase.edit_operation),
kept in a file in the machine's config directory (OperationDefaultsStore).

What is pinned down here:

* Any edit in an operation's editor - of a remembered field or not - takes
  all its remembered fields, as the operation has them then: values set
  before the edit too. What is not remembered (geometry, P1, the profile) a
  new operation does not take.
* A Profile Roughing's and a Profile Contour's are kept apart for OD and ID;
  an ID roughing's diagonal passes and their angle are an ID one's.
* Only the editor's edits are remembered, not what complete_operations sets.
* An operation made from another keeps what it takes from it: a duplicate
  all of it; a Profile Contour of a roughing its profile, side and stock, a
  Turning-Finish its Turning's speeds and inspection stop - the rest is the
  last one of their type's.
* The file is read back as written; one that cannot be read is none.
"""

import json
from types import SimpleNamespace

from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase
from teachinlathe.conversational.model.data_types import PassType, ProfilingType
from teachinlathe.conversational.model.factories import make_default_operation, make_new_program
from teachinlathe.conversational.model.operation_defaults import (
    REMEMBERED, defaults_key, remembered_values,
)
from teachinlathe.conversational.store.operation_defaults_store import (
    OPERATION_DEFAULTS_FILE, OperationDefaultsStore,
)


def _use_case(tmp_path):
    """A use case with the defaults file in ``tmp_path``, as its config directory."""
    return ConversationalUseCase(programs_dir=str(tmp_path), ini=SimpleNamespace(config_dir=str(tmp_path)),
                                 tools=[])


def _program(tmp_path):
    return make_new_program(str(tmp_path))


def _with_profile(use_case, program, kind="od"):
    use_case.insert_define_profile(program, kind, len(program.operations))


def _add(use_case, program, op_type):
    index = use_case.insert_operation(program, op_type, len(program.operations))
    return index, program.operations[index]


def _file(tmp_path):
    with open(tmp_path / OPERATION_DEFAULTS_FILE) as fh:
        return json.load(fh)


# ── what is remembered ──────────────────────────────────────────────────

def test_a_new_operation_starts_with_the_last_edited_ones_settings(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    index, _ = _add(use_case, program, "facing")
    use_case.edit_operation(program, "facing", index, {"speeds_and_feeds": {"mode": "css", "css_value": 180,
                                                                            "css_max_speed": 2500}})
    use_case.edit_operation(program, "facing", index, {"cutting_parameters": {"doc": 1.2, "retract": 2.0},
                                                       "m1_parameters": {"include_m1": True,
                                                                         "inspect_position": "G30"}})

    _, new = _add(use_case, program, "facing")

    assert new.speedsAndFeeds.mode.value == "css"
    assert new.speedsAndFeeds.css_value == 180 and new.speedsAndFeeds.css_max_speed == 2500
    assert new.cuttingParameters.doc == 1.2 and new.cuttingParameters.retract == 2.0
    assert new.m1Parameters.include_m1 is True and new.m1Parameters.inspect_position.value == "G30"


def test_any_edit_takes_all_the_operations_settings_even_those_set_before(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    _with_profile(use_case, program)
    index, roughing = _add(use_case, program, "profileRoughing")
    # as an operation saved before anything was remembered
    roughing.cuttingParameters.doc = 1.0
    roughing.m1Parameters.include_m1 = True
    roughing.stockToLeave.stockToLeaveX = 1.5

    # an edit of what is not remembered
    use_case.edit_operation(program, "profileRoughing", index, {"profiling_parameters": {"x_start": 30.0}})

    _, new = _add(use_case, program, "profileRoughing")
    assert new.cuttingParameters.doc == 1.0
    assert new.m1Parameters.include_m1 is True
    assert new.stockToLeave.stockToLeaveX == 1.5
    # what is not remembered is the factory's
    assert new.profilingParameters.xStart == 0.0


def test_what_is_not_remembered_is_not_taken(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    index, _ = _add(use_case, program, "drilling")
    use_case.edit_operation(program, "drilling", index, {"drilling_parameters": {"z_end": -15, "peck_depth": 5,
                                                                                 "dwell_time": 2}})

    _, new = _add(use_case, program, "drilling")
    assert new.drillingParameters.peckDepth == 5
    assert new.drillingParameters.zEnd == 0.0
    assert new.drillingParameters.dwellTime == make_default_operation("drilling").drillingParameters.dwellTime


def test_the_last_operation_edited_wins(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    first, _ = _add(use_case, program, "facing")
    second, _ = _add(use_case, program, "facing")
    use_case.edit_operation(program, "facing", first, {"cutting_parameters": {"doc": 2.0}})
    use_case.edit_operation(program, "facing", second, {"speeds_and_feeds": {"feed_rate": 0.3}})

    _, new = _add(use_case, program, "facing")
    # the second, edited last, had the first's AP when it was made
    assert new.cuttingParameters.doc == 0.5
    assert new.speedsAndFeeds.feed_rate == 0.3


def test_a_tap_takes_only_the_spindle_speed(tmp_path):
    assert remembered_values("tapping", make_default_operation("tapping").to_dict()) == {
        "speeds_and_feeds": {"mode": "rpm", "rpm_value": 500}}


def test_the_spindle_direction_is_not_remembered(tmp_path):
    for op_type in REMEMBERED:
        values = remembered_values(op_type, make_default_operation(op_type).to_dict())
        assert "direction" not in values.get("speeds_and_feeds", {})


def test_an_operation_nothing_is_remembered_of_writes_nothing(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    _with_profile(use_case, program)
    use_case.edit_operation(program, "defineProfile", 0, {"profile_type": "od"})
    assert defaults_key("defineProfile") is None
    assert not (tmp_path / OPERATION_DEFAULTS_FILE).exists()


def test_completing_an_operation_is_not_remembered(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    index, _ = _add(use_case, program, "facing")
    use_case.update_operation(program, "facing", index, {"cutting_parameters": {"doc": 3.0}})

    _, new = _add(use_case, program, "facing")
    assert new.cuttingParameters.doc == 0.5


# ── OD and ID apart ─────────────────────────────────────────────────────

def test_od_and_id_roughings_are_remembered_apart(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    _with_profile(use_case, program, "od")
    od, _ = _add(use_case, program, "profileRoughing")
    use_case.edit_operation(program, "profileRoughing", od, {"cutting_parameters": {"doc": 2.0},
                                                             "profile_roughing_strategy": {"pass_type": "radial"}})
    _with_profile(use_case, program, "id")
    id_, roughing = _add(use_case, program, "profileRoughing")
    assert roughing.profileRoughingStrategy.profiling_type is ProfilingType.ID
    # nothing remembered for ID yet: the factory's
    assert roughing.cuttingParameters.doc == 0.5
    use_case.edit_operation(program, "profileRoughing", id_, {
        "profile_roughing_strategy": {"pass_type": "diagonal_interior", "diagonal_angle": 30}})

    _, new_id = _add(use_case, program, "profileRoughing")
    assert new_id.profileRoughingStrategy.pass_type is PassType.DIAGONAL_INTERIOR
    assert new_id.profileRoughingStrategy.diagonal_angle == 30.0
    assert new_id.cuttingParameters.doc == 0.5

    assert set(_file(tmp_path)) == {"profileRoughing.od", "profileRoughing.id"}
    assert _file(tmp_path)["profileRoughing.od"]["cutting_parameters"]["doc"] == 2.0


# ── operations made from another ────────────────────────────────────────

def test_a_duplicate_keeps_its_source(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    first, _ = _add(use_case, program, "facing")
    second, _ = _add(use_case, program, "facing")
    program.operations[first].cuttingParameters.doc = 0.8
    use_case.edit_operation(program, "facing", second, {"cutting_parameters": {"doc": 2.0}})

    copy_index = use_case.duplicate_operation(program, first)
    assert program.operations[copy_index].cuttingParameters.doc == 0.8


def test_a_contour_of_a_roughing_takes_its_profile_and_stock_and_the_last_contours_settings(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    _with_profile(use_case, program, "id")
    rough, _ = _add(use_case, program, "profileRoughing")
    use_case.edit_operation(program, "profileRoughing", rough, {"stock_to_leave": {"radial": 0.4, "axial": 0.1}})
    contour = use_case.add_profile_contour(program, rough)
    use_case.edit_operation(program, "profileContour", contour, {"passes_count": 3,
                                                                 "speeds_and_feeds": {"feed_rate": 0.08}})

    rough2, _ = _add(use_case, program, "profileRoughing")
    use_case.edit_operation(program, "profileRoughing", rough2, {"stock_to_leave": {"radial": 0.6}})
    new = program.operations[use_case.add_profile_contour(program, rough2)]

    assert new.profileContourStrategy.profiling_type is ProfilingType.ID
    assert (new.initialStockToLeave.stockToLeaveX, new.initialStockToLeave.stockToLeaveZ) == (0.6, 0.1)
    assert new.passesCount == 3
    assert new.speedsAndFeeds.feed_rate == 0.08


def test_a_turning_finish_takes_its_turnings_speeds_and_the_last_finishs_passes(tmp_path):
    use_case, program = _use_case(tmp_path), _program(tmp_path)
    turning, _ = _add(use_case, program, "turning")
    finish = use_case.add_turning_finish(program, turning)
    use_case.edit_operation(program, "turningFinish", finish, {"passes_count": 4,
                                                               "speeds_and_feeds": {"feed_rate": 0.05}})

    turning2, _ = _add(use_case, program, "turning")
    use_case.edit_operation(program, "turning", turning2, {"speeds_and_feeds": {"feed_rate": 0.25},
                                                           "m1_parameters": {"include_m1": False}})
    new = program.operations[use_case.add_turning_finish(program, turning2)]

    assert new.passesCount == 4
    assert new.speedsAndFeeds.feed_rate == 0.25
    assert new.m1Parameters.include_m1 is False


# ── the file ────────────────────────────────────────────────────────────

def test_the_file_is_read_back(tmp_path):
    path = str(tmp_path / OPERATION_DEFAULTS_FILE)
    OperationDefaultsStore(path).remember("facing", {"cutting_parameters": {"doc": 1.5}})
    assert OperationDefaultsStore(path).patch_for("facing") == {"cutting_parameters": {"doc": 1.5}}


def test_remembering_replaces_what_the_type_had(tmp_path):
    store = OperationDefaultsStore()
    store.remember("facing", {"speeds_and_feeds": {"mode": "css", "css_value": 180}})
    store.remember("facing", {"speeds_and_feeds": {"mode": "rpm", "rpm_value": 900}})
    assert store.patch_for("facing") == {"speeds_and_feeds": {"mode": "rpm", "rpm_value": 900}}


def test_what_a_store_gives_is_a_copy(tmp_path):
    store = OperationDefaultsStore()
    store.remember("facing", {"cutting_parameters": {"doc": 1.0}})
    store.patch_for("facing")["cutting_parameters"]["doc"] = 9.0
    assert store.patch_for("facing") == {"cutting_parameters": {"doc": 1.0}}


def test_a_file_that_cannot_be_read_is_none(tmp_path):
    path = tmp_path / OPERATION_DEFAULTS_FILE
    path.write_text("{ not json")
    assert OperationDefaultsStore(str(path)).patch_for("facing") == {}
    path.write_text("[1, 2]")
    assert OperationDefaultsStore(str(path)).patch_for("facing") == {}


def test_without_a_config_directory_nothing_is_written(tmp_path):
    use_case = ConversationalUseCase(programs_dir=str(tmp_path), ini=SimpleNamespace(), tools=[])
    program = _program(tmp_path)
    index, _ = _add(use_case, program, "facing")
    use_case.edit_operation(program, "facing", index, {"cutting_parameters": {"doc": 1.5}})

    assert list(tmp_path.iterdir()) == []
    _, new = _add(use_case, program, "facing")
    assert new.cuttingParameters.doc == 1.5
