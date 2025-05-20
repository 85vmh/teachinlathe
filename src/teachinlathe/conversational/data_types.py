import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from typing import Type

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

    @classmethod
    def from_dict(cls, data: dict) -> "Operation":
        """ Factory method to create the correct subclass instance from dict """
        op_type = data.get("type")
        if op_type not in operation_types:
            raise ValueError(f"Unknown operation type: {op_type}")

        # Instantiate the correct subclass based on type
        return operation_types[op_type](**data)


@dataclass
class ToolChangeDetails:
    x_pos: float
    z_pos: float
    coordinate_type: str
    move_sequence: str
    stop_spindle: bool

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ToolChangeDetails":
        return ToolChangeDetails(**data)  # ✅ Convertim dict direct în obiect

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__  # ✅ Convertim obiect în dict


@dataclass
class SetTool(Operation):
    tool_no: int
    tool_orientation: int
    back_angle: int
    front_angle: int
    toolchange_details: ToolChangeDetails

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SetTool":
        return SetTool(
            order=data["order"],
            type=data["type"],
            tool_no=data["tool_no"],
            tool_orientation=data["tool_orientation"],
            back_angle=data["back_angle"],
            front_angle=data["front_angle"],
            toolchange_details=ToolChangeDetails.from_dict(data["toolchange_details"])  # 🔹 Convertim corect aici
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "type": self.type,
            "tool_no": self.tool_no,
            "tool_orientation": self.tool_orientation,
            "back_angle": self.back_angle,
            "front_angle": self.front_angle,
            "toolchange_details": self.toolchange_details.to_dict()  # 🔹 Convertim corect înapoi în dict
        }




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


@dataclass
class DefineProfile(Operation):
    profileId: int
    profile_primitives: List[Dict[str, Any]]


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
    stock_to_leave: Optional[Dict[str, float]] = field(default=None)  # Nullable for Finishing
    spring_passes: Optional[int] = field(default=None)  # Nullable for Roughing

    @classmethod
    def from_dict(cls, data: dict) -> "Profiling":
        """Convert dict to Profiling object, handling nullable fields."""
        return cls(
            css_value=data["css_value"],
            max_speed=data["max_speed"],
            feed_rate=data["feed_rate"],
            profileId=data["profileId"],
            strategy=Strategy[data["strategy"]],  # Ensure enum parsing
            x_start=data["x_start"],
            z_start=data["z_start"],
            doc=data["doc"],
            retract=data["retract"],
            stock_to_leave=data.get("stock_to_leave"),  # Handles missing field
            spring_passes=data.get("spring_passes")  # Handles missing field
        )

    def to_dict(self) -> Dict[str, any]:
        """Convert Profiling object to dictionary, excluding None values."""
        data = {
            "css_value": self.css_value,
            "max_speed": self.max_speed,
            "feed_rate": self.feed_rate,
            "profileId": self.profileId,
            "strategy": self.strategy.name,  # Convert enum to string
            "x_start": self.x_start,
            "z_start": self.z_start,
            "doc": self.doc,
            "retract": self.retract,
        }
        if self.stock_to_leave is not None:
            data["stock_to_leave"] = self.stock_to_leave
        if self.spring_passes is not None:
            data["spring_passes"] = self.spring_passes
        return data


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


@dataclass
class Program:
    id: str
    header: Header
    operations: List[Operation]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Program":
        header = Header.from_dict(data["header"])
        operations = [Operation.from_dict(op) for op in data["operations"]]
        return Program(id=data["id"], header=header, operations=operations)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "header": self.header.to_dict(), "operations": [op.to_dict() for op in self.operations]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=4)

    @staticmethod
    def from_json(json_str: str) -> "Program":
        return Program.from_dict(json.loads(json_str))


operation_types: dict[str, Type["Operation"]] = {
    "setTool": SetTool,
    "facing": Facing,
    "define_profile": DefineProfile,
    "profiling": Profiling,
    "odThread": OdThread
}
