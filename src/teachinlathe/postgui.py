"""The INI's ``[HAL] POSTGUI_HALFILE`` and ``POSTGUI_HALCMD`` entries.

LinuxCNC loads every ``HALFILE`` before it starts the display, but leaves
these to the display itself: they connect to pins the GUI creates, so they can
only run once its HAL component is ready. Axis and QtVCP each run them; a
display that does not leaves them silently unloaded.

Same rules as theirs: ``.tcl`` files go through ``haltcl``, everything else
through ``halcmd -f``, both with ``-i`` so ``[SECTION]VAR`` substitutions
resolve; the commands run after the files; and the first failure stops the
application, because a half-wired machine is worse than one that does not
start.
"""

from __future__ import annotations

import logging
import shlex
import subprocess
from typing import Optional

from teachinlathe.repositories.ini_repository import ini_repository

log = logging.getLogger(__name__)


def run_postgui() -> Optional[str]:
    """Load the post-GUI HAL files and commands.

    Returns None when all of them succeeded, or a message naming the one that
    failed.
    """
    ini = ini_repository()

    for path in ini.postgui_halfiles:
        if path.lower().endswith(".tcl"):
            command = ["haltcl", "-i", ini.ini_path, path]
        else:
            command = ["halcmd", "-i", ini.ini_path, "-f", path]
        log.info("POSTGUI_HALFILE: %s", path)
        error = _run(command)
        if error:
            return "POSTGUI_HALFILE {} failed: {}".format(path, error)

    for halcmd in ini.postgui_halcmds:
        log.info("POSTGUI_HALCMD: %s", halcmd)
        error = _run(["halcmd"] + shlex.split(halcmd))
        if error:
            return "POSTGUI_HALCMD '{}' failed: {}".format(halcmd, error)

    return None


def _run(command: list[str]) -> Optional[str]:
    """Run *command* from the config directory; None on success."""
    try:
        result = subprocess.run(command, cwd=ini_repository().config_dir,
                                capture_output=True, text=True)
    except OSError as exc:
        return str(exc)
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        return output or "exit status {}".format(result.returncode)
    if output:
        log.info("%s", output)
    return None
