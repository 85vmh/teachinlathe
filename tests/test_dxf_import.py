"""A profile read from a DXF drawing (ConversationalUseCase's DXF import,
ImportDxfProfile, DefineProfileEditorViewModel).

What is pinned down here:

* The preview is the profile the drawing gives, turned as asked, and says
  whether the drawing does not tell which is the lathe's axis
  (symmetryAmbiguous); a drawing that cannot be read is an error, not a raise.
* An Import DXF Profile is added only with a drawing read into it: one that
  cannot be read adds nothing. Importing again replaces its primitives; a
  Define Profile drawn by hand is not imported into.
* The drawing is nothing to the profile once read: not even where it was.
  A program saved with the old dxfFilePath reads, and drops it.
* The drawing is parsed, and each turn of it worked out, once while it
  stays as it is: a preview, then the import, read it once; changed, it is
  read again.
* An imported profile's OD / ID can be chosen again (on its editor's title);
  a drawn one's cannot.
"""

import os
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtTest import QSignalSpy

from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase
from teachinlathe.conversational.model.data_types import (
    DefineProfile, ImportDxfProfile, ProfilingType, operation_types,
)
from teachinlathe.conversational.model.factories import make_default_operation, make_new_program
from teachinlathe.conversational.model.updaters import apply_define_profile_update
from teachinlathe.conversational.store import dxf_profile_importer

ezdxf = pytest.importorskip("ezdxf")


# ── drawings ────────────────────────────────────────────────────────────

def _shaft_dxf(path):
    """A stepped shaft, both halves about the DXF's X axis: Ø20 x 10, then Ø30
    to Z-25 - its axis is plain (it is not symmetric about its middle)."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    points = [(0, 10), (-10, 10), (-10, 15), (-25, 15)]
    for a, b in zip(points, points[1:]):
        msp.add_line(a, b)
        msp.add_line((a[0], -a[1]), (b[0], -b[1]))
    msp.add_line((0, 10), (0, -10))
    msp.add_line((-25, 15), (-25, -15))
    doc.saveas(path)
    return str(path)


def _block_dxf(path):
    """A 40 x 20 rectangle: as symmetric about its middle as about its axis -
    which is the lathe's, the drawing does not say."""
    doc = ezdxf.new()
    doc.modelspace().add_lwpolyline([(0, 10), (-40, 10), (-40, -10), (0, -10)], close=True)
    doc.saveas(path)
    return str(path)


SHAFT = [("startPoint", 20.0, 0.0), ("lineTo", 20.0, -10.0),
         ("lineTo", 30.0, -10.0), ("lineTo", 30.0, -25.0)]


def _points(primitives):
    out = []
    for p in primitives:
        if p["type"] == "startPoint":
            out.append((p["type"], p["x_start"], p["z_start"]))
        else:
            out.append((p["type"], p["x_end"], p["z_end"]))
    return out


def _op_points(op):
    return _points([p.to_dict() for p in op.profile_primitives])


@pytest.fixture
def use_case(tmp_path):
    return ConversationalUseCase(programs_dir=str(tmp_path), ini=SimpleNamespace(config_dir=str(tmp_path)),
                                 tools=[])


@pytest.fixture
def program(tmp_path):
    return make_new_program(str(tmp_path))


# ── the preview ─────────────────────────────────────────────────────────

def test_the_preview_is_the_profile_the_drawing_gives(use_case, tmp_path):
    preview = use_case.preview_dxf_profile(_shaft_dxf(tmp_path / "shaft.dxf"))

    assert preview["ok"] is True and preview["error"] == ""
    assert preview["symmetryAmbiguous"] is False
    assert _points(preview["primitives"]) == SHAFT


def test_a_drawing_symmetric_both_ways_is_turned_as_asked(use_case, tmp_path):
    path = _block_dxf(tmp_path / "block.dxf")

    as_drawn = use_case.preview_dxf_profile(path)
    turned = use_case.preview_dxf_profile(path, quarter_turns=1)

    assert as_drawn["symmetryAmbiguous"] is True
    # its long side along Z as drawn, across once turned
    assert _points(as_drawn["primitives"]) == [("startPoint", 20.0, 0.0), ("lineTo", 20.0, -40.0)]
    assert _points(turned["primitives"]) == [("startPoint", 40.0, 0.0), ("lineTo", 40.0, -20.0)]


def test_a_drawing_that_cannot_be_read_is_an_error_in_the_preview(use_case, tmp_path):
    preview = use_case.preview_dxf_profile(str(tmp_path / "missing.dxf"))

    assert preview["ok"] is False
    assert preview["error"]
    assert preview["primitives"] == []
    assert preview["symmetryAmbiguous"] is False


# ── importing ───────────────────────────────────────────────────────────

def test_a_drawing_imported_is_a_new_import_dxf_profile(use_case, program, tmp_path):
    before = len(program.operations)

    at = use_case.add_dxf_profile(program, before, _shaft_dxf(tmp_path / "shaft.dxf"))

    op = program.operations[at]
    assert len(program.operations) == before + 1
    assert isinstance(op, ImportDxfProfile) and op.type == ImportDxfProfile.TYPE
    assert _op_points(op) == SHAFT


def test_a_drawing_that_cannot_be_read_adds_nothing(use_case, program, tmp_path):
    before = list(program.operations)

    with pytest.raises(Exception):
        use_case.add_dxf_profile(program, len(before), str(tmp_path / "missing.dxf"))

    assert program.operations == before


def test_importing_again_replaces_the_primitives_turned_as_asked(use_case, program, tmp_path):
    at = use_case.add_dxf_profile(program, len(program.operations), _shaft_dxf(tmp_path / "shaft.dxf"))
    op = program.operations[at]

    assert use_case.import_dxf_profile(program, at, _block_dxf(tmp_path / "block.dxf"), quarter_turns=1)

    assert program.operations[at] is op
    assert _op_points(op) == [("startPoint", 40.0, 0.0), ("lineTo", 40.0, -20.0)]


def test_nothing_is_imported_where_there_is_no_profile(use_case, program, tmp_path):
    path = _shaft_dxf(tmp_path / "shaft.dxf")
    facing = use_case.insert_operation(program, "facing", len(program.operations))

    assert use_case.import_dxf_profile(program, facing, path) is False
    assert use_case.import_dxf_profile(program, 99, path) is False


# ── nothing of the drawing is kept ──────────────────────────────────────

def test_an_imported_profile_keeps_no_file_path(use_case, program, tmp_path):
    at = use_case.add_dxf_profile(program, len(program.operations), _shaft_dxf(tmp_path / "shaft.dxf"))

    data = program.operations[at].to_dict()

    assert "dxfFilePath" not in data
    assert ImportDxfProfile.from_dict(data).to_dict() == data


def test_a_program_saved_with_the_old_file_path_reads_and_drops_it():
    data = make_default_operation(ImportDxfProfile.TYPE).to_dict()
    data["dxfFilePath"] = "/media/cnc/STICK/part.dxf"

    op = operation_types[ImportDxfProfile.TYPE].from_dict(data)

    assert isinstance(op, ImportDxfProfile)
    assert "dxfFilePath" not in op.to_dict()


def test_a_profile_without_its_type_reads_as_its_class_says():
    data = make_default_operation(ImportDxfProfile.TYPE).to_dict()
    del data["type"]
    assert ImportDxfProfile.from_dict(data).type == ImportDxfProfile.TYPE

    data = make_default_operation(DefineProfile.TYPE).to_dict()
    del data["type"]
    assert DefineProfile.from_dict(data).type == DefineProfile.TYPE


# ── read once ───────────────────────────────────────────────────────────

@pytest.fixture
def parses(monkeypatch):
    """How many times a drawing was parsed, and each turn worked out."""
    counts = {"read": 0, "profile": 0}
    read, profile = dxf_profile_importer.read_dxf_segments, dxf_profile_importer.profile_from_segments

    def counted_read(*args, **kwargs):
        counts["read"] += 1
        return read(*args, **kwargs)

    def counted_profile(*args, **kwargs):
        counts["profile"] += 1
        return profile(*args, **kwargs)
    monkeypatch.setattr(dxf_profile_importer, "read_dxf_segments", counted_read)
    monkeypatch.setattr(dxf_profile_importer, "profile_from_segments", counted_profile)
    return counts


def test_a_drawing_previewed_turned_then_imported_is_read_once(use_case, program, tmp_path, parses):
    path = _block_dxf(tmp_path / "block.dxf")

    use_case.preview_dxf_profile(path)
    use_case.preview_dxf_profile(path, quarter_turns=1)
    use_case.preview_dxf_profile(path)
    use_case.add_dxf_profile(program, len(program.operations), path, quarter_turns=1)

    assert parses == {"read": 1, "profile": 2}


def test_a_drawing_changed_is_read_again(use_case, tmp_path, parses):
    path = _shaft_dxf(tmp_path / "part.dxf")
    use_case.preview_dxf_profile(path)

    _block_dxf(tmp_path / "part.dxf")
    preview = use_case.preview_dxf_profile(path)

    assert parses["read"] == 2
    assert preview["symmetryAmbiguous"] is True


def test_another_drawing_is_read_and_the_first_again_too(use_case, tmp_path, parses):
    shaft, block = _shaft_dxf(tmp_path / "shaft.dxf"), _block_dxf(tmp_path / "block.dxf")

    use_case.preview_dxf_profile(shaft)
    use_case.preview_dxf_profile(block)
    use_case.preview_dxf_profile(shaft)

    assert parses["read"] == 3


def test_the_profiles_kept_are_not_changed_by_the_program(use_case, program, tmp_path):
    path = _shaft_dxf(tmp_path / "shaft.dxf")
    at = use_case.add_dxf_profile(program, len(program.operations), path)
    op = program.operations[at]

    op.profile_primitives[1].x_end = 99.0

    assert _points(use_case.preview_dxf_profile(path)["primitives"]) == SHAFT


# ── OD or ID ────────────────────────────────────────────────────────────

def test_an_imported_profiles_od_or_id_is_chosen_again_a_drawn_ones_is_not():
    imported = make_default_operation(ImportDxfProfile.TYPE)
    drawn = make_default_operation(DefineProfile.TYPE)

    apply_define_profile_update(imported, {"profile_type": "id"})
    apply_define_profile_update(drawn, {"profile_type": "id"})

    assert imported.profile_type == ProfilingType.ID
    assert drawn.profile_type == ProfilingType.OD


class _Tab(QObject):
    """What an editor needs of its tab: the use case, and programChanged."""
    programChanged = pyqtSignal()

    def __init__(self, use_case):
        super().__init__()
        self.use_case = use_case


def _profile_editor(use_case, program, index):
    from teachinlathe.ui.tabs.conversational.OperationEditorViewModel import DefineProfileEditorViewModel

    tab = _Tab(use_case)
    editor = DefineProfileEditorViewModel(tab, program, index, use_case.details_payload(program, index))
    return tab, editor


def test_the_editor_of_an_imported_profile_asks_for_od_or_id(use_case, program, tmp_path):
    at = use_case.add_dxf_profile(program, len(program.operations), _shaft_dxf(tmp_path / "shaft.dxf"))
    op = program.operations[at]
    _tab, editor = _profile_editor(use_case, program, at)
    asked = QSignalSpy(editor.profileTypeChoiceRequested)

    assert editor.profileTypeChangeable is True
    assert editor.editorTitle == f"Op#{op.order} {op.display_name()}"
    editor.chooseProfileType()

    assert [list(args) for args in asked] == [[op.profile_id, "od"]]


def test_the_editor_of_a_drawn_profile_does_not(use_case, program):
    use_case.insert_define_profile(program, "od", len(program.operations))
    at = len(program.operations) - 1
    _tab, editor = _profile_editor(use_case, program, at)
    asked = QSignalSpy(editor.profileTypeChoiceRequested)

    assert editor.profileTypeChangeable is False
    editor.chooseProfileType()

    assert len(asked) == 0


def test_the_editors_title_follows_the_profile_type(use_case, program, tmp_path):
    at = use_case.add_dxf_profile(program, len(program.operations), _shaft_dxf(tmp_path / "shaft.dxf"))
    tab, editor = _profile_editor(use_case, program, at)
    title_before = editor.editorTitle

    apply_define_profile_update(program.operations[at], {"profile_type": "id"})
    tab.programChanged.emit()

    assert editor.editorTitle != title_before
    assert "ID" in editor.editorTitle.upper()
