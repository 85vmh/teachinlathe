"""WCS touch off must rebuild geometry using the live, unsaved offset."""

from types import SimpleNamespace

import pytest

linuxcnc = pytest.importorskip("linuxcnc")
pytest.importorskip("rs274.glcanon_scene")

from teachinlathe.ui.tabs.programs.backplot import lathe_backplot_item as module

Canon = module.LatheBackplotCanon


def status():
    return SimpleNamespace(
        poll=lambda: None, file="/tmp/program.ngc", call_level=0,
        task_mode=linuxcnc.MODE_MDI, interp_state=linuxcnc.INTERP_IDLE,
        tool_in_spindle=1, tool_offset=(0.0,) * 9,
        g5x_index=1, g5x_offset=(0.0,) * 9, rotation_xy=0.0,
        actual_position=(0.0,) * 9, joint_actual_position=(0.0,) * 9,
        homed=(1,) * 9, g92_offset=(0.0,) * 9, limit=(0,) * 9,
        motion_mode=0,
    )


def host(monkeypatch):
    monkeypatch.setattr(module.tool_source, "describe", lambda tool: None)
    stat = status()
    reloads = []
    obj = SimpleNamespace(
        stat=stat, _perf=None, _program_file=stat.file,
        _current_file=stat.file, _pending_default_view=False,
        _last_preview_tool_signature=(stat.tool_in_spindle, stat.tool_offset),
        _last_preview_wcs_signature=Canon._wcs_signature(stat),
        _wcs_signature=Canon._wcs_signature,
        _pixel_quantum=lambda: 0, soft_limits=lambda: (),
        logger=SimpleNamespace(npts=0), source=SimpleNamespace(poll=lambda: None),
        fingerprint=None, update=lambda: None,
    )

    def reload(filename, *, sync_task):
        reloads.append((filename, sync_task))
        obj._last_preview_wcs_signature = Canon._wcs_signature(stat)

    obj._reload_preview = reload
    return obj, reloads


@pytest.mark.parametrize("mode", [linuxcnc.MODE_MDI, linuxcnc.MODE_AUTO])
@pytest.mark.parametrize("field,value", [
    ("g5x_offset", (0.0, 0.0, 125.0) + (0.0,) * 6),
    ("g5x_index", 2),
    ("rotation_xy", 30.0),
])
def test_wcs_change_rebuilds_once_when_idle(monkeypatch, mode, field, value):
    obj, reloads = host(monkeypatch)
    obj.stat.task_mode = mode
    setattr(obj.stat, field, value)
    Canon.poll(obj)
    Canon.poll(obj)
    assert reloads == [(obj.stat.file, False)]
    assert obj._pending_default_view


@pytest.mark.parametrize("state", [linuxcnc.INTERP_READING, linuxcnc.INTERP_PAUSED])
def test_a_wcs_change_the_program_makes_is_not_read_again(monkeypatch, state):
    """A Facing's new Z0: the geometry has it already. Read again from the new
    origin once the program ends, its Facing would be drawn over the part it
    faced."""
    obj, reloads = host(monkeypatch)
    obj.stat.task_mode = linuxcnc.MODE_AUTO
    obj.stat.interp_state = state
    obj.stat.g5x_offset = (0.0, 0.0, 125.0) + (0.0,) * 6
    Canon.poll(obj)
    assert not reloads
    obj.stat.interp_state = linuxcnc.INTERP_IDLE
    Canon.poll(obj)
    assert not reloads


def test_unchanged_wcs_does_not_reload(monkeypatch):
    obj, reloads = host(monkeypatch)
    Canon.poll(obj)
    assert not reloads


@pytest.mark.parametrize("index", [1, 2, 9])
def test_preview_parameters_use_live_wcs_and_preserve_other_values(tmp_path, index):
    path = tmp_path / "preview.var"
    path.write_text("100 42\n5220 1\n5223 -50\n5243 -75\n")
    stat = status()
    stat.g5x_index = index
    stat.g5x_offset = (10.0, 0.0, 125.5) + (0.0,) * 6
    stat.rotation_xy = 15.0
    Canon._refresh_preview_wcs(path, stat)
    pairs = [line.split() for line in path.read_text().splitlines()]
    values = {int(key): float(value) for key, value in pairs}
    base = 5200 + 20 * index
    assert values[5220] == index
    assert values[base + 1] == 10.0
    assert values[base + 3] == 125.5
    assert values[base + 10] == 15.0
    assert values[100] == 42
    if index != 1:
        assert values[5223] == -50
    if index != 2:
        assert values[5243] == -75
    assert [int(key) for key, _ in pairs] == sorted(values)
