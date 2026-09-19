"""The X and Z letters, each just past its arrow tip."""

from teachinlathe.widgets.backplot.actors import sizing
from teachinlathe.widgets.backplot.actors.base import VX, VZ, Actor
from teachinlathe.widgets.backplot.actors.units import mm

#: Gap between an arrow tip and its letter, in millimetres.
LETTER_GAP_MM = 2.5

#: Nudge across the axis, in millimetres, to centre the glyph on the shaft.
#: Hershey glyphs are drawn from a baseline, not a centre, so a letter sits
#: off to one side without this.
LETTER_SIDE_OFFSET_MM = -1.6

#: Size of the glyph. Upstream uses 0.2 and it is not a length in the scene's
#: unit - it scales the Hershey glyph, which is drawn about one unit tall - so
#: it is left as the bare factor rather than converted.
LETTER_SCALE = 0.2


class AxisLettersActor(Actor):
    """The axis letters, lying in the XZ plane the lathe view looks at.

    Separate from the arrows because it is a different concern with different
    failure modes: a letter is a glyph that has to be turned to face the view,
    and getting that wrong shows up as a mirrored Z rather than as a mis-sized
    arrow. The two share only the lengths, which is why those are in
    ``sizing``.
    """

    def draw(self, ctx):
        if ctx.view != VX:
            self._letter(ctx, sizing.X_DIR, sizing.x_length(ctx),
                         "X", ctx.colors['axis_x'])
        if ctx.view != VZ:
            self._letter(ctx, sizing.Z_DIR, sizing.z_length(ctx),
                         "Z", ctx.colors['axis_z'])

    def _letter(self, ctx, direction, length, letter, color):
        with ctx.mv.push():
            reach = length + mm(LETTER_GAP_MM)
            ctx.mv.translate(direction[0] * reach,
                             direction[1] * reach,
                             direction[2] * reach)
            # Upstream's own rotations for the lathe case, reduced to the view
            # this screen is always in. Working them out afresh from the view
            # flags is how the Z first came out mirrored.
            ctx.mv.rotate(-90, 0, 1, 0)
            ctx.mv.rotate(90, 1, 0, 0)
            ctx.mv.translate(mm(LETTER_SIDE_OFFSET_MM), 0, 0)
            ctx.mv.scale(LETTER_SCALE, LETTER_SCALE, LETTER_SCALE)
            ctx.prim.draw_hershey(ctx, letter, color, 0.5)
