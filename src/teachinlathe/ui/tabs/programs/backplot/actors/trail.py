"""The live trail, as the program is drawn for a blade.

The trail is of the point LinuxCNC moves - for a blade, the one it was
touched off on. The program is drawn down the blade's middle, a contour along
the corner it is cut with (``blade_middle``), and so is the trail: each point
moved as the program's are for the tool and the line that made it - which
the trail knows (plot_source.Trail.made_by), whichever source made it.

A thread's pass - a line made synced with the spindle (the trail's
``synced``) on one of the lines the loaded program cuts a thread with (the
host's ``thread_plan``) - is not drawn: the threading tooth's Vs stand for it
(actors.stock). It is drawn fully transparent. With no Vs - no stock, a
tap's G33.1 - it is drawn as any other line.
"""

import logging

from teachinlathe.diagnostics.model import operations
from teachinlathe.diagnostics.model.spans import timed
from teachinlathe.ui.tabs.programs.backplot import blade_middle, tool_source
from teachinlathe.ui.tabs.programs.backplot.plot_source.growing_array import GrowingArray
from teachinlathe.ui.tabs.programs.backplot.plot_source.trail import COLOR, COLOR2, HIDDEN_COLOR, POS

try:
    import numpy as np
    from rs274.glcanon_bake import LOGGER_DTYPE
except ImportError:  # pragma: no cover - depends on the LinuxCNC install
    np = None

LOG = logging.getLogger(__name__)

try:
    from rs274 import glcanon_scene
    _BACKPLOT_PART = glcanon_scene.BackplotPart
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot trail: preview modules unavailable: %s", exc)
    _BACKPLOT_PART = object


class CentredTrailPart(_BACKPLOT_PART):
    """Upstream's live trail, its points moved for the blade that made them.

    The points drawn - the trail's own, moved and with a thread's passes
    hidden - are worked out into one array kept from frame to frame: for a
    trail whose points stay as they were read (``appends_only``, the
    machine's), only the new ones and the last, which the logger moves on
    along its line; when a full logger drops its oldest (``dropped``), the
    array drops as many. A simulated run's are worked out again each frame.
    Everything from the start again when the trail starts over, or the
    program's contours, the unit or the thread plan change - and the
    vertices on the GPU with it, as upstream keeps those it had."""

    def __init__(self, host):
        super().__init__()
        self._host = host
        #: what the points were worked out for: (generation, contours, unit, plan)
        self._basis = None
        #: the trail's ``dropped`` they were worked out at
        self._dropped = 0
        #: how many points of ``_out`` were worked out from what made them
        self._done = 0
        #: the points as drawn, LOGGER_DTYPE
        self._out = GrowingArray(LOGGER_DTYPE) if np is not None else None
        #: whether a point worked out is moved or hidden: drawn from ``_out``
        self._moved = False
        #: (shift, half) of each blade, as it was when the trail started
        self._blades = {}
        #: the thread plan whose lines are hidden, and its lines as an array
        self._plan_lines = (None, None)

    def upload_and_draw(self, ctx):
        with timed(operations.BACKPLOT_TRAIL_DRAW):
            self._upload_and_draw(ctx)

    def _upload_and_draw(self, ctx):
        trail = ctx.lp
        raw, npts, is_xyuv = trail.points()
        if np is None or is_xyuv or npts < 2:
            self._basis = None
            super().upload_and_draw(ctx)
            return
        made_by = trail.made_by()
        plan = self._thread_plan()
        corners = getattr(self._host, "blade_corners", None) or {}
        units = getattr(ctx.stat, "linear_units", 1.0) or 1.0
        basis = (trail.generation, id(corners), units, id(plan))
        dropped = int(getattr(trail, "dropped", 0) or 0)
        again = basis != self._basis
        if not again and dropped != self._dropped:
            count = dropped - self._dropped
            if 0 < count <= self._done:
                self._out.drop_front(count)
                self._done -= count
            else:
                again = True
        if not again and npts < self._done:
            again = True
        if again:
            if self._basis is not None:
                # the vertices kept are of the points as they were drawn
                self.ring(ctx).invalidate()
            self._basis, self._done, self._moved, self._blades = basis, 0, False, {}
            self._out.clear()
        self._dropped = dropped
        first = max(0, self._done - 1) if trail.appends_only else 0
        known = min(npts, len(made_by)) if made_by is not None else 0
        self._work_out(trail, raw, npts, first, made_by, known, plan, corners, units)
        self._done = max(first, known)
        if not self._moved:
            super().upload_and_draw(ctx)
            return
        ctx.lp = _MovedLogger(trail, self._out.view(), npts, is_xyuv)
        try:
            super().upload_and_draw(ctx)
        finally:
            ctx.lp = trail

    def _work_out(self, trail, raw, npts, first, made_by, known, plan, corners, units):
        """Points ``first`` to ``npts`` of ``_out``: the trail's, moved along
        Z for the blade that made them - a point logged since the last poll,
        whose maker is not known yet, as far as the last known one - and a
        thread's passes fully transparent."""
        source = np.frombuffer(raw, dtype=LOGGER_DTYPE, count=npts)
        part = self._out.resize(npts)[first:]
        part[:] = source[first:]
        shifts = np.zeros(npts - first)
        if known > first:
            shifts[:known - first] = blade_middle.trail_shifts(
                _sliced(made_by, first, known), corners, units, self._blade)
            if known < npts:
                shifts[known - first:] = shifts[known - first - 1]
        if shifts.any():
            part[POS][:, 2] += shifts
            self._moved = True
        hidden = self._hidden(trail, npts, first, made_by, known, plan)
        if hidden is not None and hidden.any():
            part[COLOR][hidden] = HIDDEN_COLOR
            part[COLOR2][hidden] = HIDDEN_COLOR
            self._moved = True

    def _thread_plan(self):
        find = getattr(self._host, "thread_plan", None)
        return find() if find is not None else None

    def _hidden(self, trail, npts, first, made_by, known, plan):
        """Which of points ``first`` to ``npts`` end a thread's pass, not
        drawn; None for none. A synced point whose line is not known yet -
        logged since the last poll - is taken to be a pass: a point drawn
        stays as it was drawn, and the program cuts threads."""
        if plan is None:
            return None
        try:
            synced = trail.synced(npts)
        except Exception as exc:
            LOG.debug("backplot trail: which lines are synced not known: %s", exc)
            return None
        if synced is None:
            return None
        synced = synced[first:npts]
        if made_by is None:
            return synced
        if self._plan_lines[0] is not plan:
            self._plan_lines = (plan, np.fromiter(plan.synced_lines, dtype=np.int64))
        on_plan = np.ones(npts - first, dtype=bool)
        if known > first:
            on_plan[:known - first] = np.isin(made_by.lines[first:known], self._plan_lines[1])
        return synced & on_plan

    def _blade(self, tool):
        if tool not in self._blades:
            self._blades[tool] = blade_middle.blade_offsets(tool_source.describe(tool))
        return self._blades[tool]


def _sliced(origins, first, last):
    """Points ``first`` to ``last`` of a TrailOrigins."""
    return type(origins)(origins.tools[first:last], origins.lines[first:last])


class _MovedLogger:
    """The position logger with its points worked out already: moved for the
    blade, a thread's passes hidden."""

    def __init__(self, logger, raw, npts, is_xyuv):
        self._logger = logger
        self._points = (raw, npts, is_xyuv)

    def points(self):
        return self._points

    def __getattr__(self, name):
        return getattr(self._logger, name)


def install(scene, host):
    """Swap the live trail for one drawn down the blade's middle, in place."""
    scene.backplot = scene.replace(scene.backplot, CentredTrailPart(host))
    return scene.backplot
