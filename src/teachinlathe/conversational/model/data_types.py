import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar, Dict, List, Optional, Type

from teachinlathe.tooling.model.data_types import SpindleDirection


class MoveSequence(Enum):
    XZ = "xz"
    ZX = "zx"
    BOTH = "both"


class Strategy(Enum):
    ROUGH = "rough"
    FINISH = "finish"


class SpindleMode(str, Enum):
    RPM = "rpm"
    CSS = "css"


class ThreadLocation(Enum):
    OD = "OD"
    ID = "ID"


class ThreadForm(str, Enum):
    """A thread's form - its profile. Each has the included angle of its
    flanks (``angle``, degrees); more forms to come."""
    METRIC = "metric"
    WHITWORTH = "whitworth"

    @property
    def angle(self) -> float:
        return THREAD_FORM_ANGLES[self]


#: The included angle between a thread's flanks, degrees, by form.
THREAD_FORM_ANGLES = {
    ThreadForm.METRIC: 60.0,
    ThreadForm.WHITWORTH: 55.0,
}


class G33ThreadPassType(str, Enum):
    ROUGHING = "ROUGHING"
    SPRING = "SPRING"


class BlendType(Enum):
    NONE = "none"
    CHAMFER = "chamfer"
    FILLET = "fillet"
    UNDERCUT_DIN509 = "undercut_din509"


class PredefinedPosition(str, Enum):
    G28 = "G28"
    G30 = "G30"


class InspectPosition(str, Enum):
    """Where Pause to Inspect stops: at the position stored in G28, at G30's,
    or where the tool is (IN_PLACE - offered by Drilling and Tapping)."""
    G28 = "G28"
    G30 = "G30"
    IN_PLACE = "IN_PLACE"


class AfterLastOperation(str, Enum):
    DO_NOTHING = "do_nothing"
    G28 = "g28"
    G30 = "g30"

    @property
    def gcode(self) -> str:
        """Word emitted before M30; empty when nothing should be done."""
        return "" if self is AfterLastOperation.DO_NOTHING else self.value.upper()


class ProfilingType(str, Enum):
    OD = "od"
    ID = "id"


class PassType(str, Enum):
    AXIAL = "axial"
    RADIAL = "radial"
    DIAGONAL_INTERIOR = "diagonal_interior"
    DIAGONAL_EXTERIOR = "diagonal_exterior"


class GrooveRoughingStrategy(str, Enum):
    START_RIGHT = "start_right"
    START_LEFT = "start_left"
    START_CENTER = "start_center"


class GrooveFinishingStrategy(str, Enum):
    TOWARDS_LEFT = "towards_left"
    TOWARDS_RIGHT = "towards_right"
    TOWARDS_CENTER = "towards_center"


# ------------------------------ Core header ----------------------------------

@dataclass
class Workpiece:
    material: str
    external_diameter: float
    internal_diameter: float
    stickout_length: float
    stock_length: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Workpiece":
        return Workpiece(
            material=str(data.get("material", "")),
            external_diameter=float(data.get("external_diameter", 0.0) or 0.0),
            internal_diameter=float(data.get("internal_diameter", 0.0) or 0.0),
            stickout_length=float(data.get("stickout_length", 0.0) or 0.0),
            stock_length=float(data.get("stock_length", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material": self.material,
            "external_diameter": self.external_diameter,
            "internal_diameter": self.internal_diameter,
            "stickout_length": self.stickout_length,
            "stock_length": self.stock_length,
        }


@dataclass
class Header:
    name: str
    created_date: str
    last_edit: str
    datum: int  # the work offset's P number, 1 (G54) .. 6 (G59); saved as "G54".."G59"
    units: str
    workpiece: Workpiece
    after_last_operation: AfterLastOperation = AfterLastOperation.DO_NOTHING
    # order of the operation open when G-code was last generated; 0 = header
    last_operation: int = 0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Header":
        created_date = data.get("created_date")
        if created_date is None:
            created_date = data.get("last_edit", "")
        try:
            after_last = AfterLastOperation(
                str(data.get("after_last_operation", AfterLastOperation.DO_NOTHING.value)).lower())
        except ValueError:
            after_last = AfterLastOperation.DO_NOTHING
        try:
            last_operation = int(data.get("last_operation", 0) or 0)
        except (TypeError, ValueError):
            last_operation = 0
        return Header(
            name=data["name"],
            created_date=str(created_date),
            last_edit=data["last_edit"],
            datum=Header.datum_from_value(data["datum"]),
            units=data["units"],
            workpiece=Workpiece.from_dict(data["workpiece"]),
            after_last_operation=after_last,
            last_operation=last_operation
        )

    @staticmethod
    def datum_from_value(value: Any) -> int:
        """P number from "G54".."G59", or from the bare 1..6 older programs saved."""
        try:
            text = str(value).strip().upper()
            number = int(text[1:]) - 53 if text.startswith("G") else int(text)
        except (TypeError, ValueError):
            return 1
        return number if 1 <= number <= 6 else 1

    @property
    def datum_code(self) -> str:
        return f"G{53 + int(self.datum)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "created_date": self.created_date,
            "last_edit": self.last_edit,
            "datum": self.datum_code,
            "units": self.units,
            "after_last_operation": self.after_last_operation.value,
            "last_operation": self.last_operation,
            "workpiece": self.workpiece.to_dict()
        }


def _od_or_id(profiling_type) -> str:
    """"OD" or "ID", as an operation's name says which side it cuts."""
    return "ID" if ProfilingType(profiling_type) is ProfilingType.ID else "OD"


# ---------------------------- Base Operation ---------------------------------

@dataclass
class Operation:
    order: int
    type: str
    generate_gcode: bool
    is_optional_block: bool

    @classmethod
    def from_dict(cls, data: dict) -> "Operation":
        op_type = data.get("type")
        if op_type not in operation_types:
            raise ValueError(f"Unknown operation type: {op_type}")
        op = operation_types[op_type].from_dict(data)
        if isinstance(op, TurnableOperation):
            ref = data.get("tool_ref")
            op.toolRef = int(ref) if ref is not None else None
        return op

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return type(self).__name__

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "type": self.type,
            "generate_gcode": self.generate_gcode,
            "is_optional_block": self.is_optional_block
        }


# --------------------------- Speeds and feeds --------------------------------

@dataclass
class SpeedsAndFeeds:
    """How an operation turns the spindle and feeds the tool: the way it
    turns (M3 / M4), its speed - RPM, or CSS up to a maximum - and the feed,
    mm/rev: ``feed_rate`` for every operation that feeds (not a threading,
    a tapping or a knurling: they go by the pitch), ``feed_rate_2`` Parting's
    second, from Second Feed X on."""
    direction: SpindleDirection
    mode: SpindleMode
    rpm_value: Optional[int] = None
    css_value: Optional[int] = None
    css_max_speed: Optional[int] = None
    feed_rate: Optional[float] = None
    feed_rate_2: Optional[float] = None

    DEFAULT_RPM = 1000
    DEFAULT_CSS_VALUE = 100
    DEFAULT_CSS_MAX = 1000
    #: mm/rev an operation that feeds is cut at while it has no feed set
    DEFAULT_FEED_RATE = 0.1

    @property
    def feed(self) -> float:
        """The feed, mm/rev: ``feed_rate``, DEFAULT_FEED_RATE with none."""
        return float(self.feed_rate) if self.feed_rate is not None else self.DEFAULT_FEED_RATE

    @property
    def sign(self) -> int:
        """The direction as the subroutines take it: 1 M3, -1 M4."""
        return 1 if self.direction == SpindleDirection.M3 else -1

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SpeedsAndFeeds":
        if not isinstance(data, dict):
            raise ValueError("Speeds and feeds must be an object")
        mode_str = data.get("mode")
        if mode_str not in (m.value for m in SpindleMode):
            raise ValueError(f"Invalid spindle mode: {mode_str!r}")

        def as_opt_int(v):
            return None if v is None or (isinstance(v, str) and v.strip() == "") else int(v)

        def as_opt_float(v):
            return None if v is None or (isinstance(v, str) and v.strip() == "") else float(v)

        return SpeedsAndFeeds(
            direction=SpindleDirection[str(data.get("direction", SpindleDirection.M4.name))],
            mode=SpindleMode(mode_str),
            rpm_value=as_opt_int(data.get("rpm_value")),
            css_value=as_opt_int(data.get("css_value")),
            css_max_speed=as_opt_int(data.get("css_max_speed")),
            feed_rate=as_opt_float(data.get("feed_rate")),
            feed_rate_2=as_opt_float(data.get("feed_rate_2")),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "direction": self.direction.name,
            "mode": self.mode.value,
        }
        if self.rpm_value is not None:
            out["rpm_value"] = int(self.rpm_value)
        if self.css_value is not None:
            out["css_value"] = int(self.css_value)
        if self.css_max_speed is not None:
            out["css_max_speed"] = int(self.css_max_speed)
        if self.feed_rate is not None:
            out["feed_rate"] = float(self.feed_rate)
        if self.feed_rate_2 is not None:
            out["feed_rate_2"] = float(self.feed_rate_2)
        return out

# --------- TurnableOperation: all spindle-using ops inherit from this --------

@dataclass
class TurnableOperation(Operation):
    """An operation that cuts, so needs a tool: ``toolRef``, the id of one of
    the program's tools (Program.tools); None while none is chosen."""
    speedsAndFeeds: SpeedsAndFeeds
    toolRef: Optional[int] = field(default=None, kw_only=True)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        if self.toolRef is not None:
            base["tool_ref"] = int(self.toolRef)
        return base

    @staticmethod
    def _parse_speeds_and_feeds(data: Dict[str, Any]) -> SpeedsAndFeeds:
        sf = data.get("speeds_and_feeds")
        if sf is None:
            raise ValueError("Missing required 'speeds_and_feeds' block for turnable operation")
        return SpeedsAndFeeds.from_dict(sf)

    def _add_speeds_and_feeds_to(self, base: Dict[str, Any]) -> Dict[str, Any]:
        base["speeds_and_feeds"] = self.speedsAndFeeds.to_dict()
        return base


# --------------------------- Tool change (no spindle) ------------------------

@dataclass
class PositionDetails:
    x_pos: float
    z_pos: float
    move_sequence: MoveSequence
    stop_spindle_before_positioning: bool = False
    include_m0: bool = False

    def __post_init__(self):
        if isinstance(self.move_sequence, str):
            val = self.move_sequence.strip().lower()
            self.move_sequence = {
                "xz": MoveSequence.XZ,
                "zx": MoveSequence.ZX,
                "both": MoveSequence.BOTH,
                "simultaneous": MoveSequence.BOTH,  # compatibility
            }.get(val, MoveSequence.XZ)

    @staticmethod
    def coerce(obj: Any) -> "PositionDetails":
        """Accept dict or PositionDetails and always return PositionDetails instance."""
        if isinstance(obj, PositionDetails):
            obj.__post_init__()
            return obj
        if isinstance(obj, dict):
            data = dict(obj)
            # defaults (tolerant)
            x_pos = float(data.get("x_pos", 0.0))
            z_pos = float(data.get("z_pos", 0.0))
            move_sequence = data.get("move_sequence", "xz")
            stop_spindle_before_positioning = bool(data.get("stop_spindle_before_positioning", False))
            include_m0 = bool(data.get("include_m0", False))
            return PositionDetails(
                x_pos=x_pos,
                z_pos=z_pos,
                move_sequence=move_sequence,
                stop_spindle_before_positioning=stop_spindle_before_positioning,
                include_m0=include_m0,
            )
        raise TypeError("PositionDetails.coerce expects dict or PositionDetails")

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PositionDetails":
        return PositionDetails.coerce(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x_pos": float(self.x_pos),
            "z_pos": float(self.z_pos),
            "move_sequence": self.move_sequence.value,
            "stop_spindle_before_positioning": bool(self.stop_spindle_before_positioning),
            "include_m0": bool(self.include_m0),
        }


@dataclass
class PositionAt(Operation):
    position_details: PositionDetails

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PositionAt":
        details = PositionDetails.from_dict(data.get("position_details", {}))
        return PositionAt(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            position_details=details,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        details = PositionDetails.coerce(self.position_details)
        base.update({
            "position_details": details.to_dict()
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return "Position At"


# ----------------------------- M1 Parameters ---------------------------------

@dataclass
class M1Parameters:
    include_m1: bool
    inspect_position: InspectPosition
    stop_spindle: bool

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "M1Parameters":
        # backward compat: old JSON had x_inspect/z_inspect instead of inspect_position
        inspect_raw = str(data.get("inspect_position", InspectPosition.G28.value)).upper()
        try:
            inspect_position = InspectPosition(inspect_raw)
        except ValueError:
            inspect_position = InspectPosition.G28
        return M1Parameters(
            include_m1=bool(data.get("include_m1", True)),
            inspect_position=inspect_position,
            stop_spindle=bool(data.get("stop_spindle", False))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "include_m1": bool(self.include_m1),
            "inspect_position": self.inspect_position.value,
            "stop_spindle": bool(self.stop_spindle)
        }


# ---------------------- Cutting / Geometry Parameters ------------------------

@dataclass
class CuttingParameters:
    retract: float
    doc: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CuttingParameters":
        return CuttingParameters(
            retract=float(data.get("retract", 0.0)),
            doc=float(data.get("doc", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc": float(self.doc),
            "retract": float(self.retract),
        }


@dataclass
class KnurlingCuttingParameters:
    doc: float
    retract: float
    groovesCount: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "KnurlingCuttingParameters":
        return KnurlingCuttingParameters(
            doc=float(data.get("doc", 0.0) or 0.0),
            retract=float(data.get("retract", 0.0) or 0.0),
            groovesCount=int(data.get("grooves_count", 1) or 1),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc": float(self.doc),
            "retract": float(self.retract),
            "grooves_count": int(self.groovesCount),
        }


@dataclass
class GrooveRoughingCuttingParameters:
    peckDepth: float
    retract: float
    dwellTime: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GrooveRoughingCuttingParameters":
        return GrooveRoughingCuttingParameters(
            peckDepth=float(data.get("peck_depth", 0.0) or 0.0),
            retract=float(data.get("retract", 0.0) or 0.0),
            dwellTime=float(data.get("dwell_time", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peck_depth": float(self.peckDepth),
            "retract": float(self.retract),
            "dwell_time": float(self.dwellTime),
        }


@dataclass
class GrooveFinishingCuttingParameters:
    retract: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GrooveFinishingCuttingParameters":
        return GrooveFinishingCuttingParameters(
            retract=float(data.get("retract", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retract": float(self.retract),
        }


@dataclass
class GeometryParameters:
    xStart: float = 0.0
    zStart: float = 0.0
    xEnd: float = 0.0
    zEnd: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GeometryParameters":
        return GeometryParameters(
            xStart=float(data.get("x_start", 0.0) or 0.0),
            zStart=float(data.get("z_start", 0.0) or 0.0),
            xEnd=float(data.get("x_end", 0.0) or 0.0),
            zEnd=float(data.get("z_end", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "x_start": float(self.xStart),
            "z_start": float(self.zStart),
            "z_end": float(self.zEnd),
            "x_end": float(self.xEnd)
        }
        return out


@dataclass
class KnurlingGeometryParameters:
    zStart: float = 0.0
    zEnd: float = 0.0
    xStart: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "KnurlingGeometryParameters":
        return KnurlingGeometryParameters(
            zStart=float(data.get("z_start", 0.0) or 0.0),
            zEnd=float(data.get("z_end", 0.0) or 0.0),
            xStart=float(data.get("x_start", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "z_start": float(self.zStart),
            "z_end": float(self.zEnd),
            "x_start": float(self.xStart),
        }

@dataclass
class DrillingParameters:
    zStart: float = 0.0
    zEnd: float = 0.0
    # how far in front of Z Start the drill starts and every peck retracts
    # to, always positive
    toolClearance: float = 0.0
    peckDepth: float = 0.0
    # seconds at the bottom of each peck
    dwellTime: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DrillingParameters":
        return DrillingParameters(
            zStart=float(data.get("z_start", 0.0) or 0.0),
            zEnd=float(data.get("z_end", 0.0) or 0.0),
            toolClearance=abs(float(data.get("tool_clearance", 0.0) or 0.0)),
            peckDepth=float(data.get("peck_depth", 0.0) or 0.0),
            dwellTime=float(data.get("dwell_time", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "z_start": float(self.zStart),
            "z_end": float(self.zEnd),
            "tool_clearance": float(self.toolClearance),
            "peck_depth": float(self.peckDepth),
            "dwell_time": float(self.dwellTime),
        }
        return out

@dataclass
class TappingParameters:
    zStart: float = 0.0
    zEnd: float = 0.0
    # how far in front of Z Start the tap starts and every peck comes back
    # to, always positive
    toolClearance: float = 0.0
    peckDepth: float = 0.0
    # the tap's, as the Tool Library had it when last edited; the G-code
    # takes the pitch of the tap it cuts with when it can
    # find it
    pitch: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TappingParameters":
        return TappingParameters(
            zStart=float(data.get("z_start", 0.0) or 0.0),
            zEnd=float(data.get("z_end", 0.0) or 0.0),
            toolClearance=abs(float(data.get("tool_clearance", 0.0) or 0.0)),
            peckDepth=float(data.get("peck_depth", 0.0) or 0.0),
            pitch=float(data.get("pitch", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "z_start": float(self.zStart),
            "z_end": float(self.zEnd),
            "tool_clearance": float(self.toolClearance),
            "peck_depth": float(self.peckDepth),
            "pitch": float(self.pitch)
        }
        return out

@dataclass
class PartingParameters:
    xStart: float = 0.0
    xEnd: float = 0.0
    zPos: float = 0.0
    second_feed_x_pos: float = 0.0
    x_clearance: float = 1.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PartingParameters":
        return PartingParameters(
            xStart=float(data.get("x_start", 0.0) or 0.0),
            xEnd=float(data.get("x_end", 0.0) or 0.0),
            zPos=float(data.get("z_pos", 0.0) or 0.0),
            second_feed_x_pos=float(data.get("second_feed_x_pos", 0.0) or 0.0),
            x_clearance=float(data.get("x_clearance", 1.0) or 1.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "x_start": float(self.xStart),
            "x_end": float(self.xEnd),
            "z_pos" : float(self.zPos),
            "second_feed_x_pos": float(self.second_feed_x_pos),
            "x_clearance": float(self.x_clearance),
        }
        return out


@dataclass
class ProfilingParameters:
    profile_id: int
    xStart: float
    zStart: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProfilingParameters":
        return ProfilingParameters(
            profile_id=int(data.get("profile_id", 0)),
            xStart=float(data.get("x_start", 0.0)),
            zStart=float(data.get("z_start", 0.0))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": int(self.profile_id),
            "x_start": float(self.xStart),
            "z_start": float(self.zStart)
        }


@dataclass
class ProfilingOptions:
    strategy: Strategy
    stockToLeaveX: float
    stockToLeaveZ: float
    finishPasses: int
    finishSpringPasses: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProfilingOptions":
        strat = data.get("strategy", "rough")
        strat_enum = Strategy(str(strat).lower()) if isinstance(strat, str) else Strategy.ROUGH
        if isinstance(strat, str):
            try:
                strat_enum = Strategy[str(strat).upper()]
            except Exception:
                strat_enum = Strategy(str(strat).lower())

        return ProfilingOptions(
            strategy=strat_enum,
            stockToLeaveX=float(data.get("radial", 0.0)),
            stockToLeaveZ=float(data.get("axial", 0.0)),
            finishPasses=int(data.get("finish_passes", 1) or 1),
            finishSpringPasses=int(data.get("finish_spring_passes", 0))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "radial": float(self.stockToLeaveX),
            "axial": float(self.stockToLeaveZ),
            "finish_passes": int(self.finishPasses),
            "finish_spring_passes": int(self.finishSpringPasses)
        }


@dataclass
class ProfileRoughingStrategy:
    profiling_type: ProfilingType
    pass_type: PassType

    _OD_PASS_TYPES = {PassType.AXIAL, PassType.RADIAL}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProfileRoughingStrategy":
        pt_raw = str(data.get("profiling_type", "od")).lower()
        try:
            profiling_type = ProfilingType(pt_raw)
        except ValueError:
            profiling_type = ProfilingType.OD

        pp_raw = str(data.get("pass_type", "axial")).lower()
        try:
            pass_type = PassType(pp_raw)
        except ValueError:
            pass_type = PassType.AXIAL

        if profiling_type == ProfilingType.OD and pass_type not in {PassType.AXIAL, PassType.RADIAL}:
            pass_type = PassType.AXIAL

        return ProfileRoughingStrategy(profiling_type=profiling_type, pass_type=pass_type)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profiling_type": self.profiling_type.value,
            "pass_type": self.pass_type.value,
        }


@dataclass
class ProfileContourStrategy:
    profiling_type: ProfilingType

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProfileContourStrategy":
        pt_raw = str(data.get("profiling_type", "od")).lower()
        try:
            profiling_type = ProfilingType(pt_raw)
        except ValueError:
            profiling_type = ProfilingType.OD
        return ProfileContourStrategy(profiling_type=profiling_type)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profiling_type": self.profiling_type.value,
        }


@dataclass
class StockToLeave:
    stockToLeaveX: float
    stockToLeaveZ: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StockToLeave":
        return StockToLeave(
            stockToLeaveX=float(data.get("radial", 0.0)),
            stockToLeaveZ=float(data.get("axial", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "radial": float(self.stockToLeaveX),
            "axial": float(self.stockToLeaveZ),
        }


# ------------------------------- Facing --------------------------------------

@dataclass
class Facing(TurnableOperation):
    cuttingParameters: CuttingParameters
    geometryParameters: GeometryParameters
    m1Parameters: M1Parameters
    zEndBecomesNewZ0: bool

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Facing":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)

        cutting_parameters = CuttingParameters.from_dict(data.get("cutting_parameters", {}))
        geometry_parameters = GeometryParameters.from_dict(data.get("geometry_parameters", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return Facing(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            cuttingParameters=cutting_parameters,
            geometryParameters=geometry_parameters,
            m1Parameters=m1_parameters,
            zEndBecomesNewZ0=bool(data.get("z_end_becomes_new_z0", False))
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "geometry_parameters": self.geometryParameters.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
            "z_end_becomes_new_z0": bool(self.zEndBecomesNewZ0)
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return "Facing"


@dataclass
class Knurling(TurnableOperation):
    cuttingParameters: KnurlingCuttingParameters
    geometryParameters: KnurlingGeometryParameters
    m1Parameters: M1Parameters

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Knurling":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)
        cutting_parameters = KnurlingCuttingParameters.from_dict(data.get("cutting_parameters", {}))
        geometry_parameters = KnurlingGeometryParameters.from_dict(data.get("geometry_parameters", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return Knurling(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            cuttingParameters=cutting_parameters,
            geometryParameters=geometry_parameters,
            m1Parameters=m1_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "geometry_parameters": self.geometryParameters.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return "SinglePoint Knurling"


# ----------------------- Profile Primitives ----------------------------------

@dataclass
class ProfileBlend:
    blend_type:    BlendType
    chamfer_width: float = 0.0
    fillet_radius: float = 0.0
    undercut_radius: float = 0.4
    undercut_depth:  float = 0.4
    undercut_length: float = 2.5

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProfileBlend":
        try:
            bt = BlendType(data.get("type", "none"))
        except ValueError:
            bt = BlendType.NONE
        return ProfileBlend(
            blend_type=bt,
            chamfer_width=float(data.get("chamfer_width", 0.0)),
            fillet_radius=float(data.get("fillet_radius", 0.0)),
            undercut_radius=float(data.get("undercut_radius", 0.4)),
            undercut_depth=float(data.get("undercut_depth", 0.4)),
            undercut_length=float(data.get("undercut_length", 2.5)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type":          self.blend_type.value,
            "chamfer_width": float(self.chamfer_width),
            "fillet_radius": float(self.fillet_radius),
            "undercut_radius": float(self.undercut_radius),
            "undercut_depth":  float(self.undercut_depth),
            "undercut_length": float(self.undercut_length),
        }


@dataclass
class ProfilePrimitive:
    primitive_id:   int
    primitive_type: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfilePrimitive":
        t = data.get("type", "")
        if t == "startPoint":
            return StartPoint.from_dict(data)
        if t in ("lineTo", "line"):
            return LineTo.from_dict(data)
        if t in ("arcTo", "arc"):
            return ArcTo.from_dict(data)
        raise ValueError(f"Unknown primitive type: {t!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {"primitive_id": self.primitive_id, "type": self.primitive_type}


@dataclass
class StartPoint(ProfilePrimitive):
    x_start: float
    z_start: float
    blend: ProfileBlend = field(default_factory=lambda: ProfileBlend(blend_type=BlendType.NONE))

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StartPoint":
        return StartPoint(
            primitive_id=int(data.get("primitive_id", 0)),
            primitive_type="startPoint",
            x_start=float(data.get("x_start", 0.0)),
            z_start=float(data.get("z_start", 0.0)),
            blend=ProfileBlend.from_dict(data.get("blend", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"x_start": float(self.x_start), "z_start": float(self.z_start), "blend": self.blend.to_dict()})
        return d


@dataclass
class LineTo(ProfilePrimitive):
    x_end: float
    z_end: float
    blend: ProfileBlend
    angle: float = 0.0
    input: str = "xz"

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "LineTo":
        input_mode = str(data.get("input", "xz") or "xz").lower()
        if input_mode not in ("xz", "ax", "az"):
            input_mode = "xz"
        return LineTo(
            primitive_id=int(data.get("primitive_id", 0)),
            primitive_type="lineTo",
            x_end=float(data.get("x_end", 0.0)),
            z_end=float(data.get("z_end", 0.0)),
            blend=ProfileBlend.from_dict(data.get("blend", {})),
            angle=float(data.get("angle", 0.0) or 0.0),
            input=input_mode,
        )

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        input_mode = str(self.input or "xz").lower()
        if input_mode not in ("xz", "ax", "az"):
            input_mode = "xz"
        d.update({
            "x_end": float(self.x_end),
            "z_end": float(self.z_end),
            "angle": float(self.angle),
            "input": input_mode,
            "blend": self.blend.to_dict(),
        })
        return d


@dataclass
class ArcTo(ProfilePrimitive):
    direction:  str
    x_end:      float
    z_end:      float
    x_center:   float
    z_center:   float
    arc_radius: float
    blend:      ProfileBlend

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ArcTo":
        return ArcTo(
            primitive_id=int(data.get("primitive_id", 0)),
            primitive_type="arcTo",
            direction=str(data.get("direction", "cw")),
            x_end=float(data.get("x_end", 0.0)),
            z_end=float(data.get("z_end", 0.0)),
            x_center=float(data.get("x_center", 0.0)),
            z_center=float(data.get("z_center", 0.0)),
            arc_radius=float(data.get("arc_radius", 0.0)),
            blend=ProfileBlend.from_dict(data.get("blend", {})),
        )

    @property
    def ccw(self) -> bool:
        """Whether it is drawn counter-clockwise ("ccw"), else clockwise."""
        return str(self.direction).lower() == "ccw"

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "direction":  self.direction,
            "x_end":      float(self.x_end),
            "z_end":      float(self.z_end),
            "x_center":   float(self.x_center),
            "z_center":   float(self.z_center),
            "arc_radius": float(self.arc_radius),
            "blend":      self.blend.to_dict(),
        })
        return d


# ---------------------------- Define Profile ---------------------------------

@dataclass
class DefineProfile(Operation):
    #: what its name starts with: drawn here, or read from a DXF drawing
    NAME_PREFIX: ClassVar[str] = "Define"
    profile_id:         int
    profile_type:       ProfilingType
    profile_primitives: List[ProfilePrimitive]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DefineProfile":
        raw = data.get("profile_primitives", [])
        primitives = []
        for i, p in enumerate(raw):
            p_data = dict(p)
            if "primitive_id" not in p_data:
                p_data["primitive_id"] = i + 1
            primitives.append(ProfilePrimitive.from_dict(p_data))
        try:
            profile_type = ProfilingType(str(data.get("profile_type", "od")).lower())
        except ValueError:
            profile_type = ProfilingType.OD
        return DefineProfile(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            profile_id=int(data.get("profile_id", 0)),
            profile_type=profile_type,
            profile_primitives=primitives,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "profile_id":         int(self.profile_id),
            "profile_type":       self.profile_type.value,
            "profile_primitives": [p.to_dict() for p in self.profile_primitives],
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return f"{self.NAME_PREFIX} {_od_or_id(self.profile_type)} Profile (P{self.profile_id})"


@dataclass
class ImportDxfProfile(DefineProfile):
    NAME_PREFIX: ClassVar[str] = "Import DXF"
    dxfFilePath: str = ""

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ImportDxfProfile":
        raw = data.get("profile_primitives", [])
        primitives = []
        for i, p in enumerate(raw):
            p_data = dict(p)
            if "primitive_id" not in p_data:
                p_data["primitive_id"] = i + 1
            primitives.append(ProfilePrimitive.from_dict(p_data))
        try:
            profile_type = ProfilingType(str(data.get("profile_type", "od")).lower())
        except ValueError:
            profile_type = ProfilingType.OD
        return ImportDxfProfile(
            order=int(data["order"]),
            type=data.get("type", "importDxfProfile"),
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            profile_id=int(data.get("profile_id", 0)),
            profile_type=profile_type,
            profile_primitives=primitives,
            dxfFilePath=str(data.get("dxfFilePath", "")),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["type"] = "importDxfProfile"
        base["dxfFilePath"] = self.dxfFilePath
        return base


# ------------------------ Radial Profile Primitives --------------------------

#: A radial profile's blend types, as its editor writes them - and "radius",
#: as it once called a fillet.
_RADIAL_BLEND_TYPES = {"chamfer": BlendType.CHAMFER, "fillet": BlendType.FILLET, "radius": BlendType.FILLET}


def _number(data: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """``data[key]`` as a float; ``default`` when it is missing or not one."""
    try:
        return float(data.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _radial_blend(data) -> ProfileBlend:
    """A blend of a radial profile, from its dict; none when there is none."""
    data = data if isinstance(data, dict) else {}
    return ProfileBlend(
        blend_type=_RADIAL_BLEND_TYPES.get(str(data.get("type", "none") or "none").lower(), BlendType.NONE),
        chamfer_width=_number(data, "chamfer_width"),
        fillet_radius=_number(data, "fillet_radius"),
    )


def _radial_blend_dict(blend: ProfileBlend) -> Dict[str, Any]:
    """A radial profile's blend as it is saved: its type and sizes, no undercut."""
    return {"type": blend.blend_type.value, "chamfer_width": float(blend.chamfer_width),
            "fillet_radius": float(blend.fillet_radius)}


def _no_blend() -> ProfileBlend:
    return ProfileBlend(blend_type=BlendType.NONE)


@dataclass
class GrooveFlank:
    """A flank of a groove: where it starts at the top (X a diameter), the
    angle it leans at from straight down, and the blend on its top corner."""
    x_start: float
    z_start: float
    angle: float = 0.0
    start_blend: ProfileBlend = field(default_factory=_no_blend)

    @staticmethod
    def from_dict(data) -> "GrooveFlank":
        data = data if isinstance(data, dict) else {}
        return GrooveFlank(x_start=_number(data, "x_start"), z_start=_number(data, "z_start"),
                           angle=_number(data, "angle"), start_blend=_radial_blend(data.get("start_blend")))

    def to_dict(self) -> Dict[str, Any]:
        return {"x_start": float(self.x_start), "z_start": float(self.z_start), "angle": float(self.angle),
                "start_blend": _radial_blend_dict(self.start_blend)}


@dataclass
class GrooveBottom:
    """A groove's bottom: the diameter it ends at under either flank, and
    the blend on either of its corners."""
    x_end_right: float
    x_end_left: float
    blend_right: ProfileBlend = field(default_factory=_no_blend)
    blend_left: ProfileBlend = field(default_factory=_no_blend)

    @staticmethod
    def from_dict(data) -> "GrooveBottom":
        data = data if isinstance(data, dict) else {}
        return GrooveBottom(x_end_right=_number(data, "x_end_right"), x_end_left=_number(data, "x_end_left"),
                            blend_right=_radial_blend(data.get("blend_right")),
                            blend_left=_radial_blend(data.get("blend_left")))

    def to_dict(self) -> Dict[str, Any]:
        return {"x_end_right": float(self.x_end_right), "x_end_left": float(self.x_end_left),
                "blend_right": _radial_blend_dict(self.blend_right),
                "blend_left": _radial_blend_dict(self.blend_left)}


@dataclass
class RadialPrimitive:
    """What a radial profile is made of: a groove, or a groove repeated."""
    TYPE: ClassVar[str] = ""
    primitive_id: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RadialPrimitive":
        kind = data.get("type")
        for cls in (Groove, RepeatGroove):
            if kind == cls.TYPE:
                return cls.from_dict(data)
        raise ValueError(f"Unknown radial primitive type: {kind!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {"primitive_id": int(self.primitive_id), "type": self.TYPE}


@dataclass
class Groove(RadialPrimitive):
    """A groove, from the top of its right flank (Z+) down, across its
    bottom and up its left flank."""
    TYPE: ClassVar[str] = "groove"
    right_flank: GrooveFlank = field(default_factory=lambda: GrooveFlank(0.0, 0.0))
    bottom: GrooveBottom = field(default_factory=lambda: GrooveBottom(0.0, 0.0))
    left_flank: GrooveFlank = field(default_factory=lambda: GrooveFlank(0.0, 0.0))

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Groove":
        return Groove(primitive_id=int(data.get("primitive_id", 0)),
                      right_flank=GrooveFlank.from_dict(data.get("right_flank")),
                      bottom=GrooveBottom.from_dict(data.get("bottom")),
                      left_flank=GrooveFlank.from_dict(data.get("left_flank")))

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"right_flank": self.right_flank.to_dict(), "bottom": self.bottom.to_dict(),
                  "left_flank": self.left_flank.to_dict()})
        return d


@dataclass
class RepeatGroove(RadialPrimitive):
    """The groove ``repeat_primitive_id`` again, ``repeat_count`` times, each
    ``z_offset`` along Z from the one before."""
    TYPE: ClassVar[str] = "repeat"
    repeat_primitive_id: int = 1
    repeat_count: int = 1
    z_offset: float = -5.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "RepeatGroove":
        return RepeatGroove(primitive_id=int(data.get("primitive_id", 0)),
                            repeat_primitive_id=int(_number(data, "repeat_primitive_id", 1)),
                            repeat_count=int(_number(data, "repeat_count", 1)),
                            z_offset=_number(data, "z_offset", -5.0))

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({"repeat_primitive_id": int(self.repeat_primitive_id), "repeat_count": int(self.repeat_count),
                  "z_offset": float(self.z_offset)})
        return d


def radial_primitives_from(raw) -> List[RadialPrimitive]:
    """A radial profile's primitives from their dicts, numbered from 1 in
    their order; what is not one of them is left out."""
    primitives = []
    for data in raw or []:
        if not isinstance(data, dict):
            continue
        try:
            primitive = RadialPrimitive.from_dict(data)
        except ValueError:
            continue
        primitive.primitive_id = len(primitives) + 1
        primitives.append(primitive)
    return primitives


@dataclass
class DefineRadialProfile(Operation):
    profile_id: int
    profile_type: ProfilingType
    profile_primitives: List[RadialPrimitive]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DefineRadialProfile":
        try:
            profile_type = ProfilingType(str(data.get("profile_type", "od")).lower())
        except ValueError:
            profile_type = ProfilingType.OD
        return DefineRadialProfile(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            profile_id=int(data.get("profile_id", 0)),
            profile_type=profile_type,
            profile_primitives=radial_primitives_from(data.get("profile_primitives", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "profile_id": int(self.profile_id),
            "profile_type": self.profile_type.value,
            "profile_primitives": [p.to_dict() for p in self.profile_primitives],
        })
        return base

    def first_groove(self) -> Optional[Groove]:
        """The profile's first groove - the one a groove operation cuts - or None."""
        return next((p for p in self.profile_primitives if isinstance(p, Groove)), None)

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return f"Define Radial Profile (P{self.profile_id})"


# ------------------------------- Profiling -----------------------------------


@dataclass
class Profiling(TurnableOperation):
    cuttingParameters: CuttingParameters
    profilingParameters: ProfilingParameters
    profilingOptions: ProfilingOptions

    @classmethod
    def from_dict(cls, data: dict) -> "Profiling":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)
        cutting_parameters = CuttingParameters.from_dict(data.get("cutting_parameters", {}))
        profiling_parameters = ProfilingParameters.from_dict(data.get("profiling_parameters", {}))
        profiling_options = ProfilingOptions.from_dict(data.get("profiling_options", {}))

        return cls(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            cuttingParameters=cutting_parameters,
            profilingParameters=profiling_parameters,
            profilingOptions=profiling_options
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "profiling_parameters": self.profilingParameters.to_dict(),
            "profiling_options": self.profilingOptions.to_dict()
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        strategy = self.profilingOptions.strategy
        g_code = {Strategy.ROUGH: "G71 ", Strategy.FINISH: "G70 "}.get(strategy, "")
        return f"{g_code}Cut Profile (P:{self.profilingParameters.profile_id}, {strategy.value.capitalize()})"


# ------------------------------ Profile Roughing -----------------------------

@dataclass
class ProfileRoughing(TurnableOperation):
    cuttingParameters: CuttingParameters
    profilingParameters: ProfilingParameters
    profileRoughingStrategy: ProfileRoughingStrategy
    stockToLeave: StockToLeave
    m1Parameters: M1Parameters
    #: Rest material: cuts what the Profile Roughings above it on the same
    #: profile leave, with their stock to leave and start position, rather
    #: than a bar of its own - for a tool that reaches where theirs did not.
    restMaterial: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "ProfileRoughing":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)
        cutting_parameters = CuttingParameters.from_dict(data.get("cutting_parameters", {}))
        profiling_parameters = ProfilingParameters.from_dict(data.get("profiling_parameters", {}))
        profile_roughing_strategy = ProfileRoughingStrategy.from_dict(data.get("profile_roughing_strategy", {}))
        stock_to_leave = StockToLeave.from_dict(data.get("stock_to_leave", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return cls(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            cuttingParameters=cutting_parameters,
            profilingParameters=profiling_parameters,
            profileRoughingStrategy=profile_roughing_strategy,
            stockToLeave=stock_to_leave,
            m1Parameters=m1_parameters,
            restMaterial=bool(data.get("rest_material", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "profiling_parameters": self.profilingParameters.to_dict(),
            "profile_roughing_strategy": self.profileRoughingStrategy.to_dict(),
            "stock_to_leave": self.stockToLeave.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
            "rest_material": bool(self.restMaterial),
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        name = (f"{_od_or_id(self.profileRoughingStrategy.profiling_type)} Profile Roughing "
                f"(P{self.profilingParameters.profile_id})")
        return name + " · Rest" if self.restMaterial else name


@dataclass
class ProfileContour(TurnableOperation):
    cuttingParameters: CuttingParameters
    profilingParameters: ProfilingParameters
    profileContourStrategy: ProfileContourStrategy
    stockToLeave: StockToLeave
    stockToLeaveEnabled: bool

    @classmethod
    def from_dict(cls, data: dict) -> "ProfileContour":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)
        cutting_parameters = CuttingParameters.from_dict(data.get("cutting_parameters", {}))
        profiling_parameters = ProfilingParameters.from_dict(data.get("profiling_parameters", {}))
        profile_contour_strategy = ProfileContourStrategy.from_dict(data.get("profile_contour_strategy", {}))
        stock_to_leave = StockToLeave.from_dict(data.get("stock_to_leave", {}))

        return cls(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            cuttingParameters=cutting_parameters,
            profilingParameters=profiling_parameters,
            profileContourStrategy=profile_contour_strategy,
            stockToLeave=stock_to_leave,
            stockToLeaveEnabled=bool(data.get("stock_to_leave_enabled", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "profiling_parameters": self.profilingParameters.to_dict(),
            "profile_contour_strategy": self.profileContourStrategy.to_dict(),
            "stock_to_leave": self.stockToLeave.to_dict(),
            "stock_to_leave_enabled": bool(self.stockToLeaveEnabled),
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return (f"{_od_or_id(self.profileContourStrategy.profiling_type)} Profile Contour "
                f"(P{self.profilingParameters.profile_id})")


@dataclass
class GrooveRoughingParameters:
    profile_id: int
    strategy: GrooveRoughingStrategy
    initial_offset: float
    afterwards_offset: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GrooveRoughingParameters":
        try:
            strategy = GrooveRoughingStrategy(str(data.get("strategy", "start_center")).lower())
        except ValueError:
            strategy = GrooveRoughingStrategy.START_CENTER
        return GrooveRoughingParameters(
            profile_id=int(data.get("profile_id", 0) or 0),
            strategy=strategy,
            initial_offset=float(data.get("initial_offset", 0.0) or 0.0),
            afterwards_offset=float(data.get("afterwards_offset", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": int(self.profile_id),
            "strategy": self.strategy.value,
            "initial_offset": float(self.initial_offset),
            "afterwards_offset": float(self.afterwards_offset),
        }


@dataclass
class GrooveRoughing(TurnableOperation):
    cuttingParameters: GrooveRoughingCuttingParameters
    roughingParameters: GrooveRoughingParameters
    stockToLeave: StockToLeave
    stockToLeaveEnabled: bool
    m1Parameters: M1Parameters

    @classmethod
    def from_dict(cls, data: dict) -> "GrooveRoughing":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)
        cutting_parameters = GrooveRoughingCuttingParameters.from_dict(data.get("cutting_parameters", {}))
        roughing_parameters = GrooveRoughingParameters.from_dict(data.get("roughing_parameters", {}))
        stock_to_leave = StockToLeave.from_dict(data.get("stock_to_leave", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return cls(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            cuttingParameters=cutting_parameters,
            roughingParameters=roughing_parameters,
            stockToLeave=stock_to_leave,
            stockToLeaveEnabled=bool(data.get("stock_to_leave_enabled", False)),
            m1Parameters=m1_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "roughing_parameters": self.roughingParameters.to_dict(),
            "stock_to_leave": self.stockToLeave.to_dict(),
            "stock_to_leave_enabled": bool(self.stockToLeaveEnabled),
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return f"Groove Roughing (P{self.roughingParameters.profile_id})"


@dataclass
class GrooveFinishingParameters:
    profile_id: int
    strategy: GrooveFinishingStrategy

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "GrooveFinishingParameters":
        try:
            strategy = GrooveFinishingStrategy(str(data.get("strategy", "towards_center")).lower())
        except ValueError:
            strategy = GrooveFinishingStrategy.TOWARDS_CENTER
        return GrooveFinishingParameters(
            profile_id=int(data.get("profile_id", 0) or 0),
            strategy=strategy,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": int(self.profile_id),
            "strategy": self.strategy.value,
        }


@dataclass
class GrooveFinishing(TurnableOperation):
    cuttingParameters: GrooveFinishingCuttingParameters
    finishingParameters: GrooveFinishingParameters

    @classmethod
    def from_dict(cls, data: dict) -> "GrooveFinishing":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)
        cutting_parameters = GrooveFinishingCuttingParameters.from_dict(data.get("cutting_parameters", {}))
        finishing_parameters = GrooveFinishingParameters.from_dict(data.get("finishing_parameters", {}))

        return cls(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            cuttingParameters=cutting_parameters,
            finishingParameters=finishing_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "finishing_parameters": self.finishingParameters.to_dict(),
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return f"Groove Finishing (P{self.finishingParameters.profile_id})"


# ------------------------------- Threading -----------------------------------


def _coerce_thread_location(val):
    if isinstance(val, ThreadLocation):
        return val
    if isinstance(val, str):
        try:
            return ThreadLocation[val]
        except Exception:
            try:
                return ThreadLocation(val)
            except Exception:
                return ThreadLocation.OD
    return ThreadLocation.OD


@dataclass
class Threading(TurnableOperation):
    location: ThreadLocation
    thread_type: str
    pitch: float
    starts: int
    major_diameter: float
    minor_diameter: float
    z_start: float
    z_end: float
    initial_doc: float
    retract: float
    spring_passes: int
    depth_degression: float
    taper_type: int
    compound_angle: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Threading":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)
        d = dict(data)
        return Threading(
            order=int(d["order"]),
            type=d["type"],
            generate_gcode=bool(d.get("generate_gcode", True)),
            is_optional_block=bool(d.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            location=_coerce_thread_location(d.get("location", "OD")),
            thread_type=d["thread_type"],
            pitch=float(d["pitch"]),
            starts=int(d["starts"]),
            major_diameter=float(d["major_diameter"]),
            minor_diameter=float(d["minor_diameter"]),
            z_start=float(d["z_start"]),
            z_end=float(d["z_end"]),
            initial_doc=float(d.get("initial_doc", 0.0)),
            retract=float(d["retract"]),
            spring_passes=int(d.get("spring_passes", 0)),
            depth_degression=float(d.get("depth_degression", 1.0)),
            taper_type=int(d.get("taper_type", 0)),
            compound_angle=float(d.get("compound_angle", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "location": self.location.value,
            "thread_type": self.thread_type,
            "pitch": self.pitch,
            "starts": self.starts,
            "major_diameter": self.major_diameter,
            "minor_diameter": self.minor_diameter,
            "z_start": self.z_start,
            "z_end": self.z_end,
            "initial_doc": self.initial_doc,
            "retract": self.retract,
            "spring_passes": self.spring_passes,
            "depth_degression": self.depth_degression,
            "taper_type": self.taper_type,
            "compound_angle": self.compound_angle
        })
        return self._add_speeds_and_feeds_to(base)

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return f"G76 Threading (P: {self.pitch})"


@dataclass
class G33Threading(TurnableOperation):
    location: ThreadLocation
    thread_type: str
    pitch: float
    starts: int
    major_diameter: float
    minor_diameter: float
    z_start: float
    z_end: float
    initial_doc: float
    retract: float
    spring_passes: int
    minimum_radial_increment: float
    taper_type: int
    compound_angle: float
    m1Parameters: M1Parameters

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "G33Threading":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)
        m1_parameters = M1Parameters.from_dict(
            data.get("m1_parameters") or {"include_m1": False}
        )
        d = dict(data)
        return G33Threading(
            order=int(d["order"]),
            type=d["type"],
            generate_gcode=bool(d.get("generate_gcode", True)),
            is_optional_block=bool(d.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            location=_coerce_thread_location(d.get("location", "OD")),
            thread_type=d.get("thread_type", "g33"),
            pitch=float(d["pitch"]),
            starts=int(d.get("starts", 1)),
            major_diameter=float(d["major_diameter"]),
            minor_diameter=float(d["minor_diameter"]),
            z_start=float(d["z_start"]),
            z_end=float(d["z_end"]),
            initial_doc=float(d.get("initial_doc", 0.0)),
            retract=float(d["retract"]),
            spring_passes=int(d.get("spring_passes", 0)),
            minimum_radial_increment=float(d.get("minimum_radial_increment", 0.0)),
            taper_type=int(d.get("taper_type", 0)),
            compound_angle=float(d.get("compound_angle", 0.0)),
            m1Parameters=m1_parameters,
        )

    @property
    def final_radial_depth(self) -> float:
        return abs(float(self.major_diameter) - float(self.minor_diameter)) / 2.0

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "location": self.location.value,
            "thread_type": self.thread_type,
            "pitch": self.pitch,
            "starts": self.starts,
            "major_diameter": self.major_diameter,
            "minor_diameter": self.minor_diameter,
            "z_start": self.z_start,
            "z_end": self.z_end,
            "initial_doc": self.initial_doc,
            "retract": self.retract,
            "spring_passes": self.spring_passes,
            "minimum_radial_increment": self.minimum_radial_increment,
            "taper_type": self.taper_type,
            "compound_angle": self.compound_angle,
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return self._add_speeds_and_feeds_to(base)

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return f"G33 Threading (P: {self.pitch})"


# -------------------------------- Drilling -----------------------------------

@dataclass
class Drilling(TurnableOperation):
    drillingParameters: DrillingParameters
    m1Parameters: M1Parameters

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Drilling":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)

        drilling_parameters = DrillingParameters.from_dict(data.get("drilling_parameters", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return Drilling(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            drillingParameters=drilling_parameters,
            m1Parameters=m1_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "drilling_parameters": self.drillingParameters.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return "Drilling"


# --------------------------------- Tapping -----------------------------------

@dataclass
class Tapping(TurnableOperation):
    tappingParameters: TappingParameters
    m1Parameters: M1Parameters

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Tapping":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)

        cutting_parameters = TappingParameters.from_dict(data.get("tapping_parameters", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return Tapping(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            tappingParameters=cutting_parameters,
            m1Parameters=m1_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "tapping_parameters": self.tappingParameters.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return "Tapping"


# --------------------------------- Parting -----------------------------------

@dataclass
class EdgeBreak:
    blend_type: BlendType
    chamfer_width: float
    fillet_radius: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "EdgeBreak":
        if not isinstance(data, dict):
            raise TypeError("edge_break must be a dict")

        blend_raw = data.get("blend_type", "none")
        chamfer_width = data.get("chamfer_width", 0.0)
        fillet_radius = data.get("fillet_radius", 0.0)

        if isinstance(blend_raw, BlendType):
            blend = blend_raw
        elif isinstance(blend_raw, str):
            try:
                blend = BlendType(blend_raw)
            except ValueError:
                raise ValueError(f"Invalid blend_type: {blend_raw!r}")
        else:
            raise TypeError("blend_type must be a string or BlendType")

        return EdgeBreak(
            blend_type=blend,
            chamfer_width=float(chamfer_width),
            fillet_radius=float(fillet_radius)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blend_type": self.blend_type.value,
            "chamfer_width": float(self.chamfer_width),
            "fillet_radius": float(self.fillet_radius)
        }

@dataclass
class Parting(TurnableOperation):
    partingParameters: PartingParameters
    edgeBreak: EdgeBreak

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Parting":
        speeds_and_feeds = TurnableOperation._parse_speeds_and_feeds(data)

        parting_parameters = PartingParameters.from_dict(data.get("parting_parameters", {}))
        edge_break = EdgeBreak.from_dict(data.get("edge_break", {}))

        return Parting(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            speedsAndFeeds=speeds_and_feeds,
            partingParameters=parting_parameters,
            edgeBreak=edge_break
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_speeds_and_feeds_to(base)
        base.update({
            "parting_parameters": self.partingParameters.to_dict(),
            "edge_break": self.edgeBreak.to_dict(),
        })
        return base

    def display_name(self) -> str:
        """What the operation is called, in the program's list and its G-code."""
        return "Parting"


# --------------------------------- Program -----------------------------------

@dataclass
class ProgramTool:
    """A tool a program's operations cut with: a holder - the T number - and
    the cutting tool that was in it, as it was when chosen (``snapshot``:
    {"holder": ..., "cutting_tool": CuttingTool.to_json()}), so the program
    can tell later whether the Tool Library still has it. ``id`` is the
    program's own number for it, what an operation's toolRef names; the tool
    change to it goes to ``toolchange_position``."""
    id: int
    tool_holder_id: int
    cutting_tool_id: Optional[int]
    toolchange_position: PredefinedPosition = PredefinedPosition.G28
    snapshot: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ProgramTool":
        try:
            position = PredefinedPosition(str(data.get("toolchange_position", "G28")).upper())
        except ValueError:
            position = PredefinedPosition.G28
        cutting_tool_id = data.get("cutting_tool_id")
        return ProgramTool(
            id=int(data["id"]),
            tool_holder_id=int(data["tool_holder_id"]),
            cutting_tool_id=int(cutting_tool_id) if cutting_tool_id is not None else None,
            toolchange_position=position,
            snapshot=dict(data.get("snapshot") or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_holder_id": self.tool_holder_id,
            "cutting_tool_id": self.cutting_tool_id,
            "toolchange_position": self.toolchange_position.value,
            "snapshot": self.snapshot,
        }


@dataclass
class Program:
    id: str
    header: Header
    operations: List[Operation]
    tools: List[ProgramTool] = field(default_factory=list)
    filename: Optional[str] = field(default=None, repr=False, compare=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Program":
        header = Header.from_dict(data["header"])
        tools = [ProgramTool.from_dict(tool) for tool in data.get("tools", [])]
        operations = [Operation.from_dict(op) for op in data.get("operations", [])]
        return Program(id=data["id"], header=header, operations=operations, tools=tools)

    def tool(self, tool_ref: Optional[int]) -> Optional[ProgramTool]:
        """The program's tool ``tool_ref``, or None."""
        if tool_ref is None:
            return None
        return next((tool for tool in self.tools if tool.id == tool_ref), None)

    def index_of(self, op) -> int:
        """Where ``op`` is in the operations: that very one, or - a draft of
        it, an editor's - the one of its order; past the last when neither."""
        for index, other in enumerate(self.operations):
            if other is op:
                return index
        return next((index for index, other in enumerate(self.operations) if other.order == op.order),
                    len(self.operations))

    def tool_of(self, op) -> Optional[ProgramTool]:
        """The tool operation ``op`` cuts with, or None."""
        return self.tool(getattr(op, "toolRef", None))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "header": self.header.to_dict(),
            "tools": [tool.to_dict() for tool in self.tools],
            "operations": [op.to_dict() for op in self.operations]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=4)

    @staticmethod
    def from_json(json_str: str) -> "Program":
        return Program.from_dict(json.loads(json_str))


# --------------------------- Operation registry ------------------------------

operation_types: Dict[str, Type[Operation]] = {
    "positionAt": PositionAt,
    "facing": Facing,
    "knurling": Knurling,
    "defineProfile": DefineProfile,
    "importDxfProfile": ImportDxfProfile,
    "defineRadialProfile": DefineRadialProfile,
    "profiling": Profiling,
    "profileRoughing": ProfileRoughing,
    "profileContour": ProfileContour,
    "grooveRoughing": GrooveRoughing,
    "grooveFinishing": GrooveFinishing,
    "threading": Threading,
    "g33Threading": G33Threading,
    "drilling": Drilling,
    "tapping": Tapping,
    "parting": Parting
}

# -------------------- CAM config objects (built from the operations) -------------------


@dataclass(frozen=True)
class ProfileRoughingConfig:
    x_start: float
    z_start: float
    doc: float
    retract: float
    feed_rate: float
    stock_x: float
    stock_z: float
    profiling_type: ProfilingType
    pass_type: PassType
    optional_prefix: str


@dataclass(frozen=True)
class ProfileContourConfig:
    x_start: float
    z_start: float
    doc: float
    retract: float
    feed_rate: float
    stock_x: float
    stock_z: float
    stock_enabled: bool
    profiling_type: ProfilingType
    optional_prefix: str
