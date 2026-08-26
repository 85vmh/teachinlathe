from __future__ import annotations

import os

from PyQt5.QtCore import QObject, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt5.QtQml import QQmlApplicationEngine

from qtpyvcp import hal


class DevPanelViewModel(QObject):
    cycleStartLedChanged = pyqtSignal()

    COMPONENT_NAME = "TeachInLatheDevPanel"

    BIT_OUTPUTS = (
        "button.cycle-start",
        "button.cycle-stop",
        "button.power-on",
        "button.power-off",
        "button.single-block",
        "button.estop",
        "jog.x-clockwise",
        "jog.x-counterclockwise",
        "jog.z-clockwise",
        "jog.z-counterclockwise",
        "joystick.x-plus",
        "joystick.x-minus",
        "joystick.z-plus",
        "joystick.z-minus",
        "joystick.neutral",
        "joystick.rapid",
        "spindle.cover-opened",
        "spindle.is-first-gear",
        "spindle.switch-rev",
        "spindle.switch-neutral",
        "spindle.switch-fwd",
    )

    FLOAT_OUTPUTS = (
        "override.feed",
        "override.spindle",
        "jog.increment",
    )

    BIT_INPUTS = (
        "button.cycle-start-led",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pins = {}
        self._cycle_start_led = False
        self._build_hal_component()

    @pyqtProperty(bool, notify=cycleStartLedChanged)
    def cycleStartLed(self):
        return self._cycle_start_led

    @pyqtSlot(str, bool)
    def setBit(self, pin_name, value):
        pin = self._pins.get(str(pin_name))
        if pin is not None:
            pin.value = bool(value)

    @pyqtSlot(str, float)
    def setFloat(self, pin_name, value):
        pin = self._pins.get(str(pin_name))
        if pin is not None:
            pin.value = float(value)

    @pyqtSlot(str)
    def setSpindleLever(self, state):
        state = str(state or "neutral")
        mapping = {
            "reverse": "spindle.switch-rev",
            "neutral": "spindle.switch-neutral",
            "forward": "spindle.switch-fwd",
        }
        selected = mapping.get(state, "spindle.switch-neutral")
        for pin_name in mapping.values():
            self.setBit(pin_name, pin_name == selected)

    def _build_hal_component(self):
        self.comp = hal.component(self.COMPONENT_NAME)
        for pin_name in self.BIT_OUTPUTS:
            self.comp.addPin(pin_name, "bit", "out")
        for pin_name in self.FLOAT_OUTPUTS:
            self.comp.addPin(pin_name, "float", "out")
        for pin_name in self.BIT_INPUTS:
            self.comp.addPin(pin_name, "bit", "in")
        self.comp.ready()

        for pin_name in self.BIT_OUTPUTS:
            pin = self.comp.getPin(pin_name)
            pin.value = False
            self._pins[pin_name] = pin
        for pin_name in self.FLOAT_OUTPUTS:
            pin = self.comp.getPin(pin_name)
            pin.value = 0.0
            self._pins[pin_name] = pin

        self.setFloat("override.feed", 1.0)
        self.setFloat("override.spindle", 1.0)
        self.setSpindleLever("neutral")

        try:
            self._cycle_start_led = bool(self.comp.getPin("button.cycle-start-led").value)
            self.comp.addListener("button.cycle-start-led", self._on_cycle_start_led_changed)
        except Exception:
            self._cycle_start_led = False

    def _on_cycle_start_led_changed(self, value=False):
        active = bool(value)
        if active == self._cycle_start_led:
            return
        self._cycle_start_led = active
        self.cycleStartLedChanged.emit()


class DevPanelWindow(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._view_model = DevPanelViewModel(self)
        self._root_window = None

        qml_dir = os.path.join(os.path.dirname(__file__), "widgets", "dev_panel_qml")
        self._engine = QQmlApplicationEngine(self)
        self._engine.rootContext().setContextProperty("devPanelViewModel", self._view_model)
        self._engine.load(QUrl.fromLocalFile(os.path.join(qml_dir, "DevPanelWindow.qml")))

        root_objects = self._engine.rootObjects()
        if root_objects:
            self._root_window = root_objects[0]

    def show(self):
        if self._root_window is not None:
            self._root_window.show()

    def hide(self):
        if self._root_window is not None:
            self._root_window.hide()

    def raise_(self):
        if self._root_window is not None and hasattr(self._root_window, "raise_"):
            self._root_window.raise_()
