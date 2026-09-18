"""LinuxCNC's own diagnostic tools, launched as separate programs.

These are the utilities that ship
with LinuxCNC - HAL Show, HAL Meter, HAL Scope, Classic Ladder, the status
monitor and the PID calibration dialog - each its own program, started
detached so it outlives the click that started it.

Starting them with ``os.popen("... &")`` leaves a shell and a zombie behind
for every launch. ``QProcess.startDetached`` takes an argument
list, so nothing is passed through a shell and nothing needs reaping.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Tuple

from PyQt5.QtCore import QObject, QProcess

log = logging.getLogger(__name__)

#: Where LinuxCNC keeps its Tcl utilities.
TCL_DIR = os.getenv('LINUXCNC_TCL_DIR', '/usr/lib/tcltk/linuxcnc')

#: The HAL component Classic Ladder needs loaded before it can be shown.
CLASSICLADDER_COMPONENT = 'classicladder_rt'


class ExternalTool:
    """One launchable utility: what to run, and what to call it.

    ``needs_ini`` tools are handed the machine's INI file. That path is read
    when the tool is launched rather than when it is declared, because the
    repository can be built before the INI is known and an empty ``-ini``
    makes the tool fail in a way that points nowhere.
    """

    def __init__(self, key: str, label: str, argv: List[str],
                 requires_component: Optional[str] = None,
                 needs_ini: bool = False) -> None:
        self.key = key
        self.label = label
        self._argv = argv
        self.requires_component = requires_component
        self.needs_ini = needs_ini

    @property
    def argv(self) -> List[str]:
        if not self.needs_ini:
            return list(self._argv)
        return list(self._argv) + ['-ini', os.getenv('INI_FILE_NAME', '')]


def _tools() -> Dict[str, ExternalTool]:
    return {t.key: t for t in (
        ExternalTool('halshow', 'Hal Show',
                     ['tclsh', os.path.join(TCL_DIR, 'bin', 'halshow.tcl')]),
        ExternalTool('halmeter', 'Hal Meter', ['halmeter']),
        ExternalTool('halscope', 'Hal Scope', ['halscope']),
        ExternalTool('classicladder', 'Classic Ladder', ['classicladder'],
                     requires_component=CLASSICLADDER_COMPONENT),
        ExternalTool('status', 'LCNC Status', ['linuxcnctop']),
        ExternalTool('calibration', 'Calibration',
                     ['tclsh', os.path.join(TCL_DIR, 'bin', 'emccalib.tcl')],
                     needs_ini=True),
    )}


class ToolsRepository(QObject):
    """Launches LinuxCNC's diagnostic utilities."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._tools = _tools()

    @property
    def tools(self) -> List[ExternalTool]:
        """Every launchable tool, in the order the screens show them."""
        return list(self._tools.values())

    def can_launch(self, key: str) -> Tuple[bool, str]:
        """Whether *key* can be started, and why not when it cannot."""
        tool = self._tools.get(key)
        if tool is None:
            return False, "No such tool: {}".format(key)
        if tool.requires_component and not self._component_exists(tool.requires_component):
            return False, ("{} is not loaded, so {} has nothing to show"
                           .format(tool.requires_component, tool.label))
        if tool.needs_ini and not os.getenv('INI_FILE_NAME'):
            return False, "{} needs the machine INI file".format(tool.label)
        return True, ""

    def launch(self, key: str) -> bool:
        """Start *key* as a detached process."""
        ok, reason = self.can_launch(key)
        if not ok:
            log.warning("not launching %s: %s", key, reason)
            return False

        tool = self._tools[key]
        log.info("launching %s: %s", tool.label, " ".join(tool.argv))
        # The three-argument overload is the one that reports the pid; the
        # two-argument one returns a bare bool. The working directory is the
        # config directory so a tool that writes beside the machine config
        # lands in the right place.
        started, pid = QProcess.startDetached(
            tool.argv[0], tool.argv[1:], self._working_directory())
        if not started:
            log.error("could not launch %s (%s)", tool.label, tool.argv[0])
            return False
        log.info("%s started as pid %s", tool.label, pid)
        return True

    @staticmethod
    def _working_directory() -> str:
        return os.getenv('CONFIG_DIR') or os.path.expanduser('~')

    @staticmethod
    def _component_exists(name: str) -> bool:
        try:
            import hal
            return bool(hal.component_exists(name))
        except Exception as error:
            # HAL refuses the question until this process owns a component.
            # Not worth a traceback on every enable check; the answer is
            # simply "cannot tell", which reads the same as "not loaded".
            log.debug("could not ask HAL about %s: %s", name, error)
            return False


_INSTANCE: Optional[ToolsRepository] = None


def tools_repository() -> ToolsRepository:
    """The shared ToolsRepository."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = ToolsRepository()
    return _INSTANCE
