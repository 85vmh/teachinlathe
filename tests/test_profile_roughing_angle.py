"""The angle of Profile Roughing's angled passes (an ID profile's): kept in the
operation between 30° and 60°, 45° unless set; the passes planned at it, the
G-code naming it; and the box over the canvas that sets it - the slider that
opens under the passes, the angle taken when the finger is lifted, snapped to
30°, 45° and 60° near them, the box as wide whatever the angle."""

import math
from pathlib import Path
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QObject, QPointF, Qt, QUrl
from PyQt6.QtQml import QQmlComponent, QQmlEngine
from PyQt6.QtQuick import QQuickItem, QQuickWindow
from PyQt6.QtTest import QTest

from teachinlathe.conversational.gcode.operations import profile_roughing
from teachinlathe.conversational.gcode.operations.profile_roughing import (
    generate_profile_roughing_gcode,
    plan_profile_roughing,
)
from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase
from teachinlathe.conversational.model.data_types import (
    DIAGONAL_ANGLE,
    DIAGONAL_ANGLE_RANGE,
    Operation,
    PassType,
    ProfileRoughingStrategy,
    ProfilingType,
)
from teachinlathe.conversational.model.factories import make_default_operation, make_new_program
from teachinlathe.conversational.model.updaters import apply_profile_roughing_strategy_update
from test_profile_roughing_toolpath import DIAGONAL, operation

LOW, HIGH = DIAGONAL_ANGLE_RANGE


# ── the operation keeps it ──────────────────────────────────────────────────

def test_the_angle_is_45_degrees_unless_set():
    strategy = ProfileRoughingStrategy.from_dict({"profiling_type": "id", "pass_type": "diagonal_interior"})

    assert DIAGONAL_ANGLE == 45.0
    assert strategy.diagonal_angle == 45.0
    assert strategy.to_dict()["diagonal_angle"] == 45.0


def test_the_angle_is_saved_and_read_back():
    strategy = ProfileRoughingStrategy(ProfilingType.ID, PassType.DIAGONAL_EXTERIOR, diagonal_angle=37.0)

    again = ProfileRoughingStrategy.from_dict(strategy.to_dict())

    assert again == strategy


@pytest.mark.parametrize("written,read", [(10, LOW), (90, HIGH), (LOW, LOW), (HIGH, HIGH), (52.5, 52.5),
                                          ("abc", DIAGONAL_ANGLE), (None, DIAGONAL_ANGLE),
                                          (float("nan"), DIAGONAL_ANGLE)])
def test_an_angle_read_is_kept_within_30_to_60_degrees(written, read):
    strategy = ProfileRoughingStrategy.from_dict({"profiling_type": "id", "pass_type": "diagonal_interior",
                                                  "diagonal_angle": written})

    assert strategy.diagonal_angle == read


def test_an_edit_of_the_angle_changes_the_angle_alone():
    strategy = ProfileRoughingStrategy(ProfilingType.ID, PassType.DIAGONAL_INTERIOR)

    apply_profile_roughing_strategy_update(strategy, {"diagonal_angle": 33})

    assert strategy == ProfileRoughingStrategy(ProfilingType.ID, PassType.DIAGONAL_INTERIOR, diagonal_angle=33.0)


@pytest.mark.parametrize("edited,kept", [(5, LOW), (75, HIGH), ("abc", DIAGONAL_ANGLE)])
def test_an_edit_of_the_angle_is_kept_within_30_to_60_degrees(edited, kept):
    strategy = ProfileRoughingStrategy(ProfilingType.ID, PassType.DIAGONAL_INTERIOR, diagonal_angle=50.0)

    apply_profile_roughing_strategy_update(strategy, {"diagonal_angle": edited})

    assert strategy.diagonal_angle == kept


def test_an_edit_without_the_angle_leaves_it():
    strategy = ProfileRoughingStrategy(ProfilingType.ID, PassType.DIAGONAL_INTERIOR, diagonal_angle=50.0)

    apply_profile_roughing_strategy_update(strategy, {"pass_type": "diagonal_exterior"})
    apply_profile_roughing_strategy_update(strategy, {"diagonal_angle": None})

    assert strategy.diagonal_angle == 50.0


def test_the_angle_edited_in_a_program_is_there_when_it_is_opened_again(tmp_path):
    use_case = ConversationalUseCase(programs_dir=str(tmp_path), ini=SimpleNamespace())
    program = make_new_program(str(tmp_path))
    program.operations = [Operation.from_dict({**make_default_operation("profileRoughing").to_dict(), "order": 1})]

    assert use_case.update_operation(program, "profileRoughing", 0,
                                     {"profile_roughing_strategy": {"diagonal_angle": 33}})
    opened = use_case.load_program_file(use_case.save(program))

    assert opened.operations[0].profileRoughingStrategy.diagonal_angle == 33.0


# ── the passes are planned at it ────────────────────────────────────────────

def _at(profile, pass_type, angle):
    cut = operation(profile, pass_type)
    cut.op.profileRoughingStrategy.diagonal_angle = angle
    return cut


def _slant(m):
    """A move's angle from the Z axis, in degrees, as the part has it (on the
    radius)."""
    return math.degrees(math.atan2(abs(m.r1 - m.r0), abs(m.z1 - m.z0)))


def _angled_cuts(plan):
    """The cuts slanted across both axes, but the contour's, in the order
    they are made."""
    return [m for m in plan.moves
            if m.feed and not m.contour and abs(m.z1 - m.z0) > 0.05 and abs(m.r1 - m.r0) > 1e-6]


@pytest.mark.parametrize("profile", ["id_steps", "id_groove"])
@pytest.mark.parametrize("pass_type", DIAGONAL)
@pytest.mark.parametrize("angle", [30.0, 45.0, 60.0])
def test_the_angled_passes_cut_at_the_angle(profile, pass_type, angle):
    plan = plan_profile_roughing(_at(profile, pass_type, angle))
    cuts = _angled_cuts(plan)

    assert not plan.error
    assert len(cuts) > 10
    for m in cuts:
        assert abs(_slant(m) - angle) < 1e-6, (m, _slant(m))


@pytest.mark.parametrize("profile", ["id_steps", "id_groove"])
@pytest.mark.parametrize("pass_type", DIAGONAL)
@pytest.mark.parametrize("angle", [30.0, 60.0])
def test_the_angled_passes_are_one_depth_of_cut_apart_at_any_angle(profile, pass_type, angle):
    """Square to the passes, from one to the next - or a step back, the walk
    turning into an island, or the same line again past the profile."""
    cut = _at(profile, pass_type, angle)
    doc = cut.op.cuttingParameters.doc
    a = math.radians(angle)
    levels = [m.z0 * math.sin(a) - m.r0 * math.cos(a) for m in _angled_cuts(plan_profile_roughing(cut))]

    # (the same line within the planner's grid)
    for gap in (x - y for x, y in zip(levels, levels[1:])):
        assert abs(gap - doc) < 1e-3 or gap < 1e-3, gap


def test_another_angle_is_planned_again():
    """The plan kept for one angle is not the one for another."""
    keys = {profile_roughing.roughing_plan_key(_at("id_steps", "diagonal_interior", angle))
            for angle in (30.0, 45.0, 60.0)}

    assert len(keys) == 3


@pytest.mark.parametrize("pass_type,toward", [("diagonal_interior", "interior"),
                                             ("diagonal_exterior", "exterior")])
def test_the_gcode_names_the_angle(pass_type, toward):
    lines = generate_profile_roughing_gcode(_at("id_steps", pass_type, 33.0))

    assert any("33° toward " + toward in line for line in lines)


# ── the box that sets it ────────────────────────────────────────────────────

UI = Path(__file__).resolve().parents[1] / "src/teachinlathe/ui"

#: The box over a card it pushes down as it grows, the angle given back to it
#: once edited - as the operation gives it, the model being this.
BOX = b'''
import QtQuick
import QtQuick.Layouts
import tabs.conversational
Item {
    width: 700; height: 500
    property real angle: 45
    property var edits: []
    property string profilingType: "id"
    ColumnLayout {
        x: 20; y: 20; width: 660
        spacing: 8
        ProfilingTypeBox {
            objectName: "box"
            Layout.alignment: Qt.AlignRight
            profilingType: parent.parent.profilingType
            passType: "diagonal_interior"
            diagonalAngle: parent.parent.angle
            onDiagonalAngleEdited: function(value) {
                var root = parent.parent
                root.edits = root.edits.concat([value])
                root.angle = value
            }
        }
        Rectangle { objectName: "under"; Layout.alignment: Qt.AlignRight; width: 200; height: 60 }
    }
}'''


@pytest.fixture
def scene():
    engine = QQmlEngine()
    engine.addImportPath(str(UI))
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    component = QQmlComponent(engine)
    component.setData(BOX, QUrl.fromLocalFile(str(UI / "box_test.qml")))
    root = component.create()
    assert root is not None, [e.toString() for e in component.errors()]
    window = QQuickWindow()
    root.setParentItem(window.contentItem())
    window.resize(700, 500)
    window.show()
    QTest.qWait(50)
    yield SimpleNamespace(window=window, root=root, box=root.findChild(QObject, "box"),
                          under=root.findChild(QObject, "under"), warnings=warnings)
    window.close()
    root.setParentItem(None)
    root.deleteLater()
    QTest.qWait(1)


def _item_with(box, prop):
    """The box's item that has ``prop``: the slider (snapDistance), the
    button (iconSource)."""
    return next(i for i in box.findChildren(QQuickItem) if i.property(prop) is not None)


def _centre(item):
    return item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()


def _on_track(slider, angle):
    """Where on the window the slider's track has ``angle``."""
    x = slider.property("trackLeft") + (angle - LOW) / (HIGH - LOW) * slider.property("trackWidth")
    return slider.mapToScene(QPointF(x, slider.property("trackY"))).toPoint()


def _open(scene):
    QTest.mouseClick(scene.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     _centre(_item_with(scene.box, "iconSource")))
    QTest.qWait(scene.box.property("anglePanelDuration") + 150)


def _drag(scene, angles):
    """A finger down on the slider at the first angle, along it through the
    rest; the angles reported meanwhile, and what the slider shows at the end.
    Not yet lifted."""
    slider = _item_with(scene.box, "snapDistance")
    QTest.mousePress(scene.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                     _on_track(slider, angles[0]))
    for angle in angles[1:]:
        QTest.mouseMove(scene.window, _on_track(slider, angle))
    return _edits(scene), slider.property("shownValue")


def _edits(scene):
    """The angles reported, in order."""
    return scene.root.property("edits").toVariant()


def _lift(scene, angle):
    QTest.mouseRelease(scene.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                       _on_track(_item_with(scene.box, "snapDistance"), angle))


def test_the_button_opens_the_slider_under_the_passes_and_closes_it(scene):
    closed = scene.box.height()
    under = scene.under.y()

    _open(scene)
    opened = scene.box.height()
    assert opened > closed + 50
    assert scene.under.y() - under == pytest.approx(opened - closed)
    assert scene.box.property("_anglePanelOpen")

    _open(scene)
    assert scene.box.height() == pytest.approx(closed)
    assert scene.under.y() == pytest.approx(under)
    assert not scene.warnings, scene.warnings


def test_the_angle_is_taken_once_the_finger_is_lifted(scene):
    _open(scene)

    edits, shown = _drag(scene, [45, 42, 38, 36])
    assert edits == []
    assert shown == 36
    assert scene.box.property("diagonalAngle") == 45

    _lift(scene, 36)
    assert _edits(scene) == [36]
    assert scene.box.property("diagonalAngle") == 36


@pytest.mark.parametrize("finger,taken", [(31.5, 30), (43.4, 45), (46.9, 45), (58.2, 60), (40.4, 40), (55.6, 56)])
def test_the_angle_snaps_to_30_45_and_60_near_them_else_whole_degrees(scene, finger, taken):
    _open(scene)

    _drag(scene, [finger])
    _lift(scene, finger)

    assert _edits(scene) == ([taken] if taken != 45 else [])
    assert scene.box.property("diagonalAngle") == taken


def test_lifted_where_the_angle_already_is_nothing_is_edited(scene):
    _open(scene)

    _drag(scene, [45, 50, 45])
    _lift(scene, 45)

    assert _edits(scene) == []


def test_the_box_is_as_wide_whatever_the_angle(scene):
    widths = set()
    for angle in range(int(LOW), int(HIGH) + 1):
        scene.root.setProperty("angle", angle)
        widths.add(round(scene.box.width(), 3))

    assert len(widths) == 1, widths


def test_an_od_profile_has_no_angled_passes_and_no_angle(scene):
    scene.root.setProperty("profilingType", "od")
    QTest.qWait(10)

    assert not _item_with(scene.box, "iconSource").isVisible()
    assert not any(i.isVisible() and str(i.property("text") or "").startswith("45°")
                   for i in scene.box.findChildren(QQuickItem))
