"""The Z+ and X+ labels, each just past its arrow tip."""

from teachinlathe.widgets.backplot.actors import screen, sizing, text
from teachinlathe.widgets.backplot.actors.base import VX, VZ, Actor

#: The font, by the name ``text.FONTS`` knows it as.
FONT = "axis"

#: Gap between the arrow head and the label, in pixels. The profile editor's
#: own numbers - 2 past the head's half-width for Z, 4 for X.
Z_GAP_PX = 2.0
X_GAP_PX = 4.0


class AxisLettersActor(Actor):
    """The axis labels, placed against the arrows they name.

    Screen furniture, like the tick labels: the atlas draws in pixels, and the
    arrows are a pixel size too, so the placement below is the profile
    editor's ``AxesActor`` arithmetic with the sign of the vertical axis
    turned over - that canvas measures y downwards and this one upwards.

    They read "Z+" and "X+", as that canvas does. They could not before: the
    Hershey set has no '+'.
    """

    def draw(self, ctx):
        mvp = ctx.mv.mvp()
        scale = screen.pixels_per_unit(ctx, mvp)
        if scale is None:
            return
        viewport = (ctx.width, ctx.height)
        origin = text.to_screen(mvp, (0.0, 0.0, 0.0), viewport)
        if origin is None:
            return
        px_per_z, px_per_x = scale
        head = sizing.HEAD_LENGTH_PX
        half_width = sizing.HEAD_HALF_WIDTH_PX

        labels = []
        if ctx.view != VZ:
            tip = text.to_screen(
                mvp, (0.0, 0.0, sizing.in_model(sizing.AXIS_LENGTH_PX,
                                                px_per_z)), viewport)
            if tip is not None:
                # Above the shaft, centred back along it by half a head.
                labels.append(("Z+", _towards(tip[0], origin[0], head / 2.0),
                               origin[1] + half_width + Z_GAP_PX,
                               text.CENTRE, text.BOTTOM))
        if ctx.view != VX:
            tip = text.to_screen(
                mvp, (sizing.in_model(sizing.AXIS_LENGTH_PX, px_per_x),
                      0.0, 0.0), viewport)
            if tip is not None:
                # Right of the shaft, centred back along it by half a head.
                # The profile editor puts this one on the left; here the
                # stock and its hatching lie that way, and the label was
                # landing on them.
                labels.append(("X+", origin[0] + half_width + X_GAP_PX,
                               _towards(tip[1], origin[1], head / 2.0),
                               text.LEFT, text.CENTRE))

        # One call each, because the shader carries the colour as a uniform.
        for label, color in zip(labels, self._colors(ctx, labels)):
            text.draw(ctx, [label], color, FONT)

    @staticmethod
    def _colors(ctx, labels):
        return [ctx.colors['axis_z'] if label[0].startswith("Z")
                else ctx.colors['axis_x'] for label in labels]


def _towards(value, anchor, distance):
    """``value`` moved ``distance`` back towards ``anchor``."""
    return value - distance if value > anchor else value + distance
