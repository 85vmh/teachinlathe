"""The LinuxCNC tool table, written from the tool holders.

The holders are the source of truth: holder N is tool T<N> in pocket N, its
offsets the holder's, its shape the cutting tool mounted in it. Each time
the tool library changes the whole table is written again - a tool number
with no holder, or a holder with no tool, has no line - together with
tools_extras.json, which carries what the .tbl has no column for (a
blade's width, a drill's diameter...) for the G-code builder and the
Programs tab. LinuxCNC is then told to read the table again.

Column by column:

* X, Z - the holder's offsets, 0 until it is touched off.
* D - a diameter, as LinuxCNC takes it: twice an insert's nose radius, the
  blade's larger corner radius doubled, a drill's, reamer's or tap's own.
* I, J - an insert's edges, both measured from the Z axis as LinuxCNC
  draws them: I the front angle, J 180 less the back one, so J - I is the
  corner. 0 for tools that are not inserts.
* Q - the orientation: the insert's or the blade's, 7 on the axis.
* the comment - the tool's name, and its own comment in brackets.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from teachinlathe.tooling.model import insert_catalog
from teachinlathe.tooling.model.data_types import (
    BladeTool, BoringTool, CuttingTool, DrillingTool, ReamingTool, TappingTool,
    ThreadingTool, ToolHolder, TurningTool, ZOffsetPlace,
)
from teachinlathe.tooling.store.tool_library_store import ToolLibraryStore

from .tool_entry import ToolEntry, ToolType, make_tool
from .tool_extras_store import ToolExtrasStore
from .tool_table_file import write_tbl

log = logging.getLogger(__name__)

#: Where a drill, a reamer or a tap sits: on the axis, pointing -Z.
_AXIAL_ORIENTATION = 7

_BLADE_REFERENCES = {
    ZOffsetPlace.LEFT: "left",
    ZOffsetPlace.MIDDLE: "center",
    ZOffsetPlace.RIGHT: "right",
}


def tool_entries(store: ToolLibraryStore) -> List[ToolEntry]:
    """A tool table line, with its extras, for each holder with a tool."""
    entries = []
    for holder in store.holders:
        tool = store.find_tool(holder.cutting_tool_id)
        if tool is not None:
            entries.append(tool_entry(holder, tool))
    return entries


def tool_entry(holder: ToolHolder, tool: CuttingTool) -> ToolEntry:
    number = holder.tool_holder_id
    base = ToolEntry(t=number, p=number,
                     x=holder.x_offset or 0.0, z=holder.z_offset or 0.0,
                     r=_comment(tool), last_loaded=holder.last_loaded)
    tool_type, extras = ToolType.GENERIC, {}

    if isinstance(tool, (TurningTool, ThreadingTool)):
        insert = insert_catalog.insert_for(tool.insert)
        base.d = 2 * insert.nose_radius
        base.i = tool.front_angle if isinstance(tool, TurningTool) else 0.0
        base.j = 180.0 - tool.back_angle if isinstance(tool, TurningTool) else 0.0
        base.q = tool.orientation
        if isinstance(tool, BoringTool) and tool.solid_body is not None:
            tool_type = ToolType.BORING_BAR
            extras = {"min_diameter": tool.solid_body.diameter,
                      "max_undercut": tool.solid_body.max_radial_undercut}
    elif isinstance(tool, BladeTool):
        base.d = 2 * max(tool.left_radius, tool.right_radius)
        base.q = tool.orientation
        tool_type = ToolType.PARTING_BLADE
        extras = {"width": tool.blade_width,
                  "left_radius": tool.left_radius, "right_radius": tool.right_radius,
                  "z0_reference": _BLADE_REFERENCES.get(holder.z_offset_place, "center")}
    elif isinstance(tool, (DrillingTool, ReamingTool, TappingTool)):
        base.d = tool.diameter
        base.q = _AXIAL_ORIENTATION
        tool_type = {DrillingTool: ToolType.DRILL, ReamingTool: ToolType.REAMER,
                     TappingTool: ToolType.TAP}[type(tool)]
        extras = {"diameter": tool.diameter}
        if isinstance(tool, TappingTool):
            extras["pitch"] = tool.pitch

    entry = make_tool(base, tool_type, extras)
    entry.last_loaded = holder.last_loaded
    return entry


def write_tool_table(store: ToolLibraryStore, tbl_path: str | Path) -> None:
    """Write the .tbl and tools_extras.json from the holders."""
    entries = tool_entries(store)
    write_tbl(tbl_path, entries)
    ToolExtrasStore(tbl_path).replace_all(
        {str(entry.t): entry.to_extras_dict() for entry in entries})


class ToolTableSync:
    """Keeps the tool table written from `store`, and LinuxCNC reading it."""

    def __init__(self, store: ToolLibraryStore, tbl_path: str | Path, command=None) -> None:
        self._store = store
        self._tbl_path = Path(tbl_path)
        self._command = command if command is not None else _linuxcnc_command()
        store.add_listener(self.sync)

    def sync(self) -> None:
        try:
            write_tool_table(self._store, self._tbl_path)
        except OSError as exc:
            log.error("cannot write the tool table %s: %s", self._tbl_path, exc)
            return
        if self._command is not None:
            try:
                self._command.load_tool_table()
            except Exception:
                log.exception("LinuxCNC did not reload the tool table")


def _comment(tool: CuttingTool) -> str:
    name = _designation(tool)
    return f"{name} ({tool.comment})" if tool.comment else name


def _designation(tool: CuttingTool) -> str:
    """The tool's name as its card heads it, in plain text."""
    if isinstance(tool, ThreadingTool):
        return f"{tool.insert.size}{tool.insert.geometry.upper()} {tool.pitch:g}"
    if isinstance(tool, TurningTool):
        spec = tool.insert
        return (f"{insert_catalog.family_of(spec)} {spec.size}"
                f"{insert_catalog.thickness_code(spec)}{spec.radius}")
    if isinstance(tool, BladeTool):
        return f"Blade {tool.blade_width:g} mm"
    if isinstance(tool, DrillingTool):
        return f"Drill D{tool.diameter:g}"
    if isinstance(tool, ReamingTool):
        return f"Reamer D{tool.diameter:g}"
    if isinstance(tool, TappingTool):
        return f"Tap M{tool.diameter:g}x{tool.pitch:g}"
    return tool.details()


def _linuxcnc_command():
    try:
        import linuxcnc
        return linuxcnc.command()
    except Exception:
        return None
