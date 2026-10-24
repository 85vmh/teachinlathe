"""The material left so far, mirrored above the centre line.

With the mirror on, the half of the plot the toolpath is not on shows the bar
as it stands now: the stock, hatched, cut back to wherever the tool has been.
Before a program runs - or after the plot is cleared - that is the whole bar;
as the machine cuts, the material goes with it.

**It is read off the live trail, not the program.** The trail - logged in the
machine's units, not the scene's, so scaled first - is what the
machine actually did, so this follows a run that was stopped, restarted or
run from a line, where the program's own finished profile would show a part
that does not exist yet. The radius at each Z is worked out exactly as
``profile.finished`` does it for the program - the smallest radius any cutting
move reached, OD only, with the same caveat for boring - from the trail's feed
moves. A rapid cuts nothing: the trail colours each point by the machine's
motion type, and a segment in the rapid colour is left out.

Drawn in the moving part of the scene, after the trail and before the tool,
because it changes while the program runs; the static layer is drawn once and
would freeze it. Kept in step with the tool: on every frame only the part of
the trail from the last segment read on is cut into the radii - the radius left
only ever shrinks, so those moves are all that can change it. The hatch is cut
again only when the radii did change.

The material left is bounded by a solid line, the profile itself, so where
the hatch stops reads as an edge and not as hatching that thinned out.
"""

import logging

from teachinlathe.ui.tabs.programs.backplot import blade_middle
from teachinlathe.ui.tabs.programs.backplot.actors import palette, profile
from teachinlathe.ui.tabs.programs.backplot.actors.units import mm
from teachinlathe.ui.tabs.programs.backplot.actors.base import Actor
from teachinlathe.ui.tabs.programs.backplot.actors.stock import StockActor

LOG = logging.getLogger(__name__)

try:
    import numpy as np
    from rs274.glcanon_bake import LOGGER_DTYPE
    LIB_GOOD = profile.LIB_GOOD
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot remaining: preview modules unavailable: %s", exc)
    LIB_GOOD = False

#: The trail's colour slot a rapid is logged in: the machine's motion type,
#: EMC_MOTION_TYPE_TRAVERSE.
TRAVERSE = 1


def _blade(host):
    """``(shift, half)`` of the tool in now, in the scene's unit: from the
    point it was touched off on to its middle along Z, and half its width -
    ``(0, 0)`` for anything but a blade (``blade_middle``)."""
    shift, half = blade_middle.blade_offsets(getattr(host, "insert", None))
    return mm(shift), mm(half)


def cutting_segments(ctx, first=0, shift=0.0):
    """The trail's cutting moves from point ``first`` on, as ``(starts, ends,
    npts)`` - two ``(N, 3)`` arrays in the actor's frame and the trail's
    length - or ``None`` when there is no trail to read.
    """
    if not LIB_GOOD or ctx.lp is None:
        return None
    try:
        raw, npts, is_xyuv = ctx.lp.points()
        colours = ctx.lp.get_colors()
    except (AttributeError, TypeError) as exc:
        LOG.debug("backplot remaining: no trail to read: %s", exc)
        return None
    if is_xyuv:
        return None
    transform = profile.machine_to_actor(ctx)
    if transform is None:
        return None

    first = max(0, min(first, npts))
    points = np.frombuffer(raw, dtype=LOGGER_DTYPE, count=npts)[first:]
    if len(points) < 2:
        return np.empty((0, 3)), np.empty((0, 3)), npts
    # each segment is in the motion its end point was logged in
    rapid = np.asarray(colours[TRAVERSE], dtype=np.uint8)
    cutting = ~np.all(points["c"][1:] == rapid, axis=1)
    # The trail is logged in the machine's own units; the program, and the
    # transform from it, are in the scene's internal unit. Scaled as
    # upstream's trail part scales it before drawing.
    unit = 1.0 / ((getattr(ctx.stat, "linear_units", 1.0) or 1.0) * 25.4)
    local = profile._to_actor(points["pos"].astype(float) * unit, transform)
    # a blade's trail down its middle, as the program is drawn
    local[:, 2] += shift
    return local[:-1][cutting], local[1:][cutting], npts


def live(ctx, z_start, z_end, outer_radius, host=None):
    """The radius left at every Z, from the whole trail's cutting moves.

    ``None`` when nothing has been cut - no trail, or only rapids - which
    draws the bar whole.
    """
    if z_end <= z_start:
        return None
    shift, half = _blade(host)
    found = cutting_segments(ctx, shift=shift)
    if found is None or not len(found[0]):
        return None
    radii = np.full(profile.SAMPLES, float(outer_radius))
    _cut_into(radii, z_start, z_end, outer_radius, found[0], found[1], half)
    return profile.Profile(z_start, z_end, radii)


def _cut_into(radii, z_start, z_end, outer_radius, starts, ends, half=0.0):
    step = (z_end - z_start) / (profile.SAMPLES - 1)
    # a blade's moves swept across its width
    starts, ends = blade_middle.swept(starts, ends, half)
    profile._cut(radii, z_start, step, starts, ends)
    np.clip(radii, 0.0, outer_radius, out=radii)


class RemainingStockActor(StockActor):
    """The stock, mirrored across the centre line, cut to the material left.

    Everything a ``StockActor`` draws - the skin, the end faces, the bore,
    the hatch - with X turned over, the hatch stopped at the trail's profile
    instead of the program's, and that profile drawn as a solid line.
    """

    def __init__(self, host=None):
        super().__init__(host)
        #: What the radii were built against - the stock and the frame - and
        #: how much of the trail is in them.
        self._basis = None
        self._done = 0
        self._radii = None
        self._live = None

    def stroke(self, ctx, points, color, mvp=None, alpha=1.0):
        """As every actor strokes, on the other side of the centre line."""
        Actor.stroke(ctx, [(-x, y, z) for x, y, z in points], color, mvp, alpha)

    def draw(self, ctx):
        super().draw(ctx)
        if self._live is None:
            return
        line = self._live.polyline()
        edges = []
        for (r0, z0), (r1, z1) in zip(line, line[1:]):
            edges.extend([(r0, 0.0, z0), (r1, 0.0, z1)])
        self.stroke(ctx, edges, palette.STOCK, ctx.mv.mvp())

    def _finished(self, ctx, low, high):
        """The trail's profile, brought up to date with the trail.

        Read from the last segment taken before on, every frame - not only when
        the trail has more points. The logger does not add a point while the
        tool runs on in a straight line: it moves the last one along, so the
        trail can grow without its length changing. The last segment is cut
        again each time; the radius left only shrinks, so cutting it twice
        changes nothing.
        """
        stat = ctx.stat
        basis = (low, high, (tuple(stat.g5x_offset), tuple(stat.g92_offset), stat.rotation_xy))
        npts = _trail_length(ctx)

        # The whole bar again only when the stock or the frame moved, or the
        # trail was cleared.
        if basis != self._basis or npts < 2:
            self._basis = basis
            self._done = 0
            self._radii = np.full(profile.SAMPLES, float(high[0]))
            self._live = None
            if npts < 2:
                return None
        # Shorter than before but not cleared: the logger, full, dropped its
        # oldest points and moved the rest down. What they cut stays cut - the
        # radii are kept - and the trail is read again from its start.
        elif npts < self._done:
            self._done = 0

        # from the start of the last segment read: it is the one the logger
        # may have stretched since
        # the tool in now: a blade's trail down its middle, swept across it
        shift, half = _blade(self._host)
        found = cutting_segments(ctx, max(0, self._done - 2), shift)
        if found is None:
            return self._live
        starts, ends, self._done = found
        if len(starts):
            before = self._radii.copy()
            _cut_into(self._radii, low[1], high[1], high[0], starts, ends, half)
            if self._live is None or not np.array_equal(before, self._radii):
                # a new object, so the hatch - keyed on it - is cut again
                self._live = profile.Profile(low[1], high[1], self._radii.copy())
        return self._live


def _trail_length(ctx):
    try:
        return int(ctx.lp.npts)
    except (AttributeError, TypeError, ValueError):
        return 0
