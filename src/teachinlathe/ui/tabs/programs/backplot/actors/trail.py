"""The live trail, as the program is drawn for a blade.

The position logger records the point LinuxCNC moves - for a blade, the one it
was touched off on. The program is drawn down the blade's middle, a contour
along the corner it is cut with (``blade_middle``), and so is the trail: each
point moved as the program's are for the tool in and the line being cut when
it is logged.
"""

import logging

from teachinlathe.ui.tabs.programs.backplot import blade_middle

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
        #: How far along Z each of the logger's points is moved, in its unit:
        #: decided when the point is first seen - by the tool in then and the
        #: line it was cutting - and kept, so a trail keeps the moves it was
        #: made with when the tool or the line changes.
        self._shifts = np.zeros(0) if np is not None else None

    def upload_and_draw(self, ctx):
        if np is None:
            super().upload_and_draw(ctx)
            return
        logger = ctx.lp
        raw, npts, is_xyuv = logger.points()
        if is_xyuv:
            super().upload_and_draw(ctx)
            return
        if npts < len(self._shifts):
            # cleared, or full and moved down: from the start again
            self._shifts = np.zeros(0)
        new = npts - len(self._shifts)
        if new > 0:
            shift, half = blade_middle.blade_offsets(getattr(self._host, "insert", None))
            corners = getattr(self._host, "blade_corners", None) or {}
            line = int(getattr(ctx.stat, "motion_line", 0) or 0)
            units = getattr(ctx.stat, "linear_units", 1.0) or 1.0
            now = (shift + corners.get(line, 0) * half) * units
            self._shifts = np.concatenate([self._shifts, np.full(new, now)])
        if not self._shifts[:npts].any():
            super().upload_and_draw(ctx)
            return
        ctx.lp = _MovedLogger(logger, blade_middle.trail_points(raw, npts, self._shifts), npts, is_xyuv)
        try:
            super().upload_and_draw(ctx)
        finally:
            ctx.lp = logger


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
