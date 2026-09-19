"""The scale round the edge of the plot: ticks on all four sides, and labels.

Ported from ``ToolpathCanvas.paintTicks()``. Z reads along the top and bottom
edges in millimetres, X up the left and right edges in diameter - the number
the operator sets the tool to, not the radius the scene draws in.

This is the one actor working in two spaces at once. The **marks** are model
geometry: they sit at a model Z or X, and only their length is a screen
measurement. The **labels** are screen furniture - a glyph quad at a pixel
position - so they are placed by projecting the mark's anchor and then moving
in pixels, which is also the space the glyph atlas draws in. See ``text``.
"""

from teachinlathe.widgets.backplot.actors import (palette, screen, stepping,
                                                  text)
from teachinlathe.widgets.backplot.actors.base import Actor
from teachinlathe.widgets.backplot.actors.units import mm, to_mm

#: Tick lengths in pixels: the long one for a major or 5 mm mark, the short
#: one for everything else.
LONG_TICK_PX = 7.0
SHORT_TICK_PX = 3.0

#: Gap between a tick and its label, in pixels.
LABEL_GAP_PX = 2.0

#: The font, by the name ``text.FONTS`` knows it as.
FONT = "tick"


class TicksActor(Actor):
    """Drawn with the other annotation, over the toolpath."""

    LINE_WIDTH = palette.WIDTH_TICK

    def __init__(self, host=None):
        super().__init__(host)
        self._scales = None
        self._key = None

    def draw(self, ctx):
        mvp = ctx.mv.mvp()
        key = screen.view_key(ctx, mvp)
        if key is None:
            return
        if key != self._key:
            self._scales = self._build(ctx, mvp)
            self._key = key
        if self._scales is None:
            return
        for marks, labels, color in self._scales:
            self.stroke(ctx, marks, color, mvp)
            text.draw(ctx, labels, color, FONT)

    def _build(self, ctx, mvp):
        """Both scales, as ``(marks, labels, colour)``.

        Where every one of them goes depends on the view and on nothing else,
        so this runs when the operator moves the view rather than when the
        machine moves - which is twenty-five times a second while a program
        runs, and used to rebuild all of it each time.
        """
        bounds = screen.visible_rect(ctx, mvp)
        scale = screen.pixels_per_unit(ctx, mvp)
        edges = _edges(ctx, mvp, bounds)
        if edges is None:
            return None
        return [self._z_scale(ctx, mvp, bounds, scale, edges),
                self._x_scale(ctx, mvp, bounds, scale, edges)]

    # ── the two scales ──────────────────────────────────────────────────────

    def _z_scale(self, ctx, mvp, bounds, scale, edges):
        """Along the top and bottom edges, in millimetres of Z."""
        z_min, z_max, x_min, x_max = bounds
        px_per_z, px_per_x = scale
        minor, major = stepping.steps(px_per_z * mm(1.0))

        marks = []
        labels = []
        for z_mm in stepping.marks(to_mm(z_min), to_mm(z_max), minor):
            z = mm(z_mm)
            length, labelled = _tick_style(z_mm, major)
            reach = length / px_per_x
            marks.extend([(x_min, 0.0, z), (x_min + reach, 0.0, z)])
            marks.extend([(x_max, 0.0, z), (x_max - reach, 0.0, z)])
            if not labelled:
                continue
            column = text.to_screen(mvp, (0.0, 0.0, z), (ctx.width, ctx.height))
            if column is None:
                continue
            offset = length + LABEL_GAP_PX
            label = _label(z_mm)
            # Hanging below the top edge, standing above the bottom one.
            labels.append((label, column[0], edges["top"] - offset,
                           text.CENTRE, text.TOP))
            labels.append((label, column[0], edges["bottom"] + offset,
                           text.CENTRE, text.BOTTOM))

        return marks, labels, palette.AXIS_Z

    def _x_scale(self, ctx, mvp, bounds, scale, edges):
        """Up the left and right edges, in millimetres of diameter."""
        z_min, z_max, x_min, x_max = bounds
        px_per_z, px_per_x = scale
        # Halved: a diameter millimetre is worth half a radius millimetre on
        # screen. See ``stepping``.
        minor, major = stepping.steps(px_per_x * mm(1.0) / 2.0)

        marks = []
        labels = []
        for diameter in stepping.marks(to_mm(x_min) * 2, to_mm(x_max) * 2,
                                       minor):
            x = mm(diameter / 2.0)
            length, labelled = _tick_style(diameter, major)
            reach = length / px_per_z
            marks.extend([(x, 0.0, z_min), (x, 0.0, z_min + reach)])
            marks.extend([(x, 0.0, z_max), (x, 0.0, z_max - reach)])
            if not labelled:
                continue
            row = text.to_screen(mvp, (x, 0.0, 0.0), (ctx.width, ctx.height))
            if row is None:
                continue
            offset = length + LABEL_GAP_PX
            label = _label(diameter)
            labels.append((label, edges["left"] + offset, row[1],
                           text.LEFT, text.CENTRE))
            labels.append((label, edges["right"] - offset, row[1],
                           text.RIGHT, text.CENTRE))

        return marks, labels, palette.AXIS_X


def _edges(ctx, mvp, bounds):
    """Where the window's four edges are, in screen pixels.

    Projected rather than assumed. Which model bound is the top of the screen
    depends on the sign the view maps X with, and this plot's X grows
    *downwards*; reading it off the projection is one line and cannot be got
    backwards.
    """
    viewport = (ctx.width, ctx.height)
    z_min, z_max, x_min, x_max = bounds
    corners = [text.to_screen(mvp, point, viewport)
               for point in ((x_min, 0.0, z_min), (x_max, 0.0, z_max))]
    if any(corner is None for corner in corners):
        return None
    (left_a, top_a), (left_b, top_b) = corners
    return {
        "left": min(left_a, left_b),
        "right": max(left_a, left_b),
        "bottom": min(top_a, top_b),
        "top": max(top_a, top_b),
    }


def _tick_style(value, major):
    """``(length in pixels, whether it is labelled)`` for one mark."""
    if stepping.is_multiple(value, major):
        return LONG_TICK_PX, True
    if stepping.is_multiple(value, stepping.EMPHASIS_MM):
        return LONG_TICK_PX, False
    return SHORT_TICK_PX, False


def _label(value):
    """A tick's number. Every step in ``stepping`` is a whole millimetre, so
    this is always a plain integer."""
    return str(int(round(value)))
