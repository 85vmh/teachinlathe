from teachinlathe.conversational.data_types import ProfileContourConfig, ProfilingType

from ..helpers.utils import get_float


def parse_profile_contour_config(op) -> ProfileContourConfig:
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    strategy = op.get("profile_contour_strategy", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}

    try:
        profiling_type = ProfilingType(str(strategy.get("profiling_type", "od")).lower())
    except ValueError:
        profiling_type = ProfilingType.OD

    stock_enabled = bool(op.get("stock_to_leave_enabled", False))

    return ProfileContourConfig(
        x_start=get_float(params, "x_start", 0.0),
        z_start=get_float(params, "z_start", 0.0),
        doc=get_float(cutting, "doc", 0.5),
        retract=get_float(cutting, "retract", 1.0),
        feed_rate=get_float(cutting, "feed_rate", 0.1),
        stock_x=get_float(stock, "radial", 0.0) if stock_enabled else 0.0,
        stock_z=get_float(stock, "axial", 0.0) if stock_enabled else 0.0,
        stock_enabled=stock_enabled,
        profiling_type=profiling_type,
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


def generate_profile_contour_gcode(op):
    parse_profile_contour_config(op)
    return ["( TODO: gcode generator for Profile Contour )"]
