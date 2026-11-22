"""The diagnostics as a JSON file, on request: the series of the window asked
for, with their units, what was not available, the timed operations all
told and the slow ones, the states handed in (the backplot's transitions, its
trail limit). Nothing about the machine's programs or the operator: names of
series and operations, numbers and times.

``report`` builds it (cheap: copies of arrays); ``write`` turns it into the
file, and is what runs off the UI thread.
"""

from __future__ import annotations

import json
import os
import time
from typing import Dict, Iterable, Optional

import numpy as np

from teachinlathe.diagnostics.model.operations import MS_SUFFIX, OP_COUNT_SUFFIX
from teachinlathe.diagnostics.model.series import BUCKET_SECONDS, MAX_SUFFIX, TimeSeriesStore
from teachinlathe.diagnostics.model.units import Unit

FORMAT = "teachinlathe-diagnostics/1"
#: Where exports go: this folder of the machine's configuration, or - with
#: none given - FALLBACK_DIRECTORY.
DIRECTORY = "diagnostics"
FALLBACK_DIRECTORY = "~/teachinlathe-diagnostics"


def unit_of(store: TimeSeriesStore, name: str) -> str:
    info = store.info.get(name)
    if info is not None and info.unit:
        return info.unit
    base = name[:-len(MAX_SUFFIX)] if name.endswith(MAX_SUFFIX) else name
    info = store.info.get(base)
    if info is not None and info.unit:
        return info.unit
    if name.endswith(MS_SUFFIX):
        return Unit.MS
    if name.endswith(OP_COUNT_SUFFIX):
        return Unit.COUNT
    return Unit.NONE


def _values(values: np.ndarray) -> list:
    """A series as JSON numbers, 4 decimals - None where it had no data."""
    out = np.round(values, 4).astype(object)
    out[np.isnan(values)] = None
    return out.tolist()


def report(store: TimeSeriesStore, profiler, version: str, mode: str,
           unavailable: Iterable[str] = (), states: Optional[Dict[str, dict]] = None,
           seconds: Optional[float] = None, system: Optional[dict] = None) -> dict:
    """The last ``seconds`` of history (all of it: None) as a JSON-ready dict.

    Thread-safe - the store and the profiler are read under their locks - and
    meant to run off the UI thread: four hours of every series is a million
    numbers. ``states`` are read by the caller, on the thread that owns them."""
    rows = store.rows_since(-1)
    keep = slice(None)
    if seconds is not None and len(rows):
        keep = rows.monotonic >= rows.monotonic[-1] - seconds
    wall, monotonic = rows.wall[keep], rows.monotonic[keep]
    series = {}
    for name, values in rows.values.items():
        values = np.asarray(values[keep], dtype=float)
        if not len(values) or np.isnan(values).all():
            continue
        series[name] = {"unit": unit_of(store, name),
                        "description": store.info[name].description if name in store.info else "",
                        "values": _values(values)}
    totals, slow = profiler.snapshot()
    operations = {name: {"count": count, "total_ms": round(total, 3),
                         "average_ms": round(total / count, 3) if count else None,
                         "max_ms": round(most, 3), "failures": failures}
                  for name, (count, total, most, failures) in sorted(totals.items())}
    slow = [{"name": s.name, "wall": round(s.wall, 3), "duration_ms": round(s.duration_ms, 3),
             "ok": s.ok, "meta": s.meta} for s in slow]
    return {
        "format": FORMAT,
        "version": version,
        "mode": mode,
        "exported_wall": time.time(),
        "start_wall": float(wall[0]) if len(wall) else None,
        "end_wall": float(wall[-1]) if len(wall) else None,
        "bucket_seconds": BUCKET_SECONDS,
        "empty_bucket_policy": "null: no data in that bucket",
        "time": {"wall": np.round(wall, 3).tolist(), "monotonic": np.round(monotonic, 3).tolist()},
        "series": series,
        "unavailable": sorted(set(unavailable)),
        "operations": operations,
        "slow_operations": slow,
        "states": states or {},
        # what the machine ran at: the CPU's frequency is in the series
        # (sys.cpu_mhz_avg, sys.cpu_mhz_max); its limits and power settings here
        "system": system or {},
    }


def write(data: dict, directory: str) -> str:
    """``data`` written to a new file in ``directory``; its path."""
    os.makedirs(directory, exist_ok=True)
    name = time.strftime("diagnostics-%Y%m%d-%H%M%S.json", time.localtime(data.get("exported_wall") or time.time()))
    path = os.path.join(directory, name)
    temporary = path + ".part"
    with open(temporary, "w") as fh:
        json.dump(data, fh, separators=(",", ":"), default=str)
    os.replace(temporary, path)
    return path
