"""tool_holders.json and cutting_tools.json, loaded into the domain model.

Both files live next to the machine's tool table, as tools_extras.json does:
they describe this machine's tooling, not the program. A file that does not
exist yet is created from the seed; one that exists but cannot be read is
left alone - logged and treated as empty, never overwritten - so a bad edit
by hand costs nothing more than a restart once it is fixed.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
from pathlib import Path
from typing import Callable, List, Optional

from teachinlathe.tooling.data_types import (
    CuttingTool, CuttingToolType, ToolHolder, ZOffsetPlace, from_json, to_json,
)
from teachinlathe.tooling.seed import seed_cutting_tools, seed_tool_holders

log = logging.getLogger(__name__)

TOOL_HOLDERS_FILE = "tool_holders.json"
CUTTING_TOOLS_FILE = "cutting_tools.json"
_HOLDERS_KEY = "tool_holders"


class ToolLibraryStore:
    def __init__(self, directory: str | Path) -> None:
        directory = Path(directory)
        self._holders_path = directory / TOOL_HOLDERS_FILE
        self._tools_path = directory / CUTTING_TOOLS_FILE
        self.holders: List[ToolHolder] = []
        self.cutting_tools: List[CuttingTool] = []
        self._listeners: List[Callable[[], None]] = []
        self.load()

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Call `listener` after every change that is saved - except a
        holder going into the spindle, which changes nothing it describes."""
        self._listeners.append(listener)

    def _changed(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                log.exception("tool library listener failed")

    # ── Queries ─────────────────────────────────────────────────────────────

    def tools_of(self, tool_type: CuttingToolType) -> List[CuttingTool]:
        return [t for t in self.cutting_tools if t.tool_type is tool_type]

    def find_tool(self, cutting_tool_id: Optional[int]) -> Optional[CuttingTool]:
        return next((t for t in self.cutting_tools
                     if t.cutting_tool_id == cutting_tool_id), None)

    def find_holder(self, tool_holder_id: int) -> Optional[ToolHolder]:
        return next((h for h in self.holders
                     if h.tool_holder_id == tool_holder_id), None)

    def next_cutting_tool_id(self) -> int:
        return max((t.cutting_tool_id for t in self.cutting_tools), default=0) + 1

    # ── Changes ─────────────────────────────────────────────────────────────

    def holder_of(self, cutting_tool_id: int) -> Optional[ToolHolder]:
        return next((h for h in self.holders
                     if h.cutting_tool_id == cutting_tool_id), None)

    def mount(self, tool_holder_id: int, cutting_tool_id: Optional[int]) -> None:
        """Clamp a cutting tool in a holder; the holder's offsets are cleared.

        A cutting tool is in one holder at a time, so one that was in another
        holder moves: that holder is left empty, and its offsets go with it.
        """
        holder = self.find_holder(tool_holder_id)
        if holder is None:
            raise KeyError(f"no tool holder {tool_holder_id}")
        if cutting_tool_id is not None:
            if self.find_tool(cutting_tool_id) is None:
                raise KeyError(f"no cutting tool {cutting_tool_id}")
            previous = self.holder_of(cutting_tool_id)
            if previous is not None and previous is not holder:
                previous.mount(None)
        holder.mount(cutting_tool_id)
        self.save_holders()

    def add_holder(self) -> ToolHolder:
        """A new, empty holder, numbered after the last: T<n+1>."""
        tool_holder_id = max((h.tool_holder_id for h in self.holders), default=0) + 1
        holder = ToolHolder(tool_holder_id)
        self.holders.append(holder)
        self.save_holders()
        return holder

    def set_z_offset_place(self, tool_holder_id: int, place: Optional[ZOffsetPlace]) -> None:
        """Which point of the blade in the holder its Z offset is taken from."""
        self._holder(tool_holder_id).z_offset_place = place
        self.save_holders()

    def set_x_offset(self, tool_holder_id: int, value: Optional[float]) -> None:
        """The X offset LinuxCNC worked out when the holder was touched off."""
        self._holder(tool_holder_id).x_offset = value
        self.save_holders()

    def set_z_offset(self, tool_holder_id: int, value: Optional[float]) -> None:
        self._holder(tool_holder_id).z_offset = value
        self.save_holders()

    def record_loaded(self, tool_holder_id: int, timestamp: float) -> None:
        """The holder went into the spindle. Saved without telling the
        listeners: nothing the tool table is written from has changed."""
        self._holder(tool_holder_id).last_loaded = timestamp
        self._write_holders()

    def _holder(self, tool_holder_id: int) -> ToolHolder:
        holder = self.find_holder(tool_holder_id)
        if holder is None:
            raise KeyError(f"no tool holder {tool_holder_id}")
        return holder

    def save_cutting_tool(self, tool: CuttingTool) -> None:
        """Add the tool, or replace the one with its id.

        Offsets were taken with the tool as it was. Any change to it other
        than the spindle direction or the comment - insert, nose radius, orientation, angles
        - moves the tip, so the holder it is clamped in loses its offsets and
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
        self.save_cutting_tools()

    def _invalidate_offsets(self, cutting_tool_id: int) -> None:
        holder = self.holder_of(cutting_tool_id)
        if holder is None or (holder.x_offset is None and holder.z_offset is None):
            return
        log.info("cutting tool %s changed: holder %s needs touching off again",
                 cutting_tool_id, holder.tool_holder_id)
        # Re-mounting the same tool clears the offsets and keeps the tool.
        holder.mount(cutting_tool_id)
        self.save_holders()

    # ── Persistence ─────────────────────────────────────────────────────────

    def load(self) -> None:
        tools = _read(self._tools_path,
                      lambda raw: [CuttingTool.from_json(item) for item in raw])
        if tools is None:
            self.cutting_tools = seed_cutting_tools()
            self.save_cutting_tools()
        else:
            self.cutting_tools = tools

        holders = _read(self._holders_path,
                        lambda raw: [from_json(ToolHolder, item) for item in raw[_HOLDERS_KEY]])
        if holders is None:
            self.holders = seed_tool_holders()
            self.save_holders()
        else:
            self.holders = holders

    def save_holders(self) -> None:
        self._write_holders()
        self._changed()

    def save_cutting_tools(self) -> None:
        _write_json(self._tools_path, to_json(self.cutting_tools))
        self._changed()

    def _write_holders(self) -> None:
        _write_json(self._holders_path, {_HOLDERS_KEY: to_json(self.holders)})


def _geometry_changed(before: CuttingTool, after: CuttingTool) -> bool:
    """Whether the tool differs in anything but its spindle direction and
    its comment."""
    return (type(before) is not type(after)
            or dataclasses.replace(after, spindle_direction=before.spindle_direction,
                                   comment=before.comment) != before)


def _read(path: Path, parse: Callable[[object], list]) -> Optional[list]:
    """The parsed file; None when there is no file yet, [] when there is
    one that cannot be read."""
    if not path.exists():
        log.info("%s not found, creating it with the default tooling", path)
        return None
    try:
        return parse(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log.error("cannot read %s, the tool library starts empty: %s", path, exc)
        return []


def _write_json(path: Path, data: object) -> None:
    """Write through a temporary file, so a crash mid-write leaves the
    previous file rather than half of a new one."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
