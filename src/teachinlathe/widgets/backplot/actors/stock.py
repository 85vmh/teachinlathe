"""The bar the program cuts from: its outline, and the hatching inside it.

Ported from ``ToolpathStockActor``. The stock is not something the preview can
work out - nothing in the G-code says how long the bar is or what it started
at - so it comes from the conversational program's own header, which
``backplot.workpiece`` finds beside the loaded file.

Drawn on the diameter, like everything else the operator reads: the outline
sits at the external diameter and, when the bar is bored, a second line at the
internal one.

**The hatch stops at the finished profile**, so the material is not drawn over
the toolpath that removes it. Where the profile comes from, and what it
assumes, is ``profile.finished``; with no program loaded there is nothing to
stop at and the bar hatches whole.
"""

import math

from teachinlathe.widgets.backplot.actors import (geometry, palette, profile,
                                                  screen)
from teachinlathe.widgets.backplot.actors.base import Actor
from teachinlathe.widgets.backplot.actors.units import mm

#: Pitch of the hatch lines, in pixels, as the QML spaced them.
HATCH_PITCH_PX = 12.0

#: A guard, as in ``stepping.marks``: a bar metres long at a hard zoom would
#: otherwise fill the window with lines a pixel apart.
MAX_HATCH_LINES = 2000

#: How much the zoom has to change before the hatch is cut again, as a
#: fraction of itself. Geometric, for the reason ``rapids.SCALE_BUCKET`` is.
SCALE_BUCKET = 0.02

#: How finely a hatch line is walked when it is cut to the profile, in pixels.
#: Small enough that a shoulder cuts a line where the shoulder is rather than
#: a few pixels past it, large enough not to turn one diagonal into hundreds
#: of fragments.
PROFILE_STEP_PX = 2.0


class StockActor(Actor):
    """Drawn under the toolpath, so a cut reads as removing material from it.

    Holds the host rather than reading a context field, because the stock is
    the host's knowledge: ``FrameContext`` is upstream's contract and the
    workpiece is not in it.
    """

    LINE_WIDTH = palette.WIDTH_STOCK
    DEPTH_WRITE = False

    def __init__(self, host=None):
        super().__init__(host)
        #: The profile, and what it was built from. Reading it walks the whole
        #: program, so it belongs on a load and not on a frame - without this
        #: a ten-thousand point program measured a whole core at the redraw
        #: rate, and the plot is redrawn every time the machine moves.
        self._profile = None
        self._profile_key = None
        #: The hatch, and the zoom bucket it was cut for. Its pitch is in
        #: pixels, so it only changes when the view does.
        self._hatch_edges = None
        self._hatch_key = None

    def _dimensions(self):
        """``(length, outer diameter, bore diameter)`` in mm, or ``None``."""
        stock = getattr(self._host, "stock", None) or {}
        try:
            length = float(stock.get("stock_length") or 0.0)
            outer = float(stock.get("external_diameter") or 0.0)
            bore = float(stock.get("internal_diameter") or 0.0)
        except (TypeError, ValueError):
            return None
        if length <= 0 or outer <= 0:
            return None
        return length, outer, max(0.0, min(bore, outer))

    def draw(self, ctx):
        dimensions = self._dimensions()
        if dimensions is None:
            return
        length, outer, bore = dimensions
        mvp = ctx.mv.mvp()

        # The bar runs back from the face at Z zero; X is halved because the
        # scene draws radius and the header states diameter.
        near, far = 0.0, mm(-length)
        skin, core = mm(outer / 2.0), mm(bore / 2.0)

        self._outline(ctx, near, far, skin, core, bore, mvp)
        self._hatch(ctx, near, far, skin, core, mvp)

    # ── the hatch, and what it stops at ─────────────────────────────────────

    def _outline(self, ctx, near, far, skin, core, bore, mvp):
        """The skin, the two end faces, and the bore if there is one.

        No line is drawn along the axis: an unbored bar is solid to centre,
        and drawing one there would read as a hole.
        """
        self.stroke(ctx, [(skin, 0.0, near), (skin, 0.0, far),
                          (skin, 0.0, far), (core, 0.0, far),
                          (skin, 0.0, near), (core, 0.0, near)],
                    palette.STOCK, mvp)
        if bore > 0:
            self.stroke(ctx, [(core, 0.0, near), (core, 0.0, far)],
                        palette.STOCK_BORE, mvp)

    def _hatch(self, ctx, near, far, skin, core, mvp):
        """Diagonals at a fixed pixel pitch, cut to the stock and to the part.

        The diagonal is 45 degrees *on screen*, not in the model, so its two
        components are sized by their own scales - which is also why the pitch
        is stepped along Z in pixels rather than in millimetres.
        """
        scale = screen.pixels_per_unit(ctx, mvp)
        if scale is None:
            return
        px_per_z, px_per_x = scale

        low = (min(core, skin), min(near, far))
        high = (max(core, skin), max(near, far))

        depth_px = (high[0] - low[0]) * px_per_x
        if depth_px <= 0:
            return
        run_z = depth_px / px_per_z          # a 45-degree screen diagonal
        pitch_z = HATCH_PITCH_PX / px_per_z
        if pitch_z <= 0:
            return

        # The profile first, and it is part of the key. Checking the zoom
        # alone would keep the old hatch when a new program loaded onto the
        # same bar at the same zoom - the stock is unchanged, so nothing in
        # the view says anything moved, and the hatching would go on stopping
        # at the shape the last program cut.
        finished = self._finished(ctx, low, high)
        bucket = (round(math.log(px_per_z) / math.log(1.0 + SCALE_BUCKET))
                  if px_per_z > 0 else 0)
        key = (bucket, low, high, finished)
        if key != self._hatch_key:
            edges = []
            # Started a full run before the near end so the first diagonals
            # that only clip the corner are still drawn.
            position = low[1] - run_z
            while (position < high[1] + run_z
                   and len(edges) < 2 * MAX_HATCH_LINES):
                clipped = geometry.clip_to_rect(
                    (high[0], 0.0, position), (low[0], 0.0, position + run_z),
                    low, high)
                if clipped is not None:
                    edges.extend(_inside_part(clipped, finished, core,
                                              px_per_z))
                position += pitch_z
            self._hatch_edges = edges
            self._hatch_key = key

        self.stroke(ctx, self._hatch_edges, palette.HATCH, mvp)

    def _finished(self, ctx, low, high):
        """The finished profile, built once per program and per frame.

        Keyed on the geometry object - a reload replaces it - on the stock it
        was measured against, since that is what it is sampled between, and on
        **the offsets**.

        The offsets are not obvious and were missing. The program's points are
        in machine coordinates; the profile is built in the frame the stock is
        drawn in, which is the program origin - so a datum set mid-program, a
        facing pass that makes its own last cut the new Z zero, moves the
        profile without touching the program, the stock or the view. The
        toolpath translated and the hatching stayed where the old origin had
        put it.

        Only the ``place`` transform matters here, not the camera: the camera
        cancels out of ``profile.machine_to_actor``, and a profile is in model
        units either way.
        """
        program = getattr(ctx.canon, "program_geometry", None)
        stat = ctx.stat
        frame = (tuple(stat.g5x_offset), tuple(stat.g92_offset),
                 stat.rotation_xy)
        held, was = self._profile_key or (None, None)
        # The object itself, compared by identity, and a reference kept to it.
        # ``id()`` would be enough until the moment it is not: CPython reuses
        # an address as soon as the object at it is freed, so a reload could
        # be handed the profile of the program it replaced.
        if held is not program or was != (low, high, frame):
            self._profile = profile.finished(ctx, low[1], high[1], high[0])
            self._profile_key = (program, (low, high, frame))
        return self._profile


def _inside_part(segment, finished, core, px_per_z):
    """The parts of one hatch line that lie in material still there.

    With no profile the whole line is material - that is a bar with no program
    against it. With one, the line is walked and only the runs inside the
    finished shape are kept, so the hatch stops at the shoulder instead of
    carrying on over the toolpath.
    """
    start, end = segment
    if finished is None:
        return [start, end]

    span = end[2] - start[2]
    steps = max(1, int(abs(span) * px_per_z / PROFILE_STEP_PX))
    kept = []
    run_start = None

    for i in range(steps + 1):
        t = i / steps
        z = start[2] + span * t
        x = start[0] + (end[0] - start[0]) * t
        point = (x, 0.0, z)
        if core <= x <= finished.at(z):
            if run_start is None:
                run_start = point
            last_inside = point
        elif run_start is not None:
            kept.extend([run_start, last_inside])
            run_start = None

    if run_start is not None:
        kept.extend([run_start, last_inside])
    return kept
