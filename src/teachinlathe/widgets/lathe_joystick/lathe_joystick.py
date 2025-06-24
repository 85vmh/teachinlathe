from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer
from enum import Enum
import sys
import math

from PyQt5.uic.properties import QtCore


class JoystickState(Enum):
    NEUTRAL = 0
    FEEDING_X_NEG = 1
    FEEDING_X_POS = 2
    FEEDING_Z_NEG = 3
    FEEDING_Z_POS = 4


ACTIVE_COLOR = QColor(0, 150, 0)  # Bright green


class LatheJoystickWidget(QWidget):
    WIDTH = 250
    HEIGHT = 230
    RING_RADII = [34, 28, 22]
    JOYSTICK_RADIUS = 18
    ARROW_START_RADIUS = RING_RADII[0]
    ARROW_TOTAL_LENGTH = 70
    ARROW_HEAD_SIZE = 6
    LINE_THICKNESS = 1.2
    LABEL_WIDTH = 40
    LABEL_HEIGHT = 25
    LABEL_DISTANCE_FROM_TIP = 23
    LABEL_RADIUS = 5

    angleFeedToggled = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        super(LatheJoystickWidget, self).__init__(parent)
        self.setFixedSize(self.WIDTH, self.HEIGHT)

        self.allowsTouchInteraction = True
        self.joystickState = JoystickState.NEUTRAL
        self.currentRotation = 0
        self.rotationTarget = 0
        self.rotation_active = False
        self.rotation_step = 3
        self.animTimer = QTimer()
        self.animTimer.timeout.connect(self.animateRotation)

    def setTouchEnabled(self, enabled: bool):
        self.allowsTouchInteraction = enabled

    def resetAngle(self):
        self.currentRotation = 0
        self.rotationTarget = 0
        self.angleFeedToggled.emit(False)
        self.animTimer.start(16)

    def setJoystickState(self, state: JoystickState):
        self.joystickState = state
        self.update()

    def mousePressEvent(self, event):
        if self.allowsTouchInteraction and not self.rotation_active:
            self.rotation_active = True
            self.rotationTarget = 0 if self.currentRotation > 0 else 45
            self.angleFeedToggled.emit(self.rotationTarget == 45)
            self.animTimer.start(16)

    def animateRotation(self):
        if self.currentRotation < self.rotationTarget:
            self.currentRotation += self.rotation_step
            if self.currentRotation >= self.rotationTarget:
                self.currentRotation = self.rotationTarget
                self.animTimer.stop()
                self.rotation_active = False
        elif self.currentRotation > self.rotationTarget:
            self.currentRotation -= self.rotation_step
            if self.currentRotation <= self.rotationTarget:
                self.currentRotation = self.rotationTarget
                self.animTimer.stop()
                self.rotation_active = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()

        # Determine the angle of joystick direction
        angle_deg = {
            JoystickState.FEEDING_Z_NEG: 180,
            JoystickState.FEEDING_Z_POS: 0,
            JoystickState.FEEDING_X_NEG: -90,
            JoystickState.FEEDING_X_POS: 90
        }.get(self.joystickState, None)

        angle_rad = math.radians(angle_deg) if angle_deg is not None else None

        # Draw the outer ring (static)
        painter.setPen(QPen(Qt.black, self.LINE_THICKNESS))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, self.RING_RADII[0], self.RING_RADII[0])

        if angle_rad is not None:
            for r in self.RING_RADII[1:]:
                offset = self.RING_RADII[0] - r
                dx = offset * math.cos(angle_rad)
                dy = offset * math.sin(angle_rad)
                painter.setPen(QPen(Qt.black, self.LINE_THICKNESS))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(center + QPointF(dx, dy), r, r)

            r = self.JOYSTICK_RADIUS
            offset = self.RING_RADII[0] - r
            dx = offset * math.cos(angle_rad)
            dy = offset * math.sin(angle_rad)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            painter.drawEllipse(center + QPointF(dx, dy), r, r)
        else:
            for r in self.RING_RADII[1:]:
                painter.setPen(QPen(Qt.black, self.LINE_THICKNESS))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(center, r, r)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            painter.drawEllipse(center, self.JOYSTICK_RADIUS, self.JOYSTICK_RADIUS)

        # Draw rotated arrows
        def draw_arrow(cx, cy, angle_deg, is_active=False):
            angle_rad_local = math.radians(angle_deg + self.currentRotation)
            x_start = cx + self.ARROW_START_RADIUS * math.cos(angle_rad_local)
            y_start = cy + self.ARROW_START_RADIUS * math.sin(angle_rad_local)
            x_line_end = cx + (self.ARROW_TOTAL_LENGTH - 10) * math.cos(angle_rad_local)
            y_line_end = cy + (self.ARROW_TOTAL_LENGTH - 10) * math.sin(angle_rad_local)
            x_tip = cx + self.ARROW_TOTAL_LENGTH * math.cos(angle_rad_local)
            y_tip = cy + self.ARROW_TOTAL_LENGTH * math.sin(angle_rad_local)

            color = ACTIVE_COLOR if is_active else Qt.black
            painter.setPen(QPen(color, self.LINE_THICKNESS))
            painter.drawLine(QPointF(x_start, y_start), QPointF(x_line_end, y_line_end))

            back_offset = self.ARROW_HEAD_SIZE * 1.5
            base_width = self.ARROW_HEAD_SIZE * 2.5
            perp_angle = angle_rad_local + math.pi / 2
            tip = QPointF(x_tip, y_tip)
            base_center = QPointF(
                x_tip - back_offset * math.cos(angle_rad_local),
                y_tip - back_offset * math.sin(angle_rad_local)
            )
            left = QPointF(
                base_center.x() + base_width / 2 * math.cos(perp_angle),
                base_center.y() + base_width / 2 * math.sin(perp_angle)
            )
            right = QPointF(
                base_center.x() - base_width / 2 * math.cos(perp_angle),
                base_center.y() - base_width / 2 * math.sin(perp_angle)
            )
            arrow = QPolygonF([tip, left, right])
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(arrow)

        draw_arrow(center.x(), center.y(), -90, self.joystickState == JoystickState.FEEDING_X_NEG)
        draw_arrow(center.x(), center.y(), 90, self.joystickState == JoystickState.FEEDING_X_POS)
        draw_arrow(center.x(), center.y(), 180, self.joystickState == JoystickState.FEEDING_Z_NEG)
        draw_arrow(center.x(), center.y(), 0, self.joystickState == JoystickState.FEEDING_Z_POS)

        # Draw labels
        def draw_label(angle_deg, text, is_active=False):
            angle_rad_local = math.radians(angle_deg + self.currentRotation)
            x_tip = center.x() + self.ARROW_TOTAL_LENGTH * math.cos(angle_rad_local)
            y_tip = center.y() + self.ARROW_TOTAL_LENGTH * math.sin(angle_rad_local)
            x = x_tip + self.LABEL_DISTANCE_FROM_TIP * math.cos(angle_rad_local)
            y = y_tip + self.LABEL_DISTANCE_FROM_TIP * math.sin(angle_rad_local)

            rect = QRectF(x - self.LABEL_WIDTH / 2, y - self.LABEL_HEIGHT / 2,
                          self.LABEL_WIDTH, self.LABEL_HEIGHT)

            background_color = ACTIVE_COLOR if is_active else QColor(50, 50, 50)
            painter.setBrush(background_color)
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, self.LABEL_RADIUS, self.LABEL_RADIUS)

            painter.setPen(Qt.white)
            painter.drawText(rect, Qt.AlignCenter, text)

        draw_label(-90, "X-", self.joystickState == JoystickState.FEEDING_X_NEG)
        draw_label(90, "X+", self.joystickState == JoystickState.FEEDING_X_POS)
        draw_label(180, "Z-", self.joystickState == JoystickState.FEEDING_Z_NEG)
        draw_label(0, "Z+", self.joystickState == JoystickState.FEEDING_Z_POS)


def main():
    app = QApplication(sys.argv)
    widget = LatheJoystickWidget()
    widget.setJoystickState(JoystickState.NEUTRAL)
    widget.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
