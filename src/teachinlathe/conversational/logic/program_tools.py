"""The tools a program cuts with (Program.tools), against the Tool Library.

An operation that cuts names one of the program's tools (its toolRef); the
tool keeps the holder it was chosen in, the cutting tool that was in it, and
a snapshot of both as they were then. The Tool Library may change after - the
cutting tool moved to another holder, edited, or gone - so before the tool is
used it is checked against the library: ``check``. A program is only turned
into G-code when every tool it cuts with is ``OK``.

``tools`` is anything with find_holder(id), tool_in(id) and its holders: the
Tool Library (ToolLibraryRepository) or a ToolSnapshot of it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from teachinlathe.conversational.model.data_types import (
    PredefinedPosition, Program, ProgramTool, TurnableOperation,
)


class ToolStatus(str, Enum):
    #: no tool chosen yet
    NONE = "none"
    #: the cutting tool is in its holder, as it was
    OK = "ok"
    #: the cutting tool, as it was, is in another holder now: to be confirmed
    MOVED = "moved"
    #: the cutting tool is mounted, but no longer as it was
    CHANGED = "changed"
    #: the cutting tool is in no holder
    MISSING = "missing"
    #: as chosen, but not a tool the operation can cut with (tool_fit) -
    #: the operation changed since: an OD profile become an ID one, say
    UNFIT = "unfit"


@dataclass(frozen=True)
class ToolCheck:
    status: ToolStatus
    #: where the cutting tool is now - the holder to confirm for MOVED, the
    #: one it was changed in for CHANGED; 0 when it is in none
    tool_holder_id: int = 0


def needs_tool(op) -> bool:
    return isinstance(op, TurnableOperation)


def _holders(tools):
    holders = tools.holders
    return list(holders.values()) if isinstance(holders, dict) else list(holders)


def snapshot_of(holder, tool) -> dict:
    """What a ProgramTool keeps of holder ``holder`` and the cutting tool
    ``tool`` in it."""
    place = getattr(holder, "z_offset_place", None)
    return {
        "holder": {"orientation": getattr(holder.orientation, "value", holder.orientation),
                   "z_offset_place": getattr(place, "value", place)},
        "cutting_tool": tool.to_json(),
    }


def _geometry(snapshot: dict) -> dict:
    """The part of a snapshot that tells two tools apart: all of it but the
    cutting tool's id and comment."""
    cutting = {k: v for k, v in (snapshot.get("cutting_tool") or {}).items()
               if k not in ("cutting_tool_id", "comment")}
    return {"holder": snapshot.get("holder") or {}, "cutting_tool": cutting}


def same_tool(snapshot: dict, holder, tool) -> bool:
    return _geometry(snapshot) == _geometry(snapshot_of(holder, tool))


def check(entry: Optional[ProgramTool], tools) -> ToolCheck:
    """Whether the Tool Library still has ``entry``'s tool as it was."""
    if entry is None:
        return ToolCheck(ToolStatus.NONE)
    tool = tools.tool_in(entry.tool_holder_id)
    if tool is not None and tool.cutting_tool_id == entry.cutting_tool_id:
        holder = tools.find_holder(entry.tool_holder_id)
        ok = same_tool(entry.snapshot, holder, tool)
        return ToolCheck(ToolStatus.OK if ok else ToolStatus.CHANGED, entry.tool_holder_id)
    for holder in _holders(tools):
        tool = tools.tool_in(holder.tool_holder_id)
        if tool is not None and tool.cutting_tool_id == entry.cutting_tool_id:
            ok = same_tool(entry.snapshot, holder, tool)
            return ToolCheck(ToolStatus.MOVED if ok else ToolStatus.CHANGED, holder.tool_holder_id)
    return ToolCheck(ToolStatus.MISSING)


def check_for(program: Program, op, tools) -> ToolCheck:
    """``check`` of ``op``'s tool, and UNFIT for one as chosen that ``op``
    cannot cut with."""
    from teachinlathe.conversational.logic import tool_fit
    result = check(program.tool_of(op), tools)
    if (result.status is ToolStatus.OK
            and not tool_fit.fits(program, op, tools.tool_in(result.tool_holder_id))):
        return ToolCheck(ToolStatus.UNFIT, result.tool_holder_id)
    return result


def users_of(program: Program, entry: ProgramTool) -> list:
    """The operations that cut with ``entry``."""
    return [op for op in program.operations if getattr(op, "toolRef", None) == entry.id]


def users_from(program: Program, op) -> list:
    """``op`` and the operations below it that cut with its tool; [op] with
    none chosen."""
    entry = program.tool_of(op)
    if entry is None:
        return [op]
    index = program.index_of(op)
    return [o for o in program.operations[index:] if getattr(o, "toolRef", None) == entry.id]


class Scope(str, Enum):
    """Which operations a tool chosen for one of them is for."""
    #: that one only
    THIS = "this"
    #: that one and those below it that cut with its tool - the ones above
    #: keep theirs
    BELOW = "below"
    #: every one cutting with its tool: the tool itself chosen again - a new
    #: tool change position, a move confirmed
    ALL = "all"


def choose_tool(program: Program, op, tool_holder_id: int, toolchange_position: PredefinedPosition,
                scope: Scope, tools) -> bool:
    """Have ``op`` - and with ``scope`` the others that cut with its tool -
    cut with the tool in holder ``tool_holder_id``, changed to at
    ``toolchange_position``; the others only where it fits them (tool_fit).
    A tool the program already has is used again, not added twice. False
    when the holder is empty, or its tool does not fit ``op``."""
    from teachinlathe.conversational.logic import tool_fit
    holder = tools.find_holder(int(tool_holder_id))
    tool = tools.tool_in(int(tool_holder_id))
    if holder is None or tool is None or not tool_fit.fits(program, op, tool):
        return False
    snapshot = snapshot_of(holder, tool)
    current = program.tool_of(op)
    same = next((t for t in program.tools if t.tool_holder_id == holder.tool_holder_id
                 and t.cutting_tool_id == tool.cutting_tool_id
                 and _geometry(t.snapshot) == _geometry(snapshot)), None)
    movers = {Scope.THIS: [op], Scope.BELOW: users_from(program, op),
              Scope.ALL: users_of(program, current) if current is not None else [op]}[scope]
    movers = [m for m in movers if m is op or tool_fit.fits(program, m, tool)]

    if current is not None and all(any(user is m for m in movers) for user in users_of(program, current)):
        # every operation cutting with it changes: the tool itself does
        target = current
        if same is not None and same is not current:
            # the program had it already: one tool, not two
            for user in users_of(program, same):
                user.toolRef = current.id
    elif same is not None:
        target = same
    else:
        target = ProgramTool(id=max((t.id for t in program.tools), default=0) + 1,
                             tool_holder_id=0, cutting_tool_id=None)
        program.tools.append(target)
    target.tool_holder_id = holder.tool_holder_id
    target.cutting_tool_id = tool.cutting_tool_id
    target.toolchange_position = toolchange_position
    target.snapshot = snapshot
    for user in movers:
        user.toolRef = target.id
    prune(program)
    return True


def prune(program: Program) -> None:
    """Drop the tools no operation cuts with, and the toolRefs naming none."""
    known = {t.id for t in program.tools}
    for op in program.operations:
        if getattr(op, "toolRef", None) is not None and op.toolRef not in known:
            op.toolRef = None
    used = {op.toolRef for op in program.operations if getattr(op, "toolRef", None) is not None}
    program.tools[:] = [t for t in program.tools if t.id in used]


def not_ready(program: Program, tools) -> List[str]:
    """What keeps the program from being turned into G-code: for each
    operation that is generated and cuts, with no tool or one the Tool
    Library no longer has as it was, a line saying so. Empty when ready."""
    problems = []
    for number, op in enumerate(program.operations, 1):
        if not op.generate_gcode or not needs_tool(op):
            continue
        result = check_for(program, op, tools)
        if result.status is ToolStatus.OK:
            continue
        name = op.display_name()
        entry = program.tool_of(op)
        problems.append(f"Operation #{number} {name}: " + {
            ToolStatus.NONE: "no tool chosen",
            ToolStatus.MOVED: f"T{entry.tool_holder_id if entry else 0} is now in "
                              f"T{result.tool_holder_id}, to be confirmed",
            ToolStatus.CHANGED: f"T{entry.tool_holder_id if entry else 0} was changed in the Tool Library",
            ToolStatus.MISSING: f"T{entry.tool_holder_id if entry else 0} is no longer in the Tool Library",
            ToolStatus.UNFIT: f"T{entry.tool_holder_id if entry else 0} is not a tool it can cut with",
        }[result.status])
    return problems
