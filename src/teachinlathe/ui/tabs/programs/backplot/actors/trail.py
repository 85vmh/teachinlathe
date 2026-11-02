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

from teachinlathe.ui.tabs.programs.backplot import blade_middle, tool_source
from teachinlathe.ui.tabs.programs.backplot.plot_source.trail import HIDDEN_COLOR

try:
    import numpy as np
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
    """Upstream's live trail, its points moved for the blade that made them."""

    def __init__(self, host):
        super().__init__()
        self._host = host
        #: How far along Z each of the trail's points is moved, in its unit,
        #: worked out once a point is known - the points after it are added
        #: on - and again from the start when the trail starts over
        #: (``generation``), or the program, its contours or the unit change.
        self._shifts = np.zeros(0) if np is not None else None
        self._basis = None
        #: (shift, half) of each blade, as it was when the trail started
        self._blades = {}
        #: the thread plan whose lines are hidden, and its lines as an array
        self._plan_lines = (None, None)

    def upload_and_draw(self, ctx):
        trail = ctx.lp
        raw, npts, is_xyuv = trail.points()
        made_by = trail.made_by() if np is not None and not is_xyuv else None
        hidden = self._hidden(trail, npts, is_xyuv, made_by)
        if hidden is not None:
            raw = _without(raw, npts, hidden)
        if made_by is None:
            self._draw(ctx, trail, raw, npts, is_xyuv, hidden is not None)
            return
        corners = getattr(self._host, "blade_corners", None) or {}
        units = getattr(ctx.stat, "linear_units", 1.0) or 1.0
        basis = (trail.generation, id(corners), units)
        if basis != self._basis or npts < len(self._shifts):
            self._basis, self._shifts, self._blades = basis, np.zeros(0), {}
        known = min(npts, len(made_by))
        if known > len(self._shifts):
            added = blade_middle.trail_shifts(
                _sliced(made_by, len(self._shifts), known), corners, units, self._blade)
            self._shifts = np.concatenate([self._shifts, added])
        shifts = self._shifts[:npts]
        if len(shifts) < npts:
            # logged since the last poll, not known yet: where the last known is
            last = shifts[-1] if len(shifts) else 0.0
            shifts = np.concatenate([shifts, np.full(npts - len(shifts), last)])
        if not shifts.any():
            self._draw(ctx, trail, raw, npts, is_xyuv, hidden is not None)
            return
        self._draw(ctx, trail, blade_middle.trail_points(raw, npts, shifts), npts, is_xyuv, True)

    def _draw(self, ctx, trail, raw, npts, is_xyuv, changed):
        """The trail drawn from ``raw`` - its own points unless ``changed``."""
        if not changed:
            super().upload_and_draw(ctx)
            return
        ctx.lp = _MovedLogger(trail, raw, npts, is_xyuv)
        try:
            super().upload_and_draw(ctx)
        finally:
            ctx.lp = trail

    def _hidden(self, trail, npts, is_xyuv, made_by):
        """Which of the trail's points end a thread's pass, not drawn; None
        for none. A synced point whose line is not known yet - logged since
        the last poll - is taken to be a pass: a point drawn stays as it was
        drawn, and the program cuts threads."""
        find = getattr(self._host, "thread_plan", None)
        plan = find() if find is not None else None
        if np is None or plan is None or is_xyuv or npts < 2:
            return None
        try:
            synced = trail.synced(npts)
        except Exception as exc:
            LOG.debug("backplot trail: which lines are synced not known: %s", exc)
            return None
        if synced is None or made_by is None:
            return synced
        if self._plan_lines[0] is not plan:
            self._plan_lines = (plan, np.fromiter(plan.synced_lines, dtype=np.int64))
        on_plan = np.ones(npts, dtype=bool)
        known = min(npts, len(made_by.lines))
        on_plan[:known] = np.isin(made_by.lines[:known], self._plan_lines[1])
        hidden = synced & on_plan
        return hidden if hidden.any() else None

    def _blade(self, tool):
        if tool not in self._blades:
            self._blades[tool] = blade_middle.blade_offsets(tool_source.describe(tool))
        return self._blades[tool]


def _without(raw, npts, hidden):
    """The trail's points ``raw`` with the lines ending at ``hidden`` ones
    fully transparent: an array, which is read as the bytes are."""
    from rs274.glcanon_bake import LOGGER_DTYPE

    points = np.frombuffer(raw, dtype=LOGGER_DTYPE, count=npts).copy()
    points["c"][hidden] = HIDDEN_COLOR
    points["c2"][hidden] = HIDDEN_COLOR
    return points


def _sliced(origins, first, last):
    """Points ``first`` to ``last`` of a TrailOrigins."""
    return type(origins)(origins.tools[first:last], origins.lines[first:last])


class _MovedLogger:
    """The position logger with its points read already, moved
    (trail_points)."""

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
