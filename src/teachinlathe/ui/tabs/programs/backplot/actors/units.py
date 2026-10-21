"""Millimetres, for a scene that draws in inches.

The backplot's model space is LinuxCNC's canonical internal linear unit, which
is inches - always, whatever ``[TRAJ]LINEAR_UNITS`` says and whatever the
operator is shown. ``GlCanonDraw.to_internal_units`` is where that is decided:
it divides by ``stat.linear_units * 25.4``, so a metric machine reporting 1.0
divides millimetres by 25.4 and lands in inches. ``canon.min_extents`` is in
the same unit: a part 52 mm across reads as 1.02.

So every length in these actors is written in millimetres and passed through
``mm()``. The factor is a constant rather than something read from status,
because the target unit does not change with the machine - only the numbers
arriving from it do.
"""

#: Inches per millimetre: the scale from what these actors are written in to
#: what the scene draws in.
INTERNAL_PER_MM = 1.0 / 25.4


def mm(value):
    """A length in millimetres, in the unit the scene draws in."""
    return value * INTERNAL_PER_MM


def to_mm(value):
    """The inverse of :func:`mm` - a model-space length back in millimetres.

    Used where a length comes out of the scene rather than going in, such as
    the program extents an actor sizes itself against.
    """
    return value / INTERNAL_PER_MM
