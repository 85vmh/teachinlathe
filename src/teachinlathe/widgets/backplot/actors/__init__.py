"""The backplot's actors: one concern per file, each drawing itself.

    units.py          millimetres, for a scene whose model space is inches
    palette.py        the colours and line weights, from the QML renderer
    screen.py         what a model length is worth in pixels, and what the
                      window covers
    stepping.py       how far apart grid lines and ticks are spaced
    text.py           real text, from the renderer's Pango glyph atlas
    geometry.py       the shapes, with no GL and no frame
    inserts.py        ISO insert geometry, ported from the QML tool shapes
    profile.py        the finished shape, read off the program's cutting moves
    sizing.py         the axes' size in pixels; shared by the arrows, the
                      letters and the origin symbol they all sit on
    base.py           the frame and the draw-on-top rule every actor shares

    grid.py           the grid behind the plot
    stock.py          the bar, outlined and hatched back to the profile
    centerline.py     the spindle axis and the face datum
    rapids.py         the traverse moves, dashed - taken out of upstream's
                      baked buffer, which has no dash to give
    ticks.py          the scale round the edge, with labels
    axis_arrows.py    the X and Z arrows
    axis_letters.py   the Z+ and X+ labels
    origin.py         the origin symbol
    insert_tool.py    the insert at the tool tip, in place of upstream's cone

    scene.py          the whole cast and its draw order, including upstream's

``scene.install(canon)`` is the entry point.
"""

from teachinlathe.widgets.backplot.actors.scene import install

__all__ = ["install"]
