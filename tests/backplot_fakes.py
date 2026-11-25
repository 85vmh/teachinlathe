"""A LatheBackplotCanon without GL, for poll() to be tested on: the status it
reads and the plot state poll() touches, in a namespace. The methods under
test are called on the class (``LatheBackplotCanon.poll(plot)``)."""

from types import SimpleNamespace

import linuxcnc

from teachinlathe.ui.tabs.programs.backplot.lathe_backplot_item import LatheBackplotCanon as Canon


def status(file="/tmp/program.ngc"):
    """linuxcnc.stat as poll() reads it: MDI, idle, tool 1, at G54's zero."""
    return SimpleNamespace(
        poll=lambda: None, file=file, call_level=0,
        task_mode=linuxcnc.MODE_MDI, interp_state=linuxcnc.INTERP_IDLE,
        tool_in_spindle=1, tool_offset=(0.0,) * 9,
        g5x_index=1, g5x_offset=(0.0,) * 9, rotation_xy=0.0,
        actual_position=(0.0,) * 9, joint_actual_position=(0.0,) * 9,
        homed=(1,) * 9, g92_offset=(0.0,) * 9, limit=(0,) * 9,
        motion_mode=0,
    )


def plot(stat):
    """The plot with ``stat.file`` read, at ``stat``'s tool and origin; its
    ``_reload_preview`` is the test's to set."""
    return SimpleNamespace(
        stat=stat, _perf=None, _program_file=stat.file,
        _current_file=stat.file, _missing_file=None, _pending_default_view=False,
        _last_preview_tool_signature=Canon._tool_signature(stat),
        _last_preview_wcs_signature=Canon._wcs_signature(stat),
        _tool_signature=Canon._tool_signature,
        _wcs_signature=Canon._wcs_signature,
        _pixel_quantum=lambda: 0, soft_limits=lambda: (),
        logger=SimpleNamespace(npts=0), source=SimpleNamespace(poll=lambda: None),
        fingerprint=None, update=lambda: None,
        _show_thread_plan=lambda: False, invalidate_static=lambda: None,
        _follow_excursion=lambda: None,
    )
