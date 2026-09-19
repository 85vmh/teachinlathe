"""How long the axes are, and how big their heads.

Its own module because two actors need the same answer: the arrows draw to
these lengths and the letters sit just past them. Were the rule kept inside
the arrows, the letters would either import that actor or grow a second copy
of it that could drift.

All lengths are in millimetres - see ``units`` for why that needs saying.
"""

from teachinlathe.widgets.backplot.actors.units import mm

#: Length of the solid arrow head, tip to base. The axis lengths are given in
#: multiples of this, so it is the unit the rest of the sizing is built on.
HEAD_LENGTH_MM = 3.0

#: Half the arrow head's width at its base.
HEAD_WIDTH_MM = 1.3

#: X reaches past the program's radial extent by this many head lengths.
X_OVERSHOOT_HEADS = 2.0

#: Z is this many head lengths long. It marks the direction rather than the
#: extent, so unlike X it does not follow the program.
Z_LENGTH_HEADS = 3.0

#: X's length when no program is loaded and there is no extent to read.
X_FALLBACK_MM = 26.0

#: Unit vectors, in the sense the lathe view shows them: +X down the screen
#: (growing radius), +Z to the right (along the spindle).
X_DIR = (1.0, 0.0, 0.0)
Z_DIR = (0.0, 0.0, 1.0)


def head_length():
    return mm(HEAD_LENGTH_MM)


def head_width():
    return mm(HEAD_WIDTH_MM)


#: Anything at least this large is a sentinel, not a measurement. glcanon
#: leaves the extents at +-9e99 when nothing has been parsed - after a failed
#: load, for instance - and an axis built from that overflows the float32 the
#: vertex arrays are cast to, which loses the axis and corrupts the draw.
#: Upstream guards its own limits the same way, in ``soft_limits``.
EXTENT_SENTINEL = 1e30


def radial_extent(ctx):
    """How far the program reaches from the spindle axis, or None.

    The larger of the two X bounds in magnitude, so a program described either
    side of centre still gets an axis that covers it. None when there is no
    usable measurement - no program, or one that failed to parse.
    """
    canon = ctx.canon
    low = getattr(canon, "min_extents", None)
    high = getattr(canon, "max_extents", None)
    if not low or not high:
        return None
    try:
        reach = max(abs(low[0]), abs(high[0]))
    except (IndexError, TypeError):
        return None
    if reach != reach or reach >= EXTENT_SENTINEL:   # NaN, or the sentinel
        return None
    return reach


def x_length(ctx):
    """The program's radial reach, overshot by X_OVERSHOOT_HEADS heads."""
    radial = radial_extent(ctx)
    if radial is None or radial <= 0:
        return mm(X_FALLBACK_MM)
    return radial + X_OVERSHOOT_HEADS * head_length()


def z_length(_ctx):
    """A fixed number of head lengths, independent of the program."""
    return Z_LENGTH_HEADS * head_length()
