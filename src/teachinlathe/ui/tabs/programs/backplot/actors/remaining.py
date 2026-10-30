"""The material left so far, mirrored above the centre line.

With the mirror on, the half of the plot the toolpath is not on shows the bar
as it stands now, as the half under the toolpath does (``StockActor``, which
says where it comes from) - drawn with it, under the centre line.
"""

from teachinlathe.ui.tabs.programs.backplot.actors.base import Actor
from teachinlathe.ui.tabs.programs.backplot.actors.stock import StockActor


class RemainingStockActor(StockActor):
    """The stock as StockActor draws it - the material left - mirrored
    across the centre line."""

    def stroke(self, ctx, points, color, mvp=None, alpha=1.0):
        """As every actor strokes, on the other side of the centre line."""
        Actor.stroke(ctx, [(-x, y, z) for x, y, z in points], color, mvp, alpha)

    def fill(self, ctx, points, color, mvp=None):
        """As every actor fills, on the other side of the centre line."""
        Actor.fill(ctx, [(-x, y, z) for x, y, z in points], color, mvp)
