"""The centreline cross: the spindle axis, and the face datum that crosses it.

The horizontal run is the centreline proper - X zero, the axis the work turns
about. The vertical run is Z zero, the face the program is set from. Both are
drawn dash-dot and span the whole window, which is what makes them read as
datums rather than as geometry - as the profile canvases draw them: the
centre line in the Z axis's green, the Z0 line thinner, in the X axis's blue.

Ported from ``ToolpathCanvas.paintAxes()``, which drew exactly this pair
before drawing the arrows over it.
"""

from teachinlathe.ui.tabs.programs.backplot.actors import geometry, palette, screen
from teachinlathe.ui.tabs.programs.backplot.actors.base import Actor, line_width


class CenterlineActor(Actor):
    """Drawn under the toolpath, so a cut sitting on centre stays readable."""

    LINE_WIDTH = palette.WIDTH_CENTERLINE
    DEPTH_WRITE = False

    def __init__(self, host=None):
        super().__init__(host)
        self._centre = []
        self._zero = []
        self._key = None

    def draw(self, ctx):
        mvp = ctx.mv.mvp()
        key = screen.view_key(ctx, mvp)
        if key is None:
            return
        if key != self._key:
            self._centre, self._zero = self._build(ctx, mvp)
            self._key = key
        self.stroke(ctx, self._centre, palette.CENTERLINE, mvp,
                    palette.CENTERLINE_ALPHA)
        # the Z0 line thinner, in its own colour, as on the profile canvases
        line_width(palette.WIDTH_ZERO_LINE)
        self.stroke(ctx, self._zero, palette.ZERO_LINE, mvp,
                    palette.CENTERLINE_ALPHA)

    def _build(self, ctx, mvp):
        """The dashes - the centre line's, and the Z0 line's. Cutting them is
        the expensive half and the view is all it depends on, so it is done
        only when the view changes."""
        bounds = screen.visible_rect(ctx, mvp)
        scale = screen.pixels_per_unit(ctx, mvp)
        z_min, z_max, x_min, x_max = bounds
        px_per_z, px_per_x = scale

        # The dash pattern is in pixels, so each run is converted with the
        # scale of the direction it runs in - otherwise a non-square viewport
        # would dash the two lines differently.
        centre = geometry.dashed((0.0, 0.0, z_min), (0.0, 0.0, z_max),
                                 palette.DASH_CENTERLINE, px_per_z)
        zero = geometry.dashed((x_min, 0.0, 0.0), (x_max, 0.0, 0.0),
                               palette.DASH_CENTERLINE, px_per_x)
        return centre, zero
