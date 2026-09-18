"""Read-only access to the machine's INI file.

Only the entries this application actually reads are exposed; the generic ``find``/``file_path`` helpers are
there so a new entry does not need a new dependency.

The INI is static configuration, read once at startup, so this class is
deliberately plain Python: no QObject, no signals, nothing to poll. A missing
or unreadable INI is not an error here - every accessor falls back the way
LinuxCNC's own front-ends do, so callers need no try/except.
"""

from __future__ import annotations

import logging
import os
from typing import NamedTuple, Optional

import linuxcnc

log = logging.getLogger(__name__)

NC_FILES_FALLBACK = "~/linuxcnc/nc_files"

#: Axis letters in the order LinuxCNC reports positions in.
AXIS_LETTERS = "xyzabcuvw"


class AxisLimits(NamedTuple):
    """Soft limits of one axis, in machine units.

    A NamedTuple so that both ``limits.min`` and ``limits[0]`` read correctly.
    """

    min: float
    max: float


def _normalize(path: Optional[str], base: Optional[str]) -> str:
    """Expand and absolutise *path*, resolving a relative one against *base*.

    ``~`` and ``$VARS`` are expanded, a relative path is joined onto *base*,
    and the result is passed through ``realpath``.
    """
    if not path or not isinstance(path, str):
        return ""
    path = os.path.expandvars(path)
    if path.startswith("~"):
        path = os.path.expanduser(path)
    elif not os.path.isabs(path):
        path = os.path.join(base or "", path)
    return os.path.realpath(path)


class IniRepository:
    """The machine INI file, as the values this application needs."""

    def __init__(self, ini_path: Optional[str] = None) -> None:
        self._ini_path = ini_path or os.environ.get("INI_FILE_NAME") or os.devnull
        self._config_dir = os.environ.get("CONFIG_DIR") or os.path.dirname(self._ini_path)
        try:
            self._ini = linuxcnc.ini(self._ini_path)
        except Exception:
            # A bad path is what running outside a LinuxCNC session looks
            # like. Every accessor then returns its fallback.
            log.warning("could not read INI file '%s'; using defaults", self._ini_path)
            self._ini = None

    @property
    def ini_path(self) -> str:
        return self._ini_path

    @property
    def config_dir(self) -> str:
        return self._config_dir

    # -- generic access ---------------------------------------------------

    def find(self, section: str, option: str) -> Optional[str]:
        """The raw string value of ``[section] option``, or None."""
        if self._ini is None:
            return None
        return self._ini.find(section, option)

    def file_path(self, section: str, option: str,
                  base: Optional[str] = None, default: Optional[str] = None) -> str:
        """``[section] option`` as an absolute path, or "" when unset."""
        return _normalize(self.find(section, option) or default,
                          self._config_dir if base is None else base)

    # -- the entries this application reads -------------------------------

    @property
    def program_prefix(self) -> str:
        """``[DISPLAY] PROGRAM_PREFIX``, the base folder for G-code.

        Falls back to ``~/linuxcnc/nc_files`` and then to the home directory,
        matching what the LinuxCNC front-ends do, so the returned path always
        exists.
        """
        path = _normalize(self.find("DISPLAY", "PROGRAM_PREFIX"), self._config_dir)
        if path and os.path.exists(path):
            return path
        if path:
            log.warning("[DISPLAY] PROGRAM_PREFIX '%s' does not exist, "
                        "trying '%s'", path, NC_FILES_FALLBACK)

        fallback = os.path.expanduser(NC_FILES_FALLBACK)
        if os.path.exists(fallback):
            return fallback

        log.warning("'%s' does not exist either, using the home directory",
                    NC_FILES_FALLBACK)
        return os.path.expanduser("~/")

    @property
    def tool_table_file(self) -> str:
        """``[EMCIO] TOOL_TABLE`` as an absolute path to the .tbl file."""
        return self.file_path("EMCIO", "TOOL_TABLE", default="tool.tbl")

    @property
    def subroutine_search_dirs(self) -> list[str]:
        """Where an ``o<name> call`` is looked up, in search order.

        The program prefix first, then each entry of
        ``[RS274NGC] SUBROUTINE_PATH``.
        """
        dirs = [self.program_prefix]
        paths = self.find("RS274NGC", "SUBROUTINE_PATH")
        if not paths:
            log.info("no [RS274NGC] SUBROUTINE_PATH in the INI file")
            return dirs
        dirs.extend(_normalize(p, self._config_dir)
                    for p in paths.strip(":").split(":") if p)
        return dirs

    @property
    def coordinates(self) -> str:
        """``[TRAJ] COORDINATES`` as a lowercase letter string, e.g. ``"xz"``."""
        raw = self.find("TRAJ", "COORDINATES") or ""
        raw = raw.replace(" ", "").lower()
        if not raw:
            log.warning("no [TRAJ] COORDINATES in the INI file, assuming 'xyz'")
            return "xyz"
        return raw

    @property
    def axis_letters(self) -> list[str]:
        """The machine's axis letters, in order, without duplicates.

        A gantry names one axis twice in COORDINATES (``xyyz``); it is still
        one axis, so it appears once here.
        """
        seen = []
        for letter in self.coordinates:
            if letter in AXIS_LETTERS and letter not in seen:
                seen.append(letter)
        return seen

    @property
    def axis_numbers(self) -> list[int]:
        """The machine's axis indices into a nine-axis position tuple."""
        return [AXIS_LETTERS.index(letter) for letter in self.axis_letters]

    @property
    def is_metric(self) -> bool:
        """Whether the machine's native linear unit is the millimetre."""
        units = self.find("TRAJ", "LINEAR_UNITS") or self.find("AXIS_X", "UNITS")
        return (units or "").strip().lower() in ("mm", "metric")

    @property
    def no_force_homing(self) -> bool:
        """``[TRAJ] NO_FORCE_HOMING``: whether MDI/AUTO are allowed unhomed."""
        return (self.find("TRAJ", "NO_FORCE_HOMING") or "").strip() == "1"

    @property
    def position_feedback_is_actual(self) -> bool:
        """Whether the DRO should show actual rather than commanded position.

        ``[DISPLAY] POSITION_FEEDBACK``: absent or ``0`` or ``ACTUAL`` means
        actual, anything else (``COMMANDED``) means commanded.
        """
        feedback = (self.find("DISPLAY", "POSITION_FEEDBACK") or "").strip()
        return feedback == "" or feedback == "0" or feedback.lower() == "actual"

    @property
    def default_jog_velocity(self) -> float:
        """``[DISPLAY] DEFAULT_LINEAR_VELOCITY``, in units per *minute*.

        The INI states it per second; every front-end shows it per minute.
        """
        return self._float("DISPLAY", "DEFAULT_LINEAR_VELOCITY", 3.0) * 60.0

    @property
    def max_jog_velocity(self) -> float:
        """``[DISPLAY] MAX_LINEAR_VELOCITY``, in units per minute."""
        return self._float("DISPLAY", "MAX_LINEAR_VELOCITY", 10.0) * 60.0

    def _float(self, section: str, option: str, default: float) -> float:
        raw = self.find(section, option)
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    def axis_limits(self, axis: str) -> Optional[AxisLimits]:
        """Soft limits of *axis* (a letter), or None when the INI omits them."""
        section = "AXIS_{}".format(axis.upper())
        low = self.find(section, "MIN_LIMIT")
        high = self.find(section, "MAX_LIMIT")
        if low is None or high is None:
            log.error("[%s] is missing MIN_LIMIT or MAX_LIMIT", section)
            return None
        try:
            return AxisLimits(float(low), float(high))
        except ValueError:
            log.error("[%s] has a non-numeric MIN_LIMIT/MAX_LIMIT: %r / %r",
                      section, low, high)
            return None


_INSTANCE: Optional[IniRepository] = None


def ini_repository() -> IniRepository:
    """The shared IniRepository, built from ``$INI_FILE_NAME`` on first use."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = IniRepository()
    return _INSTANCE
