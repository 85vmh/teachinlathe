import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Type


class CoordinateType(Enum):
    RELATIVE = "relative"
    ABSOLUTE = "absolute"


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


class ProfilingType(str, Enum):
    OD = "od"
    ID = "id"


class PassType(str, Enum):
    AXIAL = "axial"
    RADIAL = "radial"
    DIAGONAL_INTERIOR = "diagonal_interior"
    DIAGONAL_EXTERIOR = "diagonal_exterior"


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
    datum: int
    units: str
    workpiece: Workpiece

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Header":
        created_date = data.get("created_date")
        if created_date is None:
            created_date = data.get("last_edit", "")
        return Header(
            name=data["name"],
            created_date=str(created_date),
            last_edit=data["last_edit"],
            datum=data["datum"],
            units=data["units"],
            workpiece=Workpiece.from_dict(data["workpiece"])
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "created_date": self.created_date,
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
class SpindleParameters:
    direction: int
    mode: SpindleMode
    rpm_value: Optional[int] = None
    css_value: Optional[int] = None
    css_max_speed: Optional[int] = None

    DEFAULT_RPM = 1000
    DEFAULT_CSS_VALUE = 100
    DEFAULT_CSS_MAX = 1000

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SpindleParameters":
        if not isinstance(data, dict):
            raise ValueError("Spindle must be an object")
        mode_str = data.get("mode")
        if mode_str not in (m.value for m in SpindleMode):
            raise ValueError(f"Invalid spindle mode: {mode_str!r}")

        def as_opt_int(v):
            return None if v is None or (isinstance(v, str) and v.strip() == "") else int(v)

        return SpindleParameters(
            direction=int(data.get("direction", -1)),
            mode=SpindleMode(mode_str),
            rpm_value=as_opt_int(data.get("rpm_value")),
            css_value=as_opt_int(data.get("css_value")),
            css_max_speed=as_opt_int(data.get("css_max_speed")),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "direction": int(self.direction),
            "mode": self.mode.value,
        }
        if self.rpm_value is not None:
            out["rpm_value"] = int(self.rpm_value)
        if self.css_value is not None:
            out["css_value"] = int(self.css_value)
        if self.css_max_speed is not None:
            out["css_max_speed"] = int(self.css_max_speed)
        return out

# --------- TurnableOperation: all spindle-using ops inherit from this --------

@dataclass
class TurnableOperation(Operation):
    spindleParameters: SpindleParameters

    @staticmethod
    def _parse_spindle(data: Dict[str, Any]) -> SpindleParameters:
        sp = data.get("spindle_parameters")
        if sp is None:
            raise ValueError("Missing required 'spindle_parameters' block for turnable operation")
        return SpindleParameters.from_dict(sp)

    def _add_spindle_to(self, base: Dict[str, Any]) -> Dict[str, Any]:
        base["spindle_parameters"] = self.spindleParameters.to_dict()
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
class ChangeTool(Operation):
    tool_no: int
    tool_orientation: int
    back_angle: int
    front_angle: int
    toolchange_position: PredefinedPosition

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChangeTool":
        position_raw = str(data.get("toolchange_position", PredefinedPosition.G28.value))
        try:
            toolchange_position = PredefinedPosition(position_raw)
        except ValueError:
            toolchange_position = PredefinedPosition.G28
        return ChangeTool(
            order=data["order"],
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            tool_no=int(data["tool_no"]),
            tool_orientation=int(data["tool_orientation"]),
            back_angle=int(data["back_angle"]),
            front_angle=int(data["front_angle"]),
            toolchange_position=toolchange_position
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "tool_no": int(self.tool_no),
            "tool_orientation": int(self.tool_orientation),
            "back_angle": int(self.back_angle),
            "front_angle": int(self.front_angle),
            "toolchange_position": self.toolchange_position.value
        })
        return base


@dataclass
class PositionAt(Operation):
    position_details: PositionDetails

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PositionAt":
        details = PositionDetails.from_dict(
            data.get("position_details", data.get("toolchange_rules", {}))
        )
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


# ----------------------------- M1 Parameters ---------------------------------

@dataclass
class M1Parameters:
    include_m1: bool
    inspect_position: PredefinedPosition
    stop_spindle: bool

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "M1Parameters":
        # backward compat: old JSON had x_inspect/z_inspect instead of inspect_position
        inspect_raw = str(data.get("inspect_position", PredefinedPosition.G28.value))
        try:
            inspect_position = PredefinedPosition(inspect_raw)
        except ValueError:
            inspect_position = PredefinedPosition.G28
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
    feedRate: float
    retract: float
    doc: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CuttingParameters":
        return CuttingParameters(
            feedRate=float(data.get("feed_rate", 0.0)),
            retract=float(data.get("retract", 0.0)),
            doc=float(data.get("doc", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feed_rate": float(self.feedRate),
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
    zRetract: float = 0.0
    peckDepth: float = 0.0
    feedRate: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DrillingParameters":
        return DrillingParameters(
            zStart=float(data.get("z_start", 0.0) or 0.0),
            zEnd=float(data.get("z_end", 0.0) or 0.0),
            zRetract=float(data.get("z_retract", 0.0) or 0.0),
            peckDepth=float(data.get("peck_depth", 0.0) or 0.0),
            feedRate=float(data.get("feed_rate", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "z_start": float(self.zStart),
            "z_end": float(self.zEnd),
            "z_retract" : float(self.zRetract),
            "peck_depth" : float(self.peckDepth),
            "feed_rate": float(self.feedRate)
        }
        return out

@dataclass
class TappingParameters:
    zStart: float = 0.0
    zEnd: float = 0.0
    zRetract: float = 0.0
    peckDepth: float = 0.0
    pitch: float = 0.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TappingParameters":
        return TappingParameters(
            zStart=float(data.get("z_start", 0.0) or 0.0),
            zEnd=float(data.get("z_end", 0.0) or 0.0),
            zRetract=float(data.get("z_retract", 0.0) or 0.0),
            peckDepth=float(data.get("peck_depth", 0.0) or 0.0),
            pitch=float(data.get("pitch", 0.0) or 0.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "z_start": float(self.zStart),
            "z_end": float(self.zEnd),
            "z_retract" : float(self.zRetract),
            "peck_depth" : float(self.peckDepth),
            "pitch": float(self.pitch)
        }
        return out

@dataclass
class PartingParameters:
    xStart: float = 0.0
    xEnd: float = 0.0
    zPos: float = 0.0
    first_feed_rate: float = 0.0
    second_feed_rate: float = 0.0
    second_feed_x_pos: float = 0.0
    x_clearance: float = 1.0

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PartingParameters":
        return PartingParameters(
            xStart=float(data.get("x_start", 0.0) or 0.0),
            xEnd=float(data.get("x_end", 0.0) or 0.0),
            zPos=float(data.get("z_pos", 0.0) or 0.0),
            first_feed_rate=float(data.get("first_feed_rate", 0.0) or 0.0),
            second_feed_rate=float(data.get("second_feed_rate", 0.0) or 0.0),
            second_feed_x_pos=float(data.get("second_feed_x_pos", 0.0) or 0.0),
            x_clearance=float(data.get("x_clearance", 1.0) or 1.0),
        )

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "x_start": float(self.xStart),
            "x_end": float(self.xEnd),
            "z_pos" : float(self.zPos),
            "first_feed_rate" : float(self.first_feed_rate),
            "second_feed_rate" : float(self.second_feed_rate),
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
        spindle_parameters = TurnableOperation._parse_spindle(data)

        cutting_parameters = CuttingParameters.from_dict(data.get("cutting_parameters", {}))
        geometry_parameters = GeometryParameters.from_dict(data.get("geometry_parameters", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return Facing(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindleParameters=spindle_parameters,
            cuttingParameters=cutting_parameters,
            geometryParameters=geometry_parameters,
            m1Parameters=m1_parameters,
            zEndBecomesNewZ0=bool(data.get("z_end_becomes_new_z0", False))
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_spindle_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "geometry_parameters": self.geometryParameters.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
            "z_end_becomes_new_z0": bool(self.zEndBecomesNewZ0)
        })
        return base


@dataclass
class Knurling(TurnableOperation):
    cuttingParameters: KnurlingCuttingParameters
    geometryParameters: KnurlingGeometryParameters
    m1Parameters: M1Parameters

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Knurling":
        spindle_parameters = TurnableOperation._parse_spindle(data)
        cutting_parameters = KnurlingCuttingParameters.from_dict(data.get("cutting_parameters", {}))
        geometry_parameters = KnurlingGeometryParameters.from_dict(data.get("geometry_parameters", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return Knurling(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindleParameters=spindle_parameters,
            cuttingParameters=cutting_parameters,
            geometryParameters=geometry_parameters,
            m1Parameters=m1_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_spindle_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "geometry_parameters": self.geometryParameters.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return base


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


@dataclass
class DefineRadialProfile(Operation):
    profile_id: int
    profile_type: ProfilingType
    profile_primitives: List[Dict[str, Any]]

    @staticmethod
    def _ordered_primitive(primitive: Dict[str, Any], primitive_id: int) -> Dict[str, Any]:
        p_data = dict(primitive)
        p_data.setdefault("primitive_id", primitive_id)
        p_type = p_data.get("type")
        if p_type == "groove":
            ordered = {
                "primitive_id": p_data.get("primitive_id"),
                "type": p_type,
            }
            for key in ("right_flank", "bottom", "left_flank"):
                if key in p_data:
                    ordered[key] = p_data[key]
            for key, value in p_data.items():
                if key not in ordered:
                    ordered[key] = value
            return ordered
        ordered = {
            "primitive_id": p_data.get("primitive_id"),
            "type": p_type,
        }
        for key, value in p_data.items():
            if key not in ordered:
                ordered[key] = value
        return ordered

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DefineRadialProfile":
        raw = data.get("profile_primitives", [])
        primitives = []
        for i, primitive in enumerate(raw, start=1):
            if not isinstance(primitive, dict):
                continue
            primitives.append(DefineRadialProfile._ordered_primitive(primitive, i))
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
            profile_primitives=primitives,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        primitives = []
        for i, primitive in enumerate(self.profile_primitives or [], start=1):
            if not isinstance(primitive, dict):
                continue
            primitives.append(self._ordered_primitive(primitive, i))
        base.update({
            "profile_id": int(self.profile_id),
            "profile_type": self.profile_type.value,
            "profile_primitives": primitives,
        })
        return base


# ------------------------------- Profiling -----------------------------------


@dataclass
class Profiling(TurnableOperation):
    cuttingParameters: CuttingParameters
    profilingParameters: ProfilingParameters
    profilingOptions: ProfilingOptions

    @classmethod
    def from_dict(cls, data: dict) -> "Profiling":
        spindle_parameters = TurnableOperation._parse_spindle(data)
        cutting_parameters = CuttingParameters.from_dict(data.get("cutting_parameters", {}))
        profiling_parameters = ProfilingParameters.from_dict(data.get("profiling_parameters", {}))
        profiling_options = ProfilingOptions.from_dict(data.get("profiling_options", {}))

        return cls(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindleParameters=spindle_parameters,
            cuttingParameters=cutting_parameters,
            profilingParameters=profiling_parameters,
            profilingOptions=profiling_options
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_spindle_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "profiling_parameters": self.profilingParameters.to_dict(),
            "profiling_options": self.profilingOptions.to_dict()
        })
        return base


# ------------------------------ Profile Roughing -----------------------------

@dataclass
class ProfileRoughing(TurnableOperation):
    cuttingParameters: CuttingParameters
    profilingParameters: ProfilingParameters
    profileRoughingStrategy: ProfileRoughingStrategy
    stockToLeave: StockToLeave
    m1Parameters: M1Parameters

    @classmethod
    def from_dict(cls, data: dict) -> "ProfileRoughing":
        spindle_parameters = TurnableOperation._parse_spindle(data)
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
            spindleParameters=spindle_parameters,
            cuttingParameters=cutting_parameters,
            profilingParameters=profiling_parameters,
            profileRoughingStrategy=profile_roughing_strategy,
            stockToLeave=stock_to_leave,
            m1Parameters=m1_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_spindle_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "profiling_parameters": self.profilingParameters.to_dict(),
            "profile_roughing_strategy": self.profileRoughingStrategy.to_dict(),
            "stock_to_leave": self.stockToLeave.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return base


@dataclass
class ProfileContour(TurnableOperation):
    cuttingParameters: CuttingParameters
    profilingParameters: ProfilingParameters
    profileContourStrategy: ProfileContourStrategy
    stockToLeave: StockToLeave
    stockToLeaveEnabled: bool

    @classmethod
    def from_dict(cls, data: dict) -> "ProfileContour":
        spindle_parameters = TurnableOperation._parse_spindle(data)
        cutting_parameters = CuttingParameters.from_dict(data.get("cutting_parameters", {}))
        profiling_parameters = ProfilingParameters.from_dict(data.get("profiling_parameters", {}))
        profile_contour_strategy = ProfileContourStrategy.from_dict(data.get("profile_contour_strategy", {}))
        stock_to_leave = StockToLeave.from_dict(data.get("stock_to_leave", {}))

        return cls(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindleParameters=spindle_parameters,
            cuttingParameters=cutting_parameters,
            profilingParameters=profiling_parameters,
            profileContourStrategy=profile_contour_strategy,
            stockToLeave=stock_to_leave,
            stockToLeaveEnabled=bool(data.get("stock_to_leave_enabled", False)),
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_spindle_to(base)
        base.update({
            "cutting_parameters": self.cuttingParameters.to_dict(),
            "profiling_parameters": self.profilingParameters.to_dict(),
            "profile_contour_strategy": self.profileContourStrategy.to_dict(),
            "stock_to_leave": self.stockToLeave.to_dict(),
            "stock_to_leave_enabled": bool(self.stockToLeaveEnabled),
        })
        return base


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
        spindle = TurnableOperation._parse_spindle(data)
        d = dict(data)
        return Threading(
            order=int(d["order"]),
            type=d["type"],
            generate_gcode=bool(d.get("generate_gcode", True)),
            is_optional_block=bool(d.get("is_optional_block", False)),
            spindleParameters=spindle,
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
        return self._add_spindle_to(base)


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
        spindle = TurnableOperation._parse_spindle(data)
        m1_parameters = M1Parameters.from_dict(
            data.get("m1_parameters") or {"include_m1": False}
        )
        d = dict(data)
        return G33Threading(
            order=int(d["order"]),
            type=d["type"],
            generate_gcode=bool(d.get("generate_gcode", True)),
            is_optional_block=bool(d.get("is_optional_block", False)),
            spindleParameters=spindle,
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
        return self._add_spindle_to(base)


# -------------------------------- Drilling -----------------------------------

@dataclass
class Drilling(TurnableOperation):
    drillingParameters: DrillingParameters
    m1Parameters: M1Parameters

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Drilling":
        spindle = TurnableOperation._parse_spindle(data)

        drilling_parameters = DrillingParameters.from_dict(data.get("drilling_parameters", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return Drilling(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindleParameters=spindle,
            drillingParameters=drilling_parameters,
            m1Parameters=m1_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_spindle_to(base)
        base.update({
            "drilling_parameters": self.drillingParameters.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return base


# --------------------------------- Tapping -----------------------------------

@dataclass
class Tapping(TurnableOperation):
    tappingParameters: TappingParameters
    m1Parameters: M1Parameters

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Tapping":
        spindle = TurnableOperation._parse_spindle(data)

        cutting_parameters = TappingParameters.from_dict(data.get("tapping_parameters", {}))
        m1_parameters = M1Parameters.from_dict(data.get("m1_parameters", {}))

        return Tapping(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindleParameters=spindle,
            tappingParameters=cutting_parameters,
            m1Parameters=m1_parameters,
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_spindle_to(base)
        base.update({
            "tapping_parameters": self.tappingParameters.to_dict(),
            "m1_parameters": self.m1Parameters.to_dict(),
        })
        return base


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
        spindle = TurnableOperation._parse_spindle(data)

        parting_parameters = PartingParameters.from_dict(data.get("parting_parameters", {}))
        edge_break = EdgeBreak.from_dict(data.get("edge_break", {}))

        return Parting(
            order=int(data["order"]),
            type=data["type"],
            generate_gcode=bool(data.get("generate_gcode", True)),
            is_optional_block=bool(data.get("is_optional_block", False)),
            spindleParameters=spindle,
            partingParameters=parting_parameters,
            edgeBreak=edge_break
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        self._add_spindle_to(base)
        base.update({
            "parting_parameters": self.partingParameters.to_dict(),
            "edge_break": self.edgeBreak.to_dict(),
        })
        return base


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
    "positionAt": PositionAt,
    "facing": Facing,
    "knurling": Knurling,
    "defineProfile": DefineProfile,
    "defineRadialProfile": DefineRadialProfile,
    "profiling": Profiling,
    "profileRoughing": ProfileRoughing,
    "profileContour": ProfileContour,
    "threading": Threading,
    "g33Threading": G33Threading,
    "drilling": Drilling,
    "tapping": Tapping,
    "parting": Parting
}

display_names: Dict[str, str] = {
    "changeTool": "Tool Change",
    "positionAt": "Position At",
    "facing": "Facing",
    "knurling": "SinglePoint Knurling",
    "defineProfile": "Define Profile",
    "defineRadialProfile": "Define Radial Profile",
    "profiling": "Profiling",
    "profileRoughing": "Profile Roughing",
    "profileContour": "Profile Contour",
    "threading": "Threading",
    "g33Threading": "G33 Threading",
    "drilling": "Drilling",
    "tapping": "Tapping",
    "parting": "Parting",
}


# -------------------- CAM config objects (built from JSON operation dicts) -------------------


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
