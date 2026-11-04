"""The LinuxCNC tool table file - ``[EMCIO] TOOL_TABLE`` - and nothing else.

This is the only code that opens the ``.tbl``. It reads it, writes it (and
tells LinuxCNC to read it again), and says when someone else has changed it:
LinuxCNC rewrites the file itself when an offset is set with G10, which is
how a touch-off lands in it.

One line per tool, fields in any order, the comment after a ``;``::

    T<n> P<pocket> X<x> Y<y> Z<z> A<a> B<b> C<c> U<u> V<v> W<w>
    D<diameter> I<front angle> J<back angle> Q<orientation> ;<comment>

What the lines mean is the tool library repository's business, not this
file's.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal

log = logging.getLogger(__name__)

#: How long the file has to stay still before a change is read: an editor -
#: or LinuxCNC - may write it in more than one go.
CHANGE_SETTLE_MS = 100

_FIELD_RE = re.compile(r"([A-Za-z])([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")


@dataclass
class TblEntry:
    """One line of the tool table, column for column."""

    t: int = 0
    p: int = 0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    a: float = 0.0
    b: float = 0.0
    c: float = 0.0
    u: float = 0.0
    v: float = 0.0
    w: float = 0.0
    d: float = 0.0
    i: float = 0.0
    j: float = 0.0
    q: int = 0
    r: str = ""

    def to_line(self) -> str:
        # The offsets as LinuxCNC writes them, to the micron and below: they
        # were measured, and a rewrite must not round them.
        return " ".join([
            f"T{self.t}", f"P{self.p}",
            f"X{self.x:.6f}", f"Y{self.y:.6f}", f"Z{self.z:.6f}",
            f"A{self.a:.4f}", f"B{self.b:.4f}", f"C{self.c:.4f}",
            f"U{self.u:.4f}", f"V{self.v:.4f}", f"W{self.w:.4f}",
            f"D{self.d:.4f}", f"I{self.i:.4f}", f"J{self.j:.4f}",
            f"Q{self.q}", f";{self.r}",
        ])


def parse_line(line: str) -> Optional[TblEntry]:
    """A line of the table; None for a blank line, a comment, or one with no T."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    line, _, comment = line.partition(";")
    fields = {m.group(1).upper(): m.group(2) for m in _FIELD_RE.finditer(line)}
    if "T" not in fields:
        return None

    def number(key: str) -> float:
        try:
            return float(fields.get(key, 0.0))
        except ValueError:
            return 0.0

    return TblEntry(
        t=int(number("T")), p=int(number("P")),
        x=number("X"), y=number("Y"), z=number("Z"),
        a=number("A"), b=number("B"), c=number("C"),
        u=number("U"), v=number("V"), w=number("W"),
        d=number("D"), i=number("I"), j=number("J"),
        q=int(number("Q")), r=comment.strip(),
    )


class ToolTblFileDataSource(QObject):
    """The tool table file."""

    #: The file was changed - by LinuxCNC, or by hand. Not emitted for
    #: write(): whoever wrote knows what is in it.
    changed = pyqtSignal()

    def __init__(self, path: str | Path, command=None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._path = Path(path)
        self._command = command if command is not None else _linuxcnc_command()
        self._written: Optional[str] = None

        self._settle = QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(CHANGE_SETTLE_MS)
        self._settle.timeout.connect(self._on_settled)

        self._watcher = QFileSystemWatcher(self)
        self._watcher.fileChanged.connect(self._on_file_changed)
        self._watch()

    @property
    def path(self) -> Path:
        return self._path

    def read(self) -> List[TblEntry]:
        """Every tool in the file; none when there is no file or it cannot
        be read."""
        try:
            text = self._path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            log.error("cannot read the tool table %s: %s", self._path, exc)
            return []
        return [entry for entry in map(parse_line, text.splitlines()) if entry is not None]

    def write(self, entries: List[TblEntry]) -> bool:
        """Replace the file with these tools, by number, and have LinuxCNC
        read it again."""
        text = "".join(e.to_line() + "\n" for e in sorted(entries, key=lambda e: e.t))
        try:
            self._path.write_text(text, encoding="utf-8")
        except OSError as exc:
            log.error("cannot write the tool table %s: %s", self._path, exc)
            return False
        self._written = text
        self._watch()
        if self._command is not None:
            try:
                self._command.load_tool_table()
            except Exception:
                log.exception("LinuxCNC did not reload the tool table")
        return True

    def _watch(self) -> None:
        # A file replaced rather than rewritten drops out of the watch.
        if self._path.exists() and str(self._path) not in self._watcher.files():
            self._watcher.addPath(str(self._path))

    def _on_file_changed(self, _path: str) -> None:
        self._watch()
        self._settle.start()

    def _on_settled(self) -> None:
        try:
            text = self._path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        if text == self._written:
            return
        self._written = None
        log.debug("the tool table %s changed on disk", self._path)
        self.changed.emit()


def _linuxcnc_command():
    try:
        import linuxcnc
        return linuxcnc.command()
    except Exception:
        return None
