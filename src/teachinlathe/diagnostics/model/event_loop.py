"""The event loop's latency: how late a timer that should fire every
``interval`` ms fires - the time the loop was busy with something else - and
the longest it went without firing at all; summed up per 5 s bucket.

Sampled many times a second (EventLoopMonitor, in diagnostics.logic), it is
handed over once a bucket (``take``): nothing is told per sample.
"""

from __future__ import annotations

import math
import threading
from typing import Dict

from teachinlathe.diagnostics.model import series
from teachinlathe.diagnostics.model.series import Stats
from teachinlathe.diagnostics.model.units import Unit

#: Delays counted in a bucket: over so many ms.
LAG_THRESHOLDS_MS = (16, 50, 100, 500, 1000)

LOOP_MEAN_MS = "loop.mean_ms"
LOOP_P50_MS = "loop.p50_ms"
LOOP_P95_MS = "loop.p95_ms"
LOOP_P99_MS = "loop.p99_ms"
LOOP_MAX_MS = "loop.max_ms"
LOOP_LAST_MS = "loop.last_ms"
LOOP_LONGEST_GAP_MS = "loop.longest_gap_ms"
#: delays over T ms: ``LOOP_OVER % T``
LOOP_OVER = "loop.over_%d"

UNITS = {
    LOOP_MEAN_MS: (Unit.MS, "event loop lag, average"),
    LOOP_P50_MS: (Unit.MS, "event loop lag, median"),
    LOOP_P95_MS: (Unit.MS, "event loop lag, 95th percentile"),
    LOOP_P99_MS: (Unit.MS, "event loop lag, 99th percentile"),
    LOOP_MAX_MS: (Unit.MS, "event loop lag, the longest"),
    LOOP_LAST_MS: (Unit.MS, "event loop lag, the last sample"),
    LOOP_LONGEST_GAP_MS: (Unit.MS, "the longest the event loop went without answering"),
    **{LOOP_OVER % t: (Unit.COUNT, "event loop delays over %d ms" % t) for t in LAG_THRESHOLDS_MS},
}


class LagAccumulator:
    """Lags, ms, as they are measured - from the UI thread - and their
    summary per bucket, taken by the worker: thread-safe."""

    def __init__(self):
        self._lock = threading.Lock()
        self._stats = Stats()
        self._over = [0] * len(LAG_THRESHOLDS_MS)
        self._longest_gap = 0.0

    def add(self, lag_ms: float, gap_ms: float) -> None:
        with self._lock:
            self._stats.add(lag_ms)
            for at, threshold in enumerate(LAG_THRESHOLDS_MS):
                if lag_ms > threshold:
                    self._over[at] += 1
            if gap_ms > self._longest_gap:
                self._longest_gap = gap_ms

    def take(self) -> Dict[str, float]:
        """The bucket's summary - NaN with no samples - and a new bucket."""
        with self._lock:
            stats, over, gap = self._stats, self._over, self._longest_gap
            self._stats, self._over, self._longest_gap = Stats(), [0] * len(LAG_THRESHOLDS_MS), 0.0
        summary = stats.summary()
        if not stats.count:
            return {name: math.nan for name in UNITS}
        out = {LOOP_MEAN_MS: summary[series.MEAN], LOOP_P50_MS: summary[series.P50],
               LOOP_P95_MS: summary[series.P95], LOOP_P99_MS: summary[series.P99],
               LOOP_MAX_MS: summary[series.MAX], LOOP_LAST_MS: summary[series.LAST],
               LOOP_LONGEST_GAP_MS: gap}
        for threshold, count in zip(LAG_THRESHOLDS_MS, over):
            out[LOOP_OVER % threshold] = float(count)
        return out
