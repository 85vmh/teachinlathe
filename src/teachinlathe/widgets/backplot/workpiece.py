"""Where the stock dimensions come from.

Nothing in a G-code file says how long the bar is or what diameter it started
at, so the stock outline cannot be recovered from the preview. What does know
is the conversational program that generated the file, which keeps its header
- material, external and internal diameter, stock length - in a JSON file
beside the output.

Ported from ``ProgramsQml``'s toolpath model on ``native_2d_rendering``, which
is where the same lookup was written for the QML renderer. It is here rather
than in an actor because it is file handling, not drawing, and an actor that
opened files would be the odd one out.
"""

import json
import logging
import os
import re

LOG = logging.getLogger(__name__)

#: How far into a generated file to look for the header comment naming the
#: program it came from.
HEADER_LINES = 20

#: The comment the generator writes, e.g. ``(Program: shaft.json)``.
PROGRAM_COMMENT = re.compile(r"\(\s*Program:\s*([^)]+?)\s*\)")

#: Where the conversational programs are kept, relative to the G-code's
#: parent.
JSON_SUBDIRECTORY = "Conversational Json"


def for_program(filename):
    """The workpiece header for a loaded G-code file, as a dict.

    Empty when there is nothing to find - a hand-written file, a program
    saved before the header existed, or one whose JSON has been moved. That
    is not an error: it means the plot draws without stock, which is what it
    did before this existed.
    """
    data = _program_data(filename)
    if not data:
        return {}
    header = (data.get("header") or {})
    workpiece = header.get("workpiece")
    if not isinstance(workpiece, dict):
        return {}

    found = dict(workpiece)
    # Older programs recorded only what stuck out of the chuck; it is the
    # length the preview wants when nothing else was stated.
    if not found.get("stock_length") and found.get("stickout_length"):
        found["stock_length"] = found["stickout_length"]
    return found


def _program_data(filename):
    path = _json_path(filename)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        LOG.exception("backplot: could not read program data from %s", path)
        return None
    return data if isinstance(data, dict) else None


def _json_path(filename):
    """The conversational JSON for ``filename``, or ``''``.

    Four places, in the order they are worth trying: what the file's own
    header names, next to it and then in the programs directory; and the
    file's own name, in the programs directory and then beside it.
    """
    if not filename:
        return ""
    directory = os.path.dirname(filename)
    parent = os.path.dirname(directory)
    base = os.path.splitext(os.path.basename(filename))[0] + ".json"

    candidates = []
    named = _header_program(filename)
    if named:
        candidates.append(os.path.join(directory, named))
        candidates.append(os.path.join(parent, JSON_SUBDIRECTORY, named))
    candidates.append(os.path.join(parent, JSON_SUBDIRECTORY, base))
    candidates.append(os.path.splitext(filename)[0] + ".json")

    for candidate in candidates:
        candidate = os.path.abspath(candidate)
        if os.path.isfile(candidate):
            return candidate
    return ""


def _header_program(filename):
    """The program named in the file's header comment, or ``''``."""
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as handle:
            for _line_number in range(HEADER_LINES):
                line = handle.readline()
                if not line:
                    break
                match = PROGRAM_COMMENT.search(line)
                if match:
                    return os.path.basename(match.group(1).strip())
    except OSError:
        LOG.exception("backplot: could not inspect program header %s", filename)
    return ""
