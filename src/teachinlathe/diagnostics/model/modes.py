"""How much the diagnostics gather (ProfilingMode):

    off       nothing runs: no timer, no worker, no series; a timed operation
              is an attribute test
    basic     the event loop's latency, the process, the system, the CPU
              temperatures and the backplot's state
    detailed  all of that and every timed operation (spans)

Kept as a setting (``diagnostics.profiling-mode``); ``TEACHINLATHE_PROFILING``
in the environment sets it for one start, without changing the setting.
"""

from __future__ import annotations

import os
from enum import Enum

SETTING = "diagnostics.profiling-mode"
ENVIRONMENT = "TEACHINLATHE_PROFILING"


class ProfilingMode(Enum):
    OFF = "off"
    BASIC = "basic"
    DETAILED = "detailed"

    @classmethod
    def parse(cls, value, default: "ProfilingMode" = None) -> "ProfilingMode":
        try:
            return cls(str(value).strip().lower())
        except ValueError:
            return cls.OFF if default is None else default


def mode_at_start(stored, environ=os.environ) -> ProfilingMode:
    """The mode to start in: the environment's, if it names one; else the
    setting's."""
    named = environ.get(ENVIRONMENT)
    stored_mode = ProfilingMode.parse(stored)
    return ProfilingMode.parse(named, stored_mode) if named else stored_mode
