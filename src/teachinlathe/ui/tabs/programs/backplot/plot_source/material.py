"""The part as it is being cut, from a trail: the bar, less what the trail's
cutting moves took off it, each with the tool that made it (the trail's
``made_by``) - one model of a tool taking off material for the machine and a
simulation alike (simulation.logic.material).
"""

from __future__ import annotations

import logging

from teachinlathe.ui.tabs.programs.backplot.plot_source.trail import TRAVERSE

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
    bar when the bar, the frame it is in or the trail starts over."""

    def __init__(self):
        self._material = None
        self._basis = None
        self._done = 0
        self._shapes = {}

    def material_left(self, trail, stat, stock, origin):
        """The bar ``stock`` (the header's, as the plot holds it), less what
        ``trail``'s cutting moves took off it so far, in the frame ``origin``
        - (g5x, g92, XY rotation), machine units - a MaterialLeft; None with
        no bar."""
        from teachinlathe.simulation.logic.material import MaterialLeft

        basis = (tuple(sorted(stock.items())) if isinstance(stock, dict) else stock, origin, trail.generation)
        npts = trail.npts
        # the bar again when it, or the frame it is in, changed, or the trail
        # started over; a full logger moved its points down: read it again
        if basis != self._basis or npts < 2 or self._material is None:
            self._basis, self._done = basis, 0
            shape = stock_shape(stock)
            self._material = MaterialLeft(shape) if shape is not None else None
        elif npts < self._done:
            self._done = 0
        if self._material is None:
            return None
        # from the start of the last segment read: the logger may have
        # stretched it since; cut twice, it takes nothing more off
        found = cutting_segments(trail, stat, origin, max(0, self._done - 2))
        if found is None:
            return self._material
        starts, ends, self._done, index = found
        made_by = trail.made_by()
        for start, end, at in zip(starts, ends, index):
            tool = int(made_by.tools[at]) if made_by is not None and at < len(made_by) else 0
            self._material.cut([tuple(start), tuple(end)], self._shape(tool))
        return self._material

    def _shape(self, tool):
        """What cuts of tool ``tool``, as the Tool Library has it now: its
        drawing is part of the key, as the tool in its holder can be edited."""
        from teachinlathe.ui.tabs.programs.backplot import tool_source

        drawing = tool_source.describe(tool) if tool else None
        key = (tool, drawing)
        if key not in self._shapes:
            from teachinlathe.conversational.gcode.operations.profiling.tool_shape import cutting_shape
            from teachinlathe.core.tool_library_repository import tool_library_repository
            from teachinlathe.tooling.model.data_types import MountedTool

            self._shapes[key] = cutting_shape(MountedTool.of(tool_library_repository(), tool)) if tool else None
        return self._shapes[key]


def cutting_segments(trail, stat, origin, first=0):
    """The trail's cutting moves from point ``first`` on, as ``(starts, ends,
    npts, index)`` - two ``(N, 2)`` arrays of (z, r) in mm, from ``origin``
    (g5x, g92, XY rotation; machine units), the trail's length and, for each
    move, the index of the point it starts at - or None when there is no
    trail to read. A rapid cuts nothing: each segment is in the motion its
    end point was logged in, and one in the rapid colour is left out."""
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
    first = max(0, min(first, npts))
    points = np.frombuffer(raw, dtype=LOGGER_DTYPE, count=npts)[first:]
    if len(points) < 2:
        return np.empty((0, 2)), np.empty((0, 2)), npts, np.empty(0, dtype=np.int64)
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
    return zr[:-1][cutting], zr[1:][cutting], npts, index
