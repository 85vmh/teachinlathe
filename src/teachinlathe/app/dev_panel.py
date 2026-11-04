"""The dev panel: the machine's operator controls, for a machine that has none.

On the lathe the E-stop, the power button, the apron's selectors, handwheels
and joystick are wired to the Mesa input card, and mesa-io.hal nets each input
to an ``in.*`` signal. On the development machine this panel stands in for
them: it is its own process with its own HAL component, ``DevPanel``, whose
pins are those inputs, and the simulated config nets them to the same
``in.*`` signals. Everything downstream - program_state, weiler_manual_mode,
weiler_spindle, the post-GUI file that reaches TeachInLathe - is then wired
the way it is on the machine.

Started from the simulated config's HAL, before the GUI::

    loadusr -Wn DevPanel python3 -m teachinlathe.app.dev_panel
"""

from __future__ import annotations

import os
import signal
import sys

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance

from teachinlathe.core.hal_repository import hal_component
from teachinlathe.app import APP_QML_IMPORT_DIR
from teachinlathe.ui import QML_IMPORT_DIR

COMPONENT_NAME = "DevPanel"

#: Quadrature counts per handwheel detent: the encoders run in x4 mode.
COUNTS_PER_DETENT = 4

#: The jog increment selector's positions, as the two bits of its switch
#: (axes-mpg.hal decodes them with mux4: sel0 = a, sel1 = b).
JOG_INCREMENTS = {
    "off": (False, False),
    "0.001": (True, False),
    "0.01": (False, True),
    "0.1": (True, True),
}

SPINDLE_LEVER = {
    "M3": "spindle-fwd",
    "stop": "spindle-neutral",
    "M4": "spindle-rev",
}

JOYSTICK_DIRECTIONS = ("x-plus", "x-minus", "z-plus", "z-minus")

#: The arrow keys, held down while the panel has the keyboard: the joystick
#: that way, as the panel lays it out - X- up, X+ down, Z- left, Z+ right.
ARROW_KEYS = {
    Qt.Key.Key_Up: "x-minus",
    Qt.Key.Key_Down: "x-plus",
    Qt.Key.Key_Left: "z-minus",
    Qt.Key.Key_Right: "z-plus",
}


class DevPanelViewModel(QObject):
    """The panel's controls, each written straight to its HAL pin."""

    estopChanged = pyqtSignal()
    powerOnChanged = pyqtSignal()
    ncReadyChanged = pyqtSignal()
    cycleStartLedChanged = pyqtSignal()
    spindleLeverChanged = pyqtSignal()
    jogIncrementChanged = pyqtSignal()
    joystickChanged = pyqtSignal()
    switchesChanged = pyqtSignal()

    BIT_OUTPUTS = (
        "estop-free",
        "enable-drives",
        "home-all",
        "cycle-start",
        "cycle-abort",
        "chuck-cover",
        "spindle-gear1",
        "spindle-fwd",
        "spindle-neutral",
        "spindle-rev",
        "jog-increment-a",
        "jog-increment-b",
        "joystick-neutral",
        "joystick-x-plus",
        "joystick-x-minus",
        "joystick-z-plus",
        "joystick-z-minus",
        "joystick-rapid",
    )

    S32_OUTPUTS = (
        "feed-override",
        "spindle-override",
        "mpg-x-counts",
        "mpg-z-counts",
    )

    BIT_INPUTS = (
        "nc-ready",
        "cycle-start-led",
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._estop = False
        self._power_on = False
        self._spindle_lever = "stop"
        self._jog_increment = "0.1"
        self._joystick = ""
        self._rapid = False
        self._chuck_cover = False
        self._first_gear = False

        self.comp = hal_component(COMPONENT_NAME)
        for name in self.BIT_OUTPUTS:
            self.comp.addPin(name, "bit", "out")
        for name in self.S32_OUTPUTS:
            self.comp.addPin(name, "s32", "out")
        for name in self.BIT_INPUTS:
            self.comp.addPin(name, "bit", "in")
        self.comp.ready()

        self.comp.addListener("nc-ready", lambda _value: self.ncReadyChanged.emit())
        self.comp.addListener("cycle-start-led", lambda _value: self.cycleStartLedChanged.emit())

        self._set("estop-free", True)
        self._set("feed-override", 100)
        self._set("spindle-override", 100)
        self._write_spindle_lever()
        self._write_jog_increment()
        self._write_joystick()

    def _set(self, name, value):
        self.comp.getPin(name).value = value

    def _get(self, name):
        return self.comp.getPin(name).value

    # ── machine ────────────────────────────────────────────────────────────

    @pyqtProperty(bool, notify=estopChanged)
    def estop(self):
        return self._estop

    @pyqtSlot(bool)
    def setEstop(self, engaged):
        if engaged == self._estop:
            return
        self._estop = engaged
        self._set("estop-free", not engaged)
        # The E-stop chain drops the main contactor: power has to be switched
        # on again once it is released.
        if engaged:
            self.setPowerOn(False)
        self.estopChanged.emit()

    @pyqtProperty(bool, notify=powerOnChanged)
    def powerOn(self):
        return self._power_on

    @pyqtSlot(bool)
    def setPowerOn(self, on):
        # The contactor only latches through the NC-ready relay, and never
        # with the E-stop pressed.
        if on and (self._estop or not self.ncReady):
            on = False
        if on == self._power_on:
            self.powerOnChanged.emit()  # puts a refused toggle back
            return
        self._power_on = on
        self._set("enable-drives", on)
        self.powerOnChanged.emit()

    @pyqtProperty(bool, notify=ncReadyChanged)
    def ncReady(self):
        return bool(self._get("nc-ready"))

    @pyqtSlot(bool)
    def setHomeAll(self, pressed):
        self._set("home-all", pressed)

    @pyqtProperty(bool, notify=switchesChanged)
    def chuckCoverOpen(self):
        return self._chuck_cover

    @pyqtSlot(bool)
    def setChuckCoverOpen(self, opened):
        self._chuck_cover = opened
        self._set("chuck-cover", opened)
        self.switchesChanged.emit()

    @pyqtProperty(bool, notify=switchesChanged)
    def firstGear(self):
        return self._first_gear

    @pyqtSlot(bool)
    def setFirstGear(self, first):
        self._first_gear = first
        self._set("spindle-gear1", first)
        self.switchesChanged.emit()

    # ── apron ──────────────────────────────────────────────────────────────

    @pyqtSlot(int)
    def setFeedOverride(self, percent):
        self._set("feed-override", int(percent))

    @pyqtSlot(int)
    def setSpindleOverride(self, percent):
        self._set("spindle-override", int(percent))

    @pyqtProperty(str, notify=spindleLeverChanged)
    def spindleLever(self):
        return self._spindle_lever

    @pyqtSlot(str)
    def setSpindleLever(self, position):
        if position not in SPINDLE_LEVER or position == self._spindle_lever:
            return
        self._spindle_lever = position
        self._write_spindle_lever()
        self.spindleLeverChanged.emit()

    def _write_spindle_lever(self):
        selected = SPINDLE_LEVER[self._spindle_lever]
        for pin in SPINDLE_LEVER.values():
            self._set(pin, pin == selected)

    @pyqtProperty(str, notify=jogIncrementChanged)
    def jogIncrement(self):
        return self._jog_increment

    @pyqtSlot(str)
    def setJogIncrement(self, increment):
        if increment not in JOG_INCREMENTS or increment == self._jog_increment:
            return
        self._jog_increment = increment
        self._write_jog_increment()
        self.jogIncrementChanged.emit()

    def _write_jog_increment(self):
        a, b = JOG_INCREMENTS[self._jog_increment]
        self._set("jog-increment-a", a)
        self._set("jog-increment-b", b)

    @pyqtSlot(str, int)
    def turnHandwheel(self, axis, detents):
        """Turn the X or Z handwheel by *detents* clicks (negative: the other way).
        Counted down for a clockwise turn: the HAL's scales are the machine's,
        whose encoders count that way, so the axis moves the way the wheel on
        the screen turns."""
        name = "mpg-{}-counts".format(axis)
        self._set(name, int(self._get(name)) - int(detents) * COUNTS_PER_DETENT)

    @pyqtSlot()
    def pressCycleStart(self):
        self._set("cycle-start", True)

    @pyqtSlot()
    def releaseCycleStart(self):
        self._set("cycle-start", False)

    @pyqtSlot()
    def pressCycleAbort(self):
        self._set("cycle-abort", True)

    @pyqtSlot()
    def releaseCycleAbort(self):
        self._set("cycle-abort", False)

    @pyqtProperty(bool, notify=cycleStartLedChanged)
    def cycleStartLed(self):
        return bool(self._get("cycle-start-led"))

    # ── joystick ───────────────────────────────────────────────────────────
    # A direction stays where it is put, like the lever does on the machine,
    # until it is clicked again. Rapid is the button on top of the lever: held
    # down, never latched, and letting go of it brings the lever back to
    # neutral as well.

    @pyqtProperty(str, notify=joystickChanged)
    def joystickDirection(self):
        return self._joystick

    @pyqtProperty(bool, notify=joystickChanged)
    def joystickRapid(self):
        return self._rapid

    @pyqtSlot(str)
    def toggleJoystick(self, direction):
        if direction not in JOYSTICK_DIRECTIONS:
            return
        if self._joystick == direction:
            self._joystick = ""
        elif not self._joystick:
            self._joystick = direction
        else:
            return  # the lever is already held in another direction
        self._write_joystick()

    def holdJoystick(self, direction):
        """The lever pushed ``direction`` while a key is held: as clicking
        it, unless it is already held some way. Whether it was."""
        if direction not in JOYSTICK_DIRECTIONS or self._joystick:
            return False
        self._joystick = direction
        self._write_joystick()
        return True

    def releaseJoystick(self, direction):
        """The key let go: back to neutral, if the lever is still that way."""
        if self._joystick == direction:
            self._joystick = ""
            self._write_joystick()

    @pyqtSlot(bool)
    def setJoystickRapid(self, pressed):
        if pressed == self._rapid:
            return
        self._rapid = pressed
        if not pressed:
            self._joystick = ""
        self._write_joystick()

    def _write_joystick(self):
        for direction in JOYSTICK_DIRECTIONS:
            self._set("joystick-" + direction, self._joystick == direction)
        self._set("joystick-neutral", not self._joystick)
        self._set("joystick-rapid", self._rapid)
        self.joystickChanged.emit()


class ArrowKeyJog(QObject):
    """The arrow keys as the joystick, for as long as each is held: an
    application-wide filter, so they work whichever of the panel's controls
    has the focus. The repeats of a held key are swallowed; and the panel
    losing the keyboard lets go of a key held, whose release it would not
    see."""

    def __init__(self, view_model, parent=None):
        super().__init__(parent)
        self._view_model = view_model
        self._held = None

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.ApplicationDeactivate:
            self._let_go()
            return False
        if event.type() not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            return False
        direction = ARROW_KEYS.get(event.key())
        if direction is None:
            return False
        if not event.isAutoRepeat():
            if event.type() == QEvent.Type.KeyPress:
                # one at a time, as the lever: a second key held is ignored
                if self._held is None and self._view_model.holdJoystick(direction):
                    self._held = direction
            elif direction == self._held:
                self._let_go()
        return True

    def _let_go(self):
        if self._held is not None:
            self._view_model.releaseJoystick(self._held)
            self._held = None


def main(argv=None):
    app = QGuiApplication(sys.argv if argv is None else argv)
    app.setApplicationName("TeachInLathe Dev Panel")

    view_model = DevPanelViewModel()
    arrow_keys = ArrowKeyJog(view_model)
    app.installEventFilter(arrow_keys)

    # Creating the HAL component installed LinuxCNC's SIGTERM handler, which
    # raises KeyboardInterrupt under the event loop. halcmd stops userspace
    # components with SIGTERM at shutdown: quit the loop instead, so the
    # component is unloaded on the way out (hal_repository's atexit).
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_args: app.quit())
    wake = QTimer()
    wake.timeout.connect(lambda: None)
    wake.start(200)

    qmlRegisterSingletonInstance("TeachInLathe", 1, 0, "DevPanelViewModel", view_model)
    engine = QQmlApplicationEngine()
    engine.addImportPath(QML_IMPORT_DIR)
    engine.addImportPath(APP_QML_IMPORT_DIR)
    engine.load(QUrl.fromLocalFile(os.path.join(APP_QML_IMPORT_DIR, "dev_panel_qml", "DevPanelWindow.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
