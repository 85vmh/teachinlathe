from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.core.tool_library_repository import tool_library_repository
from teachinlathe.ui.tabs.tool_library.tool_library_models import card_and_view

log = logging.getLogger(__name__)


class ProgramsToolChangeViewModel(QObject):
    stateChanged = pyqtSignal()
    toolChangedPulsed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._requested = False
        self._tool_no = 0
        self._confirm_ui_pressed = False
        self._confirm_button_pressed = False
        self._cancel_ui_pressed = False
        self._cancel_button_pressed = False
        self._response_output = False
        # The tool the request is for - the request's number goes back to 0
        # as the change completes - and whether its toast has been asked for.
        self._requested_tool = 0
        self._announced = False
        self._tool_card = ""
        self._tool_view = None
        self._component = TeachInLatheComponent()
        self._tool_library = tool_library_repository()
        self._tool_library.toolsChanged.connect(self._on_tools_changed)
        self._bind_hal()
        self._read_initial_hal_state()
        self._refresh_tool_view()

    @pyqtProperty(bool, notify=stateChanged)
    def requested(self):
        return self._requested

    @pyqtProperty(int, notify=stateChanged)
    def toolNo(self):
        return self._tool_no

    @pyqtProperty(str, notify=stateChanged)
    def toolNoText(self):
        return f"T{self._tool_no}" if self._tool_no > 0 else "T?"

    # The tool mounted in the holder asked for, as the Manual Turning list
    # names it (ToolTitles.listTitle): its card kind ("turning", ...) and its
    # view; "" and None for an empty holder.
    @pyqtProperty(str, notify=stateChanged)
    def toolCard(self):
        return self._tool_card

    @pyqtProperty(QObject, notify=stateChanged)
    def toolView(self):
        return self._tool_view

    @pyqtProperty(str, notify=stateChanged)
    def toolComment(self):
        tool = self._tool_library.tool_in(self._tool_no)
        return tool.comment if tool is not None else ""

    def _refresh_tool_view(self):
        old = self._tool_view
        self._tool_card, self._tool_view = card_and_view(self._tool_library.tool_in(self._tool_no), self)
        if old is not None:
            old.deleteLater()

    def _on_tools_changed(self):
        self._refresh_tool_view()
        self.stateChanged.emit()

    @pyqtSlot()
    def confirmPressed(self):
        self._confirm_ui_pressed = True
        self._refresh_outputs()

    @pyqtSlot()
    def confirmReleased(self):
        self._confirm_ui_pressed = False
        self._refresh_outputs()

    @pyqtSlot()
    def cancelPressed(self):
        self._cancel_ui_pressed = True
        self._refresh_outputs()

    @pyqtSlot()
    def cancelReleased(self):
        self._cancel_ui_pressed = False
        self._refresh_outputs()

    @pyqtSlot()
    def refreshFromHal(self):
        requested = self._read_bool_pin(TeachInLatheComponent.PinToolChangeRequest, self._requested)
        tool_no = self._read_int_pin(TeachInLatheComponent.PinToolChangeToolNo, self._tool_no)
        changed = requested != self._requested or tool_no != self._tool_no
        self._requested = requested
        if tool_no != self._tool_no:
            self._tool_no = tool_no
            self._refresh_tool_view()
        if not requested:
            self._confirm_ui_pressed = False
            self._confirm_button_pressed = False
            self._cancel_ui_pressed = False
            self._cancel_button_pressed = False
        self._refresh_outputs(emit=False)
        if changed:
            self.stateChanged.emit()

    def _bind_hal(self):
        comp = self._component.comp
        for pin_name, callback in (
            (TeachInLatheComponent.PinToolChangeRequest, self._on_requested_changed),
            (TeachInLatheComponent.PinToolChangeToolNo, self._on_tool_no_changed),
            (TeachInLatheComponent.PinButtonCycleStart, self._on_cycle_start_changed),
            (TeachInLatheComponent.PinButtonCycleStop, self._on_cycle_stop_changed),
        ):
            try:
                comp.addListener(pin_name, callback)
            except Exception:
                log.error("Could not bind HAL pin %s", pin_name, exc_info=True)

    def _read_initial_hal_state(self):
        self._requested = self._read_bool_pin(TeachInLatheComponent.PinToolChangeRequest, False)
        self._tool_no = self._read_int_pin(TeachInLatheComponent.PinToolChangeToolNo, 0)
        self._refresh_outputs(emit=False)

    def _on_requested_changed(self, value=False):
        requested = self._read_bool_pin(TeachInLatheComponent.PinToolChangeRequest, bool(value))
        if requested == self._requested:
            return
        self._requested = requested
        if requested:
            self._announced = False
            if self._tool_no > 0:
                self._requested_tool = self._tool_no
        else:
            # Done, one way or the other. Seen by its result rather than by the
            # Cycle Start that confirmed it: the button is read every 100 ms,
            # and a short press - the dev panel's - can fall between two
            # reads, while program_state, in real time, does not miss it.
            tool = self._requested_tool
            QTimer.singleShot(300, lambda: self._announce_if_loaded(tool))
            self._confirm_ui_pressed = False
            self._confirm_button_pressed = False
            self._cancel_ui_pressed = False
            self._cancel_button_pressed = False
        self._refresh_outputs()

    def _on_tool_no_changed(self, value=0):
        tool_no = self._read_int_pin(TeachInLatheComponent.PinToolChangeToolNo, value)
        if tool_no == self._tool_no:
            return
        self._tool_no = tool_no
        if tool_no > 0:
            self._requested_tool = tool_no
        self._refresh_tool_view()
        self.stateChanged.emit()

    def _on_cycle_start_changed(self, value=False):
        pressed = bool(value)
        if pressed == self._confirm_button_pressed:
            return
        self._confirm_button_pressed = pressed
        self._refresh_outputs()

    def _on_cycle_stop_changed(self, value=False):
        pressed = bool(value)
        if pressed == self._cancel_button_pressed:
            return
        self._cancel_button_pressed = pressed
        self._refresh_outputs()

    def _refresh_outputs(self, emit=True):
        response_output = self._requested and (self._confirm_ui_pressed or self._confirm_button_pressed)
        canceled_output = self._requested and (self._cancel_ui_pressed or self._cancel_button_pressed)
        response_pulsed = response_output and not self._response_output

        self._set_pin(
            TeachInLatheComponent.PinToolChangeResponse,
            response_output,
        )
        self._set_pin(
            TeachInLatheComponent.PinToolChangeCanceled,
            canceled_output,
        )
        self._response_output = response_output
        if response_pulsed and not self._announced:
            self._announced = True
            self.toolChangedPulsed.emit(self._tool_no)
        if emit:
            self.stateChanged.emit()

    def _announce_if_loaded(self, tool):
        """The toast for a change the confirming press of was not seen: the
        tool asked for is in the spindle - not when it was cancelled."""
        if self._announced or tool <= 0 or self._requested:
            return
        from teachinlathe.core.status_repository import status_repository
        try:
            loaded = int(status_repository().stat.tool_in_spindle)
        except Exception:
            return
        if loaded == tool:
            self._announced = True
            self.toolChangedPulsed.emit(tool)

    def _set_pin(self, pin_name, value):
        try:
            self._component.comp.getPin(pin_name).value = bool(value)
        except Exception:
            log.error("Could not set HAL pin %s", pin_name, exc_info=True)

    def _read_bool_pin(self, pin_name, default=False):
        try:
            return bool(self._component.comp.getPin(pin_name).value)
        except Exception:
            return bool(default)

    def _read_int_pin(self, pin_name, default=0):
        try:
            value = self._component.comp.getPin(pin_name).value
        except Exception:
            value = default
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
