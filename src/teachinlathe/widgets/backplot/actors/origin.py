"""The origin symbol: a circle with two opposite quadrants filled."""

import math

from teachinlathe.widgets.backplot.actors import geometry, palette, screen
from teachinlathe.widgets.backplot.actors.base import Actor

#: Radius of the symbol, in pixels.
#:
#: Pixels, like the arrows that run out of it: a symbol marking a point has no
#: size of its own to show. It was 1.8 mm, and with the arrows now fixed on
#: screen that would have the disc swallowing them whole at a hard zoom.
#: ``sizing.ORIGIN_CLEARANCE_PX`` is where the shafts start, clear of the
#: ring's outer edge, and the two are meant to be read together.
RADIUS_PX = 12.0

#: Segments the circle is drawn with.
SEGMENTS = 48

#: Thickness of the ring, in pixels. Kept apart from the arrows' width: at
#: that thickness the ring closes over the two empty quadrants on a circle
#: this small and the symbol reads as a filled disc.
OUTLINE_WIDTH = palette.WIDTH_ORIGIN

#: Near-black, for the light background. Not in the scene's palette - it is
#: the actor's own mark, not one of LinuxCNC's colours - so it comes from
#: ours.
COLOR = palette.ORIGIN

#: What the two empty quadrants are filled with.
#:
#: Filled, not left clear: the centreline and the face datum cross underneath
#: the symbol, and through an open quadrant their dashes read as part of it.
#: The symbol is a marker sitting on the drawing, not a window into it.
BACKGROUND = palette.BACK


class OriginActor(Actor):
    """Drawn last of the annotation actors, so it sits over both shafts.

    Three passes, in this order: the disc that hides what crosses underneath,
    the two filled quadrants, then the ring round the outside. Each covers the
    one before it where they overlap, which is why the ring is last - it is
    the edge of the symbol and nothing may encroach on it.

    The filled quadrants are the pair the arrows do not run through, so
    neither shaft cuts across a filled wedge.
    """

    #: Thinner than the arrows: see OUTLINE_WIDTH.
    LINE_WIDTH = OUTLINE_WIDTH

    #: Everything here is a curve, and a curve is what aliasing shows on.
    MULTISAMPLE = True

    def __init__(self, host=None):
        super().__init__(host)
        self._shapes = None
        self._key = None

    def draw(self, ctx):
        mvp = ctx.mv.mvp()
        key = screen.view_key(ctx, mvp)
        if key is None:
            return
        if key != self._key:
            self._shapes = self._build(ctx, mvp)
            self._key = key
        disc, wedges, ring = self._shapes
        self.fill(ctx, disc, BACKGROUND, mvp)
        self.fill(ctx, wedges, COLOR, mvp)
        self.fill(ctx, ring, COLOR, mvp)

    def _build(self, ctx, mvp):
        """The three shapes, in draw order. A fixed size on screen, so they
        change only when the scale does."""
        scale = screen.pixels_per_unit(ctx, mvp)
        # The circle is drawn in the plane, so it takes one radius; on the
        # square orthographic view this screen is always in, the two scales
        # agree and either would do.
        radius = RADIUS_PX / scale[0]
        width = OUTLINE_WIDTH / scale[0]
        outer = radius + width / 2.0

        # Out to the ring's own outer edge, so nothing shows through under the
        # ring either.
        disc = geometry.circle_sector(outer, 0.0, 2 * math.pi, SEGMENTS)

        quadrant = math.pi / 2
        wedges = []
        for start in (quadrant, 3 * quadrant):
            wedges.extend(
                geometry.circle_sector(radius, start, quadrant,
                                       max(2, SEGMENTS // 4)))

        # Filled, not stroked - see geometry.annulus for why a stroked circle
        # this small comes out gappy.
        ring = geometry.annulus(radius, width, SEGMENTS)
        return disc, wedges, ring
