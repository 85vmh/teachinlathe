import logging
import os
import re
import shutil
import stat
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt6.QtCore import (
    QCoreApplication, QFileSystemWatcher, QObject, QThread, QTimer,
    pyqtProperty, pyqtSignal, pyqtSlot,
)

from teachinlathe.core.date_utils import format_recent_timestamp

from .data_types import FileSystemEntry, FileSystemLocation, LocationType

LOG = logging.getLogger(__name__)

GCODE_EXTENSIONS = ('.ngc', '.nc', '.gcode', '.G', '.NGC', '.NC')
PROGRAM_HEADER_RE = re.compile(r"^\s*\(\s*Program:\s*(?P<program>.*?)\s*\)\s*$")

#: how long the list waits for more folder counts before it is shown again
COUNTS_SHOWN_EVERY_MS = 250

#: how many folders are counted at once
COUNTING_THREADS = 4

#: how long quitting waits for each folder count still running
COUNT_WORKER_QUIT_WAIT_MS = 2000

#: The image a row shows before its name, by the file's extension (ui/common/images);
#: any other file is a program.
FILE_ICONS = {".dxf": "dxf_file.svg"}
PROGRAM_ICON = "gcode.png"
FOLDER_ICON = "folder-icon.svg"
UP_ICON = "folder_parent.svg"


#: A folder's item_count before it is read (_list_dir reads it once the folder is shown).
ITEM_COUNT_UNREAD = -1


def _hidden(name: str) -> bool:
    return name.startswith(".")


def _matches(name: str, extensions: tuple) -> bool:
    """A file of one of ``extensions`` (lower case), not hidden."""
    return not _hidden(name) and name.lower().endswith(extensions)


def count_matching_files(abs_dir: str, extensions: tuple, stop=lambda: False) -> dict:
    """How many files ending in one of ``extensions`` each folder holds, at any
    depth: ``abs_dir`` and every folder under it (hidden ones left out), in one
    walk. Returns what it has counted when ``stop()`` turns true."""
    own: dict[str, int] = {}
    children: dict[str, list] = {}
    for root, dirs, files in os.walk(abs_dir):
        if stop():
            break
        dirs[:] = [name for name in dirs if not _hidden(name)]
        children[root] = [os.path.join(root, name) for name in dirs]
        own[root] = sum(1 for name in files if _matches(name, extensions))
    counts: dict[str, int] = {}
    # the deepest folders first, so that every child is summed before its parent
    for folder in sorted(own, key=lambda p: p.count(os.sep), reverse=True):
        counts[folder] = own[folder] + sum(counts.get(c, 0) for c in children[folder])
    return counts


class _CountWorker(QThread):
    """Counts the matching files under some folders, away from the GUI thread
    (a stick's first walk takes seconds): COUNTING_THREADS folders at a time,
    so that a small one is not left waiting behind a big one; one ``counted``
    for each folder, as it is done."""
    counted = pyqtSignal(int, object)   # generation, {folder: count}

    def __init__(self, generation: int, folders: list, extensions: tuple, parent=None):
        super().__init__(parent)
        self._generation = generation
        self._folders = folders
        self._extensions = extensions

    def run(self) -> None:
        stop = self.isInterruptionRequested
        with ThreadPoolExecutor(max_workers=COUNTING_THREADS) as pool:
            pending = [pool.submit(count_matching_files, folder, self._extensions, stop)
                       for folder in self._folders]
            # emitted from here, the worker's own thread, as each finishes
            for done in as_completed(pending):
                if stop():
                    for future in pending:
                        future.cancel()
                    return
                self.counted.emit(self._generation, done.result())


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


def _icon(entry: FileSystemEntry) -> str:
    """The image a row shows before its name (ui/common/images)."""
    if entry.is_up:
        return UP_ICON
    if entry.is_dir:
        return FOLDER_ICON
    return FILE_ICONS.get(os.path.splitext(entry.name)[1].lower(), PROGRAM_ICON)


def _drive_location(name: str, path: str) -> FileSystemLocation:
    """A mounted drive: browsed folder by folder."""
    return FileSystemLocation(name, path, LocationType.MOUNTED_MEDIA, browses_folders=True)


def _format_modified(entry: FileSystemEntry) -> str:
    if entry.is_up or entry.modified_timestamp == 0.0:
        return ""
    return format_recent_timestamp(entry.modified_timestamp)


class FileSystemViewModel(QObject):
    """
    Single source of truth for filesystem browsing in the Programs tab.

    Handles: predefined locations, the mounted drives (RemovableDrivesRepository) and their unmounting,
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
    deleteFailed = pyqtSignal(str, arguments=["errorMessage"])
    fileSelected = pyqtSignal(str, arguments=["absolutePath"])
    fileOpenRequested = pyqtSignal(str, arguments=["absolutePath"])
    unmountingChanged = pyqtSignal()
    #: an Unmount asked for here is done, or could not be: what to tell
    unmountReported = pyqtSignal(str, arguments=["message"])

    def __init__(
        self,
        locations: list,
        parent=None,
        json_folder_path: str = "",
        file_extensions: tuple[str, ...] | None = None,
        file_filter_label: str = "NGC",
        allow_file_filter_toggle: bool = True,
        show_folders: bool = True,
        prefers_mounted_media: bool = False,
        show_recursive_folder_file_counts: bool = False,
        hides_empty_folders: bool = False,
        drives_tab: str = "",
        drives=None,
    ):
        """
        Parameters
        ----------
        locations : list[FileSystemLocation]
            Predefined locations in display order. The first one is selected
            on startup. The USB_STICK location is the copy destination.
        prefers_mounted_media : bool
            A drive is shown as it comes, and first when the browser starts
            or is rescanned; gone, the first location is shown again.
        show_recursive_folder_file_counts : bool
            Each folder says how many matching files it holds, at any depth.
        hides_empty_folders : bool
            A folder with no matching file at any depth is not listed (they
            are counted for it).
        drives_tab : str
            The drives shown as one tab of this name, there with none mounted
            (disabled), showing the first drive mounted; "": a tab per drive,
            each named after it, as they come.
        drives : RemovableDrivesRepository
            The mounted sticks (the app's one, by default).
        """
        super().__init__(parent)
        self._static: list[FileSystemLocation] = list(locations)
        self._mounted: list[FileSystemLocation] = []
        self._current_name: str = self._static[0].name if self._static else ""
        self._current_path: str = ""
        self._selected_path: str = ""
        self._show_folders: bool = bool(show_folders)
        self._ngc_only: bool = True
        self._file_extensions = tuple(ext.lower() for ext in (file_extensions or GCODE_EXTENSIONS))
        self._file_filter_label = file_filter_label or "Files"
        self._allow_file_filter_toggle = bool(allow_file_filter_toggle)
        self._prefers_mounted_media = bool(prefers_mounted_media)
        self._show_recursive_folder_file_counts = bool(show_recursive_folder_file_counts)
        self._hides_empty_folders = bool(hides_empty_folders)
        self._drives_tab = str(drives_tab or "")
        self._counts_folders = self._show_recursive_folder_file_counts or self._hides_empty_folders
        # the drive an Unmount was asked for here, until it is done or fails
        self._unmounting_name: str | None = None
        self._unmount_started = False
        # the folder shown as it was last read (_list_dir), until it changes:
        # the counts coming in show the list again without reading it again
        self._listing_dir: str | None = None
        self._listing: list[FileSystemEntry] = []
        self._sort_col: str = "modified"
        self._sort_asc: bool = False
        self._is_copying: bool = False
        self._copy_progress: float = 0.0
        self._copy_worker: _CopyWorker | None = None
        self._json_folder_path = os.path.abspath(json_folder_path) if json_folder_path else ""
        # how many matching files each folder holds, at any depth: counted on
        # a worker thread (a stick's first walk takes seconds), each folder
        # once, until something changes (a drive comes or goes, a watched
        # folder changes). The list shows a folder not counted yet, and is
        # shown again as the counts come in.
        self._matching_counts: dict[str, int] = {}
        self._counts_pending: set[str] = set()
        self._counts_generation = 0
        self._count_workers: list[_CountWorker] = []
        self._counts_shown = QTimer(self)
        self._counts_shown.setSingleShot(True)
        self._counts_shown.setInterval(COUNTS_SHOWN_EVERY_MS)
        self._counts_shown.timeout.connect(self.entriesChanged.emit)
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._stop_counting)

        if drives is None:
            from teachinlathe.core.removable_drives_repository import removable_drives_repository
            drives = removable_drives_repository()
        self._drives = drives
        self._drives.driveConnected.connect(self._on_drive_connected)
        self._drives.driveDisconnected.connect(self._on_drive_disconnected)
        self._drives.driveUnmounted.connect(self._on_drive_unmounted)
        self._drives.unmountFailed.connect(self._on_unmount_failed)
        # another browser's Unmount, too
        self._drives.unmountingChanged.connect(self.unmountingChanged)
        # canUnmount follows the location shown
        self.navigationChanged.connect(self.unmountingChanged)
        self.locationsChanged.connect(self.unmountingChanged)
        for drive in self._drives.drives:
            self._mounted.append(_drive_location(drive.name, drive.path))
        if self._prefers_mounted_media and self._mounted:
            self._current_name = self._mounted[0].name

        self._dir_watcher = QFileSystemWatcher(self)
        self._dir_watcher.directoryChanged.connect(self._on_directory_changed)
        self._watch_current()

    # ------------------------------------------------------------------
    # QML Properties
    # ------------------------------------------------------------------

    @pyqtProperty("QVariantList", notify=locationsChanged)
    def locations(self) -> list:
        def entry(name, available, selected, mounted, location_type):
            return {"name": name, "type": location_type.value, "isAvailable": available,
                    "isSelected": selected, "isMountedMedia": mounted}

        result = [entry(loc.name, os.path.isdir(loc.root_path), loc.name == self._current_name,
                        False, loc.location_type)
                  for loc in self._static]
        if self._drives_tab:
            # the first drive mounted, under the tab's name; none: disabled
            result.append(entry(self._drives_tab, bool(self._mounted), self._in_mounted_media(),
                                True, LocationType.MOUNTED_MEDIA))
        else:
            result += [entry(loc.name, os.path.ismount(loc.root_path), loc.name == self._current_name,
                             True, loc.location_type)
                       for loc in self._mounted]
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

    @pyqtProperty(str, notify=selectionChanged)
    def selectedAbsolutePath(self) -> str:
        return self._selected_absolute_path() or ""

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

    @pyqtProperty(bool, notify=unmountingChanged)
    def canUnmount(self) -> bool:
        """An Unmount is offered: a drive is shown and none is being
        unmounted."""
        return self._unmount_target() is not None and not self._is_unmounting()

    def _is_unmounting(self) -> bool:
        # asked for here (waiting for the counts to stop), or by any browser
        return self._unmounting_name is not None or self._drives.is_unmounting

    @pyqtSlot()
    def unmountCurrentDrive(self) -> None:
        """Unmounts the drive shown, so that it can be pulled out, once the
        folder counts walking it have stopped - nothing waits for them:
        unmountReported(message) when done or not."""
        loc = self._unmount_target()
        if loc is None or self._is_unmounting():
            return
        self._unmounting_name = loc.name
        self._unmount_started = False
        self._forget_counts(under=loc.root_path)
        self.unmountingChanged.emit()
        self._unmount_when_not_counting()

    def _unmount_when_not_counting(self) -> None:
        name = self._unmounting_name
        if name is None or self._unmount_started or self._count_workers:
            return
        self._unmount_started = True
        if not self._drives.unmount(name):
            self._unmount_done(f'"{name}" could not be unmounted.')

    def _unmount_done(self, message: str) -> None:
        self._unmounting_name = None
        self.unmountingChanged.emit()
        self.unmountReported.emit(message)

    def _unmount_target(self) -> FileSystemLocation | None:
        return self._current_location() if self._in_mounted_media() else None

    def _on_drive_unmounted(self, name: str) -> None:
        if name == self._unmounting_name:
            self._unmount_done(f'You can now remove your "{name}" Usb Stick')

    def _on_unmount_failed(self, name: str, message: str) -> None:
        if name == self._unmounting_name:
            self.entriesChanged.emit()
            self._unmount_done(f'"{name}" could not be unmounted: {message}')

    @pyqtProperty(bool, notify=navigationChanged)
    def isInMountedMedia(self) -> bool:
        return self._in_mounted_media()

    def _in_mounted_media(self) -> bool:
        loc = self._current_location()
        return loc is not None and loc.location_type == LocationType.MOUNTED_MEDIA

    @pyqtProperty(bool, notify=navigationChanged)
    def browsesFolders(self) -> bool:
        """The location shown is browsed folder by folder, with the path and
        the Folders / file-type filters (FileSystemLocation.browses_folders);
        otherwise it is the root of a folder of files, shown as they are."""
        return self._browses_folders()

    def _browses_folders(self) -> bool:
        loc = self._current_location()
        return loc is not None and loc.browses_folders

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

    @pyqtProperty(bool, notify=filterChanged)
    def allFiltersOn(self) -> bool:
        """Every filter is on: the matching files alone, and the folders."""
        return self._ngc_only and self._show_folders

    @pyqtProperty(str, notify=filterChanged)
    def fileFilterLabel(self) -> str:
        return self._file_filter_label

    @pyqtProperty(bool, notify=filterChanged)
    def allowFileFilterToggle(self) -> bool:
        return self._allow_file_filter_toggle

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
        if self._drives_tab and name == self._drives_tab:
            if not self._mounted:
                return
            name = self._mounted[0].name
        if self._current_name == name and self._current_path == "":
            return
        self._go_to_root(name)
        self.locationsChanged.emit()

    def _go_to_root(self, name: str) -> None:
        """At the root of the location ``name``, with nothing selected
        (locationsChanged is the caller's)."""
        self._current_name = name
        self._go_to("")

    def _go_to(self, path: str, selected: str = "") -> None:
        """At ``path`` in the location shown, ``selected`` selected in it."""
        self._current_path = path
        self._selected_path = selected
        self._watch_current()
        self.navigationChanged.emit()
        self.entriesChanged.emit()
        self.selectionChanged.emit()

    @pyqtSlot()
    def rescan(self) -> None:
        """Starts afresh, as a screen showing it opens: the mounted drives
        looked for again, every folder counted again, at the root of the
        first drive (where drives are preferred) or of the location already there,
        with nothing selected."""
        self._forget_counts()
        name = self._current_name
        if self._prefers_mounted_media and self._mounted:
            name = self._mounted[0].name
        elif self._current_location() is None and self._static:
            name = self._static[0].name
        self._go_to_root(name)
        self.locationsChanged.emit()

    @pyqtSlot(str)
    def navigateInto(self, relative_path: str) -> None:
        loc = self._current_location()
        if loc is None:
            return
        abs_path = self._resolve(loc.root_path, relative_path)
        if abs_path is None or not os.path.isdir(abs_path):
            return
        self._go_to(relative_path)

    @pyqtSlot(str)
    def navigateToBreadcrumb(self, path: str) -> None:
        loc = self._current_location()
        if loc is None:
            return
        if path != "" and self._resolve(loc.root_path, path) is None:
            return
        self._go_to(path)

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
        self.deleteSelectedConfirmed()

    @pyqtSlot()
    def deleteSelectedConfirmed(self) -> None:
        if self._selected_path:
            self.deleteEntry(self._selected_path)

    @pyqtSlot(str)
    def deleteEntry(self, relative_path: str) -> None:
        """Delete the entry at ``relative_path`` in the current location, once
        the user has confirmed it. Nothing is deleted from mounted media."""
        if not relative_path:
            return
        loc = self._current_location()
        if loc is None or loc.location_type == LocationType.MOUNTED_MEDIA:
            return
        abs_path = self._resolve(loc.root_path, relative_path)
        if abs_path is None:
            return
        try:
            if os.path.isfile(abs_path):
                os.remove(abs_path)
            else:
                shutil.rmtree(abs_path)
        except Exception as exc:
            LOG.error("failed to delete %s: %s", abs_path, exc)
            self.deleteFailed.emit(str(exc))
            return
        if relative_path == self._selected_path:
            self._selected_path = ""
            self.selectionChanged.emit()
        self._forget_listing()
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
        if not self._allow_file_filter_toggle:
            return
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
        self.fileSelected.emit(abs_path)

    @pyqtSlot(result=str)
    def selectedGeneratedJsonPathForEdit(self) -> str:
        return self._selected_generated_json_path()

    def selectedFilePath(self) -> str:
        """The selected file, as an absolute path; "" with none."""
        path = self._selected_absolute_path()
        return path if path and os.path.isfile(path) else ""

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
        self._forget_listing()
        if self._dir_watcher.directories():
            self._dir_watcher.removePaths(self._dir_watcher.directories())
        loc = self._current_location()
        if loc is None:
            return
        target = self._resolve(loc.root_path, self._current_path)
        if target and os.path.isdir(target):
            self._dir_watcher.addPath(target)

    def _count_items(self, abs_dir: str) -> int:
        """The folders and matching files in ``abs_dir``: from the directory's
        own entry types (no stat of each, slow on a stick), links followed."""
        count = 0
        try:
            with os.scandir(abs_dir) as it:
                for entry in it:
                    try:
                        if entry.is_dir() or (entry.is_file() and _matches(entry.name, self._file_extensions)):
                            count += 1
                    except OSError:
                        pass
        except OSError:
            pass
        return count

    def _count_folders(self, folders: list) -> None:
        """Counts, on a worker thread, the folders not counted nor being
        counted - none while a drive is to be unmounted."""
        if self._unmounting_name is not None:
            return
        folders = [f for f in folders
                   if f not in self._matching_counts and f not in self._counts_pending]
        if not folders:
            return
        self._counts_pending.update(folders)
        worker = _CountWorker(self._counts_generation, folders, self._file_extensions, self)
        worker.counted.connect(self._on_counted)
        worker.finished.connect(lambda w=worker: self._on_count_worker_finished(w))
        self._count_workers.append(worker)
        worker.start()

    def _on_counted(self, generation: int, counts: dict) -> None:
        if generation != self._counts_generation:
            return
        self._matching_counts.update(counts)
        self._counts_pending.difference_update(counts)
        if not self._counts_shown.isActive():
            self._counts_shown.start()

    def _on_count_worker_finished(self, worker: _CountWorker) -> None:
        if worker in self._count_workers:
            self._count_workers.remove(worker)
        worker.deleteLater()
        self._unmount_when_not_counting()

    def _forget_counts(self, under: str | None = None) -> None:
        """Counts again: what was counted (under the folder ``under`` alone, if
        given - a drive gone), or is being counted, may no longer be so. The
        counts in progress are stopped either way; a folder they were for is
        counted again once it is shown."""
        self._counts_generation += 1
        if under is None:
            self._matching_counts.clear()
        else:
            prefix = os.path.join(under, "")
            self._matching_counts = {folder: count for folder, count in self._matching_counts.items()
                                     if folder != under and not folder.startswith(prefix)}
        self._counts_pending.clear()
        for worker in self._count_workers:
            worker.requestInterruption()

    def _stop_counting(self) -> None:
        """At quit: the counts stopped, waited for."""
        self._forget_counts()
        for worker in list(self._count_workers):
            worker.wait(COUNT_WORKER_QUIT_WAIT_MS)

    def _folder_file_count_display(self, entry: FileSystemEntry) -> str:
        if (
            not self._show_recursive_folder_file_counts
            or entry.is_up
            or not entry.is_dir
        ):
            return ""
        count = self._matching_counts.get(entry.absolute_path)
        if count is None:
            return "[counting…]"
        ext_label = self._file_extensions[0] if len(self._file_extensions) == 1 else "matching"
        if count <= 0:
            return f"[no {ext_label} files]"
        return f"[has {count} {ext_label} file{'s' if count != 1 else ''}]"

    def _list_dir(self, abs_dir: str) -> list:
        """The folders and files in ``abs_dir`` (hidden ones left out), read
        once until it changes (_forget_listing): the filters and the counts
        coming in choose from it without reading the folder again."""
        if self._listing_dir == abs_dir:
            return self._listing
        listing: list[FileSystemEntry] = []
        try:
            names = os.listdir(abs_dir)
        except OSError:
            names = []
        for name in names:
            if _hidden(name):
                continue
            full = os.path.join(abs_dir, name)
            try:
                st = os.stat(full)
            except OSError:
                continue
            is_dir = stat.S_ISDIR(st.st_mode)
            if not is_dir and not stat.S_ISREG(st.st_mode):
                continue
            listing.append(FileSystemEntry(
                name=name,
                relative_path=os.path.join(self._current_path, name) if self._current_path else name,
                absolute_path=full,
                is_dir=is_dir,
                is_up=False,
                size_bytes=0 if is_dir else st.st_size,
                item_count=ITEM_COUNT_UNREAD if is_dir else 0,
                modified_timestamp=st.st_mtime,
            ))
        self._listing_dir, self._listing = abs_dir, listing
        return listing

    def _forget_listing(self) -> None:
        self._listing_dir = None
        self._listing = []

    def _scan(self, abs_dir: str) -> list:
        # outside Home and the mounted drives: the files of the location's root,
        # of the type asked for, whatever the filters were left at there
        browses_folders = self._browses_folders()
        show_folders = self._show_folders if browses_folders else False
        matching_only = self._ngc_only if browses_folders else True
        raw: list[FileSystemEntry] = []
        uncounted: list[str] = []
        for entry in self._list_dir(abs_dir):
            if entry.is_dir:
                if not show_folders:
                    continue
                if entry.item_count == ITEM_COUNT_UNREAD:
                    # read once it is shown: a listing of its own
                    entry.item_count = self._count_items(entry.absolute_path)
                # counted where they say how many matching files they hold, or
                # where one without any is not worth opening (the DXF browser);
                # one not counted yet is shown until it is
                if self._counts_folders:
                    count = self._matching_counts.get(entry.absolute_path)
                    if count is None:
                        uncounted.append(entry.absolute_path)
                    elif count == 0 and self._hides_empty_folders:
                        continue
            elif matching_only and not _matches(entry.name, self._file_extensions):
                continue
            raw.append(entry)
        self._count_folders(uncounted)
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
                name="Up",
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
            "icon": _icon(e),
            "sizeDisplay": _format_size(e),
            "folderFileCountDisplay": self._folder_file_count_display(e),
            "modifiedDisplay": _format_modified(e),
            "modifiedTimestamp": e.modified_timestamp,
        }

    def _on_directory_changed(self, path: str) -> None:
        # what changed is in ``path``: its count, and those of the folders
        # above it, which hold it - not the others, nor its subfolders'
        self._forget_listing()
        folder = os.path.abspath(path)
        while True:
            self._matching_counts.pop(folder, None)
            parent = os.path.dirname(folder)
            if parent == folder:
                break
            folder = parent
        self.entriesChanged.emit()

    def _on_drive_connected(self, name: str, path: str) -> None:
        if any(l.name == name for l in self._mounted):
            return
        # nothing counted is under it: a drive gone took its counts along
        self._mounted.append(_drive_location(name, path))
        if self._prefers_mounted_media:
            self._go_to_root(name)
        self.locationsChanged.emit()

    def _on_drive_disconnected(self, name: str, path: str) -> None:
        self._mounted = [l for l in self._mounted if l.name != name]
        self._forget_counts(under=path)
        if self._current_name == name:
            if self._prefers_mounted_media and self._mounted:
                self._go_to_root(self._mounted[0].name)
            elif self._static:
                self._go_to_root(self._static[0].name)
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
            self._go_to("", selected=os.path.basename(dest_path))
            self.locationsChanged.emit()
        self.copyCompleted.emit(dest_path)

    def _on_copy_error(self, msg: str) -> None:
        self._is_copying = False
        self._copy_progress = 0.0
        self._copy_worker = None
        self.copyProgressChanged.emit(0.0)
        LOG.error("copy to USB failed: %s", msg)
        self.copyFailed.emit(msg)
