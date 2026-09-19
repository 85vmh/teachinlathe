"""The X and Z arrows: a shaft and a solid head, one per axis."""

from teachinlathe.widgets.backplot.actors import geometry, sizing
from teachinlathe.widgets.backplot.actors.base import Actor


class AxisArrowsActor(Actor):
    """Two arrows from the program origin, drawn over the toolpath.

    Y is not drawn. On a lathe the view is the XZ plane, so it would point
    straight at the camera and amount to a dot on the origin symbol.
    """

    def draw(self, ctx):
        mvp = ctx.mv.mvp()
        self._arrow(ctx, sizing.X_DIR, sizing.x_length(ctx),
                    ctx.colors['axis_x'], mvp)
        self._arrow(ctx, sizing.Z_DIR, sizing.z_length(ctx),
                    ctx.colors['axis_z'], mvp)

    def _arrow(self, ctx, direction, length, color, mvp):
        head_length = sizing.head_length()

        # The shaft stops at the head's base rather than at the tip, so a wide
        # line does not show through the point of the triangle.
        self.stroke(ctx,
                    [(0.0, 0.0, 0.0),
                     geometry.scaled(direction, length - head_length)],
                    color, mvp)

        self.fill(ctx,
                  geometry.arrow_head(direction, length,
                                      head_length, sizing.head_width()),
                  color, mvp)
