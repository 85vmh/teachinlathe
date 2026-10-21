"""The tool library's own files: tool_holders.json and cutting_tools.json.

They hold what the LinuxCNC tool table has no column for - which cutting
tool is in which holder, what that tool is, whether the holder has been
touched off with it, when it was last used - and which tool was in the
spindle, which LinuxCNC forgets across a restart. They live next to the tool
table: they describe this machine's tooling, not a program.

The offsets themselves are not here: the tool table has them.

A file that does not exist yet is created from the seed; one that exists
but cannot be read is left alone - logged and treated as empty, never
overwritten - so a bad edit by hand costs nothing more than a restart once
it is fixed.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from teachinlathe.tooling.model.data_types import CuttingTool, ToolHolder, from_json, to_json
from teachinlathe.tooling.model.seed import seed_cutting_tools, seed_tool_holders

log = logging.getLogger(__name__)

TOOL_HOLDERS_FILE = "tool_holders.json"
CUTTING_TOOLS_FILE = "cutting_tools.json"
_HOLDERS_KEY = "tool_holders"
_IN_SPINDLE_KEY = "tool_in_spindle"

#: Read from the tool table, never saved with the holder.
_TBL_FIELDS = ("x_offset", "z_offset")


class LatheToolExtrasDataSource:
    def __init__(self, directory: str | Path) -> None:
        directory = Path(directory)
        self._holders_path = directory / TOOL_HOLDERS_FILE
        self._tools_path = directory / CUTTING_TOOLS_FILE

    # ── Cutting tools ───────────────────────────────────────────────────────

    def read_cutting_tools(self) -> List[CuttingTool]:
        raw = _read(self._tools_path)
        if raw is None:
            tools = seed_cutting_tools()
            self.write_cutting_tools(tools)
            return tools
        try:
            return [CuttingTool.from_json(item) for item in raw]
        except (ValueError, KeyError, TypeError) as exc:
            log.error("cannot read %s, the tool library starts empty: %s", self._tools_path, exc)
            return []

    def write_cutting_tools(self, tools: List[CuttingTool]) -> None:
        _write_json(self._tools_path, to_json(tools))

    # ── Holders, and the tool in the spindle ────────────────────────────────

    def read_holders(self) -> tuple[List[ToolHolder], int]:
        """The holders, and the tool that was in the spindle (0 for none)."""
        raw = _read(self._holders_path)
        if raw is None:
            holders = seed_tool_holders()
            self.write_holders(holders, 0)
            return holders, 0
        try:
            holders = [_holder_from_json(item) for item in raw[_HOLDERS_KEY]]
            return holders, int(raw.get(_IN_SPINDLE_KEY, 0) or 0)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            log.error("cannot read %s, the tool library starts empty: %s", self._holders_path, exc)
            return [], 0

    def write_holders(self, holders: List[ToolHolder], tool_in_spindle: int) -> None:
        _write_json(self._holders_path, {
            _HOLDERS_KEY: [_holder_to_json(h) for h in holders],
            _IN_SPINDLE_KEY: int(tool_in_spindle),
        })


def _holder_to_json(holder: ToolHolder) -> dict:
    body = to_json(holder)
    for key in _TBL_FIELDS:
        body.pop(key, None)
    return body


def _holder_from_json(raw: dict) -> ToolHolder:
    raw = dict(raw)
    # A file from before the offsets moved to the tool table: an offset that
    # was set there is one that was touched off.
    for axis in ("x", "z"):
        raw.setdefault(f"{axis}_touched", raw.get(f"{axis}_offset") is not None)
    for key in _TBL_FIELDS:
        raw.pop(key, None)
    return from_json(ToolHolder, raw)


def _read(path: Path) -> Optional[object]:
    """The parsed file; None when there is no file yet, [] when there is
    one that cannot be read."""
    if not path.exists():
        log.info("%s not found, creating it with the default tooling", path)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.error("cannot read %s, the tool library starts empty: %s", path, exc)
        return []


def _write_json(path: Path, data: object) -> None:
    """Write through a temporary file, so a crash mid-write leaves the
    previous file rather than half of a new one."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
