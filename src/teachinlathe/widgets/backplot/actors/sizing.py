"""How long the axes are, how big their heads, and how far off the letters sit.

Its own module because three actors need the same answers: the arrows draw to
these lengths, the letters sit just past them, and the origin symbol has to
stay out from under both.

**Everything here is in pixels.** The axes are annotation - a drawing on top
of the plot rather than a part of it - so they keep their size as the operator
zooms, and the numbers are the QML renderer's own, from
``ToolpathCanvas.paintAxes``.

They were in millimetres, which meant the X arrow grew with the program's
radial extent and both arrows grew with the zoom until they ran off the
window. The conversion back to model space is one division by the scale for
the axis in question - see ``screen.pixels_per_unit`` - and it has to be the
scale of *that* axis, because a head's width lies across the direction its
shaft runs in.
"""

#: How far the shaft reaches from the origin.
AXIS_LENGTH_PX = 60.0

#: Length of the solid arrow head, tip to base.
HEAD_LENGTH_PX = 14.0

#: Half the arrow head's width at its base.
HEAD_HALF_WIDTH_PX = 7.0

#: How far out the shaft starts, so it does not run through the origin symbol.
#:
#: Clear of the ring's *outer* edge, which is half a stroke past
#: ``origin.RADIUS_PX`` - the two are meant to be read together, and a test
#: holds this the larger of them.
ORIGIN_CLEARANCE_PX = 14.0

#: Gap between an arrow tip and the letter naming it.
LETTER_GAP_PX = 4.0

#: Cap height of that letter. A Hershey glyph is about one unit tall, so this
#: is also what it is scaled to.
LETTER_PX = 16.0

#: Unit vectors, in the sense the lathe view shows them: +X down the screen
#: (growing radius), +Z to the right (along the spindle).
X_DIR = (1.0, 0.0, 0.0)
Z_DIR = (0.0, 0.0, 1.0)


def in_model(pixels, pixels_per_unit):
    """``pixels`` as a length in model space, at this frame's scale."""
    if pixels_per_unit <= 0:
        return 0.0
    return pixels / pixels_per_unit
