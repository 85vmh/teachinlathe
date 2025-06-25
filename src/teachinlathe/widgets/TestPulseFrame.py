from PyQt5.QtWidgets import QFrame, QApplication
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QPropertyAnimation, pyqtProperty, QEasingCurve, Qt, QTimer
import sys


class PulsingFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("feedFrame")
        self.setFixedSize(200, 100)

        self._pulseColor = QColor(0, 0, 0)
        self._borderWidth = 1

        self.anim = QPropertyAnimation(self, b"pulseColor")
        self.anim.setDuration(500)
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.InOutSine)
        self.anim.setStartValue(QColor(0, 0, 0))  # black
        self.anim.setEndValue(QColor(255, 140, 0))  # orange
        self.anim.valueChanged.connect(self.updateStyle)
        self.anim.start()

    def getPulseColor(self):
        return self._pulseColor

    def setPulseColor(self, color):
        self._pulseColor = color
        self.updateStyle(color)

    pulseColor = pyqtProperty(QColor, fget=getPulseColor, fset=setPulseColor)

    def updateStyle(self, color):
        border_width = int(1 + 5 * (color.red() / 255))  # Pulse from 1px to 3px based on red intensity
        self.setStyleSheet(f"""
            QFrame#feedFrame {{
                background-color: rgb(230, 230, 230);
                border: {border_width}px solid {color.name()};
                border-radius: 8px;
            }}
        """)


def main():
    app = QApplication(sys.argv)
    frame = PulsingFrame()
    frame.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
