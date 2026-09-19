"""The rapids, dashed.

Upstream draws the whole trajectory - traverse, feed and arc - from one baked
buffer, and that buffer is deliberately never quad-expanded, so it has no
width and no dash to give. Its own ``ProgramPart`` says as much: "nothing in
this renderer dashes, and there is no attribute or uniform left to do it
with".

So the rapids are taken out of it and drawn here instead. ``show_rapids`` is
already the switch for that - upstream hides the traverse category on the
shader's side - and what is left on the fast path is the cutting moves, which
are the bulk of a program and want none of this.

What makes it affordable is that the parsed program is now arrays.
``gcode.parse`` builds the preview in C++ and hands it over as
``program_geometry``: ``positions()`` is every drawn point and ``kinds`` says
which of traverse, feed or arc each one ends. Reading the rapids out of that
is two numpy indexing steps, and it happens once per program, not per frame.
"""

import logging
import math

from teachinlathe.widgets.backplot.actors import geometry, palette, screen
from teachinlathe.widgets.backplot.actors.base import Actor

LOG = logging.getLogger(__name__)

try:
    import numpy as np
    from rs274.glcanon_bake import KIND_TRAVERSE
    LIB_GOOD = True
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot rapids: preview modules unavailable: %s", exc)
    KIND_TRAVERSE = 0
    LIB_GOOD = False

#: Above this many rapid segments the dashes are not built and the moves draw
#: solid instead.
#:
#: Dashing is per-segment Python and its result depends on the zoom, so it is
#: rebuilt when the operator zooms. A few hundred segments is nothing; a
#: program that rapids tens of thousands of times would make zooming lurch,
#: and a solid rapid is a far better outcome than that.
MAX_DASHED_SEGMENTS = 5000

#: How much the zoom has to change before the dashes are rebuilt, as a
#: fraction of itself. Bucketing is what stops a rebuild on every frame of a
#: drag-zoom while keeping the dash visibly the same size.
#:
#: Fractional, so the buckets have to be geometric - a fixed step in pixels
#: per unit is a huge relative change when zoomed out and an invisible one
#: when zoomed in. Hence the logarithm below.
SCALE_BUCKET = 0.02


class RapidsActor(Actor):
    """Drawn under the cutting moves, so a cut over a rapid reads as the cut.

    In the program's own frame, not the actors' usual one: these are the
    program's vertices, and ``preview_mvp`` is the transform upstream draws
    them with.
    """

    LINE_WIDTH = palette.WIDTH_TRAVERSE
    DEPTH_WRITE = False
    FOLLOW_PROGRAM_ORIGIN = False

    def __init__(self, host=None):
        super().__init__(host)
        self._source = None         # what the segments were read from
        self._segments = None       # (N, 2, 3) endpoints, model space
        self._dashed = None         # the vertex list, for one zoom bucket
        self._dashed_at = None

    def draw(self, ctx):
        segments = self._read(ctx)
        if segments is None or not len(segments):
            return
        mvp = ctx.preview_mvp()
        scale = screen.pixels_per_unit(ctx, mvp)
        if scale is None:
            return
        self.stroke(ctx, self._dash(segments, scale[0]), palette.TRAVERSE,
                    mvp)

    # ── the program's rapids, once per program ──────────────────────────────

    def _read(self, ctx):
        """The traverse segments as ``(N, 2, 3)``, or ``None``.

        Cached against the geometry object, held and compared by identity:
        a reload replaces it, and nothing else changes what the rapids are.
        """
        if not LIB_GOOD or ctx.canon is None:
            return None
        program = getattr(ctx.canon, "program_geometry", None)
        if program is None:
            return None

        try:
            points = program.positions(0)
            kinds = program.kinds
        except (AttributeError, IndexError, TypeError) as exc:
            LOG.debug("backplot rapids: no usable program geometry: %s", exc)
            return None
        if len(points) < 2:
            return None

        # The object itself, compared by identity, and a reference kept to
        # it. ``id()`` would be enough until the moment it is not: CPython
        # reuses an address as soon as the object at it is freed, so a reload
        # could be handed the rapids of the program it replaced.
        if self._source is program:
            return self._segments

        # Segment i joins vertex i to i+1 and takes the kind of the vertex it
        # ends on - GL's last-vertex provoking convention, which is what
        # upstream's own span builder reads too.
        is_rapid = kinds[1:] == KIND_TRAVERSE
        starts = points[:-1][is_rapid]
        ends = points[1:][is_rapid]
        self._segments = np.stack([starts, ends], axis=1)
        self._source = program
        self._dashed = None
        return self._segments

    # ── the dashes, once per zoom ───────────────────────────────────────────

    def _dash(self, segments, px_per_unit):
        """``segments`` as GL_LINES endpoints, cut into dashes.

        The dash is a pixel length, so it has to be rebuilt when the scale
        changes - but only then, and only in buckets, so a drag of the zoom
        does not rebuild on every frame of it.
        """
        bucket = (round(math.log(px_per_unit) / math.log(1.0 + SCALE_BUCKET))
                  if px_per_unit > 0 else 0)
        if bucket == self._dashed_at and self._dashed is not None:
            return self._dashed

        if len(segments) > MAX_DASHED_SEGMENTS:
            edges = [tuple(point) for segment in segments for point in segment]
        else:
            edges = []
            for start, end in segments:
                edges.extend(geometry.dashed(tuple(start), tuple(end),
                                             palette.DASH_TRAVERSE,
                                             px_per_unit))
        self._dashed = edges
        self._dashed_at = bucket
        return edges
