"""The grid behind the plot: one line per major step, on both axes.

Not upstream's ``GridPart``. That one draws the machine's ground grid, in the
plane the view is looking down and at a spacing ``[DISPLAY]GRIDS`` fixes; this
one is the QML renderer's grid - in the lathe's XZ plane, at a spacing chosen
from the zoom, and sized in diameter on X. Upstream's stays in the scene,
gated off by its own ``grid_size``, rather than being bent into this.
"""

from teachinlathe.widgets.backplot.actors import palette, screen, stepping
from teachinlathe.widgets.backplot.actors.base import Actor
from teachinlathe.widgets.backplot.actors.units import mm, to_mm


class GridActor(Actor):
    """The first thing drawn, and the only one that draws nothing else."""

    LINE_WIDTH = palette.WIDTH_GRID
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
        self.stroke(ctx, self._edges, palette.GRID, mvp, palette.GRID_ALPHA)

    def _build(self, ctx, mvp):
        """Where the lines are. Depends on the view and nothing else, which is
        why it is built only when the view changes."""
        bounds = screen.visible_rect(ctx, mvp)
        scale = screen.pixels_per_unit(ctx, mvp)
        z_min, z_max, x_min, x_max = bounds
        px_per_z, px_per_x = scale

        edges = []

        # Along Z: a vertical line at every major step, spanning the window.
        _minor, major_z = stepping.steps(px_per_z * mm(1.0))
        for z_mm in stepping.marks(to_mm(z_min), to_mm(z_max), major_z):
            z = mm(z_mm)
            edges.extend([(x_min, 0.0, z), (x_max, 0.0, z)])

        # Along X: a horizontal line at every major step *of diameter*, hence
        # the halved scale going in and the halved value coming out.
        _minor, major_x = stepping.steps(px_per_x * mm(1.0) / 2.0)
        for diameter in stepping.marks(to_mm(x_min) * 2, to_mm(x_max) * 2,
                                       major_x):
            x = mm(diameter / 2.0)
            edges.extend([(x, 0.0, z_min), (x, 0.0, z_max)])

        return edges
