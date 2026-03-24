import os

from PyQt5.QtCore import QFileSystemWatcher, QObject, pyqtSignal


class UsbDriveMonitor(QObject):
    """
    Watches /media and /media/<user> for mounted USB drives using Qt's
    inotify wrapper (QFileSystemWatcher).

    Signals
    -------
    driveConnected(name, path)    — a new mount point appeared
    driveDisconnected(name, path) — an existing mount point disappeared
    """

    driveConnected = pyqtSignal(str, str, arguments=["name", "path"])
    driveDisconnected = pyqtSignal(str, str, arguments=["name", "path"])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._known: dict[str, str] = {}

        username = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
        self._user_media = os.path.join("/media", username) if username else "/media"

        for path in ("/media", self._user_media):
            if os.path.isdir(path):
                self._watcher.addPath(path)

        self._watcher.directoryChanged.connect(self._on_changed)
        self._scan()

    @property
    def mounted_drives(self) -> list:
        """Returns list of (name, path) tuples for currently mounted drives."""
        return list(self._known.items())

    def _scan(self) -> None:
        found: dict[str, str] = {}
        for base in ("/media", self._user_media):
            if not os.path.isdir(base):
                continue
            try:
                for name in os.listdir(base):
                    full = os.path.join(base, name)
                    if os.path.ismount(full) and name not in found:
                        found[name] = full
            except OSError:
                pass
        self._known = found

    def _on_changed(self, _path: str) -> None:
        prev = dict(self._known)
        self._scan()
        for name, path in self._known.items():
            if name not in prev:
                self._watcher.addPath(path)
                self.driveConnected.emit(name, path)
        for name, path in prev.items():
            if name not in self._known:
                self.driveDisconnected.emit(name, path)