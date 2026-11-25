"""The USB sticks mounted on the machine, and their unmounting.

The only part of the app that knows how drives come and go. udisks2 mounts a
stick under /media/<user> (or /media) as it is plugged in; the kernel's mount
table, /proc/self/mounts, says so the moment it is done - its file descriptor
turns "exceptional" (POLLPRI) on every mount and unmount, which a
QSocketNotifier watches. Nothing is polled, nothing waits on a timer.

Unmounting goes through udisksctl, which unmounts for the user logged in with
no root, in the background (writing out what is cached can take seconds).
"""

from __future__ import annotations

import getpass
import logging
import os
import re
from typing import BinaryIO, NamedTuple

from PyQt6.QtCore import QObject, QProcess, QSocketNotifier, pyqtSignal

LOG = logging.getLogger(__name__)

#: The kernel's mount table, as this process sees it.
MOUNTS_FILE = "/proc/self/mounts"

#: Where udisks2 mounts the sticks (in a folder of the user's, or straight in it).
MEDIA_DIR = "/media"

#: udisks2's command line: unmounts and powers off a stick for the user.
UDISKSCTL = "udisksctl"
UDISKSCTL_UNMOUNT = "unmount"
UDISKSCTL_POWER_OFF = "power-off"
#: never ask for a password (there is no one to type it): fail instead
UDISKSCTL_NO_INTERACTION = "--no-user-interaction"
#: the block device to act on follows
UDISKSCTL_BLOCK_DEVICE = "-b"

# a line of the mount table: "<device> <mount point> <type> <options> <dump> <pass>"
_DEVICE_FIELD = 0
_MOUNT_POINT_FIELD = 1

#: How the mount table writes what would break its fields: a space as \040,
#: a tab as \011, a newline as \012, a backslash as \134 (octal, all ASCII).
_MOUNT_ESCAPE = re.compile(r"\\([0-7]{3})")


class Drive(NamedTuple):
    name: str     # the folder it is mounted as (its label)
    path: str     # where it is mounted
    device: str   # what is mounted there (/dev/sda1)


def _unescape_mount_path(path: str) -> str:
    """A path as the mount table writes it, its escapes undone."""
    return _MOUNT_ESCAPE.sub(lambda m: chr(int(m.group(1), 8)), path)


def media_dirs() -> frozenset[str]:
    """The folders udisks2 mounts the sticks in: /media/<user>, /media."""
    try:
        username = getpass.getuser()
    except (OSError, KeyError):  # no login name, nor a passwd entry
        username = ""
    if not username:
        return frozenset((MEDIA_DIR,))
    return frozenset((os.path.join(MEDIA_DIR, username), MEDIA_DIR))


def parse_drives(mounts_text: str, parents: frozenset[str] | tuple[str, ...]) -> dict[str, Drive]:
    """The drives of a mount table (/proc/mounts' text): what is mounted
    straight in one of ``parents``, by name, the first of a name kept."""
    drives: dict[str, Drive] = {}
    for line in mounts_text.splitlines():
        fields = line.split()
        if len(fields) <= _MOUNT_POINT_FIELD:
            continue
        # most of the table (/, /proc, /sys, ...) is not under /media: no unescaping it
        if not fields[_MOUNT_POINT_FIELD].startswith(MEDIA_DIR):
            continue
        path = _unescape_mount_path(fields[_MOUNT_POINT_FIELD])
        parent_dir, name = os.path.split(path)
        if name and parent_dir in parents and name not in drives:
            drives[name] = Drive(name, path, fields[_DEVICE_FIELD])
    return drives


def _udisksctl_args(action: str, device: str) -> list[str]:
    """udisksctl's arguments to ``action`` (unmount, power-off) the block ``device``."""
    return [action, UDISKSCTL_NO_INTERACTION, UDISKSCTL_BLOCK_DEVICE, device]


class RemovableDrivesRepository(QObject):
    """
    Signals
    -------
    driveConnected(name, path)    — a drive was mounted
    driveDisconnected(name, path) — a drive is no longer mounted
    unmountingChanged()           — is_unmounting changed
    driveUnmounted(name)          — unmount(name) is done: the stick can be pulled out
    unmountFailed(name, message)  — unmount(name) could not (busy, not allowed, ...)
    """

    driveConnected = pyqtSignal(str, str, arguments=["name", "path"])
    driveDisconnected = pyqtSignal(str, str, arguments=["name", "path"])
    unmountingChanged = pyqtSignal()
    driveUnmounted = pyqtSignal(str, arguments=["name"])
    unmountFailed = pyqtSignal(str, str, arguments=["name", "message"])

    def __init__(self, mounts_file: str = MOUNTS_FILE,
                 parents: frozenset[str] | tuple[str, ...] | None = None, parent=None):
        super().__init__(parent)
        self._mounts_file = mounts_file
        self._parents = frozenset(parents) if parents else media_dirs()
        self._unmounting: QProcess | None = None
        self._mounts: BinaryIO | None = None
        self._notifier: QSocketNotifier | None = None
        try:
            self._mounts = open(mounts_file, "rb")
        except OSError as exc:
            LOG.error("drives will not be seen: %s: %s", mounts_file, exc)
        else:
            self._notifier = QSocketNotifier(self._mounts.fileno(), QSocketNotifier.Type.Exception, self)
            self._notifier.activated.connect(self._refresh)
        self._drives: dict[str, Drive] = {}  # what _read keeps when the table cannot be read
        self._drives = self._read()

    @property
    def drives(self) -> list[Drive]:
        """The drives mounted now."""
        return list(self._drives.values())

    def _read(self) -> dict[str, Drive]:
        if self._mounts is None:
            return {}
        try:
            # read to its end: what clears the notification
            self._mounts.seek(0)
            text = os.fsdecode(self._mounts.read())
        except OSError as exc:
            LOG.error("could not read %s: %s", self._mounts_file, exc)
            return dict(self._drives)
        return parse_drives(text, self._parents)

    def _refresh(self, *_notifier_args) -> None:
        """Reads the mount table again and says which drives came and went."""
        before, self._drives = self._drives, self._read()
        # in the mount table's order (the order the browser shows them in)
        for name, drive in self._drives.items():
            if name in before:
                continue
            LOG.info("drive %s mounted at %s", name, drive.path)
            self.driveConnected.emit(name, drive.path)
        for name, drive in before.items():
            if name in self._drives:
                continue
            LOG.info("drive %s at %s gone", name, drive.path)
            self.driveDisconnected.emit(name, drive.path)

    # ── unmounting ─────────────────────────────────────────────────────────

    @property
    def is_unmounting(self) -> bool:
        return self._unmounting is not None

    def unmount(self, name: str) -> bool:
        """Unmounts the drive ``name``, then powers it off where it can, as a
        desktop's "Safely remove" does: driveUnmounted or unmountFailed when
        done; False when it cannot even start."""
        drive = self._drives.get(name)
        if self._unmounting is not None or drive is None:
            return False
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.finished.connect(lambda code, _status: self._on_unmounted(drive, process, code))
        process.errorOccurred.connect(lambda error: self._on_unmount_error(drive, process, error))
        self._unmounting = process
        LOG.info("unmounting %s (%s at %s)", name, drive.device, drive.path)
        process.start(UDISKSCTL, _udisksctl_args(UDISKSCTL_UNMOUNT, drive.device))
        self.unmountingChanged.emit()
        return True

    def _done_unmounting(self, process: QProcess) -> bool:
        if self._unmounting is not process:
            return False
        self._unmounting = None
        process.deleteLater()
        self.unmountingChanged.emit()
        return True

    def _on_unmounted(self, drive: Drive, process: QProcess, code: int) -> None:
        output = bytes(process.readAll()).decode(errors="replace").strip()
        if not self._done_unmounting(process):
            return
        if code != 0:
            LOG.error("could not unmount %s: %s", drive.name, output)
            self.unmountFailed.emit(drive.name, output or f"{UDISKSCTL} exited with {code}")
            return
        LOG.info("%s unmounted", drive.name)
        # the stick itself off too, where udisks can: a failure here (another
        # partition still mounted, a card reader) leaves it unmounted all the same
        QProcess.startDetached(UDISKSCTL, _udisksctl_args(UDISKSCTL_POWER_OFF, drive.device))
        # the mount table may not have been read yet: the drive is gone now
        self._refresh()
        self.driveUnmounted.emit(drive.name)

    def _on_unmount_error(self, drive: Drive, process: QProcess, error: QProcess.ProcessError) -> None:
        # any other error (a crash, ...) still ends in finished
        if error != QProcess.ProcessError.FailedToStart or not self._done_unmounting(process):
            return
        LOG.error("could not start %s to unmount %s", UDISKSCTL, drive.name)
        self.unmountFailed.emit(drive.name, f"{UDISKSCTL} could not be started")


_INSTANCE: RemovableDrivesRepository | None = None


def removable_drives_repository() -> RemovableDrivesRepository:
    """The shared RemovableDrivesRepository, built on first use."""
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = RemovableDrivesRepository()
    return _INSTANCE
