"""The USB sticks mounted on the machine (core.removable_drives_repository).

What is pinned down here:

* The mount table is read for what is mounted straight in /media/<user> or
  /media, by its folder's name, its escapes (a space as \\040, ...) undone;
  the rest of the table, deeper folders and other users' are not drives.
* A drive mounted or gone is said once (driveConnected / driveDisconnected),
  in the mount table's order; a table that cannot be read is no drives.
* Unmounting runs udisksctl for the drive's device, without asking for a
  password, then powers it off; driveUnmounted when it is done, unmountFailed
  with what udisksctl said (or that it could not start) when it is not; one
  at a time, and only a drive that is mounted.
"""

import os
import stat
import textwrap

import pytest
from PyQt6.QtTest import QSignalSpy, QTest

from teachinlathe.core import removable_drives_repository as drives_module
from teachinlathe.core.removable_drives_repository import (
    Drive, RemovableDrivesRepository, media_dirs, parse_drives,
)

PARENTS = frozenset({"/media/cnc", "/media"})

MOUNTS = textwrap.dedent("""\
    sysfs /sys sysfs rw,nosuid 0 0
    /dev/nvme0n1p2 / ext4 rw,relatime 0 0
    /dev/sda1 /media/cnc/KINGSTON vfat rw,nosuid 0 0
    /dev/sdb1 /media/cnc/MY\\040STICK vfat rw 0 0
    /dev/sdc1 /media/BACKUP ext4 rw 0 0
    /dev/sdd1 /media/other/THEIRS vfat rw 0 0
    /dev/sde1 /media/cnc/KINGSTON/inner vfat rw 0 0
    /dev/sdf1 /mnt/data ext4 rw 0 0
""")


# ── the mount table ─────────────────────────────────────────────────────

def test_the_drives_are_what_is_mounted_straight_in_the_media_folders():
    drives = parse_drives(MOUNTS, PARENTS)

    assert list(drives) == ["KINGSTON", "MY STICK", "BACKUP"]
    assert drives["KINGSTON"] == Drive("KINGSTON", "/media/cnc/KINGSTON", "/dev/sda1")
    assert drives["BACKUP"] == Drive("BACKUP", "/media/BACKUP", "/dev/sdc1")


def test_a_path_is_read_with_its_escapes_undone():
    table = ("/dev/sda1 /media/cnc/a\\040b\\011c vfat rw 0 0\n"
             "/dev/sdb1 /media/cnc/back\\134slash vfat rw 0 0\n")

    drives = parse_drives(table, PARENTS)

    assert drives["a b\tc"].path == "/media/cnc/a b\tc"
    assert drives["back\\slash"].path == "/media/cnc/back\\slash"


def test_a_label_that_is_not_utf8_stays_a_path_that_can_be_opened():
    # the table's bytes as the repository reads them (os.fsdecode)
    table = os.fsdecode(b"/dev/sda1 /media/cnc/caf\xe9 vfat rw 0 0\n")

    (drive,) = parse_drives(table, PARENTS).values()

    assert os.fsencode(drive.path) == b"/media/cnc/caf\xe9"


def test_of_two_drives_of_one_name_the_first_is_kept():
    table = ("/dev/sda1 /media/cnc/STICK vfat rw 0 0\n"
             "/dev/sdb1 /media/STICK vfat rw 0 0\n")

    assert parse_drives(table, PARENTS)["STICK"].device == "/dev/sda1"


def test_lines_too_short_and_media_itself_are_no_drives():
    table = "garbage\n\n/dev/sda1 /media vfat rw 0 0\n/dev/sdb1 /media/ vfat rw 0 0\n"

    assert parse_drives(table, PARENTS) == {}


def test_the_media_folders_are_the_users_and_media(monkeypatch):
    monkeypatch.setattr(drives_module.getpass, "getuser", lambda: "cnc")
    assert media_dirs() == frozenset({"/media/cnc", "/media"})

    def no_user():
        raise OSError("no login name")
    monkeypatch.setattr(drives_module.getpass, "getuser", no_user)
    assert media_dirs() == frozenset({"/media"})


# ── drives coming and going ─────────────────────────────────────────────

@pytest.fixture
def mounts(tmp_path):
    """A mount table of our own, and a repository reading it."""
    path = tmp_path / "mounts"
    path.write_text("")
    made = []

    def make(text=""):
        path.write_text(text)
        repo = RemovableDrivesRepository(str(path), parents=PARENTS)
        made.append(repo)
        return repo
    make.path = path
    yield make
    for repo in made:
        repo.deleteLater()


def _line(device, mount_point):
    return f"{device} {mount_point} vfat rw 0 0\n"


def test_the_drives_mounted_at_start_are_there_without_a_signal(mounts):
    repo = mounts(_line("/dev/sda1", "/media/cnc/A") + _line("/dev/sdb1", "/media/cnc/B"))

    assert [d.name for d in repo.drives] == ["A", "B"]


def test_a_drive_mounted_and_gone_is_said_once(mounts):
    repo = mounts(_line("/dev/sda1", "/media/cnc/A"))
    connected, disconnected = QSignalSpy(repo.driveConnected), QSignalSpy(repo.driveDisconnected)

    mounts.path.write_text(_line("/dev/sda1", "/media/cnc/A")
                           + _line("/dev/sdb1", "/media/cnc/B")
                           + _line("/dev/sdc1", "/media/cnc/C"))
    repo._refresh()
    repo._refresh()   # nothing changed: nothing said

    assert [list(args) for args in connected] == [["B", "/media/cnc/B"], ["C", "/media/cnc/C"]]
    assert len(disconnected) == 0

    mounts.path.write_text(_line("/dev/sdc1", "/media/cnc/C"))
    repo._refresh()

    assert [list(args) for args in disconnected] == [["A", "/media/cnc/A"], ["B", "/media/cnc/B"]]
    assert [d.name for d in repo.drives] == ["C"]


def test_a_mount_table_that_cannot_be_opened_is_no_drives(tmp_path):
    repo = RemovableDrivesRepository(str(tmp_path / "missing"), parents=PARENTS)

    assert repo.drives == []
    assert repo.unmount("A") is False


# ── unmounting ──────────────────────────────────────────────────────────

@pytest.fixture
def udisksctl(tmp_path, monkeypatch):
    """A udisksctl of our own: writes its arguments to a log, one call a
    line, prints ``output`` and exits with ``code``."""
    log = tmp_path / "udisksctl.log"

    def install(code=0, output=""):
        script = tmp_path / "udisksctl"
        script.write_text(textwrap.dedent(f"""\
            #!/bin/sh
            echo "$@" >> {log}
            printf '%s' '{output}'
            exit {code}
        """))
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
        monkeypatch.setattr(drives_module, "UDISKSCTL", str(script))
        return log
    return install


def _calls(log):
    return log.read_text().splitlines() if log.exists() else []


def _wait_for(spy, timeout_ms=5000):
    assert len(spy) > 0 or spy.wait(timeout_ms), "the signal never came"


def test_a_drive_unmounted_is_powered_off_and_said_so(mounts, udisksctl):
    log = udisksctl(code=0)
    repo = mounts(_line("/dev/sda1", "/media/cnc/A"))
    unmounted, failed = QSignalSpy(repo.driveUnmounted), QSignalSpy(repo.unmountFailed)
    unmounting = QSignalSpy(repo.unmountingChanged)

    assert repo.unmount("A") is True
    assert repo.is_unmounting
    # the stick is gone from the table by the time udisksctl is done
    mounts.path.write_text("")
    _wait_for(unmounted)

    assert [list(args) for args in unmounted] == [["A"]]
    assert len(failed) == 0
    assert not repo.is_unmounting
    assert len(unmounting) == 2   # started, done
    assert repo.drives == []
    # power-off is started detached, after the unmount: wait for its line
    for _ in range(50):
        if len(_calls(log)) == 2:
            break
        QTest.qWait(100)
    assert _calls(log) == ["unmount --no-user-interaction -b /dev/sda1",
                           "power-off --no-user-interaction -b /dev/sda1"]


def test_an_unmount_that_fails_says_what_udisksctl_said(mounts, udisksctl):
    log = udisksctl(code=1, output="target is busy")
    repo = mounts(_line("/dev/sda1", "/media/cnc/A"))
    failed, unmounted = QSignalSpy(repo.unmountFailed), QSignalSpy(repo.driveUnmounted)

    repo.unmount("A")
    _wait_for(failed)

    assert [list(args) for args in failed] == [["A", "target is busy"]]
    assert len(unmounted) == 0
    assert not repo.is_unmounting
    # not powered off: it is still mounted
    assert _calls(log) == ["unmount --no-user-interaction -b /dev/sda1"]
    assert [d.name for d in repo.drives] == ["A"]


def test_an_unmount_that_fails_silently_says_how_udisksctl_exited(mounts, udisksctl):
    udisksctl(code=3)
    repo = mounts(_line("/dev/sda1", "/media/cnc/A"))
    failed = QSignalSpy(repo.unmountFailed)

    repo.unmount("A")
    _wait_for(failed)

    assert list(failed[0]) == ["A", f"{drives_module.UDISKSCTL} exited with 3"]


def test_an_unmount_where_udisksctl_cannot_start_fails(mounts, monkeypatch, tmp_path):
    monkeypatch.setattr(drives_module, "UDISKSCTL", str(tmp_path / "no-such-udisksctl"))
    repo = mounts(_line("/dev/sda1", "/media/cnc/A"))
    failed = QSignalSpy(repo.unmountFailed)

    assert repo.unmount("A") is True
    _wait_for(failed)

    assert list(failed[0])[0] == "A"
    assert "could not be started" in list(failed[0])[1]
    assert not repo.is_unmounting


def test_one_unmount_at_a_time_and_only_of_a_drive_mounted(mounts, udisksctl):
    udisksctl(code=0)
    repo = mounts(_line("/dev/sda1", "/media/cnc/A") + _line("/dev/sdb1", "/media/cnc/B"))
    unmounted = QSignalSpy(repo.driveUnmounted)

    assert repo.unmount("nothing") is False
    assert repo.unmount("A") is True
    assert repo.unmount("B") is False   # A's still going
    _wait_for(unmounted)

    assert [list(args) for args in unmounted] == [["A"]]
