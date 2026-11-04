"""The part as it is being cut, from a trail: the bar, less what the trail's
cutting moves took off it, each with the tool that made it (the trail's
``made_by``) - one model of a tool taking off material for the machine and a
simulation alike (simulation.logic.material).

A line the machine made synced with the spindle on position (G33, G76) cuts
a thread: the trail's ``sync_points`` say, for each point, the mode, the
pitch (machine units a turn) and the angle from the index the synced motion
started at. The run of synced lines that follow one another turns on with the
spindle from where the first started - the point before the first of them -
as the planner makes it; the pitch is in mm here, as the points are.
"""

from __future__ import annotations

import logging
import math

from teachinlathe.ui.tabs.programs.backplot.plot_source.trail import SPINDLE_SYNC_POSITION, TRAVERSE

LOG = logging.getLogger(__name__)

try:
    import numpy as np
    from rs274.glcanon_bake import LOGGER_DTYPE
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot material: preview modules unavailable: %s", exc)
    np = None


def stock_shape(stock):
    """The bar ``stock`` - the conversational header's workpiece, as the
    backplot holds it - as the shapely shape the material left is cut from;
    None with no bar."""
    from teachinlathe.conversational.gcode.stock import header_material
    from teachinlathe.conversational.model.data_types import Workpiece

    if not stock:
        return None
    try:
        shape = header_material(Workpiece.from_dict(dict(stock)))
    except (KeyError, TypeError, ValueError) as exc:
        LOG.debug("backplot: no bar to cut from %s: %s", stock, exc)
        return None
    return None if shape.is_empty else shape


class TrailMaterial:
    """The material left cut from a trail as it grows: read again from the
    bar when the bar or its coordinate frame changes; clearing the displayed
    trail keeps the material already cut."""

    def __init__(self):
        self._material = None
        self._basis = None
        self._done = 0
        self._shapes = {}
        # by point: where the spindle is there, degrees from its index, at
        # the end of a synced line - the next synced one goes on from it
        self._phase = {}

    def material_left(self, trail, stat, stock, origin):
        """The bar ``stock`` (the header's, as the plot holds it), less what
        ``trail``'s cutting moves took off it so far, in the frame ``origin``
        - (g5x, g92, XY rotation), machine units - a MaterialLeft; None with
        no bar."""
        from teachinlathe.simulation.logic.material import MaterialLeft

        basis = (tuple(sorted(stock.items())) if isinstance(stock, dict) else stock, origin)
        npts = trail.npts
        # the bar again when it or its coordinate frame changed; a full
        # logger may move its points down, without restoring material removed
        # by the earlier points.
        if basis != self._basis or self._material is None:
            self._basis, self._done = basis, 0
            shape = stock_shape(stock)
            self._material = MaterialLeft(shape) if shape is not None else None
        elif npts < self._done:
            self._done = 0
        if self._done == 0:
            self._phase = {}
        if self._material is None:
            return None
        # from the start of the last segment read: the logger may have
        # stretched it since; cut twice, it takes nothing more off
        found = cutting_segments(trail, stat, origin, max(0, self._done - 2))
        if found is None:
            return self._material
        starts, ends, self._done, index, syncs = found
        made_by = trail.made_by()
        per_mm = float(getattr(stat, "linear_units", 1.0) or 1.0)
        for start, end, at, synced in zip(starts, ends, index, syncs):
            tool = int(made_by.tools[at]) if made_by is not None and at < len(made_by) else 0
            points = [tuple(start), tuple(end)]
            self._material.cut(points, self._shape(tool), self._sync(at, points, synced, per_mm))
        # what is left behind the lines read again next time is not wanted
        for at in [at for at in self._phase if at < self._done - 4]:
            del self._phase[at]
        return self._material

    def _sync(self, at, points, synced, per_mm):
        """How the line from point ``at`` along ``points`` turned with the
        spindle - a SpindleSync - or None when it was not synced with it on
        position. ``synced``: its sync_points record, None when not known."""
        from teachinlathe.simulation.model.moves import SpindleSync

        if synced is None or int(synced["mode"]) != SPINDLE_SYNC_POSITION or not synced["pitch"] > 0:
            self._phase.pop(at + 1, None)
            return None
        before = self._phase.get(at)
        sync = SpindleSync(float(synced["pitch"]) / per_mm, before if before is not None else float(synced["angle"]))
        self._phase[at + 1] = sync.angle_after(math.dist(*points))
        return sync

    def clear_trace(self, trail, stat, stock, origin):
        """Forget the displayed trail while keeping the material it cut."""
        # Consume any logger points not yet incorporated before the logger is
        # cleared. The toolpath trace is disposable; the material state is not.
        self.material_left(trail, stat, stock, origin)
        trail.clear()
        self._done = 0

    def reset(self):
        """Start a fresh material model for a newly loaded program."""
        self._material = None
        self._basis = None
        self._done = 0

    def _shape(self, tool):
        """What cuts of tool ``tool``, as the Tool Library has it now: its
        drawing is part of the key, as the tool in its holder can be edited."""
        from teachinlathe.ui.tabs.programs.backplot import tool_source

        drawing = tool_source.describe(tool) if tool else None
        key = (tool, drawing)
        if key not in self._shapes:
            from teachinlathe.conversational.gcode.operations.profiling.tool_shape import (
                cutting_shape, thread_tooth_shape)
            from teachinlathe.core.tool_library_repository import tool_library_repository
            from teachinlathe.tooling.model.data_types import MountedTool

            mounted = MountedTool.of(tool_library_repository(), tool) if tool else None
            self._shapes[key] = (cutting_shape(mounted) or thread_tooth_shape(mounted)) if mounted else None
        return self._shapes[key]


def cutting_segments(trail, stat, origin, first=0):
    """The trail's cutting moves from point ``first`` on, as ``(starts, ends,
    npts, index, syncs)`` - two ``(N, 2)`` arrays of (z, r) in mm, from
    ``origin`` (g5x, g92, XY rotation; machine units), the trail's length,
    for each move the index of the point it starts at, and its sync with the
    spindle (a trail.SYNC_DTYPE record, or None for each when the trail does not
    say) - or None when there is no trail to read. A rapid cuts nothing:
    each segment is in the motion its end point was logged in, and one in
    the rapid colour is left out. The points and their syncs are read one
    after the other, the logger adding points between: as many of each."""
    if np is None or trail is None:
        return None
    try:
        raw, npts, is_xyuv = trail.points()
        colours = trail.get_colors()
    except (AttributeError, TypeError) as exc:
        LOG.debug("backplot material: no trail to read: %s", exc)
        return None
    if is_xyuv:
        return None
    try:
        sync = trail.sync_points()
    except (AttributeError, TypeError) as exc:
        LOG.debug("backplot material: no sync points: %s", exc)
        sync = None
    if sync is not None:
        npts = min(npts, len(sync))
    first = max(0, min(first, npts))
    points = np.frombuffer(raw, dtype=LOGGER_DTYPE, count=npts)[first:]
    if len(points) < 2:
        return np.empty((0, 2)), np.empty((0, 2)), npts, np.empty(0, dtype=np.int64), []
    rapid = np.asarray(colours[TRAVERSE], dtype=np.uint8)
    cutting = ~np.all(points["c"][1:] == rapid, axis=1)
    # machine units, the work origin taken out, in mm; the XY rotation
    # turns X into Y, which a lathe has none of
    g5x, g92, _rotation = origin
    per_mm = float(getattr(stat, "linear_units", 1.0) or 1.0)
    pos = points["pos"].astype(float)
    zr = np.column_stack([(pos[:, 2] - g5x[2] - g92[2]) / per_mm,
                          (pos[:, 0] - g5x[0] - g92[0]) / per_mm])
    index = first + np.flatnonzero(cutting)
    syncs = list(sync[index + 1]) if sync is not None else [None] * len(index)
    return zr[:-1][cutting], zr[1:][cutting], npts, index, syncs

