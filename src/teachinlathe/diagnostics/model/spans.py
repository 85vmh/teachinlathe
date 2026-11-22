"""Timed operations: ``with timed("backplot.render"):`` around what is to
be measured - its duration, whether it raised, a few small
numbers about it - gathered per name per 5 s bucket, with a short list of the
slow ones; never a line of log per call.

Off (Profiler.enabled False, as in the "off" and "basic" modes) ``timed``
hands back one shared object that does nothing: an attribute test and a call.

``PROFILER`` is the application's; a test makes its own or ``reset()``s it.

There is no decorator, on purpose: a slot wrapped in one takes ``*args``, and
PyQt no longer drops the arguments of a signal the slot does not take - it
calls it with them, and the application aborts. ``with timed(...)`` goes in
the function's body.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, Optional

from teachinlathe.diagnostics.model.series import Stats

#: An operation this long or longer, ms, goes in the list of slow ones.
SLOW_MS = 50.0
#: How many slow operations are kept, the newest.
SLOW_KEPT = 200


@dataclass(frozen=True)
class SlowOperation:
    name: str
    wall: float             # Unix time it started
    monotonic: float        # monotonic seconds it started
    duration_ms: float
    ok: bool
    meta: Dict[str, float] = field(default_factory=dict)


class OperationTotals:
    """An operation over the whole of the history: count, total, max."""

    __slots__ = ("count", "total_ms", "max_ms", "failures")

    def __init__(self):
        self.count = 0
        self.total_ms = 0.0
        self.max_ms = 0.0
        self.failures = 0


class Profiler:
    """Where timed operations are gathered: per name, for the bucket under way
    (``take_bucket`` hands it over and starts the next) and all told."""

    def __init__(self, slow_ms: float = SLOW_MS, slow_kept: int = SLOW_KEPT):
        self.enabled = False
        self.slow_ms = slow_ms
        # re-entrant: a record from inside a record - a GC callback, a signal
        # handler timed in turn - must not lock the thread out of itself
        self._lock = threading.RLock()
        self._bucket: Dict[str, Stats] = {}
        self.totals: Dict[str, OperationTotals] = {}
        self.slow: Deque[SlowOperation] = deque(maxlen=slow_kept)
        #: the newest of each mark (``mark``): monotonic ns
        self.marks: Dict[str, int] = {}

    def record(self, name: str, start_ns: int, duration_ns: int, ok: bool = True,
               meta: Optional[Dict[str, float]] = None) -> None:
        ms = duration_ns / 1e6
        with self._lock:
            stats = self._bucket.get(name)
            if stats is None:
                stats = self._bucket[name] = Stats()
            stats.add(ms)
            totals = self.totals.get(name)
            if totals is None:
                totals = self.totals[name] = OperationTotals()
            totals.count += 1
            totals.total_ms += ms
            if ms > totals.max_ms:
                totals.max_ms = ms
            if not ok:
                totals.failures += 1
            if ms >= self.slow_ms:
                started = start_ns / 1e9
                wall = time.time() - (time.perf_counter_ns() - start_ns) / 1e9
                self.slow.append(SlowOperation(name, wall, started, ms, ok, dict(meta or {})))

    def mark(self, name: str) -> int:
        """A moment, by name (monotonic ns): the stages of something that
        crosses threads and signals - a tool picked, then M61 sent, then...
        - and the time from the one before to it, timed as ``name``.
        Off: nothing, 0."""
        if not self.enabled:
            return 0
        now = time.perf_counter_ns()
        with self._lock:
            self.marks[name] = now
        return now

    def interval(self, name: str, since_mark: str) -> None:
        """The time from mark ``since_mark`` to now, recorded as ``name`` -
        when that mark was made."""
        if not self.enabled:
            return
        start = self.marks.get(since_mark)
        if start:
            now = time.perf_counter_ns()
            self.record(name, start, now - start)

    def pending(self, name: str) -> bool:
        """Whether mark ``name`` was made, and not cleared since."""
        return self.enabled and name in self.marks

    def clear_mark(self, name: str) -> None:
        with self._lock:
            self.marks.pop(name, None)

    def take_bucket(self) -> Dict[str, Stats]:
        with self._lock:
            bucket, self._bucket = self._bucket, {}
        return bucket

    def snapshot(self):
        """``(totals, slow)`` as they are now - copies, taken under the lock:
        for a reader on another thread (an export)."""
        with self._lock:
            totals = {name: (t.count, t.total_ms, t.max_ms, t.failures) for name, t in self.totals.items()}
            return totals, list(self.slow)

    def reset(self) -> None:
        """Nothing gathered; ``enabled`` as it was."""
        with self._lock:
            self._bucket = {}
            self.totals = {}
            self.slow.clear()
            self.marks = {}


PROFILER = Profiler()

class _Span:
    __slots__ = ("_profiler", "name", "meta", "_start")

    def __init__(self, profiler, name, meta):
        self._profiler = profiler
        self.name = name
        self.meta = meta

    def __enter__(self):
        self._start = time.perf_counter_ns()
        return self

    def __exit__(self, exc_type, _exc, _tb):
        self._profiler.record(self.name, self._start, time.perf_counter_ns() - self._start,
                              exc_type is None, self.meta)
        return False

    def note(self, **meta):
        """Small numbers about this call, kept with it if it is slow."""
        if self.meta is None:
            self.meta = {}
        self.meta.update(meta)


class _Nothing:
    __slots__ = ()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def note(self, **_meta):
        pass


_NOTHING = _Nothing()


def timed(name: str, profiler: Profiler = None, **meta):
    """A context timing what runs in it as ``name``; does nothing while the
    profiler is off."""
    profiler = PROFILER if profiler is None else profiler
    if not profiler.enabled:
        return _NOTHING
    return _Span(profiler, name, meta or None)
