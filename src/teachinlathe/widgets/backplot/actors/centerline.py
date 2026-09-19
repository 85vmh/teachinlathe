"""The centreline cross: the spindle axis, and the face datum that crosses it.

The horizontal run is the centreline proper - X zero, the axis the work turns
about. The vertical run is Z zero, the face the program is set from. Both are
drawn dash-dot and span the whole window, which is what makes them read as
datums rather than as geometry.

Ported from ``ToolpathCanvas.paintAxes()``, which drew exactly this pair
before drawing the arrows over it.
"""

from teachinlathe.widgets.backplot.actors import geometry, palette, screen
from teachinlathe.widgets.backplot.actors.base import Actor


class CenterlineActor(Actor):
    """Drawn under the toolpath, so a cut sitting on centre stays readable."""

    LINE_WIDTH = palette.WIDTH_CENTERLINE
    DEPTH_WRITE = False

    def __init__(self, host=None):
        super().__init__(host)
        self._edges = []
        self._key = None

    def draw(self, ctx):
        mvp = ctx.mv.mvp()
        key = screen.view_key(ctx, mvp)
        if key is None:
            return
        if key != self._key:
            self._edges = self._build(ctx, mvp)
            self._key = key
        self.stroke(ctx, self._edges, palette.CENTERLINE, mvp,
                    palette.CENTERLINE_ALPHA)

    def _build(self, ctx, mvp):
        """The dashes. Cutting them is the expensive half and the view is all
        it depends on, so it is done only when the view changes."""
        bounds = screen.visible_rect(ctx, mvp)
        scale = screen.pixels_per_unit(ctx, mvp)
        z_min, z_max, x_min, x_max = bounds
        px_per_z, px_per_x = scale

        # The dash pattern is in pixels, so each run is converted with the
        # scale of the direction it runs in - otherwise a non-square viewport
        # would dash the two lines differently.
        edges = geometry.dashed((0.0, 0.0, z_min), (0.0, 0.0, z_max),
                                palette.DASH_CENTERLINE, px_per_z)
        edges += geometry.dashed((x_min, 0.0, 0.0), (x_max, 0.0, 0.0),
                                 palette.DASH_CENTERLINE, px_per_x)
        return edges
