from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty, QObject, QAbstractAnimation
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QFrame, QGraphicsDropShadowEffect


class FrameAnimator(QObject):
    def __init__(self, frame: QFrame):
        super().__init__()
        self.frame = frame

        # Setează stilul static de bază o singură dată
        self.frame.setStyleSheet("""
            QFrame#feedFrame {
                background-color: rgb(230, 230, 230);
                border: 1px solid rgb(10, 10, 10);
                border-radius: 8px;
            }
        """)

        self.shadow = None
        self._color = QColor(0, 0, 0, 0)

        self.anim = QPropertyAnimation(self, b"color")
        self.anim.setDuration(300)
        self.anim.setStartValue(QColor(0, 0, 0, 0))  # Transparent glow
        self.anim.setEndValue(QColor(255, 140, 0, 255))  # Semi-transparent orange
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.finished.connect(self.on_anim_finished)
        self.anim.valueChanged.connect(self.update_style)
        self.forward = True

    def startAnimation(self):
        self._ensure_shadow()
        self.anim.setDirection(QAbstractAnimation.Forward)
        self.forward = True
        self.anim.start()

    def stopAnimation(self):
        self.anim.stop()
        if self.shadow is not None:
            self.shadow.setColor(QColor(0, 0, 0, 0))  # Glow off
        self.frame.setGraphicsEffect(None)
        self.shadow = None

    def _ensure_shadow(self):
        if self.shadow is not None and self.frame.graphicsEffect() is self.shadow:
            return
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setOffset(0, 0)
        self.shadow.setBlurRadius(50)
        self.shadow.setColor(self._color)
        self.frame.setGraphicsEffect(self.shadow)

    def on_anim_finished(self):
        self.forward = not self.forward
        self.anim.setDirection(QAbstractAnimation.Forward if self.forward else QAbstractAnimation.Backward)
        self.anim.start()

    def getColor(self):
        return self._color

    def setColor(self, color):
        self._color = color

    color = pyqtProperty(QColor, fget=getColor, fset=setColor)

    def update_style(self, color: QColor):
        self._color = color
        if self.shadow is not None:
            self.shadow.setColor(color)  # Glow only
