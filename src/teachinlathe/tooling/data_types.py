"""The tool library's domain model.

A tool LinuxCNC can use is two things put together: a ToolHolder - the
station on the turret or the gang plate, radial or axial - and the
CuttingTool clamped in it. Putting a cutting tool into a holder invalidates
whatever offsets the holder had, so the holder is not usable again until it
has been touched off.

Everything here maps one-to-one onto tool_holders.json and cutting_tools.json.
The enums carry the strings those files use, so the strings are written once,
here, and nowhere else. Serialisation is generic (see `to_json` and
`from_json`): adding a field to a dataclass is all it takes to persist it.
"""

from __future__ import annotations

import dataclasses
import types
import typing
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any, ClassVar, Dict, Optional, Type, TypeVar


# ── Enums ───────────────────────────────────────────────────────────────────


class CuttingToolType(str, Enum):
    """What kind of cutting tool, the category it is listed under, and what
    one of them is called.

    The heading and the name live on the member so they cannot drift apart
    from it.
    """

    def __new__(cls, value: str, label: str, tool_name: str):
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        member.tool_name = tool_name
        return member

    TURNING = "turning", "Turning Tools", "Turning Tool"
    BORING = "boring", "Boring Tools", "Boring Tool"
    BLADE = "blade", "Parting/Grooving/Trepanning", "Blade"
    THREADING = "threading", "Threading Tools", "Threading Tool"
    DRILLING = "drilling", "Drilling Tools", "Drill"
    REAMING = "reaming", "Reaming Tools", "Reamer"
    TAPPING = "tapping", "Tapping Tools", "Tap"


class HolderOrientation(str, Enum):
    RADIAL = "radial"
    AXIAL = "axial"


class ZOffsetPlace(str, Enum):
    """Which point of a blade the Z offset was taken from: its -1 corner,
    its middle (0) or its +1 corner."""

    LEFT = "-1"
    MIDDLE = "0"
    RIGHT = "1"


class TwistDirection(str, Enum):
    RIGHT_HAND = "right_hand"
    LEFT_HAND = "left_hand"


class SpindleDirection(IntEnum):
    CW = 1
    CCW = -1


# ── Generic JSON codec ──────────────────────────────────────────────────────

T = TypeVar("T")


def to_json(obj: Any) -> Any:
    """A dataclass, enum or plain value, as what json.dumps takes."""
    if hasattr(obj, "to_json") and not isinstance(obj, type):
        return obj.to_json()
    return _encode(obj)


def _encode(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_json(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_json(item) for item in obj]
    return obj


def from_json(cls: Type[T], raw: Dict[str, Any]) -> T:
    """Build a `cls` dataclass from its JSON dict.

    Keys the class does not know are ignored; keys it does not find get the
    field's default, which is how an older file keeps loading after a field
    is added.
    """
    hints = typing.get_type_hints(cls)
    kwargs = {}
    for f in dataclasses.fields(cls):
        if not f.init or f.name not in raw:
            continue
        kwargs[f.name] = _decode(hints[f.name], raw[f.name])
    return cls(**kwargs)


def _decode(hint: Any, raw: Any) -> Any:
    if raw is None:
        return None
    origin = typing.get_origin(hint)
    if origin in (typing.Union, types.UnionType):
        inner = [arg for arg in typing.get_args(hint) if arg is not type(None)]
        return _decode(inner[0], raw)
    if isinstance(hint, type):
        if issubclass(hint, Enum):
            return hint(raw)
        if dataclasses.is_dataclass(hint):
            return from_json(hint, raw)
        if hint is float:
            return float(raw)
    return raw


def _fmt(value: Optional[float]) -> str:
    return "-" if value is None else f"{value:g}"


# ── Cutting tool parts ──────────────────────────────────────────────────────


@dataclass
class InsertSpec:
    """An ISO insert designation, e.g. CCMT 06 02. The codes stay strings:
    "06" and "02" are designations, not numbers."""

    geometry: str = ""
    size: str = ""
    radius: str = ""

    def summary(self) -> str:
        return f"{self.geometry.upper()} {self.size} {self.radius}"


@dataclass
class SolidBody:
    """The body of a solid boring bar."""

    tip_angle: float = 0.0
    diameter: float = 0.0
    max_radial_undercut: float = 0.0


# ── Cutting tools ───────────────────────────────────────────────────────────


@dataclass(kw_only=True)
class CuttingTool:
    """What is clamped in a holder. Subclasses set TYPE and are registered
    by it, which is how `from_json` knows which class a "type" names."""

    TYPE: ClassVar[CuttingToolType]
    _registry: ClassVar[Dict[CuttingToolType, Type["CuttingTool"]]] = {}

    cutting_tool_id: int
    spindle_direction: SpindleDirection = SpindleDirection.CCW
    #: The operator's note on the tool, at most COMMENT_MAX_LENGTH characters.
    comment: str = ""

    COMMENT_MAX_LENGTH: ClassVar[int] = 200

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        tool_type = cls.__dict__.get("TYPE")
        if tool_type is not None:
            CuttingTool._registry[tool_type] = cls

    @classmethod
    def class_for(cls, tool_type: CuttingToolType) -> Type["CuttingTool"]:
        return cls._registry[tool_type]

    @property
    def tool_type(self) -> CuttingToolType:
        return self.TYPE

    def to_json(self) -> Dict[str, Any]:
        body = _encode(self)
        # Laid out as the files are: id and type first, then the comment -
        # only when there is one - and the spindle direction last.
        tool_id = body.pop("cutting_tool_id")
        spindle_direction = body.pop("spindle_direction")
        comment = body.pop("comment")
        return {"cutting_tool_id": tool_id, "type": self.TYPE.value,
                **body, **({"comment": comment} if comment else {}),
                "spindle_direction": spindle_direction}

    @staticmethod
    def from_json(raw: Dict[str, Any]) -> "CuttingTool":
        return from_json(CuttingTool.class_for(CuttingToolType(raw["type"])), raw)

    def summary(self) -> str:
        """One line describing the tool, for lists."""
        return f"#{self.cutting_tool_id} {self.details()} · {self.spindle_direction.name}"

    def details(self) -> str:
        raise NotImplementedError


@dataclass(kw_only=True)
class TurningTool(CuttingTool):
    TYPE: ClassVar[CuttingToolType] = CuttingToolType.TURNING

    insert: InsertSpec = dataclasses.field(default_factory=InsertSpec)
    orientation: int = 6
    front_angle: float = 0.0
    back_angle: float = 0.0

    def details(self) -> str:
        return f"{self.insert.summary()} · Q{self.orientation}"


@dataclass(kw_only=True)
class BoringTool(TurningTool):
    TYPE: ClassVar[CuttingToolType] = CuttingToolType.BORING

    solid_body: Optional[SolidBody] = None

    def details(self) -> str:
        text = super().details()
        if self.solid_body is not None:
            text += f" · Ø{_fmt(self.solid_body.diameter)}"
        return text


@dataclass(kw_only=True)
class BladeTool(CuttingTool):
    TYPE: ClassVar[CuttingToolType] = CuttingToolType.BLADE

    blade_width: float = 0.0
    left_radius: float = 0.0
    right_radius: float = 0.0
    orientation: int = 6

    def details(self) -> str:
        return (f"width {_fmt(self.blade_width)} · R{_fmt(self.left_radius)}"
                f"/R{_fmt(self.right_radius)} · Q{self.orientation}")


@dataclass(kw_only=True)
class ThreadingTool(CuttingTool):
    TYPE: ClassVar[CuttingToolType] = CuttingToolType.THREADING

    insert: InsertSpec = dataclasses.field(default_factory=InsertSpec)
    orientation: int = 6
    #: A full-profile insert cuts one pitch, in mm.
    pitch: float = 1.5

    def details(self) -> str:
        return f"{self.insert.summary()} · P{_fmt(self.pitch)} · Q{self.orientation}"


@dataclass(kw_only=True)
class DrillingTool(CuttingTool):
    TYPE: ClassVar[CuttingToolType] = CuttingToolType.DRILLING

    diameter: float = 0.0
    tip_angle: float = 118.0
    twist_direction: TwistDirection = TwistDirection.RIGHT_HAND

    def details(self) -> str:
        return f"Ø{_fmt(self.diameter)} · {_fmt(self.tip_angle)}°"


@dataclass(kw_only=True)
class ReamingTool(CuttingTool):
    TYPE: ClassVar[CuttingToolType] = CuttingToolType.REAMING

    diameter: float = 0.0

    def details(self) -> str:
        return f"Ø{_fmt(self.diameter)}"


@dataclass(kw_only=True)
class TappingTool(CuttingTool):
    TYPE: ClassVar[CuttingToolType] = CuttingToolType.TAPPING

    diameter: float = 0.0
    pitch: float = 0.0
    twist_direction: TwistDirection = TwistDirection.RIGHT_HAND

    def details(self) -> str:
        return f"M{_fmt(self.diameter)}x{_fmt(self.pitch)}"


# ── Tool holders ────────────────────────────────────────────────────────────


@dataclass
class ToolHolder:
    """A station a cutting tool is clamped in.

    The offsets belong to the holder *with* its cutting tool: they are
    cleared whenever the cutting tool changes, and the holder cannot be used
    until they are set again. `z_offset_place` is only meaningful for
    blades, which can be touched off on either corner or in the middle.

    The holder is the tool LinuxCNC knows as T<tool_holder_id>: it is what
    the tool table is written from. `last_loaded` is when it last went into
    the spindle, a Unix time, for the recently used list.
    """

    tool_holder_id: int
    orientation: HolderOrientation = HolderOrientation.RADIAL
    cutting_tool_id: Optional[int] = None
    x_offset: Optional[float] = None
    z_offset: Optional[float] = None
    z_offset_place: Optional[ZOffsetPlace] = None
    last_loaded: Optional[float] = None

    def mount(self, cutting_tool_id: Optional[int]) -> None:
        """Clamp another cutting tool in (None empties the holder). Offsets
        taken with the previous tool no longer apply."""
        self.cutting_tool_id = cutting_tool_id
        self.x_offset = None
        self.z_offset = None
        self.z_offset_place = None

    @property
    def has_tool(self) -> bool:
        return self.cutting_tool_id is not None

    @property
    def is_ready(self) -> bool:
        return self.has_tool and self.x_offset is not None and self.z_offset is not None
