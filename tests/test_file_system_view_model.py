"""The filesystem browser's folders, drives and unmounting
(ui/tabs/programs/filesystemview/filesystem_viewmodel.py).

What is pinned down here:

* Each folder is counted, at any depth, for the files of the browser's type
  it holds - hidden ones left out - away from the GUI thread; until it is,
  it says it is being counted. A folder with none is hidden where the
  browser hides empty folders (the DXF browser), shown otherwise.
* A folder's size is how many folders and matching files it holds itself.
* A location that is not browsed folder by folder shows the matching files
  of its root alone, whatever the filters.
* Drives come and go as the drives repository says: one tab each, or all
  as one tab (drives_tab) there with none (disabled) showing the first;
  a drive mounted is shown where drives are preferred; one gone shows the
  first location again and its counts go with it - not the others'.
* Unmount is offered on a drive shown; asked for, it waits for the counts,
  then unmounts, and says how it went (unmountReported), once.
"""

import os

import pytest
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtTest import QSignalSpy, QTest

from teachinlathe.core.removable_drives_repository import Drive
from teachinlathe.ui.tabs.programs.filesystemview.data_types import FileSystemLocation, LocationType
from teachinlathe.ui.tabs.programs.filesystemview.filesystem_viewmodel import (
    FileSystemViewModel, count_matching_files,
)


class FakeDrives(QObject):
    """The drives repository's signals and calls, driven by the test."""
    driveConnected = pyqtSignal(str, str)
    driveDisconnected = pyqtSignal(str, str)
    unmountingChanged = pyqtSignal()
    driveUnmounted = pyqtSignal(str)
    unmountFailed = pyqtSignal(str, str)

    def __init__(self, drives=(), unmount_starts=True):
        super().__init__()
        self._drives = {d.name: d for d in drives}
        self.unmount_starts = unmount_starts
        self.unmount_calls = []
        self.is_unmounting = False

    @property
    def drives(self):
        return list(self._drives.values())

    def connect_drive(self, name, path):
        self._drives[name] = Drive(name, str(path), "/dev/sdx1")
        self.driveConnected.emit(name, str(path))

    def disconnect_drive(self, name):
        drive = self._drives.pop(name)
        self.driveDisconnected.emit(name, drive.path)

    def unmount(self, name):
        self.unmount_calls.append(name)
        if not self.unmount_starts:
            return False
        self.is_unmounting = True
        self.unmountingChanged.emit()
        return True

    def finish(self, name, failure=""):
        self.is_unmounting = False
        self.unmountingChanged.emit()
        if failure:
            self.unmountFailed.emit(name, failure)
        else:
            self._drives.pop(name, None)
            self.driveUnmounted.emit(name)
            self.driveDisconnected.emit(name, f"/media/{name}")


def _touch(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x")


@pytest.fixture
def tree(tmp_path):
    """drawings/          a.dxf, notes.txt
         parts/         b.dxf, c.DXF
           deep/        d.dxf
         empty/         readme.txt
         .hidden/       e.dxf
    """
    root = tmp_path / "drawings"
    _touch(root / "a.dxf")
    _touch(root / "notes.txt")
    _touch(root / "parts" / "b.dxf")
    _touch(root / "parts" / "c.DXF")
    _touch(root / "parts" / "deep" / "d.dxf")
    _touch(root / "empty" / "readme.txt")
    _touch(root / ".hidden" / "e.dxf")
    return root


@pytest.fixture
def made():
    """The view models made, their count workers stopped after."""
    vms = []
    yield vms
    for vm in vms:
        vm._stop_counting()


def _browser(made, root, drives=None, **options):
    options = {"file_extensions": (".dxf",), "file_filter_label": "DXF",
               "show_recursive_folder_file_counts": True, **options}
    vm = FileSystemViewModel(
        [FileSystemLocation("SyncThing", str(root), LocationType.SYNCTHING, browses_folders=True)],
        drives=drives if drives is not None else FakeDrives(), **options)
    made.append(vm)
    return vm


def _rows(vm):
    return {e["name"]: e for e in vm.entries}


def _counted(vm, timeout_ms=5000):
    """The entries once no folder is being counted any more."""
    waited = 0
    while any(e["folderFileCountDisplay"] == "[counting…]" for e in vm.entries):
        assert waited < timeout_ms, "the folders were never counted"
        QTest.qWait(20)
        waited += 20
    return _rows(vm)


# ── counting ────────────────────────────────────────────────────────────

def test_each_folder_is_counted_at_any_depth_hidden_ones_left_out(tree):
    counts = count_matching_files(str(tree), (".dxf",))

    assert counts[str(tree)] == 4
    assert counts[str(tree / "parts")] == 3
    assert counts[str(tree / "parts" / "deep")] == 1
    assert counts[str(tree / "empty")] == 0
    assert str(tree / ".hidden") not in counts


def test_a_count_stopped_returns_what_it_has(tree):
    assert count_matching_files(str(tree), (".dxf",), stop=lambda: True) == {}


def test_a_folder_says_it_is_counted_then_what_it_holds(made, tree):
    vm = _browser(made, tree)

    first = _rows(vm)
    assert first["parts"]["folderFileCountDisplay"] == "[counting…]"

    rows = _counted(vm)
    assert rows["parts"]["folderFileCountDisplay"] == "[has 3 .dxf files]"
    assert rows["empty"]["folderFileCountDisplay"] == "[no .dxf files]"
    assert ".hidden" not in rows


def test_a_folders_size_is_what_it_holds_itself(made, tree):
    rows = _rows(_browser(made, tree))

    # b.dxf, c.DXF and deep/
    assert rows["parts"]["sizeDisplay"] == "3 items"
    # readme.txt is no DXF
    assert rows["empty"]["sizeDisplay"] == "0 items"


def test_empty_folders_are_hidden_once_counted_where_the_browser_hides_them(made, tree):
    vm = _browser(made, tree, hides_empty_folders=True)

    assert "empty" in _rows(vm)   # not counted yet: shown until it is
    rows = _counted(vm)

    assert "empty" not in rows
    assert "parts" in rows


def test_the_files_shown_are_the_browsers_type(made, tree):
    rows = _rows(_browser(made, tree))

    assert "a.dxf" in rows
    assert "notes.txt" not in rows
    assert rows["a.dxf"]["icon"] == "dxf_file.svg"
    assert rows["parts"]["icon"] == "folder-icon.svg"


def test_a_location_not_browsed_by_folder_shows_its_roots_files_alone(made, tree):
    vm = FileSystemViewModel(
        [FileSystemLocation("Flat", str(tree), LocationType.SYNCTHING)],
        drives=FakeDrives(), file_extensions=(".dxf",))
    made.append(vm)
    vm.setNgcOnly(False)

    assert set(_rows(vm)) == {"a.dxf"}
    assert vm.browsesFolders is False


# ── drives ──────────────────────────────────────────────────────────────

def _names(vm):
    return [(loc["name"], loc["isAvailable"], loc["isSelected"]) for loc in vm.locations]


def test_drives_as_one_tab_there_with_none_disabled(made, tree, tmp_path):
    stick = tmp_path / "STICK"
    _touch(stick / "s.dxf")
    drives = FakeDrives()
    vm = _browser(made, tree, drives=drives, drives_tab="USB Stick", prefers_mounted_media=True)

    assert _names(vm) == [("SyncThing", True, True), ("USB Stick", False, False)]
    vm.selectLocation("USB Stick")   # none: nothing to show
    assert vm.currentLocationName == "SyncThing"

    drives.connect_drive("STICK", stick)

    # preferred: shown as it comes, under the tab's name
    assert vm.currentLocationName == "STICK"
    assert _names(vm) == [("SyncThing", True, False), ("USB Stick", True, True)]
    assert vm.isInMountedMedia
    assert set(_rows(vm)) == {"s.dxf"}

    vm.selectLocation("SyncThing")
    vm.selectLocation("USB Stick")
    assert vm.currentLocationName == "STICK"


def test_a_tab_per_drive_each_named_after_it(made, tree, tmp_path):
    for name in ("A", "B"):
        (tmp_path / name).mkdir()
    drives = FakeDrives([Drive("A", str(tmp_path / "A"), "/dev/sda1")])
    vm = _browser(made, tree, drives=drives)

    drives.connect_drive("B", tmp_path / "B")

    assert [loc["name"] for loc in vm.locations] == ["SyncThing", "A", "B"]
    # not preferred: the location shown stays
    assert vm.currentLocationName == "SyncThing"


def test_a_drive_gone_shows_the_first_location_again(made, tree, tmp_path):
    stick = tmp_path / "STICK"
    stick.mkdir()
    drives = FakeDrives()
    vm = _browser(made, tree, drives=drives, prefers_mounted_media=True)
    drives.connect_drive("STICK", stick)
    assert vm.currentLocationName == "STICK"

    drives.disconnect_drive("STICK")

    assert vm.currentLocationName == "SyncThing"
    assert [loc["name"] for loc in vm.locations] == ["SyncThing"]


def test_a_drive_gone_takes_its_counts_not_the_others(made, tree, tmp_path):
    stick = tmp_path / "STICK"
    _touch(stick / "folder" / "s.dxf")
    drives = FakeDrives()
    vm = _browser(made, tree, drives=drives)
    _counted(vm)                          # SyncThing's
    drives.connect_drive("STICK", stick)
    vm.selectLocation("STICK")
    _counted(vm)                          # the stick's

    drives.disconnect_drive("STICK")
    vm.selectLocation("SyncThing")

    # shown counted at once: not counted again
    assert _rows(vm)["parts"]["folderFileCountDisplay"] == "[has 3 .dxf files]"
    assert not any(folder.startswith(str(stick)) for folder in vm._matching_counts)


def test_a_drive_mounted_at_start_is_shown_first_where_drives_are_preferred(made, tree, tmp_path):
    stick = tmp_path / "STICK"
    stick.mkdir()
    drives = FakeDrives([Drive("STICK", str(stick), "/dev/sda1")])

    vm = _browser(made, tree, drives=drives, prefers_mounted_media=True)

    assert vm.currentLocationName == "STICK"


def test_rescan_goes_back_to_the_first_drive_at_its_root(made, tree, tmp_path):
    stick = tmp_path / "STICK"
    (stick / "sub").mkdir(parents=True)
    drives = FakeDrives()
    vm = _browser(made, tree, drives=drives, prefers_mounted_media=True)
    vm.selectLocation("SyncThing")
    vm.navigateInto("parts")
    drives.connect_drive("STICK", stick)
    vm.navigateInto("sub")

    vm.rescan()

    assert vm.currentLocationName == "STICK"
    assert [crumb["name"] for crumb in vm.breadcrumbs] == ["STICK"]


# ── unmounting ──────────────────────────────────────────────────────────

@pytest.fixture
def on_stick(made, tree, tmp_path):
    """A browser showing a drive, STICK, with its folders counted."""
    stick = tmp_path / "STICK"
    _touch(stick / "folder" / "s.dxf")
    drives = FakeDrives()
    vm = _browser(made, tree, drives=drives, prefers_mounted_media=True)
    drives.connect_drive("STICK", stick)
    _counted(vm)
    return vm, drives


def test_unmount_is_offered_on_a_drive_alone(on_stick):
    vm, _drives = on_stick
    assert vm.canUnmount

    vm.selectLocation("SyncThing")
    assert not vm.canUnmount


def test_a_drive_unmounted_says_it_can_be_pulled_out(on_stick):
    vm, drives = on_stick
    reported = QSignalSpy(vm.unmountReported)

    vm.unmountCurrentDrive()
    assert drives.unmount_calls == ["STICK"]
    assert not vm.canUnmount   # while it is being unmounted
    vm.unmountCurrentDrive()   # asked again: nothing more
    assert drives.unmount_calls == ["STICK"]

    drives.finish("STICK")

    assert [list(args) for args in reported] == [['You can now remove your "STICK" Usb Stick']]
    assert vm.currentLocationName == "SyncThing"


def test_an_unmount_that_fails_says_why(on_stick):
    vm, drives = on_stick
    reported = QSignalSpy(vm.unmountReported)

    vm.unmountCurrentDrive()
    drives.finish("STICK", failure="target is busy")

    assert [list(args) for args in reported] == [['"STICK" could not be unmounted: target is busy']]
    assert vm.canUnmount   # still there: can be tried again


def test_an_unmount_that_cannot_start_says_so(on_stick):
    vm, drives = on_stick
    drives.unmount_starts = False
    reported = QSignalSpy(vm.unmountReported)

    vm.unmountCurrentDrive()

    assert [list(args) for args in reported] == [['"STICK" could not be unmounted.']]
    assert vm.canUnmount


def test_another_browsers_unmount_is_not_reported_here(on_stick):
    vm, drives = on_stick
    reported = QSignalSpy(vm.unmountReported)

    drives.unmount("STICK")
    assert not vm.canUnmount   # another browser's, but the drive is busy
    drives.finish("STICK")

    assert len(reported) == 0


def test_the_unmount_waits_for_the_counts_walking_the_drive(made, tree, tmp_path):
    stick = tmp_path / "STICK"
    for i in range(30):
        _touch(stick / f"folder{i}" / "s.dxf")
    drives = FakeDrives()
    vm = _browser(made, tree, drives=drives, prefers_mounted_media=True)
    drives.connect_drive("STICK", stick)
    vm.entries   # starts counting its folders
    assert vm._count_workers

    vm.unmountCurrentDrive()
    if vm._count_workers:
        assert drives.unmount_calls == []
    waited = 0
    while not drives.unmount_calls:
        assert waited < 5000, "the unmount never started"
        QTest.qWait(20)
        waited += 20

    assert drives.unmount_calls == ["STICK"]
    assert not vm._count_workers
    # no new count started on the drive meanwhile
    vm.entries
    assert not vm._count_workers
