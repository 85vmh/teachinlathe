"""The diagnostics' one service: in the mode set (diagnostics.model.modes),
the event loop watched (EventLoopMonitor, a timer on the UI thread), and one
worker thread that reads the process, the system and the CPU temperatures
once a second and, every 5 s, closes a bucket: one row of every series in
the store, and one signal (``bucketClosed``) - nothing per sample, nothing per
metric.

What else is to be watched is handed in as gauges (``add_gauges``): a name
and a function giving a few numbers - the backplot's points, its logger on or
off - read on the worker thread as each bucket closes; and states
(``add_state``): what is shown and exported as it is, the last causes, say.

Made by the Application, shut down as the application quits; any number can
be made - a test makes its own, with its own profiler, store and collectors.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal

from teachinlathe.diagnostics.model import collectors as collectors_module
from teachinlathe.diagnostics.model import event_loop
from teachinlathe.diagnostics.model.event_loop import LagAccumulator
from teachinlathe.diagnostics.model import operations
from teachinlathe.diagnostics.model import series
from teachinlathe.diagnostics.model.collectors import (PROC_CPU_CORE_PCT, PROC_CPU_TOTAL_PCT, SYS_CPU_PCT,
                                                       TEMP_MAX_C)
from teachinlathe.diagnostics.model.modes import ProfilingMode
from teachinlathe.diagnostics.model.series import BUCKET_SECONDS, MAX_SUFFIX, Stats, TimeSeriesStore
from teachinlathe.diagnostics.model.spans import PROFILER, Profiler

LOG = logging.getLogger(__name__)

#: How often the event loop is looked at, ms: often enough to see a short
#: stall, seldom enough to cost nothing.
LOOP_INTERVAL_MS = 20
#: How often the worker reads the process and the system, seconds.
SAMPLE_SECONDS = 1.0
#: How many garbage collections are kept between two buckets, at most.
GC_KEPT = 4096
#: Of these the bucket keeps the maximum too (``<name>.max``), not only the mean.
KEEP_MAX = (PROC_CPU_CORE_PCT, PROC_CPU_TOTAL_PCT, SYS_CPU_PCT, TEMP_MAX_C)


#: A stall this long, ms - the loop not answering - goes in the list of slow
#: operations as ``event_loop.stall``, when it began: next to what ran then.
STALL_MS = 100.0

#: What a stall notes about itself, ms.
LAG_MS_META = "lag_ms"
#: Python's gc callback phase as a collection begins; what its info holds.
GC_PHASE_START = "start"
GC_INFO_GENERATION = "generation"
GC_INFO_COLLECTED = "collected"
#: A state that could not be read, shown with the error.
STATE_ERROR = "error"
#: The worker's thread.
WORKER_THREAD = "diagnostics"


class EventLoopMonitor(QObject):
    """A timer on the UI thread, firing every ``interval_ms``: how late each
    tick is - the loop's lag - into a LagAccumulator; a long stall, also as a
    slow operation of the ``profiler``'s."""

    def __init__(self, accumulator: LagAccumulator, interval_ms: int = LOOP_INTERVAL_MS, parent=None,
                 profiler: Profiler = None):
        super().__init__(parent)
        self._accumulator = accumulator
        self._profiler = profiler
        self._interval_ns = interval_ms * 1_000_000
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)
        self._last = 0

    @property
    def active(self) -> bool:
        return self._timer.isActive()

    def start(self) -> None:
        if not self._timer.isActive():
            self._last = time.perf_counter_ns()
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self):
        now = time.perf_counter_ns()
        gap = now - self._last
        self._last = now
        lag = max(0, gap - self._interval_ns)
        self._accumulator.add(lag / 1e6, gap / 1e6)
        if self._profiler is not None and lag / 1e6 >= STALL_MS:
            # recorded as an operation, so that its time sits among the others
            self._profiler.record(operations.EVENT_LOOP_STALL, now - gap, gap, True,
                                  {LAG_MS_META: round(lag / 1e6, 1)})


class DiagnosticsService(QObject):
    #: A bucket closed: the seq of its row in ``store``.
    bucketClosed = pyqtSignal(int)
    modeChanged = pyqtSignal(str)

    def __init__(self, mode: ProfilingMode = ProfilingMode.OFF, profiler: Profiler = None,
                 store: TimeSeriesStore = None, make_collectors: Callable = None,
                 bucket_seconds: float = BUCKET_SECONDS, sample_seconds: float = SAMPLE_SECONDS,
                 loop_interval_ms: int = LOOP_INTERVAL_MS, parent=None):
        super().__init__(parent)
        self.profiler = PROFILER if profiler is None else profiler
        self.store = TimeSeriesStore() if store is None else store
        self.bucket_seconds = float(bucket_seconds)
        self.sample_seconds = float(sample_seconds)
        self._make_collectors = make_collectors or default_collectors
        self._collectors = None
        self.unavailable: List[str] = []
        self.started_wall = time.time()
        self._lags = LagAccumulator()
        self._loop = EventLoopMonitor(self._lags, loop_interval_ms, self, self.profiler)
        # a collection's start, by thread; the collections since the last
        # bucket - (generation, start ns, duration ns, collected) - handed to
        # the profiler by the worker: a GC callback takes no lock (below)
        self._gc_started = {}
        self._gc_done = deque(maxlen=GC_KEPT)
        self._gauges: Dict[str, Callable[[], Dict[str, float]]] = {}
        self._states: Dict[str, Callable[[], dict]] = {}
        self._samples: Dict[str, Stats] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._next_close = 0.0
        self.mode = ProfilingMode.OFF
        for name, (unit, description) in event_loop.UNITS.items():
            self.store.declare(name, unit, description)
        for name, (unit, description) in collectors_module.UNITS.items():
            self.store.declare(name, unit, description)
            if name in KEEP_MAX:
                self.store.declare(name + MAX_SUFFIX, unit, description + ", the most in the bucket")
        self.set_mode(mode)

    # ── the mode ─────────────────────────────────────────────────────────

    def set_mode(self, mode) -> None:
        mode = ProfilingMode.parse(mode.value if isinstance(mode, ProfilingMode) else mode)
        if mode is self.mode:
            return
        self.mode = mode
        self.profiler.enabled = mode is ProfilingMode.DETAILED
        if mode is ProfilingMode.OFF:
            self._loop.stop()
            self._stop_worker()
            self._watch_gc(False)
        else:
            self._loop.start()
            self._start_worker()
            self._watch_gc(True)
        LOG.info("diagnostics: profiling %s", mode.value)
        self.modeChanged.emit(mode.value)

    @property
    def running(self) -> bool:
        return self._worker is not None

    @property
    def loop_monitor_active(self) -> bool:
        return self._loop.active

    # ── what else is watched ─────────────────────────────────────────────

    def add_gauges(self, name: str, read: Callable[[], Dict[str, float]],
                   units: Dict[str, tuple] = None) -> None:
        """``read()``: a few numbers, read on the worker thread as each bucket
        closes. Added again under the same name: replaced, not added twice."""
        self._gauges[name] = read
        for series_name, (unit, description) in (units or {}).items():
            self.store.declare(series_name, unit, description)

    def add_state(self, name: str, read: Callable[[], dict]) -> None:
        """``read()``: what is shown and exported as it is (no series)."""
        self._states[name] = read

    def states(self) -> Dict[str, dict]:
        out = {}
        for name, read in self._states.items():
            try:
                out[name] = read()
            except Exception as exc:   # a state that cannot be read is not shown
                out[name] = {STATE_ERROR: str(exc)}
        return out

    # ── history ──────────────────────────────────────────────────────────

    def reset_history(self) -> None:
        self.store.clear()
        self.profiler.reset()
        self._lags.take()
        with self._lock:
            self._samples = {}

    def shutdown(self) -> None:
        """Nothing left running: no timer, no worker."""
        self._loop.stop()
        self._stop_worker()
        self._watch_gc(False)
        self.profiler.enabled = False

    # ── Python's garbage collector ───────────────────────────────────────

    def _watch_gc(self, on: bool) -> None:
        """Each collection timed as ``python.gc.gen<N>`` - a pause of every
        thread, the UI's too - while profiling is on."""
        import gc

        if on and self._on_gc not in gc.callbacks:
            gc.callbacks.append(self._on_gc)
        elif not on and self._on_gc in gc.callbacks:
            gc.callbacks.remove(self._on_gc)

    def _on_gc(self, phase, info):
        """Runs inside the collection, on whichever thread allocated - which
        may be in the middle of ``Profiler.record`` with its lock held. So
        nothing here takes a lock: the collection goes in a deque (whose
        append is atomic), and the worker records it as the bucket closes."""
        if phase == GC_PHASE_START:
            self._gc_started[threading.get_ident()] = time.perf_counter_ns()
            return
        started = self._gc_started.pop(threading.get_ident(), None)
        if started is not None:
            self._gc_done.append((info.get(GC_INFO_GENERATION, 0), started, time.perf_counter_ns() - started,
                                  info.get(GC_INFO_COLLECTED, 0)))

    def _record_gc(self) -> None:
        while self._gc_done:
            generation, started, duration, collected = self._gc_done.popleft()
            self.profiler.record(operations.PYTHON_GC_GEN % generation, started, duration, True,
                                 {GC_INFO_COLLECTED: collected})

    # ── the worker ───────────────────────────────────────────────────────

    def _start_worker(self) -> None:
        if self._worker is not None:
            return
        if self._collectors is None:
            self._collectors = self._make_collectors()
            self.unavailable = sorted({name for c in self._collectors for name in getattr(c, "unavailable", ())})
            for collector in self._collectors:
                for series_name, (unit, description) in getattr(collector, "units", lambda: {})().items():
                    self.store.declare(series_name, unit, description)
        self._stop.clear()
        now = time.monotonic()
        self._next_close = (math.floor(now / self.bucket_seconds) + 1) * self.bucket_seconds
        self._lags.take()
        self.profiler.take_bucket()
        self._worker = threading.Thread(target=self._run, name=WORKER_THREAD, daemon=True)
        self._worker.start()

    def _stop_worker(self) -> None:
        worker, self._worker = self._worker, None
        if worker is None:
            return
        self._stop.set()
        worker.join(2.0)

    def _run(self):
        next_sample = time.monotonic()
        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_sample:
                self._sample(now)
                next_sample = now + self.sample_seconds
            if now >= self._next_close:
                self._close(now)
            wait = min(next_sample, self._next_close) - time.monotonic()
            self._stop.wait(max(0.0, wait))

    def _sample(self, now: float) -> None:
        for collector in self._collectors:
            try:
                values = collector.sample(now)
            except Exception as exc:     # one collector failing does not stop the rest
                LOG.debug("diagnostics: %s failed: %s", type(collector).__name__, exc)
                continue
            with self._lock:
                for name, value in values.items():
                    stats = self._samples.get(name)
                    if stats is None:
                        stats = self._samples[name] = Stats()
                    stats.add(value)

    def _close(self, now: float) -> None:
        """The bucket that ended at ``_next_close`` as a row - after a row of
        nothing (NaN) for each bucket missed, as when the machine slept."""
        missed = int((now - self._next_close) // self.bucket_seconds)
        wall_now = time.time()
        for at in range(missed):
            end = self._next_close + at * self.bucket_seconds
            self.store.append(end, wall_now - (now - end), {})
        end = self._next_close + missed * self.bucket_seconds
        self._next_close = end + self.bucket_seconds
        seq = self.store.append(end, wall_now - (now - end), self._bucket_values())
        self.bucketClosed.emit(seq)

    def _bucket_values(self) -> Dict[str, float]:
        self._record_gc()
        values = dict(self._lags.take())
        with self._lock:
            samples, self._samples = self._samples, {}
        for name, stats in samples.items():
            values[name] = stats.mean
            if name in KEEP_MAX:
                values[name + MAX_SUFFIX] = stats.max
        for name, stats in self.profiler.take_bucket().items():
            summary = stats.summary()
            prefix = operations.OP_SERIES_PREFIX + name
            values[prefix + operations.OP_COUNT_SUFFIX] = summary[series.COUNT]
            values[prefix + operations.OP_MEAN_SUFFIX] = summary[series.MEAN]
            values[prefix + operations.OP_P50_SUFFIX] = summary[series.P50]
            values[prefix + operations.OP_P95_SUFFIX] = summary[series.P95]
            values[prefix + operations.OP_P99_SUFFIX] = summary[series.P99]
            values[prefix + operations.OP_MAX_SUFFIX] = summary[series.MAX]
        for name, read in list(self._gauges.items()):
            try:
                values.update(read())
            except Exception as exc:
                LOG.debug("diagnostics: gauges %s failed: %s", name, exc)
        return values


def default_collectors():
    return [collectors_module.ProcessCollector(), collectors_module.SystemCollector(),
            collectors_module.ThermalCollector()]
