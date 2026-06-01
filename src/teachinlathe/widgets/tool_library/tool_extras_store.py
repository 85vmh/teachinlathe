"""Reads / writes tools_extras.json — a sidecar file next to the .tbl.

Schema (keyed by string tool number):
{
  "1": {
    "tool_type": "drill",
    "last_loaded": 1714901234.5,
    "diameter": 6.0,
    "material": "HSS",
    "length": 80.0
  },
  ...
}

Only extra fields are stored here; base .tbl fields are NOT duplicated.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class ToolExtrasStore:
    def __init__(self, tbl_path: str | Path) -> None:
        self._path = Path(tbl_path).with_suffix("").parent / "tools_extras.json"
        self._data: Dict[str, dict] = {}
        self._load()

    # ── Public API ──────────────────────────────────────────────────

    def get(self, tool_no: int) -> dict:
        """Return extras dict for a tool (empty dict if not present)."""
        return dict(self._data.get(str(tool_no), {}))

    def save(self, tool_no: int, extras: dict) -> None:
        """Persist extras for a single tool."""
        if extras:
            self._data[str(tool_no)] = extras
        else:
            self._data.pop(str(tool_no), None)
        self._flush()

    def delete(self, tool_no: int) -> None:
        """Remove extras entry for a deleted tool."""
        if self._data.pop(str(tool_no), None) is not None:
            self._flush()

    def update_last_loaded(self, tool_no: int, timestamp: float) -> None:
        entry = self._data.setdefault(str(tool_no), {})
        entry["last_loaded"] = timestamp
        self._flush()

    # ── Internal ────────────────────────────────────────────────────

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        else:
            self._data = {}

    def _flush(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
