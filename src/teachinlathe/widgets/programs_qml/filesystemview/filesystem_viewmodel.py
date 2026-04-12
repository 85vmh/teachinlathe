import os
import re
import shutil
from PyQt5.QtCore import (
    QFileSystemWatcher, QObject, QThread,
    pyqtProperty, pyqtSignal, pyqtSlot,
)
from PyQt5.QtWidgets import QMessageBox

from teachinlathe.date_utils import format_recent_timestamp

from .data_types import FileSystemEntry, FileSystemLocation, LocationType
from .usb_monitor import UsbDriveMonitor

GCODE_EXTENSIONS = ('.ngc', '.nc', '.gcode', '.G', '.NGC', '.NC')
PROGRAM_HEADER_RE = re.compile(r"^\s*\(\s*Program:\s*(?P<program>.*?)\s*\)\s*$")


class _CopyWorker(QThread):
    progressChanged = pyqtSignal(float)
    succeeded = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, source: str, dest_dir: str, parent=None):
        super().__init__(parent)
        self._source = source
        self._dest_dir = dest_dir

    def run(self) -> None:
        import time
        try:
            start = time.monotonic()
            name = os.path.basename(self._source)
            dest = os.path.join(self._dest_dir, name)
            self.progressChanged.emit(0.1)
            if os.path.isfile(self._source):
                shutil.copy2(self._source, dest)
            else:
                shutil.copytree(self._source, dest, dirs_exist_ok=True)
            self.progressChanged.emit(0.9)
            elapsed = time.monotonic() - start
            remaining = max(0.0, 0.3 - elapsed)
            if remaining > 0:
                time.sleep(remaining)
            self.progressChanged.emit(1.0)
            time.sleep(0.05)
            self.succeeded.emit(dest)
        except Exception as exc:
            self.failed.emit(str(exc))


def _format_size(entry: FileSystemEntry) -> str:
    if entry.is_up:
        return ""
    if entry.is_dir:
        n = entry.item_count
        return f"{n} item{'s' if n != 1 else ''}"
    b = entry.size_bytes
    if b < 1024:
        return f"{b} B"
    return f"{b / 1024:.1f} kB"


def _format_modified(entry: FileSystemEntry) -> str:
    if entry.is_up or entry.modified_timestamp == 0.0:
        return ""
    return format_recent_timestamp(entry.modified_timestamp)


class FileSystemViewModel(QObject):
    """
    Single source of truth for filesystem browsing in the Programs tab.

    Handles: predefined locations, USB drive detection (via inotify),
    directory listing with filtering/sorting, file selection, copy (with
    minimum 300 ms progress animation), and delete.

    Python consumers connect to:
      fileSelected(absolutePath)      — show file in editor pane
      fileOpenRequested(absolutePath) — load file into LinuxCNC
    """

    locationsChanged = pyqtSignal()
    entriesChanged = pyqtSignal()
    navigationChanged = pyqtSignal()
    selectionChanged = pyqtSignal()
    filterChanged = pyqtSignal()
    copyProgressChanged = pyqtSignal(float, arguments=["progress"])
    copyCompleted = pyqtSignal(str, arguments=["destinationPath"])
    copyFailed = pyqtSignal(str, arguments=["errorMessage"])
    fileSelected = pyqtSignal(str, arguments=["absolutePath"])
    fileOpenRequested = pyqtSignal(str, arguments=["absolutePath"])

    def __init__(self, locations: list, parent=None, json_folder_path: str = ""):
        """
        Parameters
        ----------
        locations : list[FileSystemLocation]
            Predefined locations in display order. The first one is selected
            on startup. The USB_STICK location is the copy destination.
        """
        super().__init__(parent)
        self._static: list[FileSystemLocation] = list(locations)
        self._mounted: list[FileSystemLocation] = []
        self._current_name: str = self._static[0].name if self._static else ""
        self._current_path: str = ""
        self._selected_path: str = ""
        self._show_folders: bool = True
        self._ngc_only: bool = True
        self._sort_col: str = "modified"
        self._sort_asc: bool = False
        self._is_copying: bool = False
        self._copy_progress: float = 0.0
        self._copy_worker: _CopyWorker | None = None
        self._json_folder_path = os.path.abspath(json_folder_path) if json_folder_path else ""

        self._usb_monitor = UsbDriveMonitor(self)
        self._usb_monitor.driveConnected.connect(self._on_drive_connected)
        self._usb_monitor.driveDisconnected.connect(self._on_drive_disconnected)
        for name, path in self._usb_monitor.mounted_drives:
            self._mounted.append(FileSystemLocation(name, path, LocationType.MOUNTED_MEDIA))

        self._dir_watcher = QFileSystemWatcher(self)
        self._dir_watcher.directoryChanged.connect(lambda _: self.entriesChanged.emit())
        self._watch_current()

    # ------------------------------------------------------------------
    # QML Properties
    # ------------------------------------------------------------------

    @pyqtProperty("QVariantList", notify=locationsChanged)
    def locations(self) -> list:
        at_root = self._current_path == ""
        result = []
        for loc in self._static:
            result.append({
                "name": loc.name,
                "type": loc.location_type.value,
                "isAvailable": os.path.isdir(loc.root_path),
                "isSelected": at_root and loc.name == self._current_name,
                "isMountedMedia": False,
            })
        for loc in self._mounted:
            result.append({
                "name": loc.name,
                "type": loc.location_type.value,
                "isAvailable": os.path.ismount(loc.root_path),
                "isSelected": at_root and loc.name == self._current_name,
                "isMountedMedia": True,
            })
        return result

    @pyqtProperty("QVariantList", notify=navigationChanged)
    def breadcrumbs(self) -> list:
        loc = self._location(self._current_name)
        if loc is None:
            return []
        segments = [{"name": loc.name, "path": ""}]
        if self._current_path:
            accumulated = ""
            for part in self._current_path.replace("\\", "/").split("/"):
                if not part:
                    continue
                accumulated = f"{accumulated}/{part}" if accumulated else part
                segments.append({"name": part, "path": accumulated})
        return segments

    @pyqtProperty("QVariantList", notify=entriesChanged)
    def entries(self) -> list:
        return self._build_entries()

    @pyqtProperty(str, notify=selectionChanged)
    def selectedEntryPath(self) -> str:
        return self._selected_path

    @pyqtProperty(bool, notify=selectionChanged)
    def selectedIsFile(self) -> bool:
        if not self._selected_path:
            return False
        loc = self._current_location()
        if loc is None:
            return False
        abs_path = self._resolve(loc.root_path, self._selected_path)
        return abs_path is not None and os.path.isfile(abs_path)

    @pyqtProperty(str, notify=navigationChanged)
    def currentLocationName(self) -> str:
        return self._current_name

    @pyqtProperty(bool, notify=navigationChanged)
    def canNavigateUp(self) -> bool:
        return bool(self._current_path)

    @pyqtProperty(bool, notify=navigationChanged)
    def isInMountedMedia(self) -> bool:
        loc = self._current_location()
        return loc is not None and loc.location_type == LocationType.MOUNTED_MEDIA

    @pyqtProperty(bool, notify=navigationChanged)
    def isInGeneratedPrograms(self) -> bool:
        loc = self._current_location()
        return loc is not None and loc.location_type == LocationType.GENERATED

    @pyqtProperty(str, notify=selectionChanged)
    def selectedGeneratedJsonPath(self) -> str:
        return self._selected_generated_json_path()

    @pyqtProperty(bool, notify=selectionChanged)
    def canEditSelectedGeneratedProgram(self) -> bool:
        return bool(self._selected_generated_json_path())

    @pyqtProperty(bool, notify=filterChanged)
    def showFolders(self) -> bool:
        return self._show_folders

    @pyqtProperty(bool, notify=filterChanged)
    def ngcOnly(self) -> bool:
        return self._ngc_only

    @pyqtProperty(str, notify=filterChanged)
    def sortColumn(self) -> str:
        return self._sort_col

    @pyqtProperty(bool, notify=filterChanged)
    def sortAscending(self) -> bool:
        return self._sort_asc

    @pyqtProperty(bool, notify=copyProgressChanged)
    def isCopying(self) -> bool:
        return self._is_copying

    @pyqtProperty(float, notify=copyProgressChanged)
    def copyProgress(self) -> float:
        return self._copy_progress

    # ------------------------------------------------------------------
    # Slots — Navigation
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def selectLocation(self, name: str) -> None:
        if self._current_name == name and self._current_path == "":
            return
        self._current_name = name
        self._current_path = ""
        self._selected_path = ""
        self._watch_current()
        self.navigationChanged.emit()
        self.entriesChanged.emit()
        self.selectionChanged.emit()
        self.locationsChanged.emit()

    @pyqtSlot(str)
    def navigateInto(self, relative_path: str) -> None:
        loc = self._current_location()
        if loc is None:
            return
        abs_path = self._resolve(loc.root_path, relative_path)
        if abs_path is None or not os.path.isdir(abs_path):
            return
        self._current_path = relative_path
        self._selected_path = ""
        self._watch_current()
        self.navigationChanged.emit()
        self.entriesChanged.emit()
        self.selectionChanged.emit()
        self.locationsChanged.emit()

    @pyqtSlot()
    def navigateUp(self) -> None:
        if not self._current_path:
            return
        parent = os.path.dirname(self._current_path)
        self._current_path = "" if parent in ("", ".") else parent
        self._selected_path = ""
        self._watch_current()
        self.navigationChanged.emit()
        self.entriesChanged.emit()
        self.selectionChanged.emit()
        self.locationsChanged.emit()

    @pyqtSlot(str)
    def navigateToBreadcrumb(self, path: str) -> None:
        loc = self._current_location()
        if loc is None:
            return
        if path != "" and self._resolve(loc.root_path, path) is None:
            return
        self._current_path = path
        self._selected_path = ""
        self._watch_current()
        self.navigationChanged.emit()
        self.entriesChanged.emit()
        self.selectionChanged.emit()
        self.locationsChanged.emit()

    # ------------------------------------------------------------------
    # Slots — Selection & File Actions
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def selectEntry(self, relative_path: str) -> None:
        loc = self._current_location()
        if loc is None:
            return
        abs_path = self._resolve(loc.root_path, relative_path)
        if abs_path is None:
            return
        if os.path.isdir(abs_path):
            self.navigateInto(relative_path)
            return
        if os.path.isfile(abs_path):
            self._selected_path = relative_path
            self.selectionChanged.emit()
            self.entriesChanged.emit()
            self.fileSelected.emit(abs_path)

    @pyqtSlot()
    def openSelectedFile(self) -> None:
        if not self._selected_path:
            return
        loc = self._current_location()
        if loc is None or loc.location_type == LocationType.MOUNTED_MEDIA:
            return
        abs_path = self._resolve(loc.root_path, self._selected_path)
        if abs_path and os.path.isfile(abs_path):
            self.fileOpenRequested.emit(abs_path)

    @pyqtSlot()
    def deleteSelected(self) -> None:
        if not self._selected_path:
            return
        loc = self._current_location()
        if loc is None or loc.location_type == LocationType.MOUNTED_MEDIA:
            return
        abs_path = self._resolve(loc.root_path, self._selected_path)
        if abs_path is None:
            return
        answer = QMessageBox.question(
            None, "Delete",
            f"Delete '{os.path.basename(abs_path)}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            if os.path.isfile(abs_path):
                os.remove(abs_path)
            else:
                shutil.rmtree(abs_path)
        except Exception as exc:
            QMessageBox.critical(None, "Delete failed", str(exc))
            return
        self._selected_path = ""
        self.selectionChanged.emit()
        self.entriesChanged.emit()

    @pyqtSlot()
    def copySelectedToUsbStickPrograms(self) -> None:
        if not self._selected_path or self._is_copying:
            return
        loc = self._current_location()
        if loc is None or loc.location_type != LocationType.MOUNTED_MEDIA:
            return
        source = self._resolve(loc.root_path, self._selected_path)
        if source is None or not os.path.exists(source):
            return
        dest_loc = next(
            (l for l in self._static if l.location_type == LocationType.USB_STICK), None
        )
        if dest_loc is None:
            return
        os.makedirs(dest_loc.root_path, exist_ok=True)
        self._is_copying = True
        self._copy_progress = 0.0
        self.copyProgressChanged.emit(0.0)
        self._copy_worker = _CopyWorker(source, dest_loc.root_path, self)
        self._copy_worker.progressChanged.connect(self._on_copy_progress)
        self._copy_worker.succeeded.connect(self._on_copy_done)
        self._copy_worker.failed.connect(self._on_copy_error)
        self._copy_worker.start()

    # ------------------------------------------------------------------
    # Slots — Filter & Sort
    # ------------------------------------------------------------------

    @pyqtSlot(bool)
    def setShowFolders(self, show: bool) -> None:
        if self._show_folders == show:
            return
        self._show_folders = show
        self.filterChanged.emit()
        self.entriesChanged.emit()

    @pyqtSlot(bool)
    def setNgcOnly(self, ngc_only: bool) -> None:
        if self._ngc_only == ngc_only:
            return
        self._ngc_only = ngc_only
        self.filterChanged.emit()
        self.entriesChanged.emit()

    @pyqtSlot(str)
    def setSortColumn(self, column: str) -> None:
        if column not in ("name", "size", "modified"):
            return
        if self._sort_col == column:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = column
            self._sort_asc = (column == "name")
        self.filterChanged.emit()
        self.entriesChanged.emit()

    @pyqtSlot()
    def selectGeneratedProgramsFolder(self) -> None:
        """Navigate to Generated Programs — called after a conversational export."""
        for loc in self._static:
            if loc.location_type == LocationType.GENERATED:
                self.selectLocation(loc.name)
                return

    @pyqtSlot(str)
    def showFileInGeneratedPrograms(self, abs_path: str) -> None:
        """Navigate to Generated Programs, select and show the given file in the editor."""
        self.selectGeneratedProgramsFolder()
        if not abs_path or not os.path.isfile(abs_path):
            return
        rel = os.path.basename(abs_path)
        self._selected_path = rel
        self.selectionChanged.emit()
        self.entriesChanged.emit()
        self.fileSelected.emit(abs_path)

    @pyqtSlot(result=str)
    def selectedGeneratedJsonPathForEdit(self) -> str:
        return self._selected_generated_json_path()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _location(self, name: str) -> FileSystemLocation | None:
        for loc in self._static + self._mounted:
            if loc.name == name:
                return loc
        return None

    def _current_location(self) -> FileSystemLocation | None:
        return self._location(self._current_name)

    def _resolve(self, base: str, relative: str) -> str | None:
        abs_base = os.path.abspath(base)
        if not relative:
            return abs_base
        target = os.path.abspath(os.path.join(abs_base, relative))
        try:
            if os.path.commonpath([abs_base, target]) == abs_base:
                return target
        except ValueError:
            pass
        return None

    def _selected_absolute_path(self) -> str | None:
        if not self._selected_path:
            return None
        loc = self._current_location()
        if loc is None:
            return None
        return self._resolve(loc.root_path, self._selected_path)

    def _generated_json_root(self) -> str:
        if self._json_folder_path:
            return self._json_folder_path
        generated = next((loc for loc in self._static if loc.location_type == LocationType.GENERATED), None)
        if generated is None:
            return ""
        return os.path.join(os.path.dirname(os.path.abspath(generated.root_path)), "Conversational Json")

    def _read_generated_program_json_name(self, ngc_path: str) -> str:
        try:
            with open(ngc_path, "r", encoding="utf-8", errors="replace") as handle:
                for _ in range(20):
                    line = handle.readline()
                    if not line:
                        break
                    match = PROGRAM_HEADER_RE.match(line.strip())
                    if match:
                        return match.group("program").strip()
        except OSError:
            return ""
        return ""

    def _selected_generated_json_path(self) -> str:
        loc = self._current_location()
        if loc is None or loc.location_type != LocationType.GENERATED:
            return ""
        ngc_path = self._selected_absolute_path()
        if not ngc_path or not os.path.isfile(ngc_path) or not ngc_path.lower().endswith(".ngc"):
            return ""
        json_name = self._read_generated_program_json_name(ngc_path)
        if not json_name:
            return ""
        json_name = os.path.basename(json_name)
        if not json_name.lower().endswith(".json"):
            return ""
        json_root = self._generated_json_root()
        if not json_root:
            return ""
        json_path = os.path.abspath(os.path.join(json_root, json_name))
        if os.path.commonpath([os.path.abspath(json_root), json_path]) != os.path.abspath(json_root):
            return ""
        return json_path if os.path.isfile(json_path) else ""

    def _watch_current(self) -> None:
        if self._dir_watcher.directories():
            self._dir_watcher.removePaths(self._dir_watcher.directories())
        loc = self._current_location()
        if loc is None:
            return
        target = self._resolve(loc.root_path, self._current_path)
        if target and os.path.isdir(target):
            self._dir_watcher.addPath(target)

    def _count_items(self, abs_dir: str) -> int:
        count = 0
        try:
            for name in os.listdir(abs_dir):
                full = os.path.join(abs_dir, name)
                if os.path.isdir(full) or (
                    os.path.isfile(full) and name.endswith(GCODE_EXTENSIONS)
                ):
                    count += 1
        except OSError:
            pass
        return count

    def _scan(self, abs_dir: str) -> list:
        raw: list[FileSystemEntry] = []
        try:
            names = os.listdir(abs_dir)
        except OSError:
            return raw
        for name in names:
            if name.startswith("."):
                continue
            full = os.path.join(abs_dir, name)
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.join(self._current_path, name) if self._current_path else name
            if os.path.isdir(full):
                if not self._show_folders:
                    continue
                raw.append(FileSystemEntry(
                    name=name,
                    relative_path=rel,
                    absolute_path=full,
                    is_dir=True,
                    is_up=False,
                    size_bytes=0,
                    item_count=self._count_items(full),
                    modified_timestamp=st.st_mtime,
                ))
            elif os.path.isfile(full):
                if self._ngc_only and not name.endswith(GCODE_EXTENSIONS):
                    continue
                raw.append(FileSystemEntry(
                    name=name,
                    relative_path=rel,
                    absolute_path=full,
                    is_dir=False,
                    is_up=False,
                    size_bytes=st.st_size,
                    item_count=0,
                    modified_timestamp=st.st_mtime,
                ))
        return raw

    def _build_entries(self) -> list:
        loc = self._current_location()
        if loc is None:
            return []
        abs_dir = self._resolve(loc.root_path, self._current_path)
        if not abs_dir or not os.path.isdir(abs_dir):
            return []

        raw = self._scan(abs_dir)

        def sort_key(e: FileSystemEntry):
            if self._sort_col == "name":
                return e.name.lower()
            if self._sort_col == "size":
                return e.item_count if e.is_dir else e.size_bytes
            return e.modified_timestamp

        raw.sort(key=sort_key, reverse=not self._sort_asc)

        result = []
        if self._current_path:
            parent = os.path.dirname(self._current_path)
            parent = "" if parent in ("", ".") else parent
            up = FileSystemEntry(
                name="..",
                relative_path=parent,
                absolute_path=self._resolve(loc.root_path, parent) or loc.root_path,
                is_dir=True,
                is_up=True,
                size_bytes=0,
                item_count=0,
                modified_timestamp=0.0,
            )
            result.append(self._to_dict(up))
        for e in raw:
            result.append(self._to_dict(e))
        return result

    def _to_dict(self, e: FileSystemEntry) -> dict:
        return {
            "name": e.name,
            "relativePath": e.relative_path,
            "absolutePath": e.absolute_path,
            "isDir": e.is_dir,
            "isUp": e.is_up,
            "sizeDisplay": _format_size(e),
            "modifiedDisplay": _format_modified(e),
            "modifiedTimestamp": e.modified_timestamp,
            "isSelected": (not e.is_up) and e.relative_path == self._selected_path,
        }

    def _on_drive_connected(self, name: str, path: str) -> None:
        if any(l.name == name for l in self._mounted):
            return
        self._mounted.append(FileSystemLocation(name, path, LocationType.MOUNTED_MEDIA))
        self.locationsChanged.emit()

    def _on_drive_disconnected(self, name: str, _path: str) -> None:
        self._mounted = [l for l in self._mounted if l.name != name]
        if self._current_name == name and self._static:
            self._current_name = self._static[0].name
            self._current_path = ""
            self._selected_path = ""
            self._watch_current()
            self.navigationChanged.emit()
            self.entriesChanged.emit()
        self.locationsChanged.emit()

    def _on_copy_progress(self, p: float) -> None:
        self._copy_progress = p
        self.copyProgressChanged.emit(p)

    def _on_copy_done(self, dest_path: str) -> None:
        self._is_copying = False
        self._copy_progress = 0.0
        self._copy_worker = None
        self.copyProgressChanged.emit(0.0)
        dest_loc = next(
            (l for l in self._static if l.location_type == LocationType.USB_STICK), None
        )
        if dest_loc:
            self._current_name = dest_loc.name
            self._current_path = ""
            self._selected_path = os.path.basename(dest_path)
            self._watch_current()
            self.navigationChanged.emit()
            self.locationsChanged.emit()
            self.entriesChanged.emit()
            self.selectionChanged.emit()
        self.copyCompleted.emit(dest_path)

    def _on_copy_error(self, msg: str) -> None:
        self._is_copying = False
        self._copy_progress = 0.0
        self._copy_worker = None
        self.copyProgressChanged.emit(0.0)
        self.copyFailed.emit(msg)
        QMessageBox.critical(None, "Copy failed", msg)
