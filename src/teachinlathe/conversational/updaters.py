from teachinlathe.conversational.data_types import (
    BlendType,
    DefineRadialProfile,
    MoveSequence,
    PassType,
    PredefinedPosition,
    ProfilePrimitive,
    ProfilingType,
    SpindleMode,
    Strategy,
    ThreadLocation,
)


def _coerce_enum(value, enum_cls, transform=None):
    if isinstance(value, enum_cls):
        return value
    raw = transform(value) if transform else value
    return enum_cls(raw)


def _set_attr_if_present(obj, payload, key, attr=None, coerce=None):
    if obj is None or not isinstance(payload, dict) or key not in payload:
        return
    value = payload[key]
    if value is None:
        return
    target_attr = attr or key
    try:
        setattr(obj, target_attr, coerce(value) if coerce else value)
    except Exception:
        pass


def apply_operation_update(op, payload):
    if op is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(op, payload, "order", coerce=int)
    _set_attr_if_present(op, payload, "generate_gcode", coerce=bool)
    _set_attr_if_present(op, payload, "is_optional_block", coerce=bool)


def apply_spindle_update(spindle, payload):
    if spindle is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(spindle, payload, "direction", coerce=int)
    mode_value = payload.get("mode")
    if mode_value:
        try:
            spindle.mode = _coerce_enum(mode_value, SpindleMode, lambda v: str(v).lower())
        except Exception:
            pass
    elif payload.get("rpm_value") is not None:
        spindle.mode = SpindleMode.RPM
    elif payload.get("css_value") is not None and payload.get("css_max_speed") is not None:
        spindle.mode = SpindleMode.CSS
    _set_attr_if_present(spindle, payload, "rpm_value", coerce=int)
    _set_attr_if_present(spindle, payload, "css_value", coerce=int)
    _set_attr_if_present(spindle, payload, "css_max_speed", coerce=int)


def apply_m1_update(m1, payload):
    if m1 is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(m1, payload, "include_m1", coerce=bool)
    if "inspect_position" in payload and payload["inspect_position"] is not None:
        try:
            m1.inspect_position = _coerce_enum(payload["inspect_position"], PredefinedPosition, lambda v: str(v).upper())
        except Exception:
            pass
    _set_attr_if_present(m1, payload, "stop_spindle", coerce=bool)


def apply_cutting_update(cutting, payload):
    if cutting is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(cutting, payload, "feed_rate", attr="feedRate", coerce=float)
    _set_attr_if_present(cutting, payload, "retract", coerce=float)
    _set_attr_if_present(cutting, payload, "doc", coerce=float)


def apply_knurling_cutting_update(cutting, payload):
    if cutting is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(cutting, payload, "doc", coerce=float)
    _set_attr_if_present(cutting, payload, "retract", coerce=float)
    _set_attr_if_present(cutting, payload, "grooves_count", attr="groovesCount", coerce=int)


def apply_geometry_update(geometry, payload):
    if geometry is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(geometry, payload, "x_start", attr="xStart", coerce=float)
    _set_attr_if_present(geometry, payload, "z_start", attr="zStart", coerce=float)
    _set_attr_if_present(geometry, payload, "x_end", attr="xEnd", coerce=float)
    _set_attr_if_present(geometry, payload, "z_end", attr="zEnd", coerce=float)


def apply_drilling_update(drilling, payload):
    if drilling is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(drilling, payload, "z_start", attr="zStart", coerce=float)
    _set_attr_if_present(drilling, payload, "z_end", attr="zEnd", coerce=float)
    _set_attr_if_present(drilling, payload, "z_retract", attr="zRetract", coerce=float)
    _set_attr_if_present(drilling, payload, "peck_depth", attr="peckDepth", coerce=float)
    _set_attr_if_present(drilling, payload, "feed_rate", attr="feedRate", coerce=float)


def apply_tapping_update(tapping, payload):
    if tapping is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(tapping, payload, "z_start", attr="zStart", coerce=float)
    _set_attr_if_present(tapping, payload, "z_end", attr="zEnd", coerce=float)
    _set_attr_if_present(tapping, payload, "z_retract", attr="zRetract", coerce=float)
    _set_attr_if_present(tapping, payload, "peck_depth", attr="peckDepth", coerce=float)
    _set_attr_if_present(tapping, payload, "pitch", coerce=float)


def apply_parting_update(parting, payload):
    if parting is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(parting, payload, "x_start", attr="xStart", coerce=float)
    _set_attr_if_present(parting, payload, "x_end", attr="xEnd", coerce=float)
    _set_attr_if_present(parting, payload, "z_pos", attr="zPos", coerce=float)
    _set_attr_if_present(parting, payload, "first_feed_rate", coerce=float)
    _set_attr_if_present(parting, payload, "second_feed_rate", coerce=float)
    _set_attr_if_present(parting, payload, "second_feed_x_pos", coerce=float)
    _set_attr_if_present(parting, payload, "x_clearance", coerce=float)


def apply_profiling_parameters_update(profiling, payload):
    if profiling is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(profiling, payload, "profile_id", coerce=int)
    _set_attr_if_present(profiling, payload, "x_start", attr="xStart", coerce=float)
    _set_attr_if_present(profiling, payload, "z_start", attr="zStart", coerce=float)


def apply_profiling_options_update(options, payload):
    if options is None or not isinstance(payload, dict):
        return
    if "strategy" in payload and payload["strategy"] is not None:
        try:
            options.strategy = _coerce_enum(payload["strategy"], Strategy, lambda v: str(v).lower())
        except Exception:
            pass
    _set_attr_if_present(options, payload, "radial", attr="stockToLeaveX", coerce=float)
    _set_attr_if_present(options, payload, "axial", attr="stockToLeaveZ", coerce=float)
    _set_attr_if_present(options, payload, "finish_passes", attr="finishPasses", coerce=int)
    _set_attr_if_present(options, payload, "finish_spring_passes", attr="finishSpringPasses", coerce=int)


def apply_profile_roughing_strategy_update(strategy, payload):
    if strategy is None or not isinstance(payload, dict):
        return
    if "profiling_type" in payload and payload["profiling_type"] is not None:
        try:
            strategy.profiling_type = _coerce_enum(payload["profiling_type"], ProfilingType, lambda v: str(v).lower())
        except Exception:
            pass
    if "pass_type" in payload and payload["pass_type"] is not None:
        try:
            strategy.pass_type = _coerce_enum(payload["pass_type"], PassType, lambda v: str(v).lower())
        except Exception:
            pass
    if strategy.profiling_type == ProfilingType.OD and strategy.pass_type not in {PassType.AXIAL, PassType.RADIAL}:
        strategy.pass_type = PassType.AXIAL


def apply_profile_contour_strategy_update(strategy, payload):
    if strategy is None or not isinstance(payload, dict):
        return
    if "profiling_type" in payload and payload["profiling_type"] is not None:
        try:
            strategy.profiling_type = _coerce_enum(payload["profiling_type"], ProfilingType, lambda v: str(v).lower())
        except Exception:
            pass


def apply_stock_to_leave_update(stock, payload):
    if stock is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(stock, payload, "radial", attr="stockToLeaveX", coerce=float)
    _set_attr_if_present(stock, payload, "axial", attr="stockToLeaveZ", coerce=float)


def apply_edge_break_update(edge_break, payload):
    if edge_break is None or not isinstance(payload, dict):
        return
    if "blend_type" in payload and payload["blend_type"] is not None:
        try:
            edge_break.blend_type = _coerce_enum(payload["blend_type"], BlendType, lambda v: str(v).lower())
        except Exception:
            pass
    _set_attr_if_present(edge_break, payload, "chamfer_width", coerce=float)
    _set_attr_if_present(edge_break, payload, "fillet_radius", coerce=float)


def apply_threading_update(op, payload):
    if op is None or not isinstance(payload, dict):
        return
    if "location" in payload and payload["location"] is not None:
        try:
            op.location = _coerce_enum(payload["location"], ThreadLocation, lambda v: str(v).upper())
        except Exception:
            pass
    _set_attr_if_present(op, payload, "thread_type", coerce=str)
    _set_attr_if_present(op, payload, "pitch", coerce=float)
    _set_attr_if_present(op, payload, "starts", coerce=int)
    _set_attr_if_present(op, payload, "major_diameter", coerce=float)
    _set_attr_if_present(op, payload, "minor_diameter", coerce=float)
    _set_attr_if_present(op, payload, "z_start", coerce=float)
    _set_attr_if_present(op, payload, "z_end", coerce=float)
    _set_attr_if_present(op, payload, "initial_doc", coerce=float)
    _set_attr_if_present(op, payload, "retract", coerce=float)
    _set_attr_if_present(op, payload, "spring_passes", coerce=int)
    _set_attr_if_present(op, payload, "depth_degression", coerce=float)
    _set_attr_if_present(op, payload, "taper_type", coerce=int)
    _set_attr_if_present(op, payload, "compound_angle", coerce=float)


def apply_g33_threading_update(op, payload):
    if op is None or not isinstance(payload, dict):
        return
    if "location" in payload and payload["location"] is not None:
        try:
            op.location = _coerce_enum(payload["location"], ThreadLocation, lambda v: str(v).upper())
        except Exception:
            pass
    _set_attr_if_present(op, payload, "thread_type", coerce=str)
    _set_attr_if_present(op, payload, "pitch", coerce=float)
    _set_attr_if_present(op, payload, "starts", coerce=int)
    _set_attr_if_present(op, payload, "major_diameter", coerce=float)
    _set_attr_if_present(op, payload, "minor_diameter", coerce=float)
    _set_attr_if_present(op, payload, "z_start", coerce=float)
    _set_attr_if_present(op, payload, "z_end", coerce=float)
    _set_attr_if_present(op, payload, "initial_doc", coerce=float)
    _set_attr_if_present(op, payload, "retract", coerce=float)
    _set_attr_if_present(op, payload, "spring_passes", coerce=int)
    _set_attr_if_present(op, payload, "minimum_radial_increment", coerce=float)
    _set_attr_if_present(op, payload, "taper_type", coerce=int)
    _set_attr_if_present(op, payload, "compound_angle", coerce=float)


def apply_define_profile_update(op, payload):
    if op is None or not isinstance(payload, dict):
        return
    apply_operation_update(op, payload)
    _set_attr_if_present(op, payload, "profile_id", coerce=int)
    if "profile_type" in payload and payload["profile_type"] is not None:
        try:
            op.profile_type = _coerce_enum(payload["profile_type"], ProfilingType, lambda v: str(v).lower())
        except Exception:
            pass
    primitives_payload = payload.get("profile_primitives")
    if isinstance(primitives_payload, list):
        primitives = []
        for i, primitive in enumerate(primitives_payload, start=1):
            if not isinstance(primitive, dict):
                continue
            p_data = dict(primitive)
            p_data.setdefault("primitive_id", i)
            try:
                primitives.append(ProfilePrimitive.from_dict(p_data))
            except Exception:
                pass
        op.profile_primitives = primitives


def apply_define_radial_profile_update(op, payload):
    if op is None or not isinstance(payload, dict):
        return
    apply_operation_update(op, payload)
    _set_attr_if_present(op, payload, "profile_id", coerce=int)
    if "profile_type" in payload and payload["profile_type"] is not None:
        try:
            op.profile_type = _coerce_enum(payload["profile_type"], ProfilingType, lambda v: str(v).lower())
        except Exception:
            pass
    primitives_payload = payload.get("profile_primitives")
    if isinstance(primitives_payload, list):
        primitives = []
        for i, primitive in enumerate(primitives_payload, start=1):
            if not isinstance(primitive, dict):
                continue
            primitives.append(DefineRadialProfile._ordered_primitive(primitive, i))
        op.profile_primitives = primitives


def apply_position_details_update(details, payload):
    if details is None or not isinstance(payload, dict):
        return
    _set_attr_if_present(details, payload, "x_pos", coerce=float)
    _set_attr_if_present(details, payload, "z_pos", coerce=float)
    if "move_sequence" in payload and payload["move_sequence"] is not None:
        try:
            raw = str(payload["move_sequence"]).lower()
            if raw == "simultaneous":
                raw = "both"
            details.move_sequence = _coerce_enum(raw, MoveSequence)
        except Exception:
            pass
    if "stop_spindle_before_positioning" in payload:
        details.stop_spindle_before_positioning = bool(payload.get("stop_spindle_before_positioning", False))
    if "include_m0" in payload:
        details.include_m0 = bool(payload.get("include_m0", False))


def apply_predefined_position_update(op, payload, key="toolchange_position"):
    if op is None or not isinstance(payload, dict) or key not in payload or payload[key] is None:
        return
    try:
        setattr(op, key, _coerce_enum(payload[key], PredefinedPosition, lambda v: str(v).upper()))
    except Exception:
        pass


def apply_turnable_operation_update(op, payload):
    if op is None or not isinstance(payload, dict):
        return
    apply_operation_update(op, payload)
    apply_spindle_update(getattr(op, "spindleParameters", None), payload.get("spindle_parameters"))
