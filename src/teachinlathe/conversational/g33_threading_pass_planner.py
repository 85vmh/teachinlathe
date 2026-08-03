import math
from dataclasses import dataclass
from typing import List, Union

from teachinlathe.conversational.data_types import G33ThreadPassType, ThreadLocation


ThreadLocationInput = Union[ThreadLocation, str]


@dataclass(frozen=True)
class ThreadPass:
    index: int
    type: G33ThreadPassType
    radialDepth: float
    radialIncrement: float
    x: float
    zOffset: float
    zStart: float
    zEnd: float
    pitch: float


def _coerce_thread_location(value: ThreadLocationInput) -> ThreadLocation:
    if isinstance(value, ThreadLocation):
        return value

    raw = str(value or "").strip().upper()
    if raw == "OD":
        return ThreadLocation.OD
    if raw == "ID":
        return ThreadLocation.ID
    raise ValueError(f"Invalid threadLocation: {value!r}. Expected 'OD' or 'ID'.")


def _validate_inputs(
    zStart: float,
    zEnd: float,
    pitch: float,
    firstRadialDepth: float,
    finalRadialDepth: float,
    minimumRadialIncrement: float,
    springPasses: int,
    infeedAngleDegrees: float,
) -> None:
    if firstRadialDepth <= 0:
        raise ValueError("firstRadialDepth must be > 0")
    if finalRadialDepth <= 0:
        raise ValueError("finalRadialDepth must be > 0")
    if firstRadialDepth > finalRadialDepth:
        raise ValueError("firstRadialDepth must be <= finalRadialDepth")
    if springPasses < 0:
        raise ValueError("springPasses must be >= 0")
    if minimumRadialIncrement < 0:
        raise ValueError("minimumRadialIncrement must be >= 0")
    if zStart == zEnd:
        raise ValueError("zStart must not equal zEnd")
    if pitch <= 0:
        raise ValueError("pitch must be > 0")
    if infeedAngleDegrees < 0 or infeedAngleDegrees > 30:
        raise ValueError("infeedAngleDegrees must be between 0 and 30")


def plan_g33_threading_passes(
    *,
    xReference: float,
    zStart: float,
    zEnd: float,
    pitch: float,
    firstRadialDepth: float,
    finalRadialDepth: float,
    minimumRadialIncrement: float = 0.0,
    springPasses: int = 0,
    infeedAngleDegrees: float = 0.0,
    threadLocation: ThreadLocationInput = ThreadLocation.OD,
) -> List[ThreadPass]:
    """Calculate pass geometry for a multi-pass G33 threading cycle.

    The planner uses equal-area roughing increments for a 60 degree thread
    profile. It intentionally returns geometry only; no G-code is emitted here.
    """
    xReference = float(xReference)
    zStart = float(zStart)
    zEnd = float(zEnd)
    pitch = float(pitch)
    firstRadialDepth = float(firstRadialDepth)
    finalRadialDepth = float(finalRadialDepth)
    minimumRadialIncrement = float(minimumRadialIncrement)
    springPasses = int(springPasses)
    infeedAngleDegrees = float(infeedAngleDegrees)
    location = _coerce_thread_location(threadLocation)

    _validate_inputs(
        zStart=zStart,
        zEnd=zEnd,
        pitch=pitch,
        firstRadialDepth=firstRadialDepth,
        finalRadialDepth=finalRadialDepth,
        minimumRadialIncrement=minimumRadialIncrement,
        springPasses=springPasses,
        infeedAngleDegrees=infeedAngleDegrees,
    )

    if minimumRadialIncrement != 0.0:
        raise NotImplementedError("minimumRadialIncrement values above zero are not implemented yet")

    roughing_passes = int(math.ceil((finalRadialDepth / firstRadialDepth) ** 2))
    z_direction = -1.0 if zEnd < zStart else 1.0
    tan_infeed = math.tan(math.radians(infeedAngleDegrees))
    x_sign = -1.0 if location == ThreadLocation.OD else 1.0

    passes: List[ThreadPass] = []
    previous_depth = 0.0
    for i in range(1, roughing_passes + 1):
        radial_depth = finalRadialDepth if i == roughing_passes else finalRadialDepth * math.sqrt(i / roughing_passes)
        radial_increment = radial_depth - previous_depth
        z_offset = z_direction * radial_depth * tan_infeed

        passes.append(
            ThreadPass(
                index=i,
                type=G33ThreadPassType.ROUGHING,
                radialDepth=radial_depth,
                radialIncrement=radial_increment,
                x=xReference + x_sign * 2.0 * radial_depth,
                zOffset=z_offset,
                zStart=zStart + z_offset,
                zEnd=zEnd + z_offset,
                pitch=pitch,
            )
        )
        previous_depth = radial_depth

    final_pass = passes[-1]
    for offset in range(1, springPasses + 1):
        passes.append(
            ThreadPass(
                index=offset,
                type=G33ThreadPassType.SPRING,
                radialDepth=final_pass.radialDepth,
                radialIncrement=0.0,
                x=final_pass.x,
                zOffset=final_pass.zOffset,
                zStart=final_pass.zStart,
                zEnd=final_pass.zEnd,
                pitch=final_pass.pitch,
            )
        )

    return passes
