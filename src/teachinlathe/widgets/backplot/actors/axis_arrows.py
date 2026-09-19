"""The X and Z arrows: a shaft and a solid head, one per axis."""

from teachinlathe.widgets.backplot.actors import (geometry, palette, screen,
                                                  sizing)
from teachinlathe.widgets.backplot.actors.base import Actor


class AxisArrowsActor(Actor):
    """Two arrows from the program origin, drawn over the toolpath.

    Y is not drawn. On a lathe the view is the XZ plane, so it would point
    straight at the camera and amount to a dot on the origin symbol.

    Both are the same size at every zoom: they say which way the axes run,
    which is not a measurement, so growing with the view would be telling the
    operator something the arrows do not know. See ``sizing``.
    """

    LINE_WIDTH = palette.WIDTH_ARROW

    def draw(self, ctx):
        mvp = ctx.mv.mvp()
        scale = screen.pixels_per_unit(ctx, mvp)
        if scale is None:
            return
        px_per_z, px_per_x = scale

        # Each arrow is handed the scale of the axis it runs along and the one
        # it widens across, which are two different numbers on a viewport that
        # is not square.
        self._arrow(ctx, sizing.X_DIR, px_per_x, px_per_z,
                    ctx.colors['axis_x'], mvp)
        self._arrow(ctx, sizing.Z_DIR, px_per_z, px_per_x,
                    ctx.colors['axis_z'], mvp)

    def _arrow(self, ctx, direction, along, across, color, mvp):
        length = sizing.in_model(sizing.AXIS_LENGTH_PX, along)
        head_length = sizing.in_model(sizing.HEAD_LENGTH_PX, along)
        head_width = sizing.in_model(sizing.HEAD_HALF_WIDTH_PX, across)
        start = sizing.in_model(sizing.ORIGIN_CLEARANCE_PX, along)
        if length <= 0:
            return

        # The shaft runs from clear of the origin symbol to the head's base,
        # rather than from the centre to the tip: a wide line would otherwise
        # show through the point of the triangle at one end and out of the
        # symbol at the other.
        shaft_end = length - head_length
        if shaft_end > start:
            self.stroke(ctx,
                        [geometry.scaled(direction, start),
                         geometry.scaled(direction, shaft_end)],
                        color, mvp)

        self.fill(ctx,
                  geometry.arrow_head(direction, length, head_length,
                                      head_width),
                  color, mvp)
