import os

import linuxcnc
from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from qtpyvcp.actions import program_actions
from qtpyvcp.actions.machine_actions import issue_mdi
from qtpyvcp.plugins import getPlugin

from teachinlathe.lathe_hal_component import TeachInLatheComponent


STATUS = getPlugin('status')
STAT = STATUS.stat
CMD = linuxcnc.command()


def _channel_value(name, default=None):
    channel = getattr(STATUS, name, None)
    if channel is None:
        return default
    return getattr(channel, 'value', default)


def _machine_max_linear_velocity():
    ini_path = os.getenv('INI_FILE_NAME')
    if not ini_path:
        return 0.0
    ini_file = linuxcnc.ini(ini_path)
    value = ini_file.find('TRAJ', 'MAX_LINEAR_VELOCITY')
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class ProgramButtonState(QObject):
    textChanged = pyqtSignal(str)
    enabledChanged = pyqtSignal(bool)
    activeChanged = pyqtSignal(bool)
    checkedChanged = pyqtSignal(bool)
    tooltipChanged = pyqtSignal(str)

    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self._text = text
        self._enabled = False
        self._active = False
        self._checked = False
        self._tooltip = ''

    @pyqtProperty(str, notify=textChanged)
    def text(self):
        return self._text

    @pyqtProperty(bool, notify=enabledChanged)
    def enabled(self):
        return self._enabled

    @pyqtProperty(bool, notify=activeChanged)
    def active(self):
        return self._active

    @pyqtProperty(bool, notify=checkedChanged)
    def checked(self):
        return self._checked

    @pyqtProperty(str, notify=tooltipChanged)
    def tooltip(self):
        return self._tooltip

    def update(self, *, text=None, enabled=None, active=None, checked=None, tooltip=None):
        if text is not None and text != self._text:
            self._text = text
            self.textChanged.emit(text)
        if enabled is not None and enabled != self._enabled:
            self._enabled = enabled
            self.enabledChanged.emit(enabled)
        if active is not None and active != self._active:
            self._active = active
            self.activeChanged.emit(active)
        if checked is not None and checked != self._checked:
            self._checked = checked
            self.checkedChanged.emit(checked)
        if tooltip is not None and tooltip != self._tooltip:
            self._tooltip = tooltip
            self.tooltipChanged.emit(tooltip)


class ProgramsActionSource(QObject):
    stateChanged = pyqtSignal()
    abortTriggered = pyqtSignal()
    cycleStartObserved = pyqtSignal()

    def __init__(self, runtime_store, parent=None):
        super().__init__(parent)
        self._runtime_store = runtime_store
        self._is_running = False
        self._is_active = False
        self._cycle_start_led_active = False
        self._start = ProgramButtonState('Start Program', self)
        self._stop = ProgramButtonState('Stop Program', self)
        self._pause_resume = ProgramButtonState('Pause Program', self)
        self._cycle_start_combined = ProgramButtonState('Cycle\nStart', self)
        self._optional_stop = ProgramButtonState('Break on M1', self)
        self._block_delete = ProgramButtonState('Skip "/" Blocks', self)
        self._mdi = ProgramButtonState('Run MDI', self)
        self._maximum_rapid_velocity = _machine_max_linear_velocity() * 60.0

        runtime_store.snapshotChanged.connect(lambda _snapshot: self.refresh())
        self._bind_status_updates()
        self._bind_hal_updates()
        self._reset_program_option_defaults()
        self.refresh()

    @pyqtProperty(bool, notify=stateChanged)
    def isRunning(self):
        return self._is_running

    @pyqtProperty(bool, notify=stateChanged)
    def isActive(self):
        return self._is_active

    @pyqtProperty(bool, notify=stateChanged)
    def cycleStartLedActive(self):
        return self._cycle_start_led_active

    @pyqtProperty(QObject, constant=True)
    def startAction(self):
        return self._start

    @pyqtProperty(QObject, constant=True)
    def stopAction(self):
        return self._stop

    @pyqtProperty(QObject, constant=True)
    def pauseResumeAction(self):
        return self._pause_resume

    @pyqtProperty(QObject, constant=True)
    def cycleStartAction(self):
        return self._cycle_start_combined

    @pyqtProperty(QObject, constant=True)
    def optionalStopAction(self):
        return self._optional_stop

    @pyqtProperty(QObject, constant=True)
    def blockDeleteAction(self):
        return self._block_delete

    @pyqtProperty(QObject, constant=True)
    def mdiAction(self):
        return self._mdi

    @pyqtProperty(int, notify=stateChanged)
    def rapidOverridePercent(self):
        return self._percent(getattr(self._runtime_store.snapshot, 'rapidrate', 1.0))

    @pyqtProperty(float, notify=stateChanged)
    def maximumRapidVelocity(self):
        return self._maximum_rapid_velocity

    def _bind_status_updates(self):
        channels = (
            getattr(STATUS, 'estop', None),
            getattr(STATUS, 'enabled', None),
            getattr(STATUS, 'all_axes_homed', None),
            getattr(STATUS, 'interp_state', None),
            getattr(STATUS, 'file', None),
            getattr(STATUS, 'state', None),
            getattr(STATUS, 'paused', None),
            getattr(STATUS, 'task_state', None),
            getattr(STATUS, 'block_delete', None),
            getattr(STATUS, 'optional_stop', None),
            getattr(STATUS, 'homed', None),
            getattr(STATUS, 'rapidrate', None),
        )
        for channel in channels:
            if channel is None:
                continue
            try:
                channel.onValueChanged(lambda *_args: self.refresh())
            except Exception:
                try:
                    channel.notify(lambda *_args: self.refresh())
                except Exception:
                    pass

    def _reset_program_option_defaults(self):
        try:
            CMD.set_optional_stop(False)
            CMD.set_block_delete(False)
        except Exception as e:
            print(f"[ProgramsActionSource] failed to reset optional stop/block delete defaults: {e}")

    def _bind_hal_updates(self):
        try:
            component = TeachInLatheComponent()
            pin = component.comp.getPin(TeachInLatheComponent.PinCycleStartLed)
            self._cycle_start_led_active = bool(pin.value)
            component.comp.addListener(TeachInLatheComponent.PinCycleStartLed, self._on_cycle_start_led_changed)
        except Exception:
            self._cycle_start_led_active = False

    def _on_cycle_start_led_changed(self, value):
        active = bool(value)
        if active == self._cycle_start_led_active:
            return
        self._cycle_start_led_active = active
        if active:
            self.cycleStartObserved.emit()
        self.stateChanged.emit()

    def refresh(self):
        snapshot = self._runtime_store.poll()
        stat = self._runtime_store.stat
        state = int(_channel_value('state', getattr(stat, 'state', 0)) or 0)
        interp_state = int(_channel_value('interp_state', getattr(stat, 'interp_state', 0)) or 0)
        paused = bool(_channel_value('paused', getattr(stat, 'paused', False)))

        start_enabled, start_tooltip = self._run_state(stat)
        interp_active = interp_state != linuxcnc.INTERP_IDLE
        running = interp_active and not paused
        self._is_running = running
        # "active" = a program is in progress (running OR paused); used to drive
        # the full-screen run view so a pause doesn't look like completion.
        self._is_active = interp_active or paused
        self._start.update(
            enabled=start_enabled,
            active=running,
            checked=running,
            tooltip=start_tooltip,
        )

        stop_enabled, stop_tooltip = self._abort_state(stat)
        self._stop.update(
            enabled=stop_enabled,
            active=stop_enabled,
            checked=stop_enabled,
            tooltip=stop_tooltip,
        )

        pause_enabled, pause_tooltip, pause_text, pause_active = self._pause_resume_state(stat)
        self._pause_resume.update(
            text=pause_text,
            enabled=pause_enabled,
            active=pause_active,
            checked=pause_active,
            tooltip=pause_tooltip,
        )

        # Combined Cycle Start / Pause / Resume action.
        # pauseResume takes priority: once a program is active (running or paused)
        # the button only ever shows Pause or Resume, never Cycle Start.
        if self._pause_resume.enabled and self._pause_resume.active:
            cycle_text, cycle_enabled, cycle_active = 'Feed\nResume', True, False
        elif self._pause_resume.enabled:
            cycle_text, cycle_enabled, cycle_active = 'Feed\nHold', True, True
        elif self._start.enabled:
            cycle_text, cycle_enabled, cycle_active = 'Cycle\nStart', True, False
        else:
            cycle_text, cycle_enabled, cycle_active = 'Cycle\nStart', False, False
        self._cycle_start_combined.update(text=cycle_text, enabled=cycle_enabled, active=cycle_active)

        optional_enabled, optional_tooltip = self._optional_stop_state(stat)
        optional_checked = bool(_channel_value('optional_stop', getattr(stat, 'optional_stop', False)))
        self._optional_stop.update(
            enabled=optional_enabled,
            active=optional_checked,
            checked=optional_checked,
            tooltip=optional_tooltip,
        )

        block_enabled, block_tooltip = self._block_delete_state(stat)
        block_checked = bool(_channel_value('block_delete', getattr(stat, 'block_delete', False)))
        self._block_delete.update(
            enabled=block_enabled,
            active=block_checked,
            checked=block_checked,
            tooltip=block_tooltip,
        )

        mdi_enabled, mdi_tooltip = self._mdi_state(stat)
        self._mdi.update(
            enabled=mdi_enabled,
            active=False,
            checked=False,
            tooltip=mdi_tooltip,
        )
        self.stateChanged.emit()
        return snapshot

    def _run_state(self, stat):
        estop = bool(_channel_value('estop', getattr(stat, 'estop', False)))
        enabled = bool(_channel_value('enabled', getattr(stat, 'enabled', False)))
        paused = bool(_channel_value('paused', getattr(stat, 'paused', False)))
        interp_state = int(_channel_value('interp_state', getattr(stat, 'interp_state', 0)) or 0)
        loaded_file = (_channel_value('file', getattr(stat, 'file', '')) or '')

        if estop:
            return False, "Can't run program when in E-Stop"
        if not enabled:
            return False, "Can't run program when not enabled"
        if not STATUS.allHomed():
            return False, "Can't run program when not homed"
        if not paused and interp_state != linuxcnc.INTERP_IDLE:
            return False, "Can't run program when already running"
        if not loaded_file:
            return False, "Can't run program when no file loaded"
        return True, 'Run program'

    def _abort_state(self, stat):
        state = int(_channel_value('state', getattr(stat, 'state', 0)) or 0)
        interp_state = int(_channel_value('interp_state', getattr(stat, 'interp_state', 0)) or 0)
        if interp_state != linuxcnc.INTERP_IDLE or state in (linuxcnc.RCS_EXEC, linuxcnc.RCS_ERROR):
            return True, ''
        return False, 'Nothing to abort'

    def _pause_resume_state(self, stat):
        state = int(_channel_value('state', getattr(stat, 'state', 0)) or 0)
        interp_state = int(_channel_value('interp_state', getattr(stat, 'interp_state', 0)) or 0)
        paused = bool(_channel_value('paused', getattr(stat, 'paused', False)))
        interp_active = interp_state != linuxcnc.INTERP_IDLE
        if (interp_active or state == linuxcnc.RCS_EXEC) and paused:
            return True, 'Resume program execution', 'Resume Program', True
        if interp_active or state == linuxcnc.RCS_EXEC:
            return True, 'Pause program execution', 'Pause Program', False
        return False, 'No program running to pause', 'Pause Program', False

    def _optional_stop_state(self, stat):
        if int(_channel_value('task_state', getattr(stat, 'task_state', 0)) or 0) == linuxcnc.STATE_ON:
            return True, ''
        return False, 'Machine must be ON to set Opt Stop'

    def _block_delete_state(self, stat):
        if int(_channel_value('task_state', getattr(stat, 'task_state', 0)) or 0) == linuxcnc.STATE_ON:
            return True, ''
        return False, 'Machine must be ON to set Block Del'

    def _mdi_state(self, stat):
        if stat.task_state == linuxcnc.STATE_ON and STATUS.allHomed() and stat.interp_state == linuxcnc.INTERP_IDLE:
            return True, ''
        return False, "Can't issue MDI unless machine is ON, HOMED and IDLE"

    @pyqtSlot()
    def triggerStart(self):
        if not self._start.enabled:
            return
        program_actions.run()
        self.refresh()

    @pyqtSlot()
    def triggerStop(self):
        if not self._stop.enabled:
            return
        self.abortTriggered.emit()
        program_actions.abort()
        self.refresh()

    @pyqtSlot()
    def triggerPauseResume(self):
        if not self._pause_resume.enabled:
            return
        if self._pause_resume.active:
            program_actions.resume()
        else:
            program_actions.pause()
        self.refresh()

    @pyqtSlot()
    def triggerCycleStart(self):
        if self._start.enabled:
            self.triggerStart()
        elif self._pause_resume.enabled:
            self.triggerPauseResume()

    @pyqtSlot(bool)
    def setOptionalStopEnabled(self, enabled):
        if not self._optional_stop.enabled:
            return
        CMD.set_optional_stop(bool(enabled))
        self._runtime_store.poll()
        self.refresh()

    @pyqtSlot(bool)
    def setBlockDeleteEnabled(self, enabled):
        if not self._block_delete.enabled:
            return
        CMD.set_block_delete(bool(enabled))
        self._runtime_store.poll()
        self.refresh()

    @pyqtSlot(int)
    def setRapidOverridePercent(self, value):
        try:
            percent = int(value)
        except (TypeError, ValueError):
            return
        percent = max(0, min(100, percent))
        CMD.rapidrate(float(percent) / 100.0)
        self._runtime_store.poll()
        self.refresh()

    @pyqtSlot(str)
    def submitMdi(self, command):
        command = (command or '').strip()
        if not command or not self._mdi.enabled:
            return
        issue_mdi(command)
        self.refresh()

    def _percent(self, value):
        try:
            return int(round(float(value or 0.0) * 100.0))
        except (TypeError, ValueError):
            return 0
