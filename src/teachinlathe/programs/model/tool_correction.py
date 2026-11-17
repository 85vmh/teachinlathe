"""A correction of the current loaded tool, entered while the program waits
at an M1 (subroutines/m1_remap.ngc): what the remap is to add to the tool's
offsets with G10 L1 after Cycle Start.

``dx`` is a diameter, ``dz`` a shift along Z, both mm and both where the tool
cuts: a part 0.04 too big on the diameter is ``dx = -0.04`` - the X offset, a
radius, loses 0.02 - and ``dz = -0.02`` makes it cut 0.02 further toward Z-.
"""

from __future__ import annotations

from dataclasses import dataclass

#: mm: the largest correction either way. The remap aborts past it
#: (#<max_correction> in subroutines/m1_remap.ngc): keep the two the same.
MAX_CORRECTION = 1.0

#: Smaller than this is no correction at all.
_NOTHING = 0.0005


@dataclass(frozen=True)
class ToolCorrection:
    dx: float = 0.0     # diameter, mm
    dz: float = 0.0     # mm

    @property
    def changes_x(self) -> bool:
        return abs(self.dx) >= _NOTHING

    @property
    def changes_z(self) -> bool:
        return abs(self.dz) >= _NOTHING

    @property
    def empty(self) -> bool:
        return not (self.changes_x or self.changes_z)

    @property
    def diameter_effect(self) -> str:
        """"smaller" or "bigger": what dx does to the diameter."""
        return "smaller" if self.dx < 0 else "bigger"

    @property
    def z_side(self) -> str:
        """"Z-" or "Z+": where dz moves the cut."""
        return "Z-" if self.dz < 0 else "Z+"


def check(correction: ToolCorrection) -> str:
    """Why the correction cannot be applied, "" when it can."""
    if correction.empty:
        return "No correction: the part is as it should be"
    if abs(correction.dx) > MAX_CORRECTION:
        return f"X correction over {MAX_CORRECTION:.3f} mm on the diameter"
    if abs(correction.dz) > MAX_CORRECTION:
        return f"Z correction over {MAX_CORRECTION:.3f} mm"
    return ""


def corrected_offsets(x: float, z: float, correction: ToolCorrection):
    """The tool's offsets as the remap leaves them: X a radius, as LinuxCNC
    keeps it, so it takes half of ``dx``."""
    return x + correction.dx / 2.0, z + correction.dz
