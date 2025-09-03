import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Type


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
        return self.__dict__


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


@dataclass
class ToolChangeDetails:
    x_pos: float
    z_pos: float
    coordinate_type: str
    move_sequence: str
    stop_spindle: bool

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ToolChangeDetails":
        return ToolChangeDetails(**data)

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


@dataclass
class ChangeTool(Operation):
    tool_no: int
    tool_orientation: int
    back_angle: int
    front_angle: int
    toolchange_details: ToolChangeDetails

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ChangeTool":
        return ChangeTool(
            order=data["order"],
            type=data["type"],
            generate_gcode=data["generate_gcode"],
            is_optional_block=data["is_optional_block"],
            tool_no=data["tool_no"],
            tool_orientation=data["tool_orientation"],
            back_angle=data["back_angle"],
            front_angle=data["front_angle"],
            toolchange_details=ToolChangeDetails.from_dict(data["toolchange_details"])
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "tool_no": self.tool_no,
            "tool_orientation": self.tool_orientation,
            "back_angle": self.back_angle,
            "front_angle": self.front_angle,
            "toolchange_details": self.toolchange_details.to_dict()
        })
        return base


@dataclass
class Facing(Operation):
    css_value: int
    max_speed: int
    feed_rate: float
    doc: float
    retract: float
    x_start: float
    z_start: float
    x_end: float
    z_end: float
    z_end_becomes_new_z0: bool

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Facing":
        return Facing(**data)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "css_value": self.css_value,
            "max_speed": self.max_speed,
            "feed_rate": self.feed_rate,
            "doc": self.doc,
            "retract": self.retract,
            "x_start": self.x_start,
            "z_start": self.z_start,
            "x_end": self.x_end,
            "z_end": self.z_end,
            "z_end_becomes_new_z0": self.z_end_becomes_new_z0
        })
        return base


@dataclass
class DefineProfile(Operation):
    profileId: int
    profile_primitives: List[Dict[str, Any]]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DefineProfile":
        return DefineProfile(**data)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "profileId": self.profileId,
            "profile_primitives": self.profile_primitives
        })
        return base


class Strategy(Enum):
    ROUGH = "rough"
    FINISH = "finish"


@dataclass
class Profiling(Operation):
    css_value: int
    max_speed: int
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
        return cls(
            **{
                **data,
                "strategy": Strategy[data["strategy"].upper()]
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "css_value": self.css_value,
            "max_speed": self.max_speed,
            "feed_rate": self.feed_rate,
            "profileId": self.profileId,
            "strategy": self.strategy.value,
            "x_start": self.x_start,
            "z_start": self.z_start,
            "doc": self.doc,
            "retract": self.retract,
            "stock_to_leave": self.stock_to_leave,
            "spring_passes": self.spring_passes
        })
        return base


@dataclass
class OdThread(Operation):
    spindle_rpm: int
    thread_type: str
    pitch: float
    major_diameter: float
    minor_diameter: float
    z_start: float
    z_end: float
    initial_doc: float
    retract: float
    spring_passes: int

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "OdThread":
        return OdThread(**data)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "spindle_rpm": self.spindle_rpm,
            "thread_type": self.thread_type,
            "pitch": self.pitch,
            "major_diameter": self.major_diameter,
            "minor_diameter": self.minor_diameter,
            "z_start": self.z_start,
            "z_end": self.z_end,
            "initial_doc": self.initial_doc,
            "retract": self.retract,
            "spring_passes": self.spring_passes
        })
        return base


@dataclass
class Drilling(Operation):
    spindle_rpm: int
    feed_rate: float
    z_start: float
    z_end: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Drilling":
        return Drilling(**data)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "spindle_rpm": self.spindle_rpm,
            "feed_rate": self.feed_rate,
            "z_start": self.z_start,
            "z_end": self.z_end
        })
        return base


@dataclass
class Tapping(Operation):
    spindle_rpm: int
    pitch: float
    z_start: float
    z_end: float

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Tapping":
        return Tapping(**data)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            "spindle_rpm": self.spindle_rpm,
            "pitch": self.pitch,
            "z_start": self.z_start,
            "z_end": self.z_end
        })
        return base


@dataclass
class Program:
    id: str
    header: Header
    operations: List[Operation]
    filename: Optional[str] = field(default=None, repr=False, compare=False)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Program":
        header = Header.from_dict(data["header"])
        operations = [Operation.from_dict(op) for op in data["operations"]]
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


operation_types: dict[str, Type[Operation]] = {
    "changeTool": ChangeTool,
    "facing": Facing,
    "define_profile": DefineProfile,
    "profiling": Profiling,
    "odThread": OdThread,
    "drilling": Drilling,
    "tapping": Tapping
}

display_names: dict[str, str] = {
    "changeTool": "Tool Change",
    "facing": "Facing",
    "define_profile": "Define Profile",
    "profiling": "Profiling",
    "odThread": "OD Thread",
    "drilling": "Drilling",
    "tapping": "Tapping"
}
