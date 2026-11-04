"""Persistent touch display preferences and passive window touch observation."""

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QEventPoint, QGuiApplication

from teachinlathe.core.settings_repository import (
    HIDE_POINTER, SHOW_TOUCHES, settings_repository,
)


class TouchFeedback(QObject):
    hidePointerChanged = pyqtSignal()
    showTouchesChanged = pyqtSignal()
    touchUpdated = pyqtSignal(int, float, float, bool)
    touchesCleared = pyqtSignal()

    def __init__(self, window, parent=None, settings=None):
        super().__init__(parent)
        self._settings = settings_repository() if settings is None else settings
        self._cursor_hidden = False
        self._settings.settingChanged.connect(self._setting_changed)
        window.installEventFilter(self)
        QGuiApplication.instance().aboutToQuit.connect(self.restore_cursor)
        self._apply_cursor()

    @pyqtProperty(bool, notify=hidePointerChanged)
    def hidePointer(self):
        return bool(self._settings.get(HIDE_POINTER))

    @hidePointer.setter
    def hidePointer(self, hidden):
        self._settings.set(HIDE_POINTER, hidden)

    @pyqtProperty(bool, notify=showTouchesChanged)
    def showTouches(self):
        return bool(self._settings.get(SHOW_TOUCHES))

    @showTouches.setter
    def showTouches(self, shown):
        self._settings.set(SHOW_TOUCHES, shown)

    def _setting_changed(self, name, _value):
        if name == HIDE_POINTER:
            self._apply_cursor()
            self.hidePointerChanged.emit()
        elif name == SHOW_TOUCHES:
            if not self.showTouches:
                self.touchesCleared.emit()
            self.showTouchesChanged.emit()

    def _apply_cursor(self):
        if self.hidePointer and not self._cursor_hidden:
            # An application override also covers controls with their own
            # cursorShape, such as the clickable Program Header.
            QGuiApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
            self._cursor_hidden = True
        elif not self.hidePointer:
            self.restore_cursor()

    def restore_cursor(self):
        if self._cursor_hidden:
            QGuiApplication.restoreOverrideCursor()
            self._cursor_hidden = False

    def eventFilter(self, _watched, event):
        kind = event.type()
        if kind in (QEvent.Type.TouchCancel, QEvent.Type.WindowDeactivate,
                    QEvent.Type.Hide):
            self.touchesCleared.emit()
        elif self.showTouches and kind in (
                QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            for point in event.points():
                position = point.scenePosition()
                down = (kind != QEvent.Type.TouchEnd
                        and point.state() != QEventPoint.State.Released)
                self.touchUpdated.emit(point.id(), position.x(), position.y(), down)
        # Observe before Qt Quick delivers to buttons/Flickables. Never grab
        # or accept: scrolling, pinching and the backplot keep their gestures.
        return False
