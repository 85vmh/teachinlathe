"""Pure .tbl parser / serialiser — no QtPyVCP dependency.

LinuxCNC tool table format (one tool per line):
  T<n> P<pocket> X<x> Y<y> Z<z> A<a> B<b> C<c> U<u> V<v> W<w>
  D<tip_radius> I<front_angle> J<back_angle> Q<orientation> ;<comment>

Fields are uppercase letters followed by a numeric value (or `;` for comment).
Order is not mandated by LinuxCNC but we always write a canonical order.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .tool_entry import ToolEntry


# Matches  LETTER<number>  or  ;<rest-of-line>
_FIELD_RE = re.compile(r"([A-Za-z])([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
_COMMENT_RE = re.compile(r";(.*)")


def parse_tbl(path: str | Path) -> List[ToolEntry]:
    """Read a .tbl file and return a list of ToolEntry objects (base class)."""
    tools: List[ToolEntry] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            entry = _parse_line(line)
            if entry is not None:
                tools.append(entry)
    return tools


def write_tbl(path: str | Path, tools: List[ToolEntry]) -> None:
    """Write tools to a .tbl file, sorted by tool number."""
    sorted_tools = sorted(tools, key=lambda t: t.t)
    lines = [t.to_tbl_line() for t in sorted_tools]
    text = "\n".join(lines) + "\n"
    Path(path).write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_line(line: str) -> ToolEntry | None:
    fields: dict[str, str] = {}
    comment = ""

    # Extract comment first (everything after `;`)
    m = _COMMENT_RE.search(line)
    if m:
        comment = m.group(1).strip()
        line = line[: m.start()]

    for m in _FIELD_RE.finditer(line):
        fields[m.group(1).upper()] = m.group(2)

    if "T" not in fields:
        return None

    def flt(key: str, default: float = 0.0) -> float:
        try:
            return float(fields.get(key, default))
        except ValueError:
            return default

    def intv(key: str, default: int = 0) -> int:
        try:
            return int(float(fields.get(key, default)))
        except ValueError:
            return default

    return ToolEntry(
        t=intv("T"),
        p=intv("P"),
        x=flt("X"),
        y=flt("Y"),
        z=flt("Z"),
        a=flt("A"),
        b=flt("B"),
        c=flt("C"),
        u=flt("U"),
        v=flt("V"),
        w=flt("W"),
        d=flt("D"),
        i=flt("I"),
        j=flt("J"),
        q=intv("Q", 1),
        r=comment,
    )
