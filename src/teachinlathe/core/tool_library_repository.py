"""The tool library: the tool holders, the cutting tools mounted in them, and
the LinuxCNC tool table written from them. The one place any of it is read,
changed or watched from.

Two data sources, one truth each:

* the tool table (ToolTblFileDataSource) has the offsets. Only touching off
  sets them - LinuxCNC writes the file itself for G10 - except that a holder
  given another tool starts again from zero. Everything else on a line is
  written from the holders, the offsets as the file has them at that moment.
* tool_holders.json and cutting_tools.json (LatheToolExtrasDataSource) have
  the rest: which tool is in which holder, what it is, whether the holder
  was touched off with it, and which tool was in the spindle.

Holder N is tool T<N> in pocket N; a holder with no tool has no line.

Column by column:

* X, Z - the offsets, as the tool table has them.
* D - a diameter, as LinuxCNC takes it: twice an insert's nose radius, the
  blade's larger corner radius doubled, a drill's, reamer's or tap's own.
* I, J - an insert's edges, both measured from the Z axis as LinuxCNC
  draws them: I the front angle, J 180 less the back one, so J - I is the
  corner. 0 for tools that are not inserts.
* Q - the orientation: the insert's or the blade's, 7 on the axis.
* the comment - the tool's name, and its own comment in brackets.

LinuxCNC forgets the tool in the spindle across a restart; the operator does
not, and the tool is still physically there. Once the machine is homed the
remembered tool is put back with M61, if the spindle reads as empty.
"""

from __future__ import annotations

import dataclasses
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import linuxcnc
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from teachinlathe.tooling.model import insert_catalog
from teachinlathe.tooling.model.data_types import (
    BladeTool, CuttingTool, CuttingToolType, DrillingTool, ReamingTool,
    TappingTool, ThreadingTool, ToolHolder, TurningTool, ZOffsetPlace,
)

from .command_repository import command_repository
from .ini_repository import ini_repository
from .lathe_tool_extras_data_source import LatheToolExtrasDataSource
from .status_repository import status_repository
from .tool_tbl_file_data_source import TblEntry, ToolTblFileDataSource

log = logging.getLogger(__name__)

#: Where a drill, a reamer or a tap sits: on the axis, pointing -Z.
_AXIAL_ORIENTATION = 7

#: How long to wait after homing before putting the remembered tool back,
#: so LinuxCNC has finished switching modes.
RESTORE_TOOL_DELAY_MS = 200

#: How many status polls a touch-off is waited for when the interpreter is
#: never seen busy - G10 can run inside one poll.
_TOUCH_OFF_POLLS = 4


class ToolLibraryRepository(QObject):
    #: The holders or the cutting tools changed: anything listing them
    #: reads them again.
    toolsChanged = pyqtSignal()
    #: Another tool went into the spindle: it's number, 0 for none.
    currentToolChanged = pyqtSignal(int)
    #: A touch-off finished: the holder, and the axis - "x" or "z".
    touchedOff = pyqtSignal(int, str)

    def __init__(self, tool_table: ToolTblFileDataSource,
                 extras: LatheToolExtrasDataSource,
                 status=None, commands=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._tool_table = tool_table
        self._extras = extras
        self._status = status_repository() if status is None else status
        self._commands = command_repository() if commands is None else commands

        self.cutting_tools: List[CuttingTool] = extras.read_cutting_tools()
        self.holders: List[ToolHolder]
        self.holders, self._remembered_tool = extras.read_holders()
        self._current = self._read_tool_in_spindle()
        # Until homing has had its chance to put the remembered tool back,
        # the empty spindle LinuxCNC starts with is not the operator's doing.
        self._restore_settled = False
        self._restore_in_flight = False
        self._touch_off: Optional[dict] = None

        # Both files as this code writes them from the start - a holders file
        # from before the offsets moved out of it, too - and the tool table
        # following the holders, the offsets as it has them.
        self._write_holders()
        self._write_tool_table()
        tool_table.changed.connect(self._on_tool_table_changed)

        self._status.tool_in_spindle.notify(self._on_tool_in_spindle)
        # Homed and on, in either order - or already, when only the app
        # was restarted.
        self._status.all_axes_homed.notify(self._restore_tool)
        self._status.enabled.notify(self._restore_tool)
        self._status.polled.connect(self._poll_touch_off)
        self._restore_tool()

    # ── Queries ─────────────────────────────────────────────────────────────

    @property
    def current_tool(self) -> int:
        """The tool in the spindle, 0 for none."""
        return self._current

    @property
    def current_holder(self) -> Optional[ToolHolder]:
        return self.find_holder(self._current)

    def tools_of(self, tool_type: CuttingToolType) -> List[CuttingTool]:
        return [t for t in self.cutting_tools if t.tool_type is tool_type]

    def find_tool(self, cutting_tool_id: Optional[int]) -> Optional[CuttingTool]:
        return next((t for t in self.cutting_tools
                     if t.cutting_tool_id == cutting_tool_id), None)

    def find_holder(self, tool_holder_id: Optional[int]) -> Optional[ToolHolder]:
        return next((h for h in self.holders
                     if h.tool_holder_id == tool_holder_id), None)

    def holder_of(self, cutting_tool_id: int) -> Optional[ToolHolder]:
        return next((h for h in self.holders
                     if h.cutting_tool_id == cutting_tool_id), None)

    def tool_in(self, tool_holder_id: Optional[int]) -> Optional[CuttingTool]:
        """The cutting tool mounted in a holder, or None."""
        holder = self.find_holder(tool_holder_id)
        return self.find_tool(holder.cutting_tool_id) if holder is not None else None

    def next_cutting_tool_id(self) -> int:
        return max((t.cutting_tool_id for t in self.cutting_tools), default=0) + 1

    # ── Holders ─────────────────────────────────────────────────────────────

    def mount(self, tool_holder_id: int, cutting_tool_id: Optional[int]) -> None:
        """Clamp a cutting tool in a holder; its offsets go back to zero.

        A cutting tool is in one holder at a time, so one that was in another
        holder moves: that holder is left empty.
        """
        holder = self._holder(tool_holder_id)
        if cutting_tool_id is not None:
            if self.find_tool(cutting_tool_id) is None:
                raise KeyError(f"no cutting tool {cutting_tool_id}")
            previous = self.holder_of(cutting_tool_id)
            if previous is not None and previous is not holder:
                previous.mount(None)
        holder.mount(cutting_tool_id)
        self._save_holders(zeroed={tool_holder_id})

    def add_holder(self) -> ToolHolder:
        """A new, empty holder, numbered after the last: T<n+1>."""
        tool_holder_id = max((h.tool_holder_id for h in self.holders), default=0) + 1
        holder = ToolHolder(tool_holder_id)
        self.holders.append(holder)
        self._save_holders()
        return holder

    def delete_holder(self, tool_holder_id: int) -> None:
        """Remove an empty holder. One with a tool in it, or the one in the
        spindle, is not removed."""
        holder = self._holder(tool_holder_id)
        if holder.has_tool:
            raise ValueError(f"tool holder {tool_holder_id} has a tool mounted")
        if tool_holder_id == self._current:
            raise ValueError(f"tool holder {tool_holder_id} is in the spindle")
        self.holders.remove(holder)
        self._save_holders()

    def set_z_offset_place(self, tool_holder_id: int, place: Optional[ZOffsetPlace]) -> None:
        """Which point of the blade in the holder its Z offset is taken from."""
        self._holder(tool_holder_id).z_offset_place = place
        self._save_holders()

    # ── Cutting tools ───────────────────────────────────────────────────────

    def save_cutting_tool(self, tool: CuttingTool) -> None:
        """Add the tool, or replace the one with its id.

        Offsets were taken with the tool as it was. Any change to it other
        than the spindle direction or the comment - insert, nose radius,
        orientation, angles - moves the tip, so the holder it is clamped in
        has to be touched off again.
        """
        for index, existing in enumerate(self.cutting_tools):
            if existing.cutting_tool_id == tool.cutting_tool_id:
                self.cutting_tools[index] = tool
                if _geometry_changed(existing, tool):
                    self._invalidate_offsets(tool.cutting_tool_id)
                break
        else:
            self.cutting_tools.append(tool)
        self._extras.write_cutting_tools(self.cutting_tools)
        self._save_holders()

    def delete_cutting_tool(self, cutting_tool_id: int) -> None:
        """Remove a cutting tool. One mounted in a holder is not removed:
        the holder would be left naming a tool that is gone."""
        if self.holder_of(cutting_tool_id) is not None:
            raise ValueError(f"cutting tool {cutting_tool_id} is mounted")
        tool = self.find_tool(cutting_tool_id)
        if tool is None:
            raise KeyError(f"no cutting tool {cutting_tool_id}")
        self.cutting_tools.remove(tool)
        self._extras.write_cutting_tools(self.cutting_tools)
        self.toolsChanged.emit()

    def _invalidate_offsets(self, cutting_tool_id: int) -> None:
        holder = self.holder_of(cutting_tool_id)
        if holder is None or not (holder.x_touched or holder.z_touched):
            return
        log.info("cutting tool %s changed: holder %s needs touching off again",
                 cutting_tool_id, holder.tool_holder_id)
        holder.invalidate_offsets()

    # ── The machine ─────────────────────────────────────────────────────────

    def load_tool(self, tool_holder_id: int) -> bool:
        """Put a holder in the spindle - it is there already, physically."""
        holder = self.find_holder(tool_holder_id)
        if holder is None or not holder.has_tool:
            log.warning("T%s has no tool to load", tool_holder_id)
            return False
        return self._commands.issue_mdi(f"M61 Q{tool_holder_id} G43")

    def touch_off(self, axis: str, value) -> bool:
        """Touch the holder in the spindle off in `axis` ("x" or "z"):
        LinuxCNC works the offset out and writes it to the tool table. Once
        it has, the holder counts as touched off in that axis, and
        touchedOff says so."""
        holder = self.current_holder
        if holder is None or not holder.has_tool:
            log.warning("no tool in the spindle to touch off")
            return False
        if not self._commands.issue_mdi(f"o<touch_off_{axis}> call [{value}]"):
            return False
        self._touch_off = {"axis": axis, "holder": holder.tool_holder_id,
                           "busy": False, "polls": 0}
        return True

    def _poll_touch_off(self) -> None:
        touch_off = self._touch_off
        if touch_off is None:
            return
        touch_off["polls"] += 1
        try:
            if self._status.stat.interp_state != linuxcnc.INTERP_IDLE:
                touch_off["busy"] = True
                return
        except Exception:
            return
        if not touch_off["busy"] and touch_off["polls"] < _TOUCH_OFF_POLLS:
            return
        self._touch_off = None

        holder = self.find_holder(touch_off["holder"])
        if holder is None:
            return
        self._read_offsets()
        setattr(holder, f"{touch_off['axis']}_touched", True)
        self._write_holders()
        self.toolsChanged.emit()
        self.touchedOff.emit(holder.tool_holder_id, touch_off["axis"])

    def _on_tool_in_spindle(self, tool_number) -> None:
        tool_number = int(tool_number or 0)
        if tool_number == self._current:
            return
        self._current = tool_number
        holder = self.find_holder(tool_number)
        if holder is not None:
            holder.last_loaded = time.time()
        if tool_number != 0 or self._restore_settled:
            self._remembered_tool = tool_number
        self._write_holders()
        self.currentToolChanged.emit(tool_number)

    def _restore_tool(self, *_args) -> None:
        """Put the remembered tool back in the spindle once homing is done.
        Only when the spindle reads as empty, so a real tool change is never
        second-guessed."""
        try:
            if not (self._status.all_axes_homed.value and self._status.enabled.value):
                return
        except Exception:
            log.exception("could not read the machine state")
            return
        settled, self._restore_settled = self._restore_settled, True
        if settled or self._current != 0:
            return
        remembered = self._remembered_tool
        holder = self.find_holder(remembered)
        if holder is None or not holder.has_tool:
            return
        # One restore at a time: a tool change is a real command to a real
        # machine, not an idempotent read.
        if self._restore_in_flight:
            return
        self._restore_in_flight = True
        log.info("putting back the tool that was in the spindle: T%d", remembered)
        # Delayed, because LinuxCNC is still settling the mode change that
        # finishing homing brings with it.
        QTimer.singleShot(RESTORE_TOOL_DELAY_MS, lambda: self._issue_restore(remembered))

    def _issue_restore(self, tool_number: int) -> None:
        try:
            self._commands.issue_mdi(f"M61 Q{tool_number} G43")
        finally:
            self._restore_in_flight = False

    def _read_tool_in_spindle(self) -> int:
        try:
            return int(self._status.tool_in_spindle.value or 0)
        except Exception:
            return 0

    # ── Saving ──────────────────────────────────────────────────────────────

    def _holder(self, tool_holder_id: int) -> ToolHolder:
        holder = self.find_holder(tool_holder_id)
        if holder is None:
            raise KeyError(f"no tool holder {tool_holder_id}")
        return holder

    def _save_holders(self, zeroed=frozenset()) -> None:
        self._write_holders()
        self._write_tool_table(zeroed)
        self.toolsChanged.emit()

    def _write_holders(self) -> None:
        self._extras.write_holders(self.holders, self._remembered_tool)

    def _write_tool_table(self, zeroed=frozenset()) -> None:
        """The only write to the tool table: a line per holder with a tool,
        the offsets as the file has them now - zero for the `zeroed` holders,
        given another tool."""
        offsets = self._tool_table_offsets()
        entries = []
        for holder in self.holders:
            tool = self.find_tool(holder.cutting_tool_id)
            if tool is None:
                continue
            if holder.tool_holder_id in zeroed:
                x, z = 0.0, 0.0
            else:
                x, z = offsets.get(holder.tool_holder_id, (0.0, 0.0))
            holder.x_offset, holder.z_offset = x, z
            entries.append(tbl_entry(holder, tool))
        self._tool_table.write(entries)

    def _tool_table_offsets(self) -> Dict[int, Tuple[float, float]]:
        return {e.t: (e.x, e.z) for e in self._tool_table.read()}

    def _read_offsets(self) -> bool:
        """Take the offsets from the tool table; whether any changed."""
        offsets = self._tool_table_offsets()
        changed = False
        for holder in self.holders:
            x, z = offsets.get(holder.tool_holder_id, (0.0, 0.0))
            if (x, z) != (holder.x_offset, holder.z_offset):
                holder.x_offset, holder.z_offset = x, z
                changed = True
        return changed

    def _on_tool_table_changed(self) -> None:
        if self._read_offsets():
            self.toolsChanged.emit()


# ── Holder to tool table line ───────────────────────────────────────────────


def tbl_entry(holder: ToolHolder, tool: CuttingTool) -> TblEntry:
    number = holder.tool_holder_id
    entry = TblEntry(t=number, p=number, x=holder.x_offset, z=holder.z_offset,
                     r=_comment(tool))
    if isinstance(tool, (TurningTool, ThreadingTool)):
        entry.d = 2 * insert_catalog.insert_for(tool.insert).nose_radius
        if isinstance(tool, TurningTool):
            entry.i = tool.front_angle
            entry.j = 180.0 - tool.back_angle
        entry.q = tool.orientation
    elif isinstance(tool, BladeTool):
        entry.d = 2 * max(tool.left_radius, tool.right_radius)
        entry.q = tool.orientation
    elif isinstance(tool, (DrillingTool, ReamingTool, TappingTool)):
        entry.d = tool.diameter
        entry.q = _AXIAL_ORIENTATION
    return entry


def designation(tool: CuttingTool) -> str:
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


def _comment(tool: CuttingTool) -> str:
    name = designation(tool)
    return f"{name} ({tool.comment})" if tool.comment else name


def _geometry_changed(before: CuttingTool, after: CuttingTool) -> bool:
    """Whether the tool differs in anything but its spindle direction and
    its comment."""
    return (type(before) is not type(after)
            or dataclasses.replace(after, spindle_direction=before.spindle_direction,
                                   comment=before.comment) != before)


_INSTANCE: Optional[ToolLibraryRepository] = None


def tool_library_repository() -> ToolLibraryRepository:
    """The shared ToolLibraryRepository, over the INI's tool table and the
    tool library files next to it."""
    global _INSTANCE
    if _INSTANCE is None:
        tbl_path = ini_repository().tool_table_file
        _INSTANCE = ToolLibraryRepository(
            ToolTblFileDataSource(tbl_path),
            LatheToolExtrasDataSource(Path(tbl_path).parent))
    return _INSTANCE
