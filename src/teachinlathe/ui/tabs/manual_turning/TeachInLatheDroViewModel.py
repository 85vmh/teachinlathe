from enum import Enum

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from teachinlathe.core.command_repository import command_repository, issue_mdi
from teachinlathe.core.status_repository import status_repository
from teachinlathe.core.tool_library_repository import tool_library_repository

from teachinlathe.core.positions_repository import Positions
from teachinlathe.core.predefined_positions_repository import predefined_positions
from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.manual.logic.machine_limits import MachineLimitsHandler


class LimitStatus(Enum):
    ENABLED = 0
    DISABLED = 1
    PENDING = 2
    REACHED = 3


class TeachInLatheDroViewModel(QObject):
    touchOffValueInputRequested = pyqtSignal(str)
    droChanged = pyqtSignal()
    limitsChanged = pyqtSignal()
    actionRejected = pyqtSignal(str)
    setDatumValueInputRequested = pyqtSignal()
    #: The work offset in use, or whether it can be changed, changed.
    workOffsetChanged = pyqtSignal()
    #: Something the operator is told in a toast, not a refusal.
    noticeShown = pyqtSignal(str)
    #: Whether M6, G28 or G30 is set changed.
    predefinedPositionsChanged = pyqtSignal()
    #: The current loaded tool, or whether its offsets are set, changed.
    toolStateChanged = pyqtSignal()
    #: The current loaded tool, or what it is, changed: its drawing.
    toolDrawingChanged = pyqtSignal()

    #: The tool limits along each axis (LIMIT_KEYS): kept to the tool, so
    #: there is none without the tool's offset on that axis.
    TOOL_LIMIT_KEYS = {"x": ("xMinus", "xPlus"), "z": ("zMinus", "zPlus")}

    #: The work offsets the operator can choose, as a program's header has
    #: them (HeaderDetailsView): G54 is stat.g5x_index 1.
    WORK_OFFSETS = ("G54", "G55", "G56", "G57", "G58", "G59")

    LIMIT_NONE = "--none--"
    LIMIT_KEYS = ("xMinus", "xPlus", "zMinus", "zPlus", "tailstock")
    LIMIT_SETTING_NAMES = {
        "xMinus": "smart_numpad.x-minus-limit",
        "xPlus": "smart_numpad.x-plus-limit",
        "zMinus": "smart_numpad.z-minus-limit",
        "zPlus": "smart_numpad.z-plus-limit",
        "tailstock": "smart_numpad.tailstock-limit",
        "chuck": "smart_numpad.chuck-limit",
    }

    def __init__(self, parent=None, tool_library=None):
        super().__init__(parent)
        self._tool_library = tool_library_repository() if tool_library is None else tool_library
        # the current loaded tool's drawing, and the tool it was built for
        self._tool_outline = None
        self._tool_outline_key = None
        self.limitsHandler = MachineLimitsHandler()
        self.latheComponent = TeachInLatheComponent()
        self.setDefaultMachineLimits(self.limitsHandler.getDefaultMachineLimits())
        self.latheComponent.comp.addListener(TeachInLatheComponent.PinJoystickIsFeeding, self.onJoystickFeedingChanged)

        self.status = status_repository()
        self.positions = Positions()

        self._mm_fmt = '%10.3f'
        self._in_fmt = '%9.4f'
        self._fmt = self._mm_fmt
        self._units = "mm"
        self.isDiameterMode = True
        self.previousMachineLimits = None
        self.currentMachineLimits = None
        self.currentXAbsValue = 0
        self.currentZAbsValue = 0
        # the machine coordinates, X on the radius: where the axes are, the
        # work offset and the tool offset aside
        self.currentXMachineValue = 0
        self.currentZMachineValue = 0
        self.isXAbs = True
        self.lastXAbsValue = 0
        self.isZAbs = True
        self.lastZAbsValue = 0
        self._x_primary_value = "+0000.000"
        self._x_secondary_value = "+0000.000"
        self._x_secondary_visible = False
        self._z_primary_value = "+0000.000"
        self._z_secondary_value = "+0000.000"
        self._z_secondary_visible = False
        self._is_feeding = bool(self.latheComponent.comp.getPin(TeachInLatheComponent.PinJoystickIsFeeding).value)
        # the work offset asked for and not in use yet: told once it is
        self._work_offset_asked = None

        self.limit_status = {
            "xMinus": LimitStatus.DISABLED,
            "xPlus": LimitStatus.DISABLED,
            "zMinus": LimitStatus.DISABLED,
            "zPlus": LimitStatus.DISABLED,
            "tailstock": LimitStatus.DISABLED,
            "chuck": LimitStatus.DISABLED,
        }
        self.limit_values = {
            "xMinus": self.LIMIT_NONE,
            "xPlus": self.LIMIT_NONE,
            "zMinus": self.LIMIT_NONE,
            "zPlus": self.LIMIT_NONE,
            "tailstock": self.LIMIT_NONE,
            "chuck": self.LIMIT_NONE,
        }
        self.toggle_enabled = {key: False for key in self.LIMIT_KEYS}

        self.status.program_units.notify(self.updateUnits, 'string')
        self.status.g5x_index.notify(self._on_work_offset)
        self._predefined = predefined_positions()
        self._predefined.changed.connect(self.predefinedPositionsChanged)
        self._predefined.changed.connect(self.limitsChanged)
        # the current loaded tool's offsets: set on each axis, or not
        self._tool_set = {"x": False, "z": False}
        self._tool_library.toolsChanged.connect(self._on_tool_state)
        self._tool_library.currentLoadedToolChanged.connect(self._on_tool_state)
        self._tool_library.touchedOff.connect(self._on_tool_state)
        self._on_tool_state()
        self.positions.notify(self.updateValues)
        self.positions.notify(self.onAbsPositionUpdated)
        self.limitsHandler.onLimitsChanged.connect(self.onMachineLimitsChanged)

        self.updateUnits()
        self.updateValues()

    @pyqtProperty(str, notify=droChanged)
    def xPrimaryValue(self):
        return self._x_primary_value

    @pyqtProperty(str, notify=droChanged)
    def xSecondaryValue(self):
        return self._x_secondary_value

    # Whether each axis shows its absolute position (else relative): what
    # the ABS/REL toggle lights.
    @pyqtProperty(bool, notify=droChanged)
    def xIsAbs(self):
        return self.isXAbs

    @pyqtProperty(bool, notify=droChanged)
    def zIsAbs(self):
        return self.isZAbs

    @pyqtProperty(bool, notify=droChanged)
    def xSecondaryVisible(self):
        return self._x_secondary_visible

    @pyqtProperty(str, notify=droChanged)
    def xMachineValue(self):
        """X in machine coordinates, on the radius."""
        return self._fmt % self.currentXMachineValue

    @pyqtProperty(str, notify=droChanged)
    def zMachineValue(self):
        """Z in machine coordinates."""
        return self._fmt % self.currentZMachineValue

    @pyqtProperty(str, notify=droChanged)
    def zPrimaryValue(self):
        return self._z_primary_value

    @pyqtProperty(str, notify=droChanged)
    def zSecondaryValue(self):
        return self._z_secondary_value

    @pyqtProperty(bool, notify=droChanged)
    def zSecondaryVisible(self):
        return self._z_secondary_visible

    @pyqtProperty(str, notify=droChanged)
    def units(self):
        return self._units

    def _limit_property(self, key):
        return self.limit_values[key]

    def _status_property(self, key):
        return self.limit_status[key].value

    def _toggle_text_property(self, key):
        return self._status_text(self.limit_status[key])

    def _toggle_enabled_property(self, key):
        return self.toggle_enabled[key]

    xMinusValue = pyqtProperty(str, lambda self: self._limit_property("xMinus"), notify=limitsChanged)
    xPlusValue = pyqtProperty(str, lambda self: self._limit_property("xPlus"), notify=limitsChanged)
    zMinusValue = pyqtProperty(str, lambda self: self._limit_property("zMinus"), notify=limitsChanged)
    zPlusValue = pyqtProperty(str, lambda self: self._limit_property("zPlus"), notify=limitsChanged)
    tailstockValue = pyqtProperty(str, lambda self: self._limit_property("tailstock"), notify=limitsChanged)
    chuckValue = pyqtProperty(str, lambda self: self._limit_property("chuck"), notify=limitsChanged)

    xMinusStatus = pyqtProperty(int, lambda self: self._status_property("xMinus"), notify=limitsChanged)
    xPlusStatus = pyqtProperty(int, lambda self: self._status_property("xPlus"), notify=limitsChanged)
    zMinusStatus = pyqtProperty(int, lambda self: self._status_property("zMinus"), notify=limitsChanged)
    zPlusStatus = pyqtProperty(int, lambda self: self._status_property("zPlus"), notify=limitsChanged)
    tailstockStatus = pyqtProperty(int, lambda self: self._status_property("tailstock"), notify=limitsChanged)
    chuckStatus = pyqtProperty(int, lambda self: self._status_property("chuck"), notify=limitsChanged)

    xMinusToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("xMinus"), notify=limitsChanged)
    xPlusToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("xPlus"), notify=limitsChanged)
    zMinusToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("zMinus"), notify=limitsChanged)
    zPlusToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("zPlus"), notify=limitsChanged)
    tailstockToggleText = pyqtProperty(str, lambda self: self._toggle_text_property("tailstock"), notify=limitsChanged)

    xMinusToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("xMinus"), notify=limitsChanged)
    xPlusToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("xPlus"), notify=limitsChanged)
    zMinusToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("zMinus"), notify=limitsChanged)
    zPlusToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("zPlus"), notify=limitsChanged)
    tailstockToggleEnabled = pyqtProperty(bool, lambda self: self._toggle_enabled_property("tailstock"), notify=limitsChanged)

    def setDefaultMachineLimits(self, limits):
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = limits.x_min_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = limits.x_max_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = limits.z_min_limit
        self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = limits.z_max_limit

    def setChuckLimit(self, value):
        self.limit_values["chuck"] = self._format_limit(value)
        self.limitsHandler.setChuckLimit(float(value))
        self.limitsChanged.emit()

    def _format_limit(self, value):
        return self._fmt % float(value)

    @pyqtSlot()
    def xPrimaryClicked(self):
        if not self._can_run_primary_click():
            return
        self.touchOffValueInputRequested.emit("x")

    @pyqtSlot()
    def zPrimaryClicked(self):
        if not self._can_run_primary_click():
            return
        self.touchOffValueInputRequested.emit("z")

    @pyqtSlot(str, "QVariant")
    def touchOff(self, axis, value):
        # A blade is asked which of its points this was once the offset is in.
        self._tool_library.touch_off(str(axis), value)

    @pyqtSlot(str)
    def teachLimit(self, key):
        key = str(key)
        if key not in self.LIMIT_KEYS or not self._limit_available(key):
            return
        self.limit_values[key] = self._format_limit(self._teach_value_for_key(key))
        self.toggle_enabled[key] = True
        self.limitsChanged.emit()

    def _teach_value_for_key(self, key):
        if key.startswith("x"):
            factor = 2.0 if self.isDiameterMode else 1.0
            return factor * self.positions.teachInX()
        if key == "tailstock":
            # the tailstock is the machine's, whatever the tool: where the
            # axis is, G53, no offset
            return self.positions.teachInZ(machineCoordinate=True)
        if key.startswith("z"):
            return self.positions.teachInZ()
        return 0

    @pyqtSlot(str, str)
    def commitLimit(self, key, value):
        key = str(key)
        if key not in self.limit_values:
            return
        self.limit_values[key] = self._format_limit(value)
        if key != "chuck":
            self.toggle_enabled[key] = True
        self.limitsChanged.emit()

    @pyqtSlot(str)
    def toggleLimit(self, key):
        key = str(key)
        if not self._limit_available(key):
            return
        match key:
            case "xMinus":
                self.xMinusLimitToggle()
            case "xPlus":
                self.xPlusLimitToggle()
            case "zMinus":
                self.zMinusLimitToggle()
            case "zPlus":
                self.zPlusLimitToggle()
            case "tailstock":
                self.tailstockLimitToggle()

    def _toggle_status(self, key):
        if self.limit_status[key] in (LimitStatus.ENABLED, LimitStatus.PENDING):
            self.limit_status[key] = LimitStatus.DISABLED
        elif self.limit_status[key] == LimitStatus.DISABLED:
            self.limit_status[key] = LimitStatus.PENDING
        self.limitsChanged.emit()

    def _limit_float(self, key):
        return float(str(self.limit_values[key]).strip())

    def xMinusLimitToggle(self):
        self._toggle_status("xMinus")
        x_offset = self.positions.getXPosition().offset
        self.limitsHandler.setXMinusLimit(x_offset + self._limit_float("xMinus") / 2)
        self.limitsHandler.setXMinusLimitActive(self.limit_status["xMinus"] is not LimitStatus.DISABLED)

    def xPlusLimitToggle(self):
        self._toggle_status("xPlus")
        x_offset = self.positions.getXPosition().offset
        self.limitsHandler.setXPlusLimit(x_offset + self._limit_float("xPlus") / 2)
        self.limitsHandler.setXPlusLimitActive(self.limit_status["xPlus"] is not LimitStatus.DISABLED)

    def zMinusLimitToggle(self):
        self._toggle_status("zMinus")
        z_offset = self.positions.getZPosition().offset
        self.limitsHandler.setZMinusLimit(z_offset + self._limit_float("zMinus"))
        self.limitsHandler.setZMinusLimitActive(self.limit_status["zMinus"] is not LimitStatus.DISABLED)

    def zPlusLimitToggle(self):
        self._toggle_status("zPlus")
        z_offset = self.positions.getZPosition().offset
        self.limitsHandler.setZPlusLimit(z_offset + self._limit_float("zPlus"))
        self.limitsHandler.setZPlusLimitActive(self.limit_status["zPlus"] is not LimitStatus.DISABLED)

    def tailstockLimitToggle(self):
        self._toggle_status("tailstock")
        self.limitsHandler.setTailstockLimit(self._limit_float("tailstock"))
        self.limitsHandler.setTailstockLimitActive(self.limit_status["tailstock"] is not LimitStatus.DISABLED)

    def _status_text(self, status):
        return "Disable Limit" if status in (LimitStatus.ENABLED, LimitStatus.REACHED) else "Pending..." if status == LimitStatus.PENDING else "Enable Limit"

    def updateUnits(self, units=None):
        if units is None:
            units = str(self.status.program_units)
        self._fmt = self._in_fmt if units == 'in' else self._mm_fmt
        self._units = units
        self.droChanged.emit()
        self.updateDro()

    def updateValues(self, pos=None):
        x, z = self.positions.getXPosition(), self.positions.getZPosition()
        self.currentXAbsValue = x.g5xPosition
        self.currentZAbsValue = z.g5xPosition
        self.currentXMachineValue = x.machinePosition
        self.currentZMachineValue = z.machinePosition
        self.updateDro()

    @pyqtSlot()
    def xZeroClicked(self):
        if not self._tool_set["x"]:
            return
        self.isXAbs = False
        self.lastXAbsValue = self.currentXAbsValue
        self.updateDro()

    @pyqtSlot()
    def zZeroClicked(self):
        if not self._tool_set["z"]:
            return
        self.isZAbs = False
        self.lastZAbsValue = self.currentZAbsValue
        self.updateDro()

    @pyqtSlot()
    def xAbsRelClicked(self):
        if not self._tool_set["x"]:
            return
        self.isXAbs = not self.isXAbs
        if self.isXAbs:
            self.lastXAbsValue = 0
        self.updateDro()

    @pyqtSlot()
    def zAbsRelClicked(self):
        if not self._tool_set["z"]:
            return
        self.isZAbs = not self.isZAbs
        if self.isZAbs:
            self.lastZAbsValue = 0
        self.updateDro()

    @pyqtSlot()
    def zSetDatumClicked(self):
        self._set_z_datum(0.0)

    @pyqtSlot()
    def zSetDatumLongPressed(self):
        if not self._can_set_datum():
            return
        self.setDatumValueInputRequested.emit()

    @pyqtSlot("QVariant")
    def zSetDatumValueSelected(self, value):
        self._set_z_datum(value)

    def _can_run_primary_click(self):
        if self._is_feeding:
            self.actionRejected.emit("Changing tool offsets not allowed when power feeding")
            return False
        return True

    def _can_set_datum(self):
        if self._is_feeding:
            self.actionRejected.emit("SetDatum not allowed when power feeding")
            return False
        return True

    def _set_z_datum(self, value):
        if not self._can_set_datum():
            return
        try:
            datum_value = float(value)
        except Exception:
            return
        if not self._tool_set["z"]:
            # A tool with no Z offset yet: this point is its Z - the offset
            # taken here, the tool reading the value here - as touching off
            # Z at it and setting the datum there would. The datum stays.
            if not self._tool_library.current_loaded_tool:
                self.actionRejected.emit("No tool loaded to set the datum with")
                return
            self._tool_library.touch_off("z", datum_value)
            return
        issue_mdi(f"G10 L20 P{self._current_g5x_index()} Z{datum_value:.3f}")

    def onJoystickFeedingChanged(self, value):
        self._is_feeding = bool(value)
        self.workOffsetChanged.emit()

    # ── the predefined positions: whether each is set ─────────────────────

    @pyqtProperty(bool, notify=predefinedPositionsChanged)
    def toolChangeSet(self):
        """M6: a tool change position set, not the INI's (predefined_positions_repository)."""
        return self._predefined.tool_change_set

    @pyqtProperty(bool, notify=predefinedPositionsChanged)
    def g28Set(self):
        return self._predefined.g28_set

    @pyqtProperty(bool, notify=predefinedPositionsChanged)
    def g30Set(self):
        return self._predefined.g30_set

    # ── setting them, on the back of the limits panel ─────────────────────

    @pyqtProperty("QVariant", notify=toolDrawingChanged)
    def currentToolOutline(self):
        """The current loaded tool as the backplot draws it, flat, in mm from
        its tip (X a radius): {loop, rings, lines}, each point [x, z]; null
        with no tool, or one the Tool Library cannot describe."""
        from teachinlathe.ui.tabs.programs.backplot import tool_source
        from teachinlathe.ui.tabs.programs.backplot.actors.insert_tool import plane_outline
        tool_no = self._tool_library.current_loaded_tool
        drawing = tool_source.describe(tool_no, repository=self._tool_library) if tool_no else None
        key = (tool_no, drawing)
        if key != self._tool_outline_key:
            outline = plane_outline(drawing) if drawing is not None else None
            if outline is not None:
                outline = {name: ([list(p) for p in value] if name == "loop"
                                  else [[list(p) for p in line] for line in value])
                           for name, value in outline.items()}
            self._tool_outline, self._tool_outline_key = outline, key
        return self._tool_outline

    @pyqtProperty("QVariant", notify=droChanged)
    def workOffsetOrigin(self):
        """Where the work offset in use (G54...) has its zero, machine
        coordinates (G53, X a radius): its offsets and G92's - as AXIS draws
        it, the same whatever the tool. Its name too."""
        stat = self.status.stat
        x = stat.g5x_offset[0] + stat.g92_offset[0]
        z = stat.g5x_offset[2] + stat.g92_offset[2]
        return {"x": float(x), "z": float(z), "name": self.workOffsetName}

    @pyqtProperty("QVariant", notify=droChanged)
    def toolTipPosition(self):
        """Where the current loaded tool's tip is, machine coordinates (G53,
        X a radius): the machine position - the point a tool without offsets
        has its tip on - less the tool offset in use, as AXIS draws the tool."""
        offset = self.status.stat.tool_offset
        return {"x": float(self.currentXMachineValue) - offset[0],
                "z": float(self.currentZMachineValue) - offset[2]}

    @pyqtProperty(float, notify=droChanged)
    def machineXValue(self):
        """The machine position X, G53 - a radius - as a number: where the
        drawing's cross is."""
        return float(self.currentXMachineValue)

    @pyqtProperty(float, notify=droChanged)
    def machineZValue(self):
        return float(self.currentZMachineValue)

    @pyqtSlot()
    def teachToolChange(self):
        """The tool change position (M6) where the machine is now (G53)."""
        self._predefined.set_tool_change(x=float(self.currentXMachineValue), z=float(self.currentZMachineValue))
        self.noticeShown.emit("M6 position set to the machine position")

    @pyqtSlot()
    def teachG28(self):
        """G28 where the machine is now: G28.1."""
        self._teach_position("G28.1", "G28")

    @pyqtSlot()
    def teachG30(self):
        self._teach_position("G30.1", "G30")

    def _teach_position(self, command, name):
        if self._is_feeding:
            self.actionRejected.emit(f"Setting {name} not allowed when power feeding")
            return
        ready, why = command_repository().can_issue_mdi()
        if not ready:
            self.actionRejected.emit(why)
            return
        if issue_mdi(command):
            self.noticeShown.emit(f"{name} set to the machine position")

    # ── the current loaded tool: whether its offsets are set ──────────────

    @pyqtProperty(bool, notify=toolStateChanged)
    def xToolSet(self):
        """The current loaded tool has its X offset: its X coordinate means
        something - else none is shown, and its X tool limits are off."""
        return self._tool_set["x"]

    @pyqtProperty(bool, notify=toolStateChanged)
    def zToolSet(self):
        return self._tool_set["z"]

    def _limit_available(self, key):
        """A tool limit only with the tool's offset on its axis; the machine's
        always."""
        for axis, keys in self.TOOL_LIMIT_KEYS.items():
            if key in keys:
                return self._tool_set[axis]
        return True

    def _on_tool_state(self, *_args):
        self._tool_outline_key = None
        self.toolDrawingChanged.emit()
        holder = self._tool_library.current_holder
        has_tool = holder is not None and holder.has_tool
        state = {"x": has_tool and holder.x_touched, "z": has_tool and holder.z_touched}
        if state == self._tool_set:
            return
        self._tool_set = state
        for axis, is_set in state.items():
            if is_set:
                continue
            # nothing relative to a coordinate there is none of
            if axis == "x":
                self.isXAbs, self.lastXAbsValue = True, 0
            else:
                self.isZAbs, self.lastZAbsValue = True, 0
            # and no tool limit left on, kept to an offset the tool has not
            for key in self.TOOL_LIMIT_KEYS[axis]:
                if self.limit_status[key] is not LimitStatus.DISABLED:
                    self._turn_off_tool_limit(key)
        self.toolStateChanged.emit()
        self.limitsChanged.emit()
        self.updateDro()

    def _turn_off_tool_limit(self, key):
        self.limit_status[key] = LimitStatus.DISABLED
        {"xMinus": self.limitsHandler.setXMinusLimitActive,
         "xPlus": self.limitsHandler.setXPlusLimitActive,
         "zMinus": self.limitsHandler.setZMinusLimitActive,
         "zPlus": self.limitsHandler.setZPlusLimitActive}[key](False)

    # ── the machine limits, as drawn on the back of the limits panel ──────

    @pyqtProperty("QVariant", notify=limitsChanged)
    def machineLimitsMap(self):
        """What the machine limits' drawing shows, machine coordinates (G53,
        X a radius): ``travel`` {xMin, xMax, zMin, zMax} - the INI's axis
        limits -, ``home`` {x, z} - where homing leaves the axes, the INI's
        HOME -, ``tailstock`` its limit's Z (null with none) and whether it
        is on, ``chuck`` the chuck limit's Z - its card's, 0 until it is set
        (``chuckSet``) -, and
        ``positions`` [{name, x, z, set}] - M6 (the tool change position), G28, G30."""
        from teachinlathe.core.ini_repository import ini_repository
        travel = self.limitsHandler.getDefaultMachineLimits()
        try:
            tailstock = float(str(self.limit_values["tailstock"]).strip())
        except ValueError:
            tailstock = None
        try:
            chuck = float(str(self.limit_values["chuck"]).strip())
        except ValueError:
            chuck = None
        tc_x, tc_z, _custom = self._predefined.tool_change_position()
        positions = [{"name": "M6", "x": tc_x, "z": tc_z, "set": self._predefined.tool_change_set}]
        for name, (x, z), is_set in (("G28", self._predefined.g28_position(), self._predefined.g28_set),
                                     ("G30", self._predefined.g30_position(), self._predefined.g30_set)):
            positions.append({"name": name, "x": x, "z": z, "set": is_set})
        return {
            "travel": {"xMin": travel.x_min_limit, "xMax": travel.x_max_limit,
                       "zMin": travel.z_min_limit, "zMax": travel.z_max_limit},
            "home": {"x": ini_repository().axis_home("x"), "z": ini_repository().axis_home("z")},
            "tailstock": tailstock,
            "tailstockOn": self.limit_status["tailstock"] is not LimitStatus.DISABLED,
            "chuck": chuck if chuck is not None else 0.0,
            "chuckSet": chuck is not None,
            "positions": [p for p in positions if p["x"] is not None and p["z"] is not None],
        }

    # ── the work offset (G54...) the tool coordinates are in ──────────────

    @pyqtProperty(str, notify=workOffsetChanged)
    def workOffsetName(self):
        """The work offset in use: "G54" ... - "G59.3" past the ones offered."""
        from teachinlathe.machine.model.work_offsets import work_offset_name
        return work_offset_name(self._current_g5x_index())

    @pyqtProperty("QStringList", constant=True)
    def workOffsets(self):
        return list(self.WORK_OFFSETS)

    @pyqtProperty(bool, notify=workOffsetChanged)
    def workOffsetSelectable(self):
        """Whether another can be chosen: not while feeding - no MDI then."""
        return not self._is_feeding

    @pyqtSlot(str)
    def selectWorkOffset(self, name):
        """Put work offset ``name`` ("G55"...) in use, by MDI; the operator is
        told once it is (noticeShown)."""
        if name not in self.WORK_OFFSETS or name == self.workOffsetName:
            return
        if self._is_feeding:
            self.actionRejected.emit("Changing the work coordinate system not allowed when power feeding")
            return
        ready, why = command_repository().can_issue_mdi()
        if not ready:
            self.actionRejected.emit(why)
            return
        self._work_offset_asked = name
        if not issue_mdi(name):
            self._work_offset_asked = None
            self.actionRejected.emit(f"Could not change the work coordinate system to {name}")

    def _on_work_offset(self, *_args):
        self.workOffsetChanged.emit()
        if self._work_offset_asked is not None and self.workOffsetName == self._work_offset_asked:
            self._work_offset_asked = None
            self.noticeShown.emit(f"Work Coordinate System changed to {self.workOffsetName}")

    def _current_g5x_index(self):
        try:
            return int(self.status.stat.g5x_index)
        except Exception:
            pass
        try:
            return int(self.status.g5x_index.value)
        except Exception:
            return 1

    def updateDro(self):
        factor = 2.0 if self.isDiameterMode else 1.0
        if self.isXAbs:
            self._x_primary_value = self._fmt % (factor * self.currentXAbsValue)
            self._x_secondary_visible = False
        else:
            self._x_primary_value = self._fmt % (factor * (self.currentXAbsValue - self.lastXAbsValue))
            self._x_secondary_value = self._fmt % (factor * self.currentXAbsValue)
            self._x_secondary_visible = True

        if self.isZAbs:
            self._z_primary_value = self._fmt % self.currentZAbsValue
            self._z_secondary_visible = False
        else:
            self._z_primary_value = self._fmt % (self.currentZAbsValue - self.lastZAbsValue)
            self._z_secondary_value = self._fmt % self.currentZAbsValue
            self._z_secondary_visible = True
        self.droChanged.emit()

    def onMachineLimitsChanged(self, machine_limits):
        self.currentMachineLimits = machine_limits
        self.onAbsPositionUpdated()

    def onAbsPositionUpdated(self, pos=None):
        if self.previousMachineLimits == self.currentMachineLimits:
            return
        x_abs = self.positions.getXPosition().machinePosition
        z_abs = self.positions.getZPosition().machinePosition
        x_min_limit = self.currentMachineLimits.x_min_limit
        x_max_limit = self.currentMachineLimits.x_max_limit
        z_min_limit = self.currentMachineLimits.z_min_limit
        z_max_limit = self.currentMachineLimits.z_max_limit
        tolerance = 0.005
        pin_written = {key: False for key in ("xMinus", "xPlus", "zMinus", "zPlus", "tailstock")}

        if x_abs >= x_min_limit and self.limit_status["xMinus"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = x_min_limit
            pin_written["xMinus"] = True
            self.limit_status["xMinus"] = LimitStatus.ENABLED
        elif self.limit_status["xMinus"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMin).value = x_min_limit
            pin_written["xMinus"] = True
        elif self.limit_status["xMinus"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["xMinus"] = LimitStatus.REACHED if abs(x_abs - x_min_limit) < tolerance else LimitStatus.ENABLED

        if x_abs <= x_max_limit and self.limit_status["xPlus"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = x_max_limit
            pin_written["xPlus"] = True
            self.limit_status["xPlus"] = LimitStatus.ENABLED
        elif self.limit_status["xPlus"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitXMax).value = x_max_limit
            pin_written["xPlus"] = True
        elif self.limit_status["xPlus"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["xPlus"] = LimitStatus.REACHED if abs(x_abs - x_max_limit) < tolerance else LimitStatus.ENABLED

        if z_abs >= z_min_limit and self.limit_status["zMinus"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = z_min_limit
            pin_written["zMinus"] = True
            self.limit_status["zMinus"] = LimitStatus.ENABLED
        elif self.limit_status["zMinus"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMin).value = z_min_limit
            pin_written["zMinus"] = True
        elif self.limit_status["zMinus"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["zMinus"] = LimitStatus.REACHED if abs(z_abs - z_min_limit) < tolerance else LimitStatus.ENABLED

        if z_abs <= z_max_limit and self.limit_status["zPlus"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
            pin_written["zPlus"] = True
            self.limit_status["zPlus"] = LimitStatus.ENABLED
        elif self.limit_status["zPlus"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
            pin_written["zPlus"] = True
        elif self.limit_status["zPlus"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["zPlus"] = LimitStatus.REACHED if abs(z_abs - z_max_limit) < tolerance else LimitStatus.ENABLED

        if z_abs <= z_max_limit and self.limit_status["tailstock"] == LimitStatus.PENDING:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
            pin_written["tailstock"] = True
            self.limit_status["tailstock"] = LimitStatus.ENABLED
        elif self.limit_status["tailstock"] == LimitStatus.DISABLED:
            self.latheComponent.comp.getPin(TeachInLatheComponent.PinAxisLimitZMax).value = z_max_limit
            pin_written["tailstock"] = True
        elif self.limit_status["tailstock"] in (LimitStatus.ENABLED, LimitStatus.REACHED):
            self.limit_status["tailstock"] = LimitStatus.REACHED if abs(z_abs - z_max_limit) < tolerance else LimitStatus.ENABLED

        self.limitsChanged.emit()
        if all(pin_written.values()):
            self.previousMachineLimits = self.currentMachineLimits
