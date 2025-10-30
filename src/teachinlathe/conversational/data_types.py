import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Type


# ------------------------------ Core header ----------------------------------

@dataclass
class Workpiece:
    material: str
    external_diameter: float
    internal_diameter: float
    stickout_length: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Workpiece":
        return Workpiece(**data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material": self.material,
            "external_diameter": self.external_diameter,
            "internal_diameter": self.internal_diameter,
            "stickout_length": self.stickout_length,
        }


@dataclass
class Header:
    name: str
    last_edit: str
    datum: int
    units: str
    workpiece: Workpiece

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Header":
        return Header(
            name=data["name"],
            last_edit=data["last_edit"],
            datum=data["datum"],
            units=data["units"],
            workpiece=Workpiece.from_dict(data["workpiece"])
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "last_edit": self.last_edit,
            "datum": self.datum,
            "units": self.units,
            "workpiece": self.workpiece.to_dict()
        }


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
        return operation_types[op_type].from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "type": self.type,
            "generate_gcode": self.generate_gcode,
            "is_optional_block": self.is_optional_block
        }


# ------------------------------ Spindle model --------------------------------

@dataclass
class Spindle:
    direction: int                         # mandatory: -1 / +1
    rpm_value: Optional[int] = None        # RPM mode
    css_value: Optional[float] = None      # CSS mode (value, e.g. mm/sec)
    css_max_speed: Optional[int] = None    # CSS max RPM

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Spindle":
        if not isinstance(data, dict):
            raise ValueError("Spindle must be an object")
        s = Spindle(
            direction=int(data["direction"]),
            rpm_value=(None if data.get("rpm_value") is None else int(data.get("rpm_value"))),
            css_value=(None if data.get("css_value") is None else float(data.get("css_value"))),
            css_max_speed=(None if data.get("css_max_speed") is None else int(data.get("css_max_speed"))),
        )
        s._validate_mode()
        return s

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"direction": int(self.direction)}
        if self.rpm_value is not None:
            out["rpm_value"] = int(self.rpm_value)
        if self.css_value is not None:
            out["css_value"] = float(self.css_value)
        if self.css_max_speed is not None:
            out["css_max_speed"] = int(self.css_max_speed)
        return out

    def _validate_mode(self) -> None:
        """Require 'direction' and exactly one mode:
           - RPM: rpm_value present
           - CSS: css_value AND css_max_speed present
           Never both."""
        if self.direction is None:
            raise ValueError("Spindle.direction is required")
        if int(self.direction) not in (-1, 1):
            raise ValueError("Spindle.direction must be -1 or 1")

        has_rpm = self.rpm_value is not None
        has_css_partial = (self.css_value is not None) or (self.css_max_speed is not None)
        has_css_full = (self.css_value is not None) and (self.css_max_speed is not None)

        if has_css_partial and not has_css_full:
            raise ValueError("For CSS mode, both css_value AND css_max_speed are required")

        # XOR: one or the other
        if not (has_rpm ^ has_css_full):
            raise ValueError("Choose exactly one spindle mode: rpm_value OR (css_value + css_max_speed)")


# --------- TurnableOperation: all spindle-using ops inherit from this --------

@dataclass
class TurnableOperation(Operation):
    spindle: Spindle

    @staticmethod
    def _parse_spindle(data: Dict[str, Any]) -> Spindle:
        sp = data.get("spindle")
        if sp is None:
            raise ValueError("Missing required 'spindle' block for turnable operation")
        return Spindle.from_dict(sp)

    def _add_spindle_to(self, base: Dict[str, Any]) -> Dict[str, Any]:
        base["spindle"] = self.spindle.to_dict()
        return base


# --------------------------- Tool change (no spindle) ------------------------

class CoordinateType(Enum):
    RELATIVE = "relative"
    ABSOLUTE = "absolute"


class MoveSequence(Enum):
    XZ = "xz"
    ZX = "zx"
    BOTH = "both"


@dataclass
class ToolChangeRules:
    x_pos: float
    z_pos: float
    coordinate_type: CoordinateType
    move_sequence: MoveSequence
    stop_spindle: bool

    def __post_init__(self):
        # Coerce strings to enums (defensive)
        if isinstance(self.coordinate_type, str):
            val = self.coordinate_type.strip().lower()
            self.coordinate_type = {
                "relative": CoordinateType.RELATIVE,
                "absolute": CoordinateType.ABSOLUTE
            }.get(val, CoordinateType.ABSOLUTE)

        if isinstance(self.move_sequence, str):
            val = self.move_sequence.strip().lower()
            self.move_sequence = {
                "xz": MoveSequence.XZ,
                "zx": MoveSequence.ZX,
                "both": MoveSequence.BOTH,
                "simultaneous": MoveSequence.BOTH,  # compatibility
            }.get(val, MoveSequence.XZ)

    @staticmethod
    def coerce(obj: Any) -> "ToolChangeRules":
        """Accept dict or ToolChangeRules and always return ToolChangeRules instance."""
        if isinstance(obj, ToolChangeRules):
            obj.__post_init__()
            return obj
        if isinstance(obj, dict):
            data = dict(obj)
            # defaults (tolerant)
            x_pos = float(data.get("x_pos", 0.0))
            z_pos = float(data.get("z_pos", 0.0))
            coordinate_type = data.get("coordinate_type", "absolute")
            move_sequence = data.get("move_sequence", "xz")
            stop_spindle = bool(data.get("stop_spindle", False))
            return ToolChangeRules(
                x_pos=x_pos,
                z_pos=z_pos,
                coordinate_type=coordinate_type,
                move_sequence=move_sequence,
                stop_spindle=stop_spindle
            )
        raise TypeError("ToolChangeRules.coerce expects dict or ToolChangeRules")

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ToolChangeRules":
        return ToolChangeRules.coerce(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x_pos": float(self.x_pos),
            "z_pos": float(self.z_pos),
            "coordinate_type": self.coordinate_type.value,
            "move_sequence": self.move_sequence.value,
            "stop_spindle": bool(self.stop_spindle),
        }


@dataclass
class ChangeTool(Operation):
    tool_no: int
    tool_orientation: int
    back_angle: int
    front_angle: int
    toolchange_rules: ToolChangeRules

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChangeTool":
        # tolerant parse: coerce toolchange_rules
        rules = ToolChangeRules.from_dict(data.get("toolchange_rules", {}))
        return ChangeTool(
            order=data["order"],
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            tool_no=int(data["tool_no"]),
            tool_orientation=int(data["tool_orientation"]),
            back_angle=int(data["back_angle"]),
            front_angle=int(data["front_angle"]),
            toolchange_rules=rules
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        rules = ToolChangeRules.coerce(self.toolchange_rules)
        base.update({
            "tool_no": int(self.tool_no),
            "tool_orientation": int(self.tool_orientation),
            "back_angle": int(self.back_angle),
            "front_angle": int(self.front_angle),
            "toolchange_rules": rules.to_dict()
        })
        return base


# ----------------------------- InspectOnM1 -----------------------------------

@dataclass
class InspectOnM1:
    x_inspect: float
    z_inspect: float
    stop_spindle: bool

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "InspectOnM1":
        return InspectOnM1(
            x_inspect=float(data.get("x_inspect", 0.0)),
            z_inspect=float(data.get("z_inspect", 0.0)),
            stop_spindle=bool(data.get("stop_spindle", False))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x_inspect": float(self.x_inspect),
            "z_inspect": float(self.z_inspect),
            "stop_spindle": bool(self.stop_spindle)
        }


# ------------------------------- Facing --------------------------------------

@dataclass
class Facing(TurnableOperation):
    feed_rate: float
    doc: float
    retract: float
    x_start: float
    z_start: float
    x_end: float
    z_end: float
    z_end_becomes_new_z0: bool
    inspect_on_m1: Optional[InspectOnM1] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Facing":
        spindle = TurnableOperation._parse_spindle(data)
        inspect = None
        if "inspect_on_m1" in data and isinstance(data["inspect_on_m1"], dict):
            inspect = InspectOnM1.from_dict(data["inspect_on_m1"])
        return Facing(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindle=spindle,
            feed_rate=float(data.get("feed_rate", 0.0)),
            doc=float(data.get("doc", 0.0)),
            retract=float(data.get("retract", 0.0)),
            x_start=float(data.get("x_start", 0.0)),
            z_start=float(data.get("z_start", 0.0)),
            x_end=float(data.get("x_end", 0.0)),
            z_end=float(data.get("z_end", 0.0)),
            z_end_becomes_new_z0=bool(data.get("z_end_becomes_new_z0", False)),
            inspect_on_m1=inspect,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "feed_rate": float(self.feed_rate),
            "doc": float(self.doc),
            "retract": float(self.retract),
            "x_start": float(self.x_start),
            "z_start": float(self.z_start),
            "x_end": float(self.x_end),
            "z_end": float(self.z_end),
            "z_end_becomes_new_z0": bool(self.z_end_becomes_new_z0)
        })
        if self.inspect_on_m1 is not None:
            base["inspect_on_m1"] = self.inspect_on_m1.to_dict()
        return self._add_spindle_to(base)


# ---------------------------- Define Profile ---------------------------------

@dataclass
class DefineProfile(Operation):
    profileId: int
    profile_primitives: List[Dict[str, Any]]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DefineProfile":
        return DefineProfile(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            profileId=int(data.get("profileId", data.get("profile_id", 0))),
            profile_primitives=list(data.get("profile_primitives", []))
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "profileId": int(self.profileId),
            "profile_primitives": self.profile_primitives
        })
        return base


# ------------------------------- Profiling -----------------------------------

class Strategy(Enum):
    ROUGH = "rough"
    FINISH = "finish"


@dataclass
class Profiling(TurnableOperation):
    feed_rate: float
    profileId: int
    strategy: Strategy
    x_start: float
    z_start: float
    doc: float
    retract: float
    stock_to_leave: Optional[Dict[str, float]] = field(default=None)
    spring_passes: Optional[int] = field(default=None)

    @classmethod
    def from_dict(cls, data: dict) -> "Profiling":
        spindle = TurnableOperation._parse_spindle(data)
        strat = data.get("strategy", "rough")
        strat_enum = Strategy(str(strat).lower()) if isinstance(strat, str) else Strategy.ROUGH
        # allow "ROUGH"/"rough"
        if isinstance(strat, str):
            try:
                strat_enum = Strategy[str(strat).upper()]
            except Exception:
                strat_enum = Strategy(str(strat).lower())
        return cls(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindle=spindle,
            feed_rate=float(data.get("feed_rate", 0.0)),
            profileId=int(data.get("profileId", data.get("profile_id", 0))),
            strategy=strat_enum,
            x_start=float(data.get("x_start", 0.0)),
            z_start=float(data.get("z_start", 0.0)),
            doc=float(data.get("doc", 0.0)),
            retract=float(data.get("retract", 0.0)),
            stock_to_leave=data.get("stock_to_leave"),
            spring_passes=(None if data.get("spring_passes") is None else int(data.get("spring_passes")))
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "feed_rate": float(self.feed_rate),
            "profileId": int(self.profileId),
            "strategy": self.strategy.value,
            "x_start": float(self.x_start),
            "z_start": float(self.z_start),
            "doc": float(self.doc),
            "retract": float(self.retract),
            "stock_to_leave": self.stock_to_leave,
            "spring_passes": self.spring_passes
        })
        return self._add_spindle_to(base)


# ------------------------------- Threading -----------------------------------

class ThreadLocation(Enum):
    OD = "OD"
    ID = "ID"


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

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Threading":
        spindle = TurnableOperation._parse_spindle(data)
        d = dict(data)
        return Threading(
            order=int(d["order"]),
            type=d["type"],
            generate_gcode=bool(d.get("generate_gcode", True)),
            is_optional_block=bool(d.get("is_optional_block", False)),
            spindle=spindle,
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
            "spring_passes": self.spring_passes
        })
        return self._add_spindle_to(base)


# -------------------------------- Drilling -----------------------------------

@dataclass
class Drilling(TurnableOperation):
    feed_rate: float
    z_start: float
    z_end: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Drilling":
        spindle = TurnableOperation._parse_spindle(data)
        return Drilling(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindle=spindle,
            feed_rate=float(data.get("feed_rate", 0.0)),
            z_start=float(data.get("z_start", 0.0)),
            z_end=float(data.get("z_end", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "feed_rate": float(self.feed_rate),
            "z_start": float(self.z_start),
            "z_end": float(self.z_end)
        })
        return self._add_spindle_to(base)


# --------------------------------- Tapping -----------------------------------

@dataclass
class Tapping(TurnableOperation):
    pitch: float
    z_start: float
    z_end: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Tapping":
        spindle = TurnableOperation._parse_spindle(data)
        return Tapping(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindle=spindle,
            pitch=float(data["pitch"]),
            z_start=float(data["z_start"]),
            z_end=float(data["z_end"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "pitch": float(self.pitch),
            "z_start": float(self.z_start),
            "z_end": float(self.z_end)
        })
        return self._add_spindle_to(base)


# --------------------------------- Parting -----------------------------------

@dataclass
class Parting(TurnableOperation):
    feed_rate: float
    peck_depth: float
    x_start: float
    x_end: float
    z_pos: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Parting":
        spindle = TurnableOperation._parse_spindle(data)
        return Parting(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindle=spindle,
            feed_rate=float(data.get("feed_rate", 0.0)),
            peck_depth=float(data.get("peck_depth", 0.0)),
            x_start=float(data.get("x_start", 0.0)),
            x_end=float(data.get("x_end", 0.0)),
            z_pos=float(data.get("z_pos", 0.0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "feed_rate": float(self.feed_rate),
            "peck_depth": float(self.peck_depth),
            "x_start": float(self.x_start),
            "x_end": float(self.x_end),
            "z_pos": float(self.z_pos)
        })
        return self._add_spindle_to(base)


# --------------------------------- Program -----------------------------------

@dataclass
class Program:
    id: str
    header: Header
    operations: List[Operation]
    filename: Optional[str] = field(default=None, repr=False, compare=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Program":
        header = Header.from_dict(data["header"])
        operations = [Operation.from_dict(op) for op in data.get("operations", [])]
        return Program(id=data["id"], header=header, operations=operations)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "header": self.header.to_dict(),
            "operations": [op.to_dict() for op in self.operations]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=4)

    @staticmethod
    def from_json(json_str: str) -> "Program":
        return Program.from_dict(json.loads(json_str))


# --------------------------- Operation registry ------------------------------

operation_types: Dict[str, Type[Operation]] = {
    "changeTool": ChangeTool,
    "facing": Facing,
    "define_profile": DefineProfile,
    "profiling": Profiling,
    "threading": Threading,
    "drilling": Drilling,
    "tapping": Tapping,
    "parting": Parting
}

display_names: Dict[str, str] = {
    "changeTool": "Tool Change",
    "facing": "Facing",
    "define_profile": "Define Profile",
    "profiling": "Profiling",
    "threading": "Threading",
    "drilling": "Drilling",
    "tapping": "Tapping",
    "parting": "Parting",
}
