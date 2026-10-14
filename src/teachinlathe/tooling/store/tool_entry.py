"""Tool data model.

ToolEntry maps 1:1 to LinuxCNC .tbl fields.
Subclasses carry extra fields stored in tools_extras.json.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ToolType(str, Enum):
    GENERIC       = "generic"
    DRILL         = "drill"
    REAMER        = "reamer"
    TAP           = "tap"
    BORING_BAR    = "boring_bar"
    TREPANING     = "trepaning"
    PARTING_BLADE = "parting_blade"
    GROOVING_BLADE = "grooving_blade"


class SortBy(Enum):
    NUMBER    = "number"
    LAST_USED = "last_used"


# ---------------------------------------------------------------------------
# Base — mirrors the 16 LinuxCNC .tbl columns
# ---------------------------------------------------------------------------

@dataclass
class ToolEntry:
    t: int            = 0      # tool number
    p: int            = 0      # pocket
    x: float          = 0.0    # X offset
    y: float          = 0.0    # Y offset
    z: float          = 0.0    # Z offset
    a: float          = 0.0
    b: float          = 0.0
    c: float          = 0.0
    u: float          = 0.0
    v: float          = 0.0
    w: float          = 0.0
    d: float          = 0.0    # tip radius / diameter (T field in GUI)
    i: float          = 0.0    # front angle
    j: float          = 0.0    # back angle
    q: int            = 1      # orientation (1-9)
    r: str            = ""     # comment / remark
    last_loaded: Optional[float] = None  # Unix timestamp; None = never loaded

    @property
    def tool_type(self) -> ToolType:
        return ToolType.GENERIC

    def to_tbl_line(self) -> str:
        """Serialise to a single .tbl text line."""
        parts = [
            f"T{self.t}",
            f"P{self.p}",
            f"X{self.x:.4f}",
            f"Y{self.y:.4f}",
            f"Z{self.z:.4f}",
            f"A{self.a:.4f}",
            f"B{self.b:.4f}",
            f"C{self.c:.4f}",
            f"U{self.u:.4f}",
            f"V{self.v:.4f}",
            f"W{self.w:.4f}",
            f"D{self.d:.4f}",
            f"I{self.i:.4f}",
            f"J{self.j:.4f}",
            f"Q{self.q}",
            f";{self.r}",
        ]
        return " ".join(parts)

    def to_extras_dict(self) -> dict:
        """Fields stored in tools_extras.json (subclasses extend this)."""
        d: dict = {"tool_type": self.tool_type.value}
        if self.last_loaded is not None:
            d["last_loaded"] = self.last_loaded
        return d

    def to_display_dict(self) -> dict:
        """Flat dict for QML — mirrors the old provider format plus extras."""
        return {
            "t": self.t,
            "p": self.p,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "a": self.a,
            "b": self.b,
            "c": self.c,
            "u": self.u,
            "v": self.v,
            "w": self.w,
            "d": self.d,
            "i": self.i,
            "j": self.j,
            "q": self.q,
            "r": self.r,
            "tool_type": self.tool_type.value,
            "last_loaded": self.last_loaded,
            "isCurrent": False,  # set by repository
        }


# ---------------------------------------------------------------------------
# Subclasses
# ---------------------------------------------------------------------------

@dataclass
class DrillTool(ToolEntry):
    diameter: float = 0.0
    material: str   = ""
    length:   float = 0.0

    @property
    def tool_type(self) -> ToolType:
        return ToolType.DRILL

    def to_extras_dict(self) -> dict:
        d = super().to_extras_dict()
        d.update({"diameter": self.diameter, "material": self.material, "length": self.length})
        return d

    def to_display_dict(self) -> dict:
        d = super().to_display_dict()
        d.update({"diameter": self.diameter, "material": self.material, "length": self.length})
        return d


@dataclass
class ReamerTool(ToolEntry):
    diameter: float = 0.0
    material: str   = ""
    length:   float = 0.0

    @property
    def tool_type(self) -> ToolType:
        return ToolType.REAMER

    def to_extras_dict(self) -> dict:
        d = super().to_extras_dict()
        d.update({"diameter": self.diameter, "material": self.material, "length": self.length})
        return d

    def to_display_dict(self) -> dict:
        d = super().to_display_dict()
        d.update({"diameter": self.diameter, "material": self.material, "length": self.length})
        return d


@dataclass
class TapTool(ToolEntry):
    diameter: float = 0.0
    pitch:    float = 0.0

    @property
    def tool_type(self) -> ToolType:
        return ToolType.TAP

    def to_extras_dict(self) -> dict:
        d = super().to_extras_dict()
        d.update({"diameter": self.diameter, "pitch": self.pitch})
        return d

    def to_display_dict(self) -> dict:
        d = super().to_display_dict()
        d.update({"diameter": self.diameter, "pitch": self.pitch})
        return d


@dataclass
class BoringBarTool(ToolEntry):
    min_diameter: float = 0.0
    max_undercut: float = 0.0
    max_depth:    float = 0.0

    @property
    def tool_type(self) -> ToolType:
        return ToolType.BORING_BAR

    def to_extras_dict(self) -> dict:
        d = super().to_extras_dict()
        d.update({"min_diameter": self.min_diameter, "max_undercut": self.max_undercut, "max_depth": self.max_depth})
        return d

    def to_display_dict(self) -> dict:
        d = super().to_display_dict()
        d.update({"min_diameter": self.min_diameter, "max_undercut": self.max_undercut, "max_depth": self.max_depth})
        return d


@dataclass
class TrepaningTool(ToolEntry):
    diameter: float = 0.0

    @property
    def tool_type(self) -> ToolType:
        return ToolType.TREPANING

    def to_extras_dict(self) -> dict:
        d = super().to_extras_dict()
        d.update({"diameter": self.diameter})
        return d

    def to_display_dict(self) -> dict:
        d = super().to_display_dict()
        d.update({"diameter": self.diameter})
        return d


@dataclass
class PartingBladeTool(ToolEntry):
    width:        float = 0.0
    max_depth:    float = 0.0
    left_radius:  float = 0.0
    right_radius: float = 0.0
    z0_reference: str = "center"

    @property
    def tool_type(self) -> ToolType:
        return ToolType.PARTING_BLADE

    def to_extras_dict(self) -> dict:
        d = super().to_extras_dict()
        d.update({
            "width": self.width, "max_depth": self.max_depth,
            "left_radius": self.left_radius, "right_radius": self.right_radius,
            "z0_reference": self.z0_reference,
        })
        return d

    def to_display_dict(self) -> dict:
        d = super().to_display_dict()
        d.update({
            "width": self.width, "max_depth": self.max_depth,
            "left_radius": self.left_radius, "right_radius": self.right_radius,
            "z0_reference": self.z0_reference,
        })
        return d


@dataclass
class GroovingBladeTool(PartingBladeTool):
    @property
    def tool_type(self) -> ToolType:
        return ToolType.GROOVING_BLADE


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_TYPE_CLASS = {
    ToolType.GENERIC:       ToolEntry,
    ToolType.DRILL:         DrillTool,
    ToolType.REAMER:        ReamerTool,
    ToolType.TAP:           TapTool,
    ToolType.BORING_BAR:    BoringBarTool,
    ToolType.TREPANING:     TrepaningTool,
    ToolType.PARTING_BLADE: PartingBladeTool,
    ToolType.GROOVING_BLADE: GroovingBladeTool,
}

#: Extra fields expected by each subclass (used by the factory to copy them)
_EXTRA_FIELDS = {
    ToolType.DRILL:         ("diameter", "material", "length"),
    ToolType.REAMER:        ("diameter", "material", "length"),
    ToolType.TAP:           ("diameter", "pitch"),
    ToolType.BORING_BAR:    ("min_diameter", "max_undercut", "max_depth"),
    ToolType.TREPANING:     ("diameter",),
    ToolType.PARTING_BLADE: ("width", "max_depth", "left_radius", "right_radius", "z0_reference"),
    ToolType.GROOVING_BLADE: ("width", "max_depth", "left_radius", "right_radius", "z0_reference"),
}


def make_tool(base: ToolEntry, tool_type: ToolType, extras: dict) -> ToolEntry:
    """Promote a ToolEntry to the appropriate subclass, filling in extras."""
    cls = _TYPE_CLASS.get(tool_type, ToolEntry)
    if cls is ToolEntry:
        return base
    base_fields = {f.name: getattr(base, f.name) for f in dataclasses.fields(ToolEntry)}
    extra_keys   = _EXTRA_FIELDS.get(tool_type, ())
    extra_values = {
        k: extras.get(k, "center" if k == "z0_reference" else 0.0 if k != "material" else "")
        for k in extra_keys
    }
    return cls(**base_fields, **extra_values)
