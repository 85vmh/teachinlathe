"""ViewModel behind the not-ready splash and the machine settings screen.

Both screens show the same four facts about the machine - E-stop, power, and
whether each axis is homed - and offer the same row of LinuxCNC diagnostic
tools, so one ViewModel serves both.

The ``*Ok`` properties say whether a state is *good*, not whether a lamp is
lit: the .ui lit its LEDs when something was wrong, and the QML keeps that by
showing the warning colour when ``...Ok`` is false.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.repositories.machine_repository import machine_repository
from teachinlathe.repositories.status_repository import status_repository
from teachinlathe.repositories.tools_repository import tools_repository

log = logging.getLogger(__name__)


class MachineViewModel(QObject):
    stateChanged = pyqtSignal()

    def __init__(self, parent: Optional[QObject] = None,
                 machine=None, status=None, tools=None) -> None:
        super().__init__(parent)
        self._machine = machine_repository() if machine is None else machine
        self._status = status_repository() if status is None else status
        self._tools = tools_repository() if tools is None else tools

        for channel in ('task_state', 'estop', 'enabled', 'homed'):
            try:
                getattr(self._status, channel).notify(self._onStateChanged)
            except AttributeError:
                log.debug("status has no %s channel", channel)

    def _onStateChanged(self, *_args) -> None:
        self.stateChanged.emit()

    # -- what the screens show --------------------------------------------

    @pyqtProperty(bool, notify=stateChanged)
    def estopOk(self):
        """True when the E-stop is released."""
        return not self._machine.is_estopped

    @pyqtProperty(str, notify=stateChanged)
    def estopText(self):
        return "E-Stop Free" if self.estopOk else "E-Stop Button Pressed"

    @pyqtProperty(bool, notify=stateChanged)
    def powerOk(self):
        """True when the machine is on."""
        return self._machine.is_on

    @pyqtProperty(str, notify=stateChanged)
    def powerText(self):
        return "NC Enabled" if self.powerOk else "NC not Enabled"

    @pyqtProperty(bool, notify=stateChanged)
    def xHomed(self):
        return self._machine.is_axis_homed('x')

    @pyqtProperty(str, notify=stateChanged)
    def xHomedText(self):
        return "X axis homed" if self.xHomed else "X axis NOT homed"

    @pyqtProperty(bool, notify=stateChanged)
    def zHomed(self):
        return self._machine.is_axis_homed('z')

    @pyqtProperty(str, notify=stateChanged)
    def zHomedText(self):
        return "Z axis homed" if self.zHomed else "Z axis NOT homed"

    @pyqtProperty(bool, notify=stateChanged)
    def allHomed(self):
        return self._machine.all_homed

    @pyqtProperty(bool, notify=stateChanged)
    def machineReady(self):
        """Whether the machine can be worked with.

        The rule the .ui's stacked widget switched on: out of E-stop, powered,
        and every axis homed.
        """
        return self.estopOk and self.powerOk and self.xHomed and self.zHomed

    @pyqtProperty(bool, notify=stateChanged)
    def canHome(self):
        return self._machine.can_home()[0]

    @pyqtProperty(str, notify=stateChanged)
    def homeDisabledReason(self):
        return self._machine.can_home()[1]

    @pyqtProperty(bool, notify=stateChanged)
    def canPowerOn(self):
        return self._machine.can_power_on()[0]

    @pyqtProperty(str, notify=stateChanged)
    def powerDisabledReason(self):
        return self._machine.can_power_on()[1]

    # -- what the screens do ----------------------------------------------

    @pyqtSlot()
    def toggleEstop(self):
        self._machine.toggle_estop()

    @pyqtSlot()
    def togglePower(self):
        if not self._machine.is_on and not self.canPowerOn:
            log.warning("refusing to power on: %s", self.powerDisabledReason)
            return
        self._machine.toggle_power()

    @pyqtSlot(str)
    def homeAxis(self, axis):
        self._machine.home_axis(str(axis))

    @pyqtSlot()
    def homeAll(self):
        self._machine.home_all()

    # -- the diagnostic tools ---------------------------------------------

    @pyqtProperty('QVariantList', constant=True)
    def tools(self):
        """The launchable tools, as QML needs them: a key and a label."""
        return [{"key": tool.key, "label": tool.label} for tool in self._tools.tools]

    @pyqtSlot(str, result=bool)
    def launchTool(self, key):
        return self._tools.launch(str(key))

    @pyqtSlot(str, result=bool)
    def canLaunchTool(self, key):
        return self._tools.can_launch(str(key))[0]
