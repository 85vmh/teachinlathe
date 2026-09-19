"""The origin symbol: a circle with two opposite quadrants filled."""

import math

from teachinlathe.widgets.backplot.actors import geometry
from teachinlathe.widgets.backplot.actors.base import Actor
from teachinlathe.widgets.backplot.actors.units import mm

#: Radius of the symbol, in millimetres.
RADIUS_MM = 1.8

#: Segments the circle is drawn with.
SEGMENTS = 48

#: Thickness of the outline, in pixels. Kept apart from the arrows' width: at
#: that thickness the ring closes over the two empty quadrants on a circle
#: this small and the symbol reads as a filled disc.
OUTLINE_WIDTH = 1.0

#: Near-black, for the light background. This one is not in the scene's
#: palette - it is the actor's own mark, not one of LinuxCNC's colours - so it
#: is the one entry that has to be changed here rather than with the rest.
COLOR = (0.10, 0.10, 0.10)


class OriginActor(Actor):
    """Drawn last of the annotation actors, so it sits over both shafts.

    The filled quadrants are the pair the arrows do not run through, so
    neither shaft cuts across a filled wedge.
    """

    #: Thinner than the arrows: see OUTLINE_WIDTH.
    LINE_WIDTH = OUTLINE_WIDTH

    def draw(self, ctx):
        mvp = ctx.mv.mvp()
        radius = mm(RADIUS_MM)

        self.stroke(ctx, geometry.circle_outline(radius, SEGMENTS), COLOR, mvp)

        quadrant = math.pi / 2
        wedges = []
        for start in (quadrant, 3 * quadrant):
            wedges.extend(
                geometry.circle_sector(radius, start, quadrant,
                                       max(2, SEGMENTS // 4)))
        self.fill(ctx, wedges, COLOR, mvp)
