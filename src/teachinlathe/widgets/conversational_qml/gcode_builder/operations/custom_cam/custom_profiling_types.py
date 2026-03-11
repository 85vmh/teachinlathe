from dataclasses import dataclass


@dataclass(frozen=True)
class StartPoint:
    x: float
    z: float


@dataclass(frozen=True)
class ProfileLineSegment:
    end_x: float
    end_z: float
    blend_type: str = "none"
    blend_radius: float = 0.0
    blend_width: float = 0.0


@dataclass(frozen=True)
class ProfileArcSegment:
    end_x: float
    end_z: float
    center_x: float
    center_z: float
    radius: float
    gcode_dir: int
    blend_type: str = "none"
    blend_radius: float = 0.0
    blend_width: float = 0.0


@dataclass(frozen=True)
class ToolpathLine:
    end_x: float
    end_z: float


@dataclass(frozen=True)
class ToolpathArc:
    end_x: float
    end_z: float
    center_x: float
    center_z: float
    anticlockwise: bool


@dataclass(frozen=True)
class ProfilingConfig:
    x_start: float
    z_start: float
    doc: float
    retract: float
    feed_rate: float
    stock_x: float
    stock_z: float
    finish_passes: int
    spring_passes: int
    strategy: str
    optional_prefix: str


@dataclass(frozen=True)
class RoughPass:
    cut_x: float
    cut_z: float
    exit_x: float
    exit_z: float


@dataclass(frozen=True)
class ProfilePass:
    offset_x: float
    offset_z: float
