"""The units of the diagnostics' series (SeriesInfo.unit)."""

from __future__ import annotations

from enum import StrEnum


class Unit(StrEnum):
    NONE = ""
    FLAG = "0/1"
    COUNT = "count"
    POINTS = "points"
    BYTES = "bytes"
    KIB_PER_S = "KiB/s"
    MIB = "MiB"
    PER_S = "1/s"
    MS = "ms"
    PERCENT = "%"
    LOAD = "load"
    MHZ = "MHz"
    CELSIUS = "°C"
