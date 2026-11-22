"""The process and the system, read from Linux's /proc and /sys - no
dependency beyond them - on the diagnostics worker's thread, never the UI's.

What there is is found once, as a collector is made: a file missing or not
readable then is a metric not available (``unavailable``), not an error; one
that goes away later is dropped after it fails, without a log line each time.
CPU usage is worked out from the counters' change between two samples, so the
first sample has none.

CPU percentages: ``proc.cpu_core_pct`` is of one core - 100 is one core busy,
up to 100 × the cores; ``proc.cpu_total_pct`` and ``sys.cpu_pct`` are of the
whole machine - 100 is every core busy.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from teachinlathe.diagnostics.model.units import Unit

LOG = logging.getLogger(__name__)

#: What the collectors give.
PROC_CPU_CORE_PCT = "proc.cpu_core_pct"
PROC_CPU_TOTAL_PCT = "proc.cpu_total_pct"
PROC_RSS_MIB = "proc.rss_mib"
PROC_VMS_MIB = "proc.vms_mib"
PROC_THREADS = "proc.threads"
PROC_FDS = "proc.fds"
PROC_MINOR_FAULTS_PER_S = "proc.minor_faults_per_s"
PROC_MAJOR_FAULTS_PER_S = "proc.major_faults_per_s"
PROC_VOL_CTX_PER_S = "proc.vol_ctx_per_s"
PROC_INVOL_CTX_PER_S = "proc.invol_ctx_per_s"
PROC_IO_READ_KIB_PER_S = "proc.io_read_kib_per_s"
PROC_IO_WRITE_KIB_PER_S = "proc.io_write_kib_per_s"
SYS_CPU_PCT = "sys.cpu_pct"
SYS_LOAD1 = "sys.load1"
SYS_LOAD5 = "sys.load5"
SYS_LOAD15 = "sys.load15"
SYS_MEM_TOTAL_MIB = "sys.mem_total_mib"
SYS_MEM_AVAILABLE_MIB = "sys.mem_available_mib"
SYS_MEM_USED_MIB = "sys.mem_used_mib"
SYS_MEM_USED_PCT = "sys.mem_used_pct"
SYS_SWAP_TOTAL_MIB = "sys.swap_total_mib"
SYS_SWAP_USED_MIB = "sys.swap_used_mib"
SYS_CPU_MHZ_AVG = "sys.cpu_mhz_avg"
SYS_CPU_MHZ_MAX = "sys.cpu_mhz_max"
SYS_PSI_CPU_SOME = "sys.psi_cpu_some"
SYS_PSI_MEMORY_SOME = "sys.psi_memory_some"
SYS_PSI_IO_SOME = "sys.psi_io_some"
SYS_ON_AC = "sys.on_ac"
TEMP_MAX_C = "temp.max_c"
#: a core's CPU: ``SYS_CORE_PCT % n``
SYS_CORE_PCT = "sys.core%s_pct"
#: pressure of a kind (PRESSURE_KINDS): ``SYS_PSI_SOME % kind``
SYS_PSI_SOME = "sys.psi_%s_some"
#: a CPU temperature sensor: ``TEMP_PREFIX + Sensor.key``
TEMP_PREFIX = "temp."

#: what /proc/pressure tells
PRESSURE_KINDS = ("cpu", "memory", "io")
#: /proc/stat's line of all the CPUs; a core's is this and its number
STAT_CPU = "cpu"
#: a power supply's ``type`` when it is the mains
MAINS_SUPPLY = "Mains"

# the counters a ProcessCollector works its rates out from
_CPU = "cpu"
_MINFLT = "minflt"
_MAJFLT = "majflt"
_VOL = "vol"
_INVOL = "invol"

#: The units of what the collectors give.
UNITS = {
    PROC_CPU_CORE_PCT: (Unit.PERCENT, "process CPU, of one core (100 = one core busy)"),
    PROC_CPU_TOTAL_PCT: (Unit.PERCENT, "process CPU, of every core (100 = all busy)"),
    PROC_RSS_MIB: (Unit.MIB, "process resident memory"),
    PROC_VMS_MIB: (Unit.MIB, "process virtual memory"),
    PROC_THREADS: (Unit.COUNT, "process threads"),
    PROC_FDS: (Unit.COUNT, "process open file descriptors"),
    PROC_MINOR_FAULTS_PER_S: (Unit.PER_S, "process minor page faults"),
    PROC_MAJOR_FAULTS_PER_S: (Unit.PER_S, "process major page faults"),
    PROC_VOL_CTX_PER_S: (Unit.PER_S, "process voluntary context switches"),
    PROC_INVOL_CTX_PER_S: (Unit.PER_S, "process involuntary context switches"),
    PROC_IO_READ_KIB_PER_S: (Unit.KIB_PER_S, "process storage reads"),
    PROC_IO_WRITE_KIB_PER_S: (Unit.KIB_PER_S, "process storage writes"),
    SYS_CPU_PCT: (Unit.PERCENT, "system CPU, of every core"),
    SYS_LOAD1: (Unit.LOAD, "load average, 1 min"),
    SYS_LOAD5: (Unit.LOAD, "load average, 5 min"),
    SYS_LOAD15: (Unit.LOAD, "load average, 15 min"),
    SYS_MEM_TOTAL_MIB: (Unit.MIB, "system memory"),
    SYS_MEM_AVAILABLE_MIB: (Unit.MIB, "system memory available"),
    SYS_MEM_USED_MIB: (Unit.MIB, "system memory used (total - available)"),
    SYS_MEM_USED_PCT: (Unit.PERCENT, "system memory used"),
    SYS_SWAP_TOTAL_MIB: (Unit.MIB, "swap"),
    SYS_SWAP_USED_MIB: (Unit.MIB, "swap used"),
    SYS_CPU_MHZ_AVG: (Unit.MHZ, "CPU frequency, average of the cores"),
    SYS_CPU_MHZ_MAX: (Unit.MHZ, "CPU frequency, the fastest core"),
    SYS_PSI_CPU_SOME: (Unit.PERCENT, "CPU pressure: some tasks stalled, last 10 s"),
    SYS_PSI_MEMORY_SOME: (Unit.PERCENT, "memory pressure: some tasks stalled, last 10 s"),
    SYS_PSI_IO_SOME: (Unit.PERCENT, "I/O pressure: some tasks stalled, last 10 s"),
    SYS_ON_AC: (Unit.FLAG, "on mains power (0: on battery)"),
    TEMP_MAX_C: (Unit.CELSIUS, "the hottest CPU sensor"),
}


def _read(path: str) -> Optional[str]:
    try:
        with open(path) as fh:
            return fh.read()
    except (OSError, ValueError):
        return None


class ProcessCollector:
    """This process: /proc/self/stat, status, io, fd."""

    def __init__(self, root: str = "/proc", pid: str = "self", ticks: Optional[int] = None,
                 page_size: Optional[int] = None, cores: Optional[int] = None):
        self._base = os.path.join(root, pid)
        self.ticks = ticks or os.sysconf("SC_CLK_TCK")
        self._page = page_size or os.sysconf("SC_PAGE_SIZE")
        self.cores = cores or os.cpu_count() or 1
        self._has_io = _read(os.path.join(self._base, "io")) is not None
        self._has_status = _read(os.path.join(self._base, "status")) is not None
        self._has_fd = os.path.isdir(os.path.join(self._base, "fd"))
        self._before: Optional[Tuple[float, Dict[str, float]]] = None

    @property
    def unavailable(self) -> List[str]:
        gone = []
        if not self._has_io:
            gone += [PROC_IO_READ_KIB_PER_S, PROC_IO_WRITE_KIB_PER_S]
        if not self._has_status:
            gone += [PROC_VOL_CTX_PER_S, PROC_INVOL_CTX_PER_S]
        if not self._has_fd:
            gone += [PROC_FDS]
        return gone

    def sample(self, now: float) -> Dict[str, float]:
        counters, out = {}, {}
        stat = _read(os.path.join(self._base, "stat"))
        if stat:
            # the name, in parentheses, may hold spaces: the fields after it
            fields = stat[stat.rfind(")") + 2:].split()
            # fields[0] is field 3 (state): field n is fields[n - 3]
            counters[_CPU] = (int(fields[11]) + int(fields[12])) / self.ticks
            counters[_MINFLT] = float(fields[7])
            counters[_MAJFLT] = float(fields[9])
            out[PROC_THREADS] = float(fields[17])
            out[PROC_VMS_MIB] = int(fields[20]) / 2 ** 20
            out[PROC_RSS_MIB] = int(fields[21]) * self._page / 2 ** 20
        if self._has_status:
            status = _read(os.path.join(self._base, "status"))
            if status is None:
                self._has_status = False
            else:
                for key, name in (("voluntary_ctxt_switches", _VOL), ("nonvoluntary_ctxt_switches", _INVOL)):
                    found = re.search(r"^%s:\s+(\d+)" % key, status, re.M)
                    if found:
                        counters[name] = float(found.group(1))
        if self._has_io:
            io = _read(os.path.join(self._base, "io"))
            if io is None:
                self._has_io = False
            else:
                for key in ("read_bytes", "write_bytes"):
                    found = re.search(r"^%s:\s+(\d+)" % key, io, re.M)
                    if found:
                        counters[key] = float(found.group(1))
        if self._has_fd:
            try:
                out[PROC_FDS] = float(len(os.listdir(os.path.join(self._base, "fd"))))
            except OSError:
                self._has_fd = False
        before, self._before = self._before, (now, counters)
        if before is None:
            return out
        dt = now - before[0]
        if dt <= 0:
            return out
        old = before[1]

        def rate(key):
            return (counters[key] - old[key]) / dt if key in counters and key in old else None

        cpu = rate(_CPU)
        if cpu is not None:
            out[PROC_CPU_CORE_PCT] = 100.0 * cpu
            out[PROC_CPU_TOTAL_PCT] = 100.0 * cpu / self.cores
        for key, name, scale in ((_MINFLT, PROC_MINOR_FAULTS_PER_S, 1), (_MAJFLT, PROC_MAJOR_FAULTS_PER_S, 1),
                                 (_VOL, PROC_VOL_CTX_PER_S, 1), (_INVOL, PROC_INVOL_CTX_PER_S, 1),
                                 ("read_bytes", PROC_IO_READ_KIB_PER_S, 1024),
                                 ("write_bytes", PROC_IO_WRITE_KIB_PER_S, 1024)):
            value = rate(key)
            if value is not None:
                out[name] = value / scale
        return out


class SystemCollector:
    """The machine: /proc/stat, loadavg, meminfo, pressure; the cores'
    frequencies in /sys."""

    def __init__(self, proc: str = "/proc", sys: str = "/sys"):
        self._proc = proc
        self._pressure = [kind for kind in PRESSURE_KINDS
                          if _read(os.path.join(proc, "pressure", kind)) is not None]
        cpus = os.path.join(sys, "devices", "system", "cpu")
        self._freqs = []
        try:
            for name in sorted(os.listdir(cpus)):
                path = os.path.join(cpus, name, "cpufreq", "scaling_cur_freq")
                if re.fullmatch(r"cpu\d+", name) and _read(path) is not None:
                    self._freqs.append(path)
        except OSError:
            pass
        self._before = None
        self.cores_before: Dict[str, Tuple[float, float]] = {}
        self._mains = _mains_supplies(sys)

    @property
    def unavailable(self) -> List[str]:
        gone = [SYS_PSI_SOME % kind for kind in PRESSURE_KINDS if kind not in self._pressure]
        if not self._freqs:
            gone += [SYS_CPU_MHZ_AVG, SYS_CPU_MHZ_MAX]
        if not self._mains:
            gone += [SYS_ON_AC]
        return gone

    def sample(self, _now: float = 0.0) -> Dict[str, float]:
        out = {}
        stat = _read(os.path.join(self._proc, "stat"))
        if stat:
            for line in stat.splitlines():
                if not line.startswith(STAT_CPU):
                    break
                name, *values = line.split()
                values = [float(v) for v in values]
                idle = values[3] + (values[4] if len(values) > 4 else 0.0)   # idle + iowait
                total = sum(values[:8])
                before = self.cores_before.get(name)
                self.cores_before[name] = (idle, total)
                if before is not None and total > before[1]:
                    busy = 100.0 * (1.0 - (idle - before[0]) / (total - before[1]))
                    out[SYS_CPU_PCT if name == STAT_CPU else SYS_CORE_PCT % name[len(STAT_CPU):]] = busy
        load = _read(os.path.join(self._proc, "loadavg"))
        if load:
            parts = load.split()
            out[SYS_LOAD1], out[SYS_LOAD5], out[SYS_LOAD15] = (float(p) for p in parts[:3])
        meminfo = _read(os.path.join(self._proc, "meminfo"))
        if meminfo:
            kib = {k: float(v) for k, v in re.findall(r"^(\w+):\s+(\d+)", meminfo, re.M)}
            total, available = kib.get("MemTotal"), kib.get("MemAvailable")
            if total:
                out[SYS_MEM_TOTAL_MIB] = total / 1024
                if available is not None:
                    out[SYS_MEM_AVAILABLE_MIB] = available / 1024
                    out[SYS_MEM_USED_MIB] = (total - available) / 1024
                    out[SYS_MEM_USED_PCT] = 100.0 * (total - available) / total
            if "SwapTotal" in kib:
                out[SYS_SWAP_TOTAL_MIB] = kib["SwapTotal"] / 1024
                out[SYS_SWAP_USED_MIB] = (kib["SwapTotal"] - kib.get("SwapFree", 0.0)) / 1024
        for kind in list(self._pressure):
            text = _read(os.path.join(self._proc, "pressure", kind))
            found = re.search(r"^some avg10=([\d.]+)", text or "", re.M)
            if found:
                out[SYS_PSI_SOME % kind] = float(found.group(1))
            elif text is None:
                self._pressure.remove(kind)
        mhz = []
        for path in list(self._freqs):
            text = _read(path)
            if text is None:
                self._freqs.remove(path)
            elif text.strip().isdigit():
                mhz.append(int(text) / 1000.0)
        if mhz:
            out[SYS_CPU_MHZ_AVG] = sum(mhz) / len(mhz)
            out[SYS_CPU_MHZ_MAX] = max(mhz)
        if self._mains:
            online = [(_read(path) or "").strip() for path in self._mains]
            out[SYS_ON_AC] = 1.0 if "1" in online else 0.0
        return out


def _mains_supplies(sys: str) -> List[str]:
    """The ``online`` files of the mains power supplies (a laptop's charger);
    none on a machine that does not report its supply."""
    base = os.path.join(sys, "class", "power_supply")
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return []
    return [os.path.join(base, n, "online") for n in names
            if (_read(os.path.join(base, n, "type")) or "").strip() == MAINS_SUPPLY
            and _read(os.path.join(base, n, "online")) is not None]


def system_info(proc: str = "/proc", sys: str = "/sys") -> Dict[str, object]:
    """What the machine runs at, as it is now - for an export: the CPU, its
    frequency limits and how it is told to save power, and whether it is on
    mains power. A value not found is None. Not read per sample: an export
    reads it once, off the UI thread."""
    def first(path):
        text = _read(path)
        return text.strip() if text is not None else None

    cpuinfo = _read(os.path.join(proc, "cpuinfo")) or ""
    model = re.search(r"^model name\s*:\s*(.+)$", cpuinfo, re.M)
    cpu0 = os.path.join(sys, "devices", "system", "cpu", "cpu0", "cpufreq")
    pstate = os.path.join(sys, "devices", "system", "cpu", "intel_pstate")

    def mhz(name):
        value = first(os.path.join(cpu0, name))
        return int(value) / 1000.0 if value and value.isdigit() else None

    mains = _mains_supplies(sys)
    return {
        "cpu_model": model.group(1).strip() if model else None,
        "cores": os.cpu_count(),
        "cpu_min_mhz": mhz("cpuinfo_min_freq"),
        "cpu_max_mhz": mhz("cpuinfo_max_freq"),
        "scaling_max_mhz": mhz("scaling_max_freq"),
        "scaling_governor": first(os.path.join(cpu0, "scaling_governor")),
        "energy_performance_preference": first(os.path.join(cpu0, "energy_performance_preference")),
        "intel_pstate_no_turbo": first(os.path.join(pstate, "no_turbo")),
        "intel_pstate_max_perf_pct": first(os.path.join(pstate, "max_perf_pct")),
        "platform_profile": first(os.path.join(sys, "firmware", "acpi", "platform_profile")),
        "on_mains_power": (any((_read(p) or "").strip() == "1" for p in mains) if mains else None),
    }


#: hwmon drivers that measure the CPU
CPU_HWMON = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "cpu-thermal", "soc_thermal", "x86_pkg_temp")
#: thermal zones that are the CPU's, by type
CPU_ZONE = re.compile(r"cpu|x86_pkg|soc|core", re.I)


@dataclass(frozen=True)
class Sensor:
    """A CPU temperature: ``key`` its series' (``temp.<key>``), ``label`` as
    the driver names it ("coretemp Package id 0", "k10temp Tctl"), the file."""
    key: str
    label: str
    path: str


def find_cpu_sensors(sys: str = "/sys") -> List[Sensor]:
    """The CPU's temperature sensors: hwmon's (coretemp, k10temp, ...) or,
    with none of those, the thermal zones that are the CPU's."""
    sensors = []
    hwmon = os.path.join(sys, "class", "hwmon")
    try:
        monitors = sorted(os.listdir(hwmon))
    except OSError:
        monitors = []
    for monitor in monitors:
        base = os.path.join(hwmon, monitor)
        driver = (_read(os.path.join(base, "name")) or "").strip()
        if driver not in CPU_HWMON:
            continue
        try:
            inputs = sorted(f for f in os.listdir(base) if re.fullmatch(r"temp\d+_input", f))
        except OSError:
            continue
        for name in inputs:
            path = os.path.join(base, name)
            if _read(path) is None:
                continue
            label = (_read(os.path.join(base, name.replace("_input", "_label"))) or name[:-6]).strip()
            key = re.sub(r"[^a-z0-9]+", "_", ("%s_%s" % (driver, label)).lower()).strip("_")
            sensors.append(Sensor(key, "%s %s" % (driver, label), path))
    if sensors:
        return _unique(sensors)
    zones = os.path.join(sys, "class", "thermal")
    try:
        names = sorted(n for n in os.listdir(zones) if n.startswith("thermal_zone"))
    except OSError:
        names = []
    for name in names:
        kind = (_read(os.path.join(zones, name, "type")) or "").strip()
        path = os.path.join(zones, name, "temp")
        if CPU_ZONE.search(kind) and _read(path) is not None:
            key = re.sub(r"[^a-z0-9]+", "_", ("%s_%s" % (kind, name)).lower()).strip("_")
            sensors.append(Sensor(key, kind, path))
    return _unique(sensors)


def _unique(sensors):
    """Keys told apart: hwmon's numbers may change from boot to boot, so they
    are in a key only when two sensors would share one."""
    seen, out = {}, []
    for sensor in sensors:
        count = seen.get(sensor.key, 0)
        seen[sensor.key] = count + 1
        out.append(sensor if not count else Sensor("%s_%d" % (sensor.key, count + 1), sensor.label, sensor.path))
    return out


class ThermalCollector:
    """The CPU's temperatures, each its series, and the hottest
    (``temp.max_c``). A sensor that stops answering is dropped."""

    def __init__(self, sys: str = "/sys"):
        self.sensors = find_cpu_sensors(sys)
        self._dropped: List[Sensor] = []

    @property
    def unavailable(self) -> List[str]:
        return [] if self.sensors else [TEMP_MAX_C]

    def units(self) -> Dict[str, Tuple[str, str]]:
        return {TEMP_PREFIX + s.key: (Unit.CELSIUS, s.label) for s in self.sensors}

    def sample(self, _now: float = 0.0) -> Dict[str, float]:
        out = {}
        for sensor in list(self.sensors):
            text = _read(sensor.path)
            try:
                value = int(text) / 1000.0
            except (TypeError, ValueError):
                self.sensors.remove(sensor)
                self._dropped.append(sensor)
                LOG.debug("diagnostics: temperature sensor %s gone", sensor.label)
                continue
            out[TEMP_PREFIX + sensor.key] = value
        if out:
            out[TEMP_MAX_C] = max(out.values())
        return out
