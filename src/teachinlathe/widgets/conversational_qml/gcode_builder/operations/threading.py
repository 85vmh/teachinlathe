from ..config import fmt
from ..helpers.spindle import build_spindle_gcode
from ..helpers.utils import get_float


def generate_threading_gcode(op):
    is_optional = bool(op.get("is_optional_block", False))
    line_prefix = "/" if is_optional else ""

    spindle = op.get("spindle_parameters", {}) or {}
    location = str(op.get("location", "OD"))
    major_d = get_float(op, "major_diameter", 0.0)
    minor_d = get_float(op, "minor_diameter", 0.0)

    if location.upper() == "ID":
        x_start = minor_d
        x_end = major_d
    else:
        x_start = major_d
        x_end = minor_d

    z_start = get_float(op, "z_start", 0.0)
    z_end = get_float(op, "z_end", 0.0)
    pitch = get_float(op, "pitch", 0.0)
    starts = int(op.get("starts", 1) or 1)
    retract = abs(get_float(op, "retract", 0.0))
    if location.upper() == "ID":
        retract = -retract
    initial_doc = get_float(op, "initial_doc", 0.0)
    depth_degression = get_float(op, "depth_degression", 1.0)
    compound_angle = get_float(op, "compound_angle", 0.0)
    taper_type = int(op.get("taper_type", 0) or 0)
    spring_passes = int(op.get("spring_passes", 0) or 0)

    taper_angle = 45

    lines = []
    lines.extend(build_spindle_gcode(spindle, line_prefix))
    lines.append(
        f"{line_prefix}o<threading> call "
        f"[{fmt(x_start)}] "
        f"[{fmt(z_start)}] "
        f"[{fmt(x_end)}] "
        f"[{fmt(z_end)}] "
        f"[{fmt(retract)}] "
        f"[{fmt(pitch)}] "
        f"[{starts}] "
        f"[{fmt(initial_doc)}] "
        f"[{fmt(depth_degression)}] "
        f"[{fmt(compound_angle)}] "
        f"[{taper_type}] "
        f"[{taper_angle}] "
        f"[{spring_passes}]"
    )
    return lines
