"""Touch preferences and the non-interactive overlay, without a live machine."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QEvent, QObject, QPointF, Qt, QUrl
from PyQt6.QtGui import (
    QEventPoint, QGuiApplication, QInputDevice, QPointingDevice, QTouchEvent,
)
from PyQt6.QtQml import QQmlComponent, QQmlEngine, qmlRegisterSingletonInstance
from PyQt6.QtQuick import QQuickWindow
from PyQt6.QtTest import QTest

from teachinlathe.app.touch_feedback import TouchFeedback
from teachinlathe.core.settings_repository import SettingsRepository


@pytest.fixture(scope="module")
def app():
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def setup(app, tmp_path):
    ini = SimpleNamespace(config_dir=str(tmp_path), default_jog_velocity=180,
                          max_jog_velocity=600)
    settings = SettingsRepository(ini=ini)
    window = QQuickWindow()
    feedback = TouchFeedback(window, settings=settings)
    yield window, feedback, settings, ini
    feedback.restore_cursor()
    window.close()


DEVICE = QPointingDevice(
    "touchscreen", 123, QInputDevice.DeviceType.TouchScreen,
    QPointingDevice.PointerType.Finger, QInputDevice.Capability.Position, 10, 0)


def touch(kind, points):
    # Qt 6.4's public QEventPoint constructor ignores pointId (all are 0).
    # Preserve distinct IDs here, as the platform's real touch events do.
    class TouchEvent(QEvent):
        def points(self):
            return [SimpleNamespace(id=lambda i=i: i, state=lambda s=s: s,
                                    scenePosition=lambda x=x, y=y: QPointF(x, y))
                    for i, s, x, y in points]
    return TouchEvent(kind)


def test_preferences_persist_and_cursor_is_restored(setup):
    _window, feedback, _settings, ini = setup
    previous = QGuiApplication.overrideCursor()
    assert not feedback.hidePointer and not feedback.showTouches
    feedback.hidePointer = True
    feedback.showTouches = True
    assert QGuiApplication.overrideCursor().shape() == Qt.CursorShape.BlankCursor
    restored = SettingsRepository(ini=ini)
    assert restored.get('interface.hide-pointer') is True
    assert restored.get('interface.show-touches') is True
    feedback.hidePointer = True  # does not stack a second cursor override
    feedback.hidePointer = False
    assert QGuiApplication.overrideCursor() == previous


def test_touch_tracks_scroll_and_multiple_fingers_without_consuming_events(setup):
    window, feedback, *_ = setup
    updates = []
    feedback.touchUpdated.connect(lambda *args: updates.append(args))
    press = touch(QEvent.Type.TouchBegin, [(1, QEventPoint.State.Pressed, 100, 80)])
    assert feedback.eventFilter(window, press) is False
    assert not updates
    feedback.showTouches = True
    press.setAccepted(False)
    assert feedback.eventFilter(window, press) is False
    assert not press.isAccepted()
    move = touch(QEvent.Type.TouchUpdate, [
        (1, QEventPoint.State.Updated, 100, 150),
        (2, QEventPoint.State.Pressed, 200, 150)])
    assert feedback.eventFilter(window, move) is False
    end = touch(QEvent.Type.TouchEnd, [
        (1, QEventPoint.State.Released, 100, 160),
        (2, QEventPoint.State.Released, 200, 160)])
    assert feedback.eventFilter(window, end) is False
    assert updates == [(1, 100., 80., True), (1, 100., 150., True),
                       (2, 200., 150., True), (1, 100., 160., False),
                       (2, 200., 160., False)]


def test_cancel_and_disabling_clear_touches(setup):
    window, feedback, *_ = setup
    cleared = []
    feedback.touchesCleared.connect(lambda: cleared.append(True))
    feedback.showTouches = True
    assert feedback.eventFilter(window, QEvent(QEvent.Type.TouchCancel)) is False
    feedback.showTouches = False
    assert len(cleared) == 2


def test_real_qt_touch_event_is_observed_without_accepting_it(setup):
    window, feedback, *_ = setup
    feedback.showTouches = True
    updates = []
    feedback.touchUpdated.connect(lambda *args: updates.append(args))
    event = QTouchEvent(QEvent.Type.TouchBegin, DEVICE, Qt.KeyboardModifier.NoModifier,
                        [QEventPoint(0, QEventPoint.State.Pressed,
                                     QPointF(120, 80), QPointF(120, 80))])
    event.setAccepted(False)
    assert not feedback.eventFilter(window, event)
    assert not event.isAccepted()
    assert updates == [(0, 120., 80., True)]


@pytest.mark.parametrize("popup", [False, True])
def test_overlay_renders_above_content_and_dialogs_and_fades_on_release(setup, popup):
    window, feedback, *_ = setup
    feedback.showTouches = True
    engine = QQmlEngine()
    package = Path(__file__).resolve().parents[1] / 'src/teachinlathe'
    engine.addImportPath(str(package / 'app'))
    engine.addImportPath(str(package / 'ui'))
    engine.rootContext().setContextProperty('touchFeedback', feedback)
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    component = QQmlComponent(engine)
    component.setData(b'''
import QtQuick
import QtQuick.Controls
import app_shell_qml
Item {
    id: appRoot
    width: 400; height: 300
    Rectangle { anchors.fill: parent; color: "white" }
    Popup {
        id: dialog; objectName: "dialog"
        x: 50; y: 50; width: 300; height: 200
        modal: true
        background: Rectangle { color: "white" }
    }
    TouchFeedbackOverlay {
        objectName: "feedback"
        parent: appRoot.Overlay.overlay
        anchors.fill: parent
        controller: touchFeedback
    }
}''', QUrl())
    root = component.create()
    assert root is not None, [e.toString() for e in component.errors()]
    root.setParentItem(window.contentItem())
    window.resize(400, 300)
    window.show()
    if popup:
        root.findChild(QObject, 'dialog').open()
    QTest.qWait(50)
    feedback.touchUpdated.emit(1, 200, 150, True)
    QTest.qWait(150)
    image = window.grabWindow()
    color = image.pixelColor(200, 150)
    overlay = root.findChild(QObject, 'feedback')
    assert color.green() > color.red(), color.name()
    marker = overlay.childItems()[0]
    assert marker.width() == marker.height() == 40
    feedback.touchUpdated.emit(1, 210, 170, True)
    assert marker.x() == 190 and marker.y() == 150
    feedback.touchUpdated.emit(1, 210, 170, False)
    QTest.qWait(300)
    assert not overlay.childItems()
    assert not warnings, warnings
    window.close()
    root.setParentItem(None)
    root.deleteLater()
    QTest.qWait(1)


def test_machine_settings_loads_with_both_preferences(setup):
    window, feedback, *_ = setup
    qmlRegisterSingletonInstance('TeachInLathe', 1, 0, 'TouchFeedback', feedback)
    engine = QQmlEngine()
    package = Path(__file__).resolve().parents[1] / 'src/teachinlathe'
    engine.addImportPath(str(package / 'app'))
    engine.addImportPath(str(package / 'ui'))
    warnings = []
    engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(
        package / 'ui/tabs/machine_settings/MachineSettingsScreen.qml')))
    root = component.createWithInitialProperties({
        'viewModel': {'tools': []}, 'fixturesViewModel': {'fixtures': []}})
    assert root is not None, [e.toString() for e in component.errors()]
    root.setParentItem(window.contentItem())
    root.setWidth(1000)
    root.setHeight(800)
    window.resize(1000, 800)
    window.show()
    QTest.qWait(50)
    controls = {obj.property('text'): obj for obj in root.findChildren(QObject)
                if obj.property('text') in ('Hide pointer', 'Show touches')
                and obj.property('checked') is not None}
    assert set(controls) == {'Hide pointer', 'Show touches'}
    assert not controls['Show touches'].property('checked')
    feedback.showTouches = True
    assert controls['Show touches'].property('checked')
    assert not warnings, warnings
    window.close()
    root.setParentItem(None)
    root.deleteLater()
    QTest.qWait(1)
