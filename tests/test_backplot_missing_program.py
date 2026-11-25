"""The program the backplot shows deleted from the disk, then a tool change.

Reported 2026-11-25 on ui_tweaks (db04396): a program run the day before
(M10x1.ngc) was deleted from the Programs tab; a tool change from Manual
(MDI ``M61 Q4 G43``) then aborted the whole app:

    lathe_backplot_item.py, in poll
        self._reload_preview(self._current_file, sync_task=False)
    lathe_backplot_item.py, in _reload_preview
        with open(filename, 'r', encoding='utf-8', errors='replace') as handle:
    FileNotFoundError: [Errno 2] No such file or directory: '.../M10x1.ngc'
    Aborted

A tool (or origin) changed outside AUTO reads the program again
(LatheBackplotCanon._poll); the file is gone, open() raises, nothing catches
it, and PyQt6 aborts on an exception out of a slot (the poll timer's).

What is pinned down here:

* A poll that finds the program gone does not raise: the plot shows the
  empty program (core.no_program) in its place, not the toolpath of one that
  is no more, says so once (a warning) and does not read it again at the next
  tool change or touch off.
* A program back on the disk is read again once it is asked for.
* An exception out of a slot does not abort the app (main's excepthook).
"""

import os
import subprocess
import sys
import textwrap

import pytest

linuxcnc = pytest.importorskip("linuxcnc")
pytest.importorskip("rs274.glcanon_scene")

from backplot_fakes import plot as fake_plot, status
from teachinlathe.core.no_program import NO_PROGRAM
from teachinlathe.ui.tabs.programs.backplot import lathe_backplot_item as module

Canon = module.LatheBackplotCanon

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _plot(program):
    """The backplot as it is after the program was read: its own status
    handle, and its real _reload_preview - up to where it opens the file.
    The empty program is not drawn (no GL here): ``plot.drawn`` says it was
    asked for."""
    plot = fake_plot(status(program))
    plot.drawn = []

    def reload(filename=None, *, sync_task=False):
        if filename == NO_PROGRAM:
            plot.drawn.append(filename)
            plot._current_file = filename
            return
        return Canon._reload_preview(plot, filename, sync_task=sync_task)
    plot._reload_preview = reload
    plot._show_missing_program = lambda missing, stat: Canon._show_missing_program(plot, missing, stat)
    return plot


@pytest.fixture
def deleted_program(tmp_path, monkeypatch):
    monkeypatch.setattr(module.tool_source, "describe", lambda tool: None)
    path = tmp_path / "Conversational Gcode" / "M10x1.ngc"
    path.parent.mkdir()
    path.write_text("G21\nG0 X10 Z2\nM30\n")
    plot = _plot(str(path))
    path.unlink()
    return plot


def _change_tool(plot, tool):
    # M61 Q<tool> G43, from Manual (MDI)
    plot.stat.tool_in_spindle = tool
    plot.stat.tool_offset = (0.0, 0.0, 12.5 + tool) + (0.0,) * 6


def _warnings(caplog):
    return [r for r in caplog.records if r.levelname == "WARNING" and "not on the disk" in r.getMessage()]


def test_a_tool_change_with_the_program_deleted_shows_none(deleted_program, caplog):
    plot = deleted_program
    program = plot._current_file
    _change_tool(plot, 4)

    Canon.poll(plot)

    assert plot.drawn == [NO_PROGRAM]
    # still the one asked for: poll does not read it again for itself
    assert plot._current_file == program
    assert len(_warnings(caplog)) == 1


def test_an_origin_change_with_the_program_deleted_shows_none(deleted_program):
    plot = deleted_program
    # a touch off / Set Datum, from Manual
    plot.stat.g5x_offset = (0.0, 0.0, 125.0) + (0.0,) * 6

    Canon.poll(plot)

    assert plot.drawn == [NO_PROGRAM]


def test_a_program_chosen_that_is_gone_shows_none(deleted_program):
    plot = deleted_program
    # shown again (a new plot, or the Programs tab back): not read yet
    plot._current_file = ""

    Canon.poll(plot)

    assert plot.drawn == [NO_PROGRAM]


def test_the_program_gone_is_not_read_again_nor_said_again(deleted_program, caplog):
    plot = deleted_program
    _change_tool(plot, 4)
    Canon.poll(plot)

    for tool in (5, 6):
        _change_tool(plot, tool)
        Canon.poll(plot)
    plot.stat.g5x_offset = (0.0, 0.0, 125.0) + (0.0,) * 6
    Canon.poll(plot)
    Canon.poll(plot)

    assert plot.drawn == [NO_PROGRAM]
    assert len(_warnings(caplog)) == 1


def test_a_program_back_on_the_disk_is_read_again(deleted_program):
    plot = deleted_program
    program = plot._current_file
    _change_tool(plot, 4)
    Canon.poll(plot)
    read = []
    plot._reload_preview = lambda filename=None, *, sync_task=False: read.append(filename)

    with open(program, "w") as fh:
        fh.write("G0 X10 Z2\nM30\n")
    plot._current_file = ""   # invalidatePreview: the Programs screen loads it again
    Canon.poll(plot)

    assert read == [program]


# ── the app as a whole ──────────────────────────────────────────────────

def test_an_exception_out_of_the_poll_does_not_abort_the_app(tmp_path):
    """As on the machine: the plot polled by a QTimer, in an app of its own
    (a process: PyQt6 aborts it). The app's start-up is what decides what an
    exception out of a slot does (teachinlathe.app.main)."""
    script = tmp_path / "crash.py"
    script.write_text(textwrap.dedent(f"""\
        import sys
        sys.path.insert(0, {os.path.join(ROOT, "tests")!r})
        from PyQt6.QtCore import QCoreApplication, QTimer
        import test_backplot_missing_program as t
        from teachinlathe.ui.tabs.programs.backplot import lathe_backplot_item as module
        from teachinlathe.app.main import install_exception_hook
        install_exception_hook()   # as main() does at start-up

        module.tool_source.describe = lambda tool: None
        app = QCoreApplication([])
        plot = t._plot({str(tmp_path / "M10x1.ngc")!r})   # never written: gone
        plot.stat.tool_in_spindle = 4
        QTimer.singleShot(0, lambda: module.LatheBackplotCanon.poll(plot))
        QTimer.singleShot(500, app.quit)
        app.exec()
        print("still running")
    """))
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
               PYTHONPATH=os.pathsep.join([os.path.join(ROOT, "src"), os.environ.get("PYTHONPATH", "")]))

    run = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=60)

    assert run.returncode == 0, f"the app died ({run.returncode}):\n{run.stderr[-2000:]}"
    assert "still running" in run.stdout
