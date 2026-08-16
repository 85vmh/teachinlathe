from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.lathe_hal_component import TeachInLatheComponent
from teachinlathe.widgets.tool_library.tool_entry import ToolType
from teachinlathe.widgets.tool_library.tool_repository import ToolRepository

try:
    from qtpyvcp.utilities.info import Info as _Info
    _TBL_PATH: str = _Info().getToolTableFile()
except Exception:
    _TBL_PATH = ""


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
        self._component = TeachInLatheComponent()
        self._tool_repository = None
        if _TBL_PATH:
            try:
                self._tool_repository = ToolRepository(_TBL_PATH, parent=self)
                self._tool_repository.toolsChanged.connect(self.stateChanged)
            except Exception as e:
                print(f"[ProgramsToolChangeViewModel] failed to load tool table: {e}")
        self._bind_hal()
        self._read_initial_hal_state()

    @pyqtProperty(bool, notify=stateChanged)
    def requested(self):
        return self._requested

    @pyqtProperty(int, notify=stateChanged)
    def toolNo(self):
        return self._tool_no

    @pyqtProperty(str, notify=stateChanged)
    def toolNoText(self):
        return f"T{self._tool_no}" if self._tool_no > 0 else "T?"

    @pyqtProperty(str, notify=stateChanged)
    def toolDescription(self):
        if self._tool_repository is None:
            return ""
        tool = self._tool_repository.get_tool(self._tool_no)
        if tool is None:
            return ""

        tool_type = getattr(tool, "tool_type", ToolType.GENERIC)
        try:
            tool_type = ToolType(tool_type)
        except (TypeError, ValueError):
            tool_type = ToolType.GENERIC
        type_label = {
            ToolType.PARTING_BLADE: "Parting blade",
            ToolType.GROOVING_BLADE: "Grooving blade",
            ToolType.DRILL: "Drill",
            ToolType.REAMER: "Reamer",
            ToolType.TAP: "Tap",
            ToolType.BORING_BAR: "Boring bar",
            ToolType.TREPANING: "Trepaning tool",
            ToolType.GENERIC: "",
        }.get(tool_type, "")

        if tool_type in (ToolType.PARTING_BLADE, ToolType.GROOVING_BLADE):
            width = float(getattr(tool, "width", 0.0) or 0.0)
            if width > 0:
                return f"{self._format_number(width)}mm {type_label}"
            return type_label

        diameter = float(getattr(tool, "diameter", 0.0) or 0.0)
        if diameter > 0 and type_label:
            return f"{self._format_number(diameter)}mm {type_label}"
        if type_label:
            return type_label
        return str(getattr(tool, "r", "") or "").strip()

    @pyqtProperty(str, notify=stateChanged)
    def toolSummary(self):
        description = self.toolDescription
        if description:
            return f"{self.toolNoText} [{description}]"
        return self.toolNoText

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
        self._tool_no = tool_no
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
            except Exception as e:
                print(f"[ProgramsToolChangeViewModel] failed to bind HAL pin {pin_name}: {e}")

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
        if response_pulsed:
            self.toolChangedPulsed.emit(self._tool_no)
        if emit:
            self.stateChanged.emit()

    def _set_pin(self, pin_name, value):
        try:
            self._component.comp.getPin(pin_name).value = bool(value)
        except Exception as e:
            print(f"[ProgramsToolChangeViewModel] failed to set HAL pin {pin_name}: {e}")

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

    @staticmethod
    def _format_number(value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return "0"
        if abs(number - round(number)) < 0.0001:
            return str(int(round(number)))
        return f"{number:.1f}".rstrip("0").rstrip(".")
