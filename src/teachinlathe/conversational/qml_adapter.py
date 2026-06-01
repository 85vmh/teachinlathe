def build_selected_program_summary(program):
    return {
        "id": program.id,
        "name": program.header.name,
        "created_date": getattr(program.header, "created_date", ""),
        "last_edit": program.header.last_edit,
    }


def build_details_payload(obj):
    return obj.to_dict() if hasattr(obj, "to_dict") else None


def display_name_for_op(op_type, tool_no=None, pitch=None, profile_id=None, strategy=None, profiling_type=None, profile_type=None):
    op_type_value = (op_type or "").strip()
    if op_type_value == "changeTool":
        return f"Tool Change (T{tool_no})" if tool_no is not None else "Tool Change"
    if op_type_value == "positionAt":
        return "Position At"
    if op_type_value == "facing":
        return "Facing"
    if op_type_value == "knurling":
        return "SinglePoint Knurling"
    if op_type_value == "defineProfile":
        pt = profile_type.value if hasattr(profile_type, "value") else str(profile_type or "od").lower()
        type_str = "OD" if pt == "od" else "ID"
        return f"Define {type_str} Profile (P{profile_id})" if profile_id is not None else f"Define {type_str} Profile"
    if op_type_value == "profiling":
        strategy_value = strategy.value if hasattr(strategy, "value") else str(strategy or "").lower()
        prefix = "G71 " if strategy_value == "rough" else "G70 " if strategy_value == "finish" else ""
        if profile_id is not None and strategy is not None:
            strategy_str = strategy.value.capitalize() if hasattr(strategy, "value") else str(strategy).capitalize()
            return f"{prefix}Cut Profile (P:{profile_id}, {strategy_str})"
        if profile_id is not None:
            return f"{prefix}Cut Profile (P:{profile_id})"
        return f"{prefix}Cut Profile" if prefix else "Cut Profile"
    if op_type_value == "profileRoughing":
        pt = str(profiling_type or "od").lower()
        prefix = "OD" if pt == "od" else "ID"
        return f"{prefix} Profile Roughing (P{profile_id})" if profile_id is not None else f"{prefix} Profile Roughing"
    if op_type_value == "profileContour":
        pt = str(profiling_type or "od").lower()
        prefix = "OD" if pt == "od" else "ID"
        return f"{prefix} Profile Contour (P{profile_id})" if profile_id is not None else f"{prefix} Profile Contour"
    if op_type_value == "threading":
        return f"G76 Threading (P: {pitch})" if pitch is not None else "G76 Threading"
    if op_type_value == "drilling":
        return "Drilling"
    if op_type_value == "tapping":
        return "Tapping"
    if op_type_value == "parting":
        return "Parting"
    return op_type_value or "Unknown"


def build_operations_model(program):
    out = []
    operations = getattr(program, "operations", []) or []
    for op in operations:
        item = {
            "order": getattr(op, "order", None),
            "type": getattr(op, "type", ""),
            "generate_gcode": bool(getattr(op, "generate_gcode", False)),
            "is_optional_block": bool(getattr(op, "is_optional_block", False)),
        }
        tool_no = getattr(op, "tool_no", None)
        pitch = getattr(op, "pitch", None)
        profile_id = getattr(getattr(op, "profilingParameters", None), "profile_id", None)
        if profile_id is None:
            profile_id = getattr(op, "profile_id", None)
        strategy = getattr(getattr(op, "profilingOptions", None), "strategy", None)
        profiling_type = getattr(getattr(op, "profileRoughingStrategy", None), "profiling_type", None)
        if profiling_type is None:
            profiling_type = getattr(getattr(op, "profileContourStrategy", None), "profiling_type", None)
        if profiling_type is not None and hasattr(profiling_type, "value"):
            profiling_type = profiling_type.value
        profile_type = getattr(op, "profile_type", None)
        item["display_type"] = display_name_for_op(
            item["type"], tool_no=tool_no, pitch=pitch, profile_id=profile_id,
            strategy=strategy, profiling_type=profiling_type, profile_type=profile_type,
        )
        out.append(item)
    return out
