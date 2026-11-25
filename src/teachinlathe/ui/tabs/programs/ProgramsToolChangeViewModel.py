from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.core.tool_library_repository import tool_library_repository
from teachinlathe.ui.tabs.tool_library.tool_library_models import view_of

log = logging.getLogger(__name__)


class ProgramsToolChangeViewModel(QObject):
    stateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._requested = False
        self._tool_no = 0
        # the machine's Cycle Start and Cycle Stop: what answers a tool change
        self._confirm_button_pressed = False
        self._cancel_button_pressed = False
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
    # names it (ToolTitles.listTitle): its view, None for an empty holder.
    @pyqtProperty(QObject, notify=stateChanged)
    def toolView(self):
        return self._tool_view

    @pyqtProperty(str, notify=stateChanged)
    def toolComment(self):
        tool = self._tool_library.tool_in(self._tool_no)
        return tool.comment if tool is not None else ""

    def _refresh_tool_view(self):
        old = self._tool_view
        self._tool_view = view_of(self._tool_library.tool_in(self._tool_no), self)
        if old is not None:
            old.deleteLater()

    def _on_tools_changed(self):
        self._refresh_tool_view()
        self.stateChanged.emit()

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
            self._confirm_button_pressed = False
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
        if not requested:
            # done, one way or the other
            self._confirm_button_pressed = False
            self._cancel_button_pressed = False
        self._refresh_outputs()

    def _on_tool_no_changed(self, value=0):
        tool_no = self._read_int_pin(TeachInLatheComponent.PinToolChangeToolNo, value)
        if tool_no == self._tool_no:
            return
        self._tool_no = tool_no
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
        response_output = self._requested and self._confirm_button_pressed
        canceled_output = self._requested and self._cancel_button_pressed

        self._set_pin(
            TeachInLatheComponent.PinToolChangeResponse,
            response_output,
        )
        self._set_pin(
            TeachInLatheComponent.PinToolChangeCanceled,
            canceled_output,
        )
        if emit:
            self.stateChanged.emit()

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
