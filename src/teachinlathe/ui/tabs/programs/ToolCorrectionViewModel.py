"""The correction of the current loaded tool at an M1, as the run bar shows it
(ToolCorrectionPanel): "Correct T<n>" while the program waits at the M1, the
operator's entries - ΔØ and ΔZ - and what they make of the tool's offsets,
the correction armed for Cycle Start, and the offsets it left.

The entries are this view model's until the correction is armed; the panel
shows them and sends each one here.
"""

from typing import Optional

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.programs.model.tool_correction import ToolCorrection, check


class ToolCorrectionViewModel(QObject):
    changed = pyqtSignal()
    #: The remap applied it: show the new offsets for a moment.
    appliedShown = pyqtSignal()

    def __init__(self, use_case, parent=None):
        """``use_case``: ToolCorrectionUseCase."""
        super().__init__(parent)
        self._use_case = use_case
        self._dx: Optional[float] = None
        self._dz: Optional[float] = None
        use_case.changed.connect(self.changed)
        use_case.applied.connect(lambda _applied: self.appliedShown.emit())

    # ── when ─────────────────────────────────────────────────────────────

    @pyqtProperty(bool, notify=changed)
    def available(self):
        """"Correct T<n>" is offered: at an M1, with a tool, none armed."""
        return self._use_case.available and self._use_case.armed is None

    @pyqtProperty(bool, notify=changed)
    def canCorrect(self):
        """At an M1, with a tool: the panel may be open - to edit the one
        armed, too."""
        return self._use_case.available

    @pyqtProperty(str, notify=changed)
    def buttonText(self):
        return f"Correct T{self._use_case.tool}"

    # ── the entries ──────────────────────────────────────────────────────

    @pyqtProperty("QVariant", notify=changed)
    def dDiameter(self):
        """ΔØ: how much bigger (+) or smaller (-) the tool is to cut on the
        diameter; None, not entered."""
        return self._dx

    @pyqtProperty("QVariant", notify=changed)
    def dz(self):
        return self._dz

    @pyqtSlot("QVariant")
    def setDDiameter(self, value):
        self._dx = _number(value)
        self.changed.emit()

    @pyqtSlot("QVariant")
    def setDz(self, value):
        self._dz = _number(value)
        self.changed.emit()

    @pyqtSlot()
    def clearEntries(self):
        """A new correction: both blank."""
        self._dx = self._dz = None
        self.changed.emit()

    # ── what they make ───────────────────────────────────────────────────

    def _correction(self):
        return ToolCorrection(dx=self._dx or 0.0, dz=self._dz or 0.0)

    @pyqtProperty(str, notify=changed)
    def diameterEffectText(self):
        """What ΔØ does, rich text: "(cuts 0.100 mm <b>smaller</b> on Ø)"; "" for none."""
        correction = self._correction()
        return f"({_x_effect(correction, f'{abs(correction.dx):.3f}')})" if correction.changes_x else ""

    @pyqtProperty(str, notify=changed)
    def zEffectText(self):
        """What ΔZ does, rich text: "(cuts 0.100 mm further toward <b>Z-</b>)"; "" for none."""
        correction = self._correction()
        if not correction.changes_z:
            return ""
        return f"(cuts {abs(correction.dz):.3f} mm further toward <b>{correction.z_side}</b>)"

    @pyqtProperty(str, notify=changed)
    def errorText(self):
        """Why it cannot be armed, once something is entered."""
        correction = self._correction()
        return "" if correction.empty else check(correction)

    @pyqtProperty(bool, notify=changed)
    def canArm(self):
        return self._use_case.available and not check(self._correction())

    # the offsets table: the tool's offsets now, and as the correction leaves them

    def _offsets(self):
        tool = self._use_case.tool
        return self._use_case.offsets(tool), self._use_case.expected_offsets(tool, self._correction())

    @pyqtProperty(str, notify=changed)
    def currentXText(self):
        return _value(self._offsets()[0], 0)

    @pyqtProperty(str, notify=changed)
    def currentZText(self):
        return _value(self._offsets()[0], 1)

    @pyqtProperty(str, notify=changed)
    def correctedXText(self):
        return _value(self._offsets()[1], 0)

    @pyqtProperty(str, notify=changed)
    def correctedZText(self):
        return _value(self._offsets()[1], 1)

    @pyqtProperty(bool, notify=changed)
    def xCorrected(self):
        """The correction changes the X offset."""
        return self._correction().changes_x

    @pyqtProperty(bool, notify=changed)
    def zCorrected(self):
        return self._correction().changes_z

    # ── armed, applied ───────────────────────────────────────────────────

    @pyqtProperty(bool, notify=changed)
    def armed(self):
        return self._use_case.armed is not None

    @pyqtProperty(str, notify=changed)
    def armedTitle(self):
        armed = self._use_case.armed
        return "" if armed is None else f"T{armed.tool} correction armed, applied on Cycle Start"

    @pyqtProperty("QVariantList", notify=changed)
    def armedEffects(self):
        """What it does, a line per axis it changes, rich text:
        "- cuts 0.2 mm <b>smaller</b> on Ø", "- cuts 0.1 mm further
        toward Z-"."""
        armed = self._use_case.armed
        if armed is None:
            return []
        correction, lines = armed.correction, []
        if correction.changes_x:
            lines.append(f"- {_x_effect(correction, _mm(correction.dx))}")
        if correction.changes_z:
            lines.append(f"- cuts {_mm(correction.dz)} mm further toward {correction.z_side}")
        return lines

    @pyqtSlot()
    def editArmed(self):
        """The panel again, with the correction armed in it: Arm replaces it."""
        armed = self._use_case.armed
        if armed is not None:
            self._dx, self._dz = armed.correction.dx or None, armed.correction.dz or None
            self.changed.emit()

    @pyqtProperty(str, notify=changed)
    def appliedTitle(self):
        applied = self._use_case.last_applied
        return "" if applied is None else f"T{applied.tool} offsets corrected"

    @pyqtProperty("QVariantList", notify=changed)
    def appliedRows(self):
        """The tool's offsets before the correction and as the tool table has
        them now, a row per axis: {before, after, changed}."""
        applied = self._use_case.last_applied
        if applied is None:
            return []
        now = self._use_case.offsets(applied.tool)
        rows = []
        for axis, name, suffix, changed in ((0, "X", "(r)", applied.correction.changes_x),
                                            (1, "Z", "", applied.correction.changes_z)):
            before = "?" if applied.offsets is None else f"{applied.offsets[axis]:.3f}"
            after = "?" if now is None else f"{now[axis]:.3f}"
            rows.append({"before": f"{name}: {before}{suffix}", "after": f"{name}: {after}{suffix}",
                         "changed": changed})
        return rows

    @pyqtSlot(result=str)
    def arm(self):
        """Arm the correction; why it could not be, "" when armed."""
        error = self._use_case.arm(self._correction())
        if not error:
            self._dx = self._dz = None
        self.changed.emit()
        return error

    @pyqtSlot()
    def disarm(self):
        self._use_case.disarm()


def _number(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _value(offsets, axis) -> str:
    # as LinuxCNC keeps them: X a radius
    return "-" if offsets is None else f"{offsets[axis]:.3f}"


def _mm(value) -> str:
    """A length without trailing zeros: 0.2, 0.125, 1."""
    return f"{abs(value):.3f}".rstrip("0").rstrip(".")


def _x_effect(correction, amount: str) -> str:
    return f"cuts {amount} mm <b>{correction.diameter_effect}</b> on Ø"
