"""The live trail, as the program is drawn for a blade.

The trail is of the point LinuxCNC moves - for a blade, the one it was
touched off on. The program is drawn down the blade's middle, a contour along
the corner it is cut with (``blade_middle``), and so is the trail: each point
moved as the program's are for the tool and the line that made it - which
the trail knows (plot_source.Trail.made_by), whichever source made it.
"""

import logging

from teachinlathe.ui.tabs.programs.backplot import blade_middle, tool_source

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

    def upload_and_draw(self, ctx):
        trail = ctx.lp
        raw, npts, is_xyuv = trail.points()
        made_by = trail.made_by() if np is not None and not is_xyuv else None
        if made_by is None:
            super().upload_and_draw(ctx)
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
            super().upload_and_draw(ctx)
            return
        ctx.lp = _MovedLogger(trail, blade_middle.trail_points(raw, npts, shifts), npts, is_xyuv)
        try:
            super().upload_and_draw(ctx)
        finally:
            ctx.lp = trail

    def _blade(self, tool):
        if tool not in self._blades:
            self._blades[tool] = blade_middle.blade_offsets(tool_source.describe(tool))
        return self._blades[tool]


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
