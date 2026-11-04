"""An operation's name as a program shows it and its G-code heads it."""


def _number(value):
    """25.0 as 25, 6.80 as 6.8."""
    return f"{float(value):.3f}".rstrip("0").rstrip(".")


def axial_tool_label(op, program, tools):
    """What Drilling and Tapping show of their tool, in brackets: the drill's
    diameter, (Ø25), or the tap's size, (M12 x 1mm) - the tool ``op`` cuts
    with - or (???) when that is not a drill, or a tap, or there is none.
    None for any other operation. ``tools``: where the tool is looked up,
    anything with tool_in(holder) - the Tool Library, a ToolSnapshot."""
    from teachinlathe.conversational.model.data_types import Drilling, Tapping
    from teachinlathe.tooling.model.data_types import DrillingTool, TappingTool
    if not isinstance(op, (Drilling, Tapping)):
        return None
    entry = program.tool_of(op) if program is not None else None
    tool = tools.tool_in(int(entry.tool_holder_id)) if entry is not None else None
    if isinstance(op, Drilling):
        if not isinstance(tool, DrillingTool) or tool.diameter <= 0:
            return "(???)"
        return f"(\u00d8{_number(tool.diameter)})"
    if not isinstance(tool, TappingTool) or tool.diameter <= 0 or tool.pitch <= 0:
        return "(???)"
    return f"(M{_number(tool.diameter)} x {_number(tool.pitch)}mm)"


def operation_title(op, program, tools):
    """``op``'s name as the program shows it: its display_name and, for
    Drilling and Tapping, its tool's size (axial_tool_label), looked up in
    ``tools``."""
    label = axial_tool_label(op, program, tools)
    return f"{op.display_name()} {label}" if label else op.display_name()
