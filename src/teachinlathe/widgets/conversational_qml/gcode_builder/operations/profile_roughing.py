from teachinlathe.conversational.data_types import PassType, ProfileRoughingConfig, ProfilingType

from ..helpers.utils import get_float


def parse_profile_roughing_config(op) -> ProfileRoughingConfig:
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    strategy = op.get("profile_roughing_strategy", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}

    try:
        profiling_type = ProfilingType(str(strategy.get("profiling_type", "od")).lower())
    except ValueError:
        profiling_type = ProfilingType.OD

    try:
        pass_type = PassType(str(strategy.get("pass_type", "axial")).lower())
    except ValueError:
        pass_type = PassType.AXIAL

    return ProfileRoughingConfig(
        x_start=get_float(params, "x_start", 0.0),
        z_start=get_float(params, "z_start", 0.0),
        doc=get_float(cutting, "doc", 0.5),
        retract=get_float(cutting, "retract", 1.0),
        feed_rate=get_float(cutting, "feed_rate", 0.1),
        stock_x=get_float(stock, "radial", 0.0),
        stock_z=get_float(stock, "axial", 0.0),
        profiling_type=profiling_type,
        pass_type=pass_type,
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


def generate_profile_roughing_gcode(op):
    parse_profile_roughing_config(op)
    return ["( TODO: gcode generator for Profile Roughing )"]
