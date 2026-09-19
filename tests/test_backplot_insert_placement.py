"""Where the insert ends up: hung from its tip, and turned the right way.

The two ways this goes wrong are both silent - the insert still draws, still
looks like an insert, and still has something on the toolpath:

  * placed by its centre instead of its tip, so the marker is half an insert
    away from the point the program was written to;
  * turned through half a revolution, so it cuts from the far side of the
    work.

Neither raises, so both are checked here.
"""

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.widgets.backplot.actors import inserts  # noqa: E402
from teachinlathe.widgets.backplot.actors.insert_tool import (  # noqa: E402
    _offset, _rotate, _to_plane, turn_angle,
)
from teachinlathe.widgets.backplot.actors.units import to_mm  # noqa: E402

#: Upstream's ``ToolPart.LATHE_SHAPES``, transcribed. The test states what it
#: expects of orientation rather than importing it, so a change upstream shows
#: up here as a failure instead of passing silently.
LATHE_SHAPES = [
    None,
    (1, -1), (1, 1), (-1, 1), (-1, -1),
    (0, -1), (1, 0), (0, 1), (-1, 0),
    (0, 0),
]


def place(insert, orientation, point=(0.0, 0.0)):
    """One insert-frame point through the actor's placement, to model space."""
    tip = insert.active_tip()
    angle = turn_angle(LATHE_SHAPES[orientation], tip)
    return _to_plane(_rotate(_offset(point, tip), angle))


# ── hung from the tip ──────────────────────────────────────────────────────

@pytest.mark.parametrize("orientation", range(1, 10))
def test_the_tip_lands_on_the_programmed_point(orientation):
    """Whatever the orientation, the active corner is at the origin - which
    is where upstream has already translated the stack to."""
    insert = inserts.Insert("DCMT", 1, 0.4)
    at_tip = place(insert, orientation, insert.active_tip())
    assert at_tip == pytest.approx((0.0, 0.0, 0.0), abs=1e-12)


def test_the_centre_is_not_on_the_programmed_point():
    """The obvious wrong implementation, stated so it cannot creep back."""
    insert = inserts.Insert("DCMT", 1, 0.4)
    centre = place(insert, 2, (0.0, 0.0))
    assert math.hypot(centre[0], centre[2]) > 0.0


def test_the_body_is_an_insert_away_from_the_tip():
    """The centre sits at the tip's own distance from it - the insert is moved
    rigidly, not scaled or skewed."""
    insert = inserts.Insert("DCMT", 1, 0.4)
    tip = insert.active_tip()
    centre = place(insert, 2, (0.0, 0.0))
    assert to_mm(math.hypot(centre[0], centre[2])) == pytest.approx(
        math.hypot(tip[0], tip[1]))


# ── turned the right way ───────────────────────────────────────────────────

#: Where the body must lie for each orientation, as signs of ``(model X,
#: model Z)``. Upstream centres the nose arc at ``(r*dx, r*dz)`` from the
#: programmed point, so the material is on the ``LATHE_SHAPES`` side and the
#: tip points the other way.
BODY_SIDE = {
    1: (1, -1), 2: (1, 1), 3: (-1, 1), 4: (-1, -1),
    5: (0, -1), 6: (1, 0), 7: (0, 1), 8: (-1, 0),
}


@pytest.mark.parametrize("orientation,side", sorted(BODY_SIDE.items()))
def test_the_body_lies_on_the_orientation_side(orientation, side):
    insert = inserts.Insert("DCMT", 1, 0.4)
    centre = place(insert, orientation, (0.0, 0.0))
    want_x, want_z = side
    assert _sign(centre[0]) == want_x
    assert _sign(centre[2]) == want_z


def test_orientation_nine_does_not_turn():
    """A centred tool has no direction to point in."""
    assert turn_angle(LATHE_SHAPES[9], (1.0, 0.0)) == 0.0


def test_orientation_zero_does_not_turn():
    assert turn_angle(LATHE_SHAPES[0], (1.0, 0.0)) == 0.0


def test_a_round_insert_does_not_turn():
    """Its tip is on the axis of symmetry, so there is nothing to align."""
    assert turn_angle((1, 1), (0.0, 0.0)) == 0.0


def test_opposite_orientations_are_half_a_revolution_apart():
    insert = inserts.Insert("DCMT", 1, 0.4)
    tip = insert.active_tip()
    difference = turn_angle((1, 1), tip) - turn_angle((-1, -1), tip)
    assert abs(difference) % (2 * math.pi) == pytest.approx(math.pi)


# ── the insert plane on the lathe's ────────────────────────────────────────

def test_insert_x_runs_along_z():
    """The insert is drawn x-right; the lathe view has Z right."""
    x, _y, z = _to_plane((1.0, 0.0))
    assert z > 0
    assert x == pytest.approx(0.0)


def test_insert_y_runs_up_the_screen_which_is_negative_x():
    """Growing radius is *down* the screen, so the insert's +y is -X. The sign
    that mirrors the insert about the spindle axis if it is wrong."""
    x, _y, z = _to_plane((0.0, 1.0))
    assert x < 0
    assert z == pytest.approx(0.0)


def _sign(value, tolerance=1e-12):
    if abs(value) < tolerance:
        return 0
    return 1 if value > 0 else -1
