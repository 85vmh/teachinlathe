"""How far apart the grid lines and the ticks are spaced.

Its own module for the reason ``sizing`` is: the grid draws the major lines
and the ticks draw both, and a second copy of the rule would let the two drift
apart - a grid line without a tick under it is the visible result.

The rule is the QML renderer's ``_steps()``, unchanged: the spacing is chosen
from how many pixels a millimetre is worth, so the lines stay a readable
distance apart at every zoom rather than piling up as the operator pulls back.

Z is spaced in millimetres along the spindle. **X is spaced in diameter**, as
the lathe DRO reads it, so its steps are chosen against pixels per diameter
millimetre - half of what a radius millimetre is worth. That halving is the
whole reason the two axes ask for their steps separately.
"""

import math

#: ``(pixels per millimetre at least, minor step mm, major step mm)``, coarsest
#: last. The first row whose threshold is met wins.
LADDER = (
    (2.0, 1.0, 10.0),
    (0.4, 10.0, 50.0),
    (0.0, 50.0, 100.0),
)

#: A tick every 5 mm is drawn at the major length without a label. Upstream of
#: this module it is only a length; it is here because it is part of the same
#: reading of the scale.
EMPHASIS_MM = 5.0

#: How much room a label needs on screen, in pixels, before the next one.
#:
#: **The ladder alone does not give it.** Its bottom rung has no lower bound,
#: so the further out the operator zooms the closer the labels come, and they
#: run into each other long before that: at the top rung's own threshold of
#: 2 px/mm a major step of 10 mm puts them 20 px apart, and "-100" measures 28
#: at the size they are drawn ("-1000" measures 36). So the step is coarsened
#: below until they fit.
#:
#: Measured from the font rather than guessed - Pango was asked, offscreen -
#: and rounded up to leave a clear gap between one number and the next.
MIN_LABEL_PITCH_PX = 56.0

#: The steps a coarsened one may become: a 1-2-5 progression, which is what
#: every scale on every drawing has used for a century, and what the ladder's
#: own rungs already are.
MANTISSAS = (1.0, 2.0, 5.0)


def steps(pixels_per_mm, min_label_pitch=MIN_LABEL_PITCH_PX):
    """``(minor, major)`` step in millimetres for a scale in pixels per mm.

    The ladder decides it, and then it is coarsened until a label fits in the
    space before the next one. The coarsening only ever makes the step larger,
    so wherever the labels already fit - which is most of the range an
    operator works in - this is exactly the ladder, and exactly what the
    profile editor's canvas shows.
    """
    minor, major = _rung(pixels_per_mm)
    if pixels_per_mm <= 0 or min_label_pitch <= 0:
        return minor, major

    # The ratio is the rung's own - 1:10, 1:5 or 1:2 - and a coarsened step
    # keeps it, so the minor ticks thin out with the labels instead of closing
    # into a solid band behind them.
    ratio = minor / major
    guard = 0
    while major * pixels_per_mm < min_label_pitch and guard < 40:
        major = _next_125(major)
        minor = major * ratio
        guard += 1
    return minor, major


def _rung(pixels_per_mm):
    """The ladder's own answer, before any coarsening."""
    for threshold, minor, major in LADDER:
        if pixels_per_mm >= threshold:
            return minor, major
    return LADDER[-1][1], LADDER[-1][2]


def _next_125(value):
    """The next step up the 1-2-5 progression."""
    if value <= 0:
        return 1.0
    decade = 10.0 ** math.floor(math.log10(value))
    mantissa = value / decade
    for candidate in MANTISSAS:
        if candidate > mantissa + 1e-9:
            return candidate * decade
    return 10.0 * decade


def is_multiple(value, step):
    """Whether ``value`` lands on ``step``, in the QML's own integer-micron
    arithmetic - so a value that is a step away by a rounding error still
    counts as on it."""
    if step <= 0:
        return False
    return round(abs(value) * 1000) % round(step * 1000) < 1


def marks(low, high, step, limit=4000):
    """Every multiple of ``step`` in ``[low, high]``.

    ``limit`` is a guard, not a policy: a window showing a metre at a
    millimetre step would otherwise build tens of thousands of vertices for
    lines a pixel apart. Reaching it means the scale was misread, so it stops
    rather than drawing something useless slowly.
    """
    if step <= 0 or high < low:
        return []
    first = int(low // step)
    values = []
    value = first * step
    while value <= high and len(values) < limit:
        if value >= low:
            values.append(value)
        value += step
    return values
