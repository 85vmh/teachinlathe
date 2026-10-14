"""The backplot's three-finger swipe, which clears the plot.

Qt Quick cannot deliver it. The plot's QML stacks a MouseArea (one finger)
inside a PinchArea (two); each takes its touch point exclusively as it lands,
so by the time a third finger comes down the first two are spoken for and a
pointer handler asking for three never sees three. So this watches the
window's events before Qt Quick hands them out - and only watches: nothing is
consumed, and the pan, pinch and double tap carry on as before.

Three fingers arrive one of two ways:

* from a touchscreen, as touch events carrying every finger's point;
* from a touchpad, already recognised by the system as a gesture: on X11 a
  native gesture that begins, pans (with the finger count and how far it
  moved) and ends; on other platforms a single swipe.
"""

import math

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QEventPoint, QNativeGestureEvent

_TOUCH_UPDATES = (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate)
_TOUCH_ENDS = (QEvent.Type.TouchEnd, QEvent.Type.TouchCancel)

_FINGERS = 3


class ThreeFingerSwipe(QObject):
    """Calls ``on_swipe`` when three fingers, put down on ``item``, move
    together at least ``distance`` pixels in any direction.

    Install it as an event filter on the item's window. It fires once per
    gesture: the fingers have to lift before it can fire again.
    """

    def __init__(self, item, on_swipe, distance=80, parent=None):
        super().__init__(parent)
        self._item = item
        self._on_swipe = on_swipe
        self.distance = distance
        self._origin = None     # touchscreen: the fingers' centroid as the third landed
        self._travel = None     # touchpad: how far a three-finger pan has gone
        self._fired = False

    def eventFilter(self, _watched, event):
        # By class rather than type: PyQt6 6.4's QEvent.Type has no
        # NativeGesture, and type() gives those as a bare int.
        if isinstance(event, QNativeGestureEvent):
            self._native_gesture(event)
        elif event.type() in _TOUCH_UPDATES:
            self._touch(event)
        elif event.type() in _TOUCH_ENDS:
            self._reset()
        return False

    def _reset(self):
        self._origin = None
        self._travel = None
        self._fired = False

    def _touch(self, event):
        down = [p for p in event.points() if p.state() != QEventPoint.State.Released]
        if len(down) != _FINGERS:
            # Two fingers is a pinch, four is nothing; either way, start over
            # once there are three again.
            self._origin = None
            return
        if self._fired:
            return

        positions = [p.scenePosition() for p in down]
        centroid = (sum(p.x() for p in positions) / _FINGERS,
                    sum(p.y() for p in positions) / _FINGERS)
        if self._origin is None:
            if self._on_item(positions):
                self._origin = centroid
            return
        if math.hypot(centroid[0] - self._origin[0],
                      centroid[1] - self._origin[1]) >= self.distance:
            self._fire()

    def _native_gesture(self, event):
        gesture = event.gestureType()
        if gesture in (Qt.NativeGestureType.BeginNativeGesture,
                       Qt.NativeGestureType.EndNativeGesture):
            self._reset()
        elif gesture == Qt.NativeGestureType.SwipeNativeGesture:
            if (not self._fired and event.fingerCount() in (0, _FINGERS)
                    and self._on_item([event.scenePosition()])):
                self._fire()
        elif (gesture == Qt.NativeGestureType.PanNativeGesture
              and event.fingerCount() == _FINGERS and not self._fired):
            if self._travel is None:
                if not self._on_item([event.scenePosition()]):
                    return
                self._travel = [0.0, 0.0]
            delta = event.delta()
            self._travel[0] += delta.x()
            self._travel[1] += delta.y()
            if math.hypot(*self._travel) >= self.distance:
                self._fire()

    def _fire(self):
        self._fired = True
        self._on_swipe()

    def _on_item(self, scene_positions):
        item = self._item
        return (item is not None and item.isVisible()
                and all(item.contains(item.mapFromScene(p)) for p in scene_positions))
