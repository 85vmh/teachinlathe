"""The backplot's actors: one concern per file, each drawing itself.

    units.py          millimetres, for a scene whose model space is inches
    geometry.py       the shapes, with no GL and no frame
    sizing.py         how long the axes are; shared by arrows and letters
    base.py           the frame and the draw-on-top rule every actor shares
    axis_arrows.py    the X and Z arrows
    axis_letters.py   the X and Z letters
    origin.py         the origin symbol
    scene.py          the whole cast and its draw order, including upstream's

``scene.install(canon)`` is the entry point.
"""

from teachinlathe.widgets.backplot.actors.scene import install

__all__ = ["install"]
