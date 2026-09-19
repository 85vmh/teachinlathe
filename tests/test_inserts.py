"""The insert geometry port, checked against the QML it was ported from.

``widgets/backplot/actors/inserts.py`` is a second implementation of
``widgets/tool_shapes/TurningInsertBase.qml``. Both stay: the QML is what the
tool list renders, and the Python is what the backplot draws into its
framebuffer, which cannot host a QML Canvas. Two implementations of one set of
rules drift, so this is what stops them.

The expectations below are transcribed from the QML's own arithmetic rather
than from the Python's - written out the long way, from the ISO relations the
QML file documents at the top. A test that re-derived them the way the module
under test does would agree with a wrong port.
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
from teachinlathe.widgets.backplot.actors import geometry  # noqa: E402

TOLERANCE = 1e-9


def polar(degrees, radius):
    """The QML's own ``polar()``."""
    return (radius * math.cos(math.radians(degrees)),
            radius * math.sin(math.radians(degrees)))


def approx_points(actual, expected):
    assert len(actual) == len(expected)
    for got, want in zip(actual, expected):
        assert got[0] == pytest.approx(want[0], abs=TOLERANCE)
        assert got[1] == pytest.approx(want[1], abs=TOLERANCE)


# ── the family table ───────────────────────────────────────────────────────

@pytest.mark.parametrize("family,shape,insert_type,ic,codes", [
    ("CCMT", "C", "T", (6.35, 9.525, 12.7, 15.875), ("06", "09", "12", "16")),
    ("DCMT", "D", "T", (6.35, 9.525, 12.7), ("07", "11", "15")),
    ("VBMT", "V", "T", (6.35, 9.525), ("11", "16")),
    ("TCMT", "T", "T", (6.35, 9.525, 12.7), ("11", "16", "22")),
    ("WNMG", "W", "G", (9.525, 12.7, 15.875), ("06", "08", "10")),
    ("SNMG", "S", "G", (9.525, 12.7, 15.875, 19.05), ("09", "12", "15", "19")),
    ("RCMT", "R", "T", (8, 10, 12, 16), ("08", "10", "12", "16")),
])
def test_family_matches_qml(family, shape, insert_type, ic, codes):
    """Each family file's shape, type, sizes and codes, in enum order."""
    spec = inserts.FAMILIES[family]
    assert spec["shape"] == shape
    assert spec["type"] == insert_type
    assert tuple(spec["ic"]) == ic
    assert spec["codes"] == codes


def test_size_index_selects_ic_and_code():
    insert = inserts.Insert("DCMT", size_index=1)
    assert insert.ic == pytest.approx(9.525)
    assert insert.size_code == "11"


def test_size_index_is_clamped_like_the_qml():
    """The QML clamps with ``Math.max(0, Math.min(size, len - 1))``."""
    assert inserts.Insert("VBMT", size_index=99).size_code == "16"
    assert inserts.Insert("VBMT", size_index=-5).size_code == "11"


def test_iso_code():
    assert inserts.Insert("DCMT", 1, 0.4).iso_code == "DCMT 11 .. 04"
    assert inserts.Insert("CCMT", 1, 1.2).iso_code == "CCMT 09 .. 12"


# ── outlines ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("family,alpha", [
    ("CCMT", 80.0), ("DCMT", 55.0), ("VBMT", 35.0),
])
def test_rhombic_outline(family, alpha):
    """``side = IC/sin a``; vertices at ``(+-side cos(a/2), 0)`` and
    ``(0, +-side sin(a/2))``; the cutting corners are the sharp pair."""
    insert = inserts.Insert(family, size_index=0)
    radius = insert.ic / 2
    side = (radius * 2) / math.sin(math.radians(alpha))
    dx = side * math.cos(math.radians(alpha / 2))
    dy = side * math.sin(math.radians(alpha / 2))

    verts, cutting = insert.outline()
    approx_points(verts, [(dx, 0.0), (0.0, dy), (-dx, 0.0), (0.0, -dy)])
    assert cutting == [0, 2]


def test_square_outline():
    """S: circumradius ``(IC/2)/cos45``, vertices at 45/135/225/315."""
    insert = inserts.Insert("SNMG", size_index=0)
    circum = (insert.ic / 2) / math.cos(math.radians(45))
    verts, cutting = insert.outline()
    approx_points(verts, [polar(45 + 90 * k, circum) for k in range(4)])
    assert cutting == [0, 1, 2, 3]


def test_triangle_outline():
    """T: circumradius == IC, vertices at 90/210/330."""
    insert = inserts.Insert("TCMT", size_index=0)
    verts, cutting = insert.outline()
    approx_points(verts, [polar(90 + 120 * k, insert.ic) for k in range(3)])
    assert cutting == [0, 1, 2]


def test_trigon_outline_is_in_angular_order():
    """W: ``Rc = IC/1.286``, ``Ro = 0.6527 Rc``, the six vertices walked by
    angle - 30(Ro) 90(Rc) 150(Ro) 210(Rc) 270(Ro) 330(Rc) - with the cutting
    corners the three at Rc.

    Order is the point of this one: the QML warns that a vertex list which
    jumps makes ``arcTo`` draw a star, and the Python's ``rounded_polygon``
    has the same failure.
    """
    insert = inserts.Insert("WNMG", size_index=0)
    corner = insert.ic / 1.286
    flank = 0.6527 * corner
    verts, cutting = insert.outline()
    approx_points(verts, [polar(30, flank), polar(90, corner),
                          polar(150, flank), polar(210, corner),
                          polar(270, flank), polar(330, corner)])
    assert cutting == [1, 3, 5]


def test_round_outline_has_no_vertices():
    insert = inserts.Insert("RCMT", size_index=0)
    assert insert.outline() == ([], [])
    assert insert.is_round


# ── derived lengths and points ─────────────────────────────────────────────

@pytest.mark.parametrize("family,expected", [
    ("SNMG", lambda ic: ic),
    ("TCMT", lambda ic: ic * math.sqrt(3)),
    ("CCMT", lambda ic: ic / math.sin(math.radians(80))),
    ("DCMT", lambda ic: ic / math.sin(math.radians(55))),
    ("VBMT", lambda ic: ic / math.sin(math.radians(35))),
    ("WNMG", lambda ic: 0.879 * (ic / 1.286)),
    ("RCMT", lambda ic: math.pi * ic),
])
def test_edge_length(family, expected):
    insert = inserts.Insert(family, size_index=0)
    assert insert.edge_length() == pytest.approx(expected(insert.ic))


def test_active_tip_is_the_sharp_corner():
    insert = inserts.Insert("DCMT", 1, 0.4)
    verts, cutting = insert.outline()
    assert insert.active_tip() == verts[cutting[0]]


def test_active_corner_selects_the_other_cutting_corner():
    insert = inserts.Insert("DCMT", 1, 0.4, active_corner=1)
    verts, cutting = insert.outline()
    assert insert.active_tip() == verts[cutting[1]]


def test_active_corner_is_clamped():
    """The QML takes ``Math.min(activeCorner, cutting.length - 1)``."""
    insert = inserts.Insert("DCMT", 1, 0.4, active_corner=99)
    verts, cutting = insert.outline()
    assert insert.active_tip() == verts[cutting[-1]]


def test_nose_centre_is_a_nose_radius_off_both_edges():
    """The QML puts it along the bisector at ``r / sin(half angle)``. Checked
    here by what that means instead: the centre is exactly one nose radius
    from each of the two edges meeting at the corner."""
    insert = inserts.Insert("DCMT", 1, 0.8)
    verts, cutting = insert.outline()
    index = cutting[0]
    vertex = verts[index]
    centre = insert.nose_centre()

    for neighbour in (verts[(index - 1) % len(verts)],
                      verts[(index + 1) % len(verts)]):
        edge_x = neighbour[0] - vertex[0]
        edge_y = neighbour[1] - vertex[1]
        length = math.hypot(edge_x, edge_y)
        # Distance from the centre to the line through vertex and neighbour.
        distance = abs(edge_x * (vertex[1] - centre[1])
                       - edge_y * (vertex[0] - centre[0])) / length
        assert distance == pytest.approx(0.8, abs=1e-9)


def test_round_insert_nose_centre_is_the_middle():
    insert = inserts.Insert("RCMT", 0, 0.4)
    assert insert.nose_centre() == (0.0, 0.0)
    assert insert.active_tip() == (0.0, inserts.Insert("RCMT", 0).ic / 2)


def test_hole_table():
    assert inserts.Insert("DCMT", 1).hole() == (4.40, 6.33)     # 9.525, type T
    assert inserts.Insert("SNMG", 0).hole() == (3.81, 5.50)     # 9.525, type G


def test_unknown_family_is_rejected():
    with pytest.raises(KeyError):
        inserts.Insert("ZZZZ")


# ── the rounding the QML did with arcTo ────────────────────────────────────

def test_rounded_polygon_stays_a_nose_radius_from_each_corner():
    """Every point on a rounded corner is within the nose radius of the
    corner's arc centre, and the loop still closes."""
    insert = inserts.Insert("DCMT", 1, 0.8)
    verts, cutting = insert.outline()
    loop = geometry.rounded_polygon(verts, insert.nose_radius)

    assert len(loop) > len(verts)
    centre = insert.nose_centre()
    on_the_arc = [point for point in loop
                  if math.hypot(point[0] - centre[0],
                                point[1] - centre[1]) < 0.8 + 1e-6]
    assert len(on_the_arc) >= 10
    for point in on_the_arc:
        assert math.hypot(point[0] - centre[0], point[1] - centre[1]) == \
            pytest.approx(0.8, abs=1e-6)


def test_rounded_polygon_leaves_a_sharp_corner_when_the_radius_will_not_fit():
    """A nose radius larger than the edge is bad data; the corner is left
    sharp rather than smoothed into something plausible."""
    square = [(1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)]
    assert geometry.rounded_polygon(square, 10.0) == square


def test_rounded_polygon_with_no_radius_is_the_outline():
    verts, _cutting = inserts.Insert("TCMT", 0, 0.0).outline()
    assert geometry.rounded_polygon(verts, 0.0) == verts
