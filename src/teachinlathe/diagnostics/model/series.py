"""Time series in 5 s buckets, kept for 4 hours: one time axis for all of
them (TimeSeriesStore), and what a bucket gathers of a metric measured more
often than that (Stats).

Every series has a value in every bucket - NaN when it had no data in it, or
did not exist yet - so that all of them line up on the one axis: the CPU, the
temperature, the event loop's lag and the backplot's points of one moment are
one row. A bucket's time is its end: ``monotonic`` seconds for working out,
``wall`` (Unix time) for showing and exporting. Rows are numbered from the
first (``seq``); a reader asks for what came after the last it read
(``rows_since``), never for all of it again.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from teachinlathe.diagnostics.model.units import Unit

#: A bucket, seconds.
BUCKET_SECONDS = 5.0
#: How long the history goes back, seconds: 4 hours.
HISTORY_SECONDS = 4 * 60 * 60
#: Buckets kept per series: 2880.
HISTORY_BUCKETS = int(HISTORY_SECONDS / BUCKET_SECONDS)

#: The most samples a bucket keeps of one metric for its percentiles; past
#: it, one in so many is kept (reservoir), the count, sum, min and max exact.
SAMPLES_KEPT = 4096

#: The keys of ``Stats.summary``.
MEAN = "mean"
MIN = "min"
MAX = "max"
LAST = "last"
COUNT = "count"
P50 = "p50"
P95 = "p95"
P99 = "p99"

#: A series' maximum in the bucket, beside its mean: ``name + MAX_SUFFIX``.
MAX_SUFFIX = ".max"


class Stats:
    """A metric's samples over one bucket: count, sum, min, max, the last, and
    up to SAMPLES_KEPT of them for the percentiles."""

    __slots__ = ("count", "total", "min", "max", "last", "_samples", "_seed")

    def __init__(self):
        self.count = 0
        self.total = 0.0
        self.min = math.inf
        self.max = -math.inf
        self.last = math.nan
        self._samples: List[float] = []
        self._seed = 0x9E3779B9

    def add(self, value: float) -> None:
        value = float(value)
        self.count += 1
        self.total += value
        if value < self.min:
            self.min = value
        if value > self.max:
            self.max = value
        self.last = value
        if len(self._samples) < SAMPLES_KEPT:
            self._samples.append(value)
        else:
            # reservoir: each sample kept with the same chance
            self._seed = (self._seed * 1103515245 + 12345) & 0x7FFFFFFF
            at = self._seed % self.count
            if at < SAMPLES_KEPT:
                self._samples[at] = value

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else math.nan

    def percentiles(self, *qs: float) -> Tuple[float, ...]:
        if not self._samples:
            return tuple(math.nan for _ in qs)
        values = np.percentile(np.asarray(self._samples), qs)
        return tuple(float(v) for v in np.atleast_1d(values))

    def summary(self) -> Dict[str, float]:
        """mean, min, max, last, count, p50, p95, p99 - NaN with no samples."""
        p50, p95, p99 = self.percentiles(50, 95, 99)
        empty = not self.count
        return {MEAN: self.mean, MIN: math.nan if empty else self.min,
                MAX: math.nan if empty else self.max, LAST: self.last,
                COUNT: float(self.count), P50: p50, P95: p95, P99: p99}


@dataclass(frozen=True)
class SeriesInfo:
    """What a series is: its ``unit`` ("%", "ms", "°C", "MiB", "points",
    "count", "0/1", ...) and what it means."""
    unit: str
    description: str = ""


@dataclass
class Rows:
    """Rows of the store, oldest first: ``seq`` of each, its ``monotonic`` and
    ``wall`` time, and each series' values."""
    seq: np.ndarray
    monotonic: np.ndarray
    wall: np.ndarray
    values: Dict[str, np.ndarray] = field(default_factory=dict)

    def __len__(self):
        return len(self.seq)


class TimeSeriesStore:
    """Series on one time axis of buckets, the last ``capacity`` kept (a ring
    each); thread-safe - written by the diagnostics worker, read by the UI.

    Nothing is allocated until the first row is written: a store of an
    application that never profiles takes no memory. Values are float32 -
    plenty for a metric, half the memory - the times float64."""

    def __init__(self, capacity: int = HISTORY_BUCKETS):
        self.capacity = int(capacity)
        self._lock = threading.Lock()
        self._mono = self._wall = None
        self._series: Dict[str, np.ndarray] = {}
        self.info: Dict[str, SeriesInfo] = {}
        #: rows written, all told: the next row's seq
        self.next_seq = 0
        # the rows before it were cleared
        self._floor = 0

    def declare(self, name: str, unit: str, description: str = "") -> None:
        """A series, with its unit; NaN in every row before it."""
        with self._lock:
            self.info[name] = SeriesInfo(unit, description)
            if self._mono is not None and name not in self._series:
                self._series[name] = self._ring()

    def _ring(self):
        return np.full(self.capacity, np.nan, dtype=np.float32)

    def append(self, monotonic: float, wall: float, values: Dict[str, float]) -> int:
        """A row - each declared series its value from ``values``, NaN when it
        has none there; a name not declared is declared, its unit unknown.
        Its seq."""
        with self._lock:
            if self._mono is None:
                self._mono = np.full(self.capacity, math.nan)
                self._wall = np.full(self.capacity, math.nan)
                self._series = {name: self._ring() for name in self.info}
            at = self.next_seq % self.capacity
            self._mono[at] = monotonic
            self._wall[at] = wall
            for name in values:
                if name not in self._series:
                    self._series[name] = self._ring()
                    self.info.setdefault(name, SeriesInfo(Unit.NONE))
            for name, ring in self._series.items():
                value = values.get(name)
                ring[at] = math.nan if value is None else float(value)
            seq = self.next_seq
            self.next_seq += 1
            return seq

    @property
    def first_seq(self) -> int:
        """The oldest row kept's seq."""
        return max(self._floor, self.next_seq - self.capacity)

    def __len__(self):
        return self.next_seq - self.first_seq

    def names(self) -> List[str]:
        with self._lock:
            return list(self._series or self.info)

    def rows_since(self, seq: int, names: Optional[Iterable[str]] = None) -> Rows:
        """The rows after ``seq`` - from the oldest kept, when it is older -
        of ``names`` (all of them by default)."""
        with self._lock:
            start = max(int(seq) + 1, self.first_seq)
            stop = self.next_seq
            if self._mono is None or stop <= start:
                empty = np.zeros(0)
                wanted = list(self._series) if names is None else [n for n in names if n in self._series]
                return Rows(seq=np.zeros(0, dtype=int), monotonic=empty, wall=empty,
                            values={n: np.zeros(0, dtype=np.float32) for n in wanted})
            index = np.arange(start, stop) % self.capacity
            wanted = list(self._series) if names is None else [n for n in names if n in self._series]
            return Rows(seq=np.arange(start, stop), monotonic=self._mono[index].copy(),
                        wall=self._wall[index].copy(),
                        values={n: self._series[n][index].astype(float) for n in wanted})

    def last_row(self) -> Dict[str, float]:
        """The newest row's values; empty with none."""
        with self._lock:
            if self._mono is None or self.next_seq <= self._floor:
                return {}
            at = (self.next_seq - 1) % self.capacity
            return {n: float(r[at]) for n, r in self._series.items()}

    def clear(self) -> None:
        """The history gone; the series stay declared, the seqs go on - a
        reader's last one stays valid."""
        with self._lock:
            if self._mono is not None:
                self._mono[:] = math.nan
                self._wall[:] = math.nan
                for ring in self._series.values():
                    ring[:] = np.nan
            self._floor = self.next_seq

    @property
    def nbytes(self) -> int:
        if self._mono is None:
            return 0
        return int(self._mono.nbytes + self._wall.nbytes + sum(r.nbytes for r in self._series.values()))
