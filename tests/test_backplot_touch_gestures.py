"""The backplot's three-finger swipe (widgets/backplot/touch_gestures.py).

Events are sent straight to a window the swipe filters: the filter sees them
before Qt Quick tries to deliver them, so no touch device needs registering.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt6.QtCore import QPointF, Qt  # noqa: E402
from PyQt6.QtGui import (QEventPoint, QGuiApplication, QInputDevice,  # noqa: E402
                         QNativeGestureEvent, QPointingDevice, QTouchEvent)
from PyQt6.QtQuick import QQuickItem, QQuickWindow  # noqa: E402

from teachinlathe.widgets.backplot.touch_gestures import ThreeFingerSwipe  # noqa: E402

DISTANCE = 80
# The plot is the right half of an 800 x 600 window.
ON_PLOT = [(500, 300), (560, 300), (620, 300)]
OFF_PLOT = [(100, 300), (160, 300), (220, 300)]


@pytest.fixture(scope="module")
def app():
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def window(app):
    window = QQuickWindow()
    window.resize(800, 600)
    plot = QQuickItem(window.contentItem())
    plot.setX(400)
    plot.setWidth(400)
    plot.setHeight(600)
    window.show()
    window.cleared = []
    window.swipe = ThreeFingerSwipe(plot, lambda: window.cleared.append(1), DISTANCE)
    window.installEventFilter(window.swipe)
    yield window
    window.close()


def _device(kind, name, system_id):
    return QPointingDevice(name, system_id, kind, QPointingDevice.PointerType.Finger,
                           QInputDevice.Capability.Position, 10, 0)


# Made once and kept: Qt holds on to the device an event names, and one freed
# behind its back takes the process down.
TOUCHSCREEN = _device(QInputDevice.DeviceType.TouchScreen, "touchscreen", 1)
TOUCHPAD = _device(QInputDevice.DeviceType.TouchPad, "touchpad", 2)


def _touch(window, kind, points):
    event = QTouchEvent(kind, TOUCHSCREEN, Qt.KeyboardModifier.NoModifier,
                        [QEventPoint(i, state, QPointF(x, y), QPointF(x, y))
                         for i, (state, x, y) in points])
    QGuiApplication.sendEvent(window, event)


def _swipe_on_screen(window, starts, dx, dy, steps=10):
    """Fingers land one after another, as they do, then move together."""
    S = QEventPoint.State
    for k in range(1, len(starts) + 1):
        _touch(window, QTouchEvent.Type.TouchBegin if k == 1 else QTouchEvent.Type.TouchUpdate,
               [(i, (S.Pressed if i == k - 1 else S.Stationary, *starts[i])) for i in range(k)])
    for step in range(1, steps + 1):
        _touch(window, QTouchEvent.Type.TouchUpdate,
               [(i, (S.Updated, x + dx * step / steps, y + dy * step / steps))
                for i, (x, y) in enumerate(starts)])
    _touch(window, QTouchEvent.Type.TouchEnd,
           [(i, (S.Released, x + dx, y + dy)) for i, (x, y) in enumerate(starts)])


def _pan_on_touchpad(window, fingers, x, total, steps=12):
    """The X11 shape of a touchpad swipe: begin, pans with deltas, end."""
    G = Qt.NativeGestureType

    def send(gesture, delta=0.0):
        position = QPointF(x, 300)
        QGuiApplication.sendEvent(window, QNativeGestureEvent(
            gesture, TOUCHPAD, fingers, position, position, position, 0.0, QPointF(delta, 0)))

    send(G.BeginNativeGesture)
    for _ in range(steps):
        send(G.PanNativeGesture, total / steps)
    send(G.EndNativeGesture)


@pytest.mark.parametrize("dx, dy", [(120, 0), (0, 120), (-90, -60)])
def test_three_fingers_on_the_plot_clear_it(window, dx, dy):
    _swipe_on_screen(window, ON_PLOT, dx, dy)
    assert window.cleared == [1]


def test_a_long_swipe_clears_once(window):
    _swipe_on_screen(window, ON_PLOT, 400, 0)
    assert window.cleared == [1]


def test_each_swipe_clears_again(window):
    _swipe_on_screen(window, ON_PLOT, 120, 0)
    _swipe_on_screen(window, ON_PLOT, 120, 0)
    assert window.cleared == [1, 1]


@pytest.mark.parametrize("starts, dx", [
    (ON_PLOT, DISTANCE / 2),                 # not far enough
    (ON_PLOT[:2], 200),                      # a pinch
    (ON_PLOT + [(680, 300)], 200),           # four fingers
    (OFF_PLOT, 200),                         # not on the plot
])
def test_anything_else_on_the_screen_does_not(window, starts, dx):
    _swipe_on_screen(window, starts, dx, 0)
    assert window.cleared == []


def test_three_finger_touchpad_pan_on_the_plot_clears_it(window):
    _pan_on_touchpad(window, 3, 600, 120)
    assert window.cleared == [1]


@pytest.mark.parametrize("fingers, x, total", [
    (2, 600, 200),                           # two-finger scroll
    (3, 100, 200),                           # pointer off the plot
    (3, 600, DISTANCE / 2),                  # not far enough
])
def test_other_touchpad_pans_do_not(window, fingers, x, total):
    _pan_on_touchpad(window, fingers, x, total)
    assert window.cleared == []
