def build_selected_program_summary(program):
    return {
        "id": program.id,
        "name": program.header.name,
        "created_date": getattr(program.header, "created_date", ""),
        "last_edit": program.header.last_edit,
        # the work offset's P number: 1 is G54 ... 6 is G59
        "datum": int(getattr(program.header, "datum", 1) or 1),
    }


def build_details_payload(obj):
    return obj.to_dict() if hasattr(obj, "to_dict") else None


def _number(value):
    """25.0 as 25, 6.80 as 6.8."""
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def axial_tool_label(op_type, operations, index):
    """What Drilling and Tapping show of their tool, in brackets: the drill's
    diameter, (Ø25), or the tap's size, (M12 x 1mm) - the tool the last
    Change Tool above ``index`` puts in, from the Tool Library - or (???)
    when that is not a drill, or a tap, or there is none. None for any other
    operation."""
    kind = {"drilling": "drill", "tapping": "tap"}.get(op_type)
    if kind is None:
        return None
    from teachinlathe.ui.tabs.programs.backplot import tool_source
    change = next((o for o in reversed((operations or [])[:max(index, 0)])
                   if getattr(o, "type", "") == "changeTool"), None)
    tool = tool_source.describe(int(getattr(change, "tool_no", 0) or 0)) if change is not None else {}
    if tool.get("kind") != kind or not tool.get("diameter"):
        return "(???)"
    if kind == "drill":
        return f"(\u00d8{_number(tool['diameter'])})"
    if not tool.get("pitch"):
        return "(???)"
    return f"(M{_number(tool['diameter'])} x {_number(tool['pitch'])}mm)"


def display_name_for_op(op_type, tool_no=None, pitch=None, profile_id=None, strategy=None, profiling_type=None, profile_type=None, tool_label=None, rest=False):
    op_type_value = (op_type or "").strip()
    if op_type_value == "changeTool":
        if tool_no is not None and int(tool_no) <= 0:
            return "Tool Change (choose a tool)"
        return f"Tool Change (T{tool_no})" if tool_no is not None else "Tool Change"
    if op_type_value == "positionAt":
        return "Position At"
    if op_type_value == "facing":
        return "Facing"
    if op_type_value == "knurling":
        return "SinglePoint Knurling"
    if op_type_value in ("defineProfile", "importDxfProfile"):
        pt = profile_type.value if hasattr(profile_type, "value") else str(profile_type or "od").lower()
        type_str = "OD" if pt == "od" else "ID"
        prefix = "Import DXF" if op_type_value == "importDxfProfile" else "Define"
        return f"{prefix} {type_str} Profile (P{profile_id})" if profile_id is not None else f"{prefix} {type_str} Profile"
    if op_type_value == "defineRadialProfile":
        return f"Define Radial Profile (P{profile_id})" if profile_id is not None else "Define Radial Profile"
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
        name = f"{prefix} Profile Roughing (P{profile_id})" if profile_id is not None else f"{prefix} Profile Roughing"
        return name + " · Rest" if rest else name
    if op_type_value == "profileContour":
        pt = str(profiling_type or "od").lower()
        prefix = "OD" if pt == "od" else "ID"
        return f"{prefix} Profile Contour (P{profile_id})" if profile_id is not None else f"{prefix} Profile Contour"
    if op_type_value == "grooveRoughing":
        return f"Groove Roughing (P{profile_id})" if profile_id is not None else "Groove Roughing"
    if op_type_value == "grooveFinishing":
        return f"Groove Finishing (P{profile_id})" if profile_id is not None else "Groove Finishing"
    if op_type_value == "threading":
        return f"G76 Threading (P: {pitch})" if pitch is not None else "G76 Threading"
    if op_type_value == "g33Threading":
        return f"G33 Threading (P: {pitch})" if pitch is not None else "G33 Threading"
    if op_type_value == "drilling":
        return f"Drilling {tool_label}" if tool_label else "Drilling"
    if op_type_value == "tapping":
        return f"Tapping {tool_label}" if tool_label else "Tapping"
    if op_type_value == "parting":
        return "Parting"
    return op_type_value or "Unknown"


def build_operations_model(program):
    out = []
    operations = getattr(program, "operations", []) or []
    inherited_tool = None
    pending_tool = None
    group_start = None
    tool_picker_types = {
        "facing", "profileRoughing", "profileContour", "drilling",
        "tapping", "parting", "g33Threading",
    }
    for index, op in enumerate(operations):
        op_type = getattr(op, "type", "")
        if op_type == "changeTool":
            if group_start is None:
                group_start = index
            pending_tool = int(getattr(op, "tool_no", 0) or 0)
            continue

        tool_label = ""
        if pending_tool is not None:
            if op_type in tool_picker_types and pending_tool > 0 and pending_tool != inherited_tool:
                tool_label = f"T{pending_tool}"
            inherited_tool = pending_tool
        item = {
            "order": len(out) + 1,
            "source_index": index,
            "group_start_index": group_start if group_start is not None else index,
            "tool_label": tool_label,
            "type": op_type,
            "generate_gcode": bool(getattr(op, "generate_gcode", False)),
            "is_optional_block": bool(getattr(op, "is_optional_block", False)),
        }
        pending_tool = None
        group_start = None
        tool_no = getattr(op, "tool_no", None)
        pitch = getattr(op, "pitch", None)
        profile_id = getattr(getattr(op, "profilingParameters", None), "profile_id", None)
        if profile_id is None:
            profile_id = getattr(getattr(op, "roughingParameters", None), "profile_id", None)
        if profile_id is None:
            profile_id = getattr(getattr(op, "finishingParameters", None), "profile_id", None)
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
            tool_label=axial_tool_label(item["type"], operations, index),
            rest=bool(getattr(op, "restMaterial", False)),
        )
        out.append(item)
    return out
