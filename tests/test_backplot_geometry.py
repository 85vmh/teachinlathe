"""The backplot's frame arithmetic: dashes, clipping, stepping, and the
pixels-per-unit the three screen-sized actors are built on.

None of this needs a GL context - it is all plain geometry, which is the
reason it lives apart from the actors that draw it. What it does need is to be
right: a wrong ``pixels_per_unit`` puts the grid at the wrong spacing and the
tick labels off the edge of the window, and neither fails loudly.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.widgets.backplot.actors import (  # noqa: E402
    geometry, inserts, screen, stepping,
)
from teachinlathe.widgets.backplot.actors.units import mm, to_mm  # noqa: E402


# ── a stand-in for the frame ───────────────────────────────────────────────

class FakeContext:
    """Only what ``screen`` reads: a viewport size."""

    def __init__(self, width, height):
        self.width = width
        self.height = height


def lathe_mvp(z_range, x_range):
    """An orthographic MVP shaped like the lathe view's.

    Model Z runs across the window and model X down it, which is the
    permutation the real view has folded into its matrix. Model Y carries the
    depth, so the matrix inverts.
    """
    z_min, z_max = z_range
    x_min, x_max = x_range
    a = 2.0 / (z_max - z_min)
    b = -1.0 - a * z_min
    c = 2.0 / (x_max - x_min)
    d = -1.0 - c * x_min
    return np.array([
        [0.0, 0.0, a, b],
        [c, 0.0, 0.0, d],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])


# ── screen ─────────────────────────────────────────────────────────────────

def test_pixels_per_unit():
    """120 model units of Z across 800 pixels, 60 of X down 600."""
    ctx = FakeContext(800, 600)
    mvp = lathe_mvp((-100.0, 20.0), (-10.0, 50.0))
    px_per_z, px_per_x = screen.pixels_per_unit(ctx, mvp)
    assert px_per_z == pytest.approx(800.0 / 120.0)
    assert px_per_x == pytest.approx(600.0 / 60.0)


def test_visible_rect_recovers_the_view():
    ctx = FakeContext(800, 600)
    mvp = lathe_mvp((-100.0, 20.0), (-10.0, 50.0))
    z_min, z_max, x_min, x_max = screen.visible_rect(ctx, mvp)
    assert z_min == pytest.approx(-100.0)
    assert z_max == pytest.approx(20.0)
    assert x_min == pytest.approx(-10.0)
    assert x_max == pytest.approx(50.0)


def test_zooming_in_raises_the_scale_and_narrows_the_rect():
    ctx = FakeContext(800, 600)
    wide = lathe_mvp((-100.0, 20.0), (-10.0, 50.0))
    close = lathe_mvp((-10.0, 2.0), (-1.0, 5.0))
    assert (screen.pixels_per_unit(ctx, close)[0]
            > screen.pixels_per_unit(ctx, wide)[0])
    assert (screen.visible_rect(ctx, close)[1]
            < screen.visible_rect(ctx, wide)[1])


def test_unsized_window_measures_nothing():
    mvp = lathe_mvp((-100.0, 20.0), (-10.0, 50.0))
    assert screen.pixels_per_unit(FakeContext(0, 600), mvp) is None


def test_singular_matrix_has_no_visible_rect():
    assert screen.visible_rect(FakeContext(800, 600), np.zeros((4, 4))) is None


# ── stepping ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("pixels_per_mm,expected", [
    (30.0, (1.0, 10.0)),        # zoomed right in
    (10.0, (1.0, 10.0)),
    (5.6, (1.0, 10.0)),         # the last scale a 10 mm label still fits at
])
def test_steps_follow_the_ladder_where_the_labels_fit(pixels_per_mm,
                                                      expected):
    """The profile editor's own rungs, unchanged - which is the whole point of
    only ever coarsening."""
    assert stepping.steps(pixels_per_mm) == expected
    assert stepping._rung(pixels_per_mm) == expected


@pytest.mark.parametrize("pixels_per_mm", [
    30.0, 12.0, 6.0, 5.6, 3.0, 2.0, 1.0, 0.5, 0.4, 0.3, 0.1, 0.05, 0.02,
    0.005, 0.001,
])
def test_labels_never_come_closer_than_they_can_be_read(pixels_per_mm):
    """The bug this is here for: the ladder's bottom rung has no lower bound,
    so zooming out walked the labels into each other. At 2 px/mm its own top
    rung already put them 20 px apart, and "-100" is 28 px wide."""
    _minor, major = stepping.steps(pixels_per_mm)
    assert major * pixels_per_mm >= stepping.MIN_LABEL_PITCH_PX - 1e-9


@pytest.mark.parametrize("pixels_per_mm", [30.0, 3.0, 1.0, 0.1, 0.005])
def test_coarsening_only_ever_grows_the_step(pixels_per_mm):
    """It must not refine: a step finer than the ladder's would be a different
    drawing from the profile editor's, not a fix to this one."""
    raw_minor, raw_major = stepping._rung(pixels_per_mm)
    minor, major = stepping.steps(pixels_per_mm)
    assert major >= raw_major
    assert minor >= raw_minor


@pytest.mark.parametrize("pixels_per_mm", [3.0, 1.0, 0.1, 0.005])
def test_coarsening_keeps_the_rungs_minor_to_major_ratio(pixels_per_mm):
    """So the minor ticks thin out with the labels rather than closing into a
    solid band behind them."""
    raw_minor, raw_major = stepping._rung(pixels_per_mm)
    minor, major = stepping.steps(pixels_per_mm)
    assert minor / major == pytest.approx(raw_minor / raw_major)


@pytest.mark.parametrize("value,expected", [
    (1.0, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, 20.0),
    (50.0, 100.0), (100.0, 200.0), (200.0, 500.0),
])
def test_the_step_climbs_one_two_five(value, expected):
    assert stepping._next_125(value) == pytest.approx(expected)


def test_an_impossible_scale_does_not_spin():
    """The guard. A scale of zero has no step that fits, and the loop must
    stop rather than run out of floats looking for one."""
    assert stepping.steps(0.0) == stepping._rung(0.0)
    minor, major = stepping.steps(1e-12)
    assert major > 0 and minor > 0


def test_marks_are_the_multiples_inside_the_range():
    assert stepping.marks(-25.0, 25.0, 10.0) == pytest.approx(
        [-20.0, -10.0, 0.0, 10.0, 20.0])


def test_marks_include_an_exact_endpoint():
    assert stepping.marks(-20.0, 20.0, 10.0)[0] == pytest.approx(-20.0)
    assert stepping.marks(-20.0, 20.0, 10.0)[-1] == pytest.approx(20.0)


def test_a_caller_may_ask_for_denser_labels():
    """The pitch is an argument so the rule can be checked against a font
    other than the one it was measured from."""
    assert stepping.steps(2.0, min_label_pitch=0.0) == stepping._rung(2.0)


def test_marks_stop_at_the_guard():
    assert len(stepping.marks(0.0, 1e9, 1.0, limit=50)) == 50


def test_is_multiple_tolerates_the_rounding_a_step_accumulates():
    assert stepping.is_multiple(50.0, 10.0)
    assert stepping.is_multiple(-50.0, 10.0)
    assert not stepping.is_multiple(55.0, 10.0)
    # 10 steps of 0.1 do not land exactly on 1.0 in binary floating point.
    drifted = sum([0.1] * 10)
    assert drifted != 1.0
    assert stepping.is_multiple(drifted, 1.0)


# ── dashes ─────────────────────────────────────────────────────────────────

def test_dashed_cuts_a_line_into_the_on_runs():
    """A 100-unit line at 1 px per unit, dashed 10 on / 10 off, is five
    segments: 0-10, 20-30, 40-50, 60-70, 80-90."""
    edges = geometry.dashed((0.0, 0.0, 0.0), (0.0, 0.0, 100.0),
                            (10.0, 10.0), px_per_unit=1.0)
    starts = [edge[2] for edge in edges[0::2]]
    finishes = [edge[2] for edge in edges[1::2]]
    assert starts == pytest.approx([0.0, 20.0, 40.0, 60.0, 80.0])
    assert finishes == pytest.approx([10.0, 30.0, 50.0, 70.0, 90.0])


def test_dashed_is_sized_in_pixels_not_model_units():
    """Twice the zoom, half the model-space dash - so it looks the same."""
    coarse = geometry.dashed((0.0, 0.0, 0.0), (0.0, 0.0, 100.0),
                             (10.0, 10.0), px_per_unit=1.0)
    fine = geometry.dashed((0.0, 0.0, 0.0), (0.0, 0.0, 100.0),
                           (10.0, 10.0), px_per_unit=2.0)
    assert len(fine) == 2 * len(coarse)
    assert fine[1][2] == pytest.approx(5.0)


def test_dashed_does_not_run_past_the_end():
    edges = geometry.dashed((0.0, 0.0, 0.0), (0.0, 0.0, 15.0),
                            (10.0, 10.0), px_per_unit=1.0)
    assert max(edge[2] for edge in edges) == pytest.approx(10.0)


def test_dashed_without_a_pattern_is_one_solid_line():
    assert geometry.dashed((0.0, 0.0, 0.0), (0.0, 0.0, 10.0), (), 1.0) == \
        [(0.0, 0.0, 0.0), (0.0, 0.0, 10.0)]


def test_dashed_dash_dot_alternates_long_and_short():
    """The centreline's own pattern: 8 on, 5 off, 2 on, 5 off."""
    edges = geometry.dashed((0.0, 0.0, 0.0), (0.0, 0.0, 40.0),
                            (8.0, 5.0, 2.0, 5.0), px_per_unit=1.0)
    lengths = [edges[i + 1][2] - edges[i][2] for i in range(0, len(edges), 2)]
    assert lengths[0] == pytest.approx(8.0)
    assert lengths[1] == pytest.approx(2.0)
    assert lengths[2] == pytest.approx(8.0)


# ── clipping ───────────────────────────────────────────────────────────────

def test_clip_keeps_a_segment_already_inside():
    inside = geometry.clip_to_rect((1.0, 0.0, 1.0), (2.0, 0.0, 2.0),
                                   (0.0, 0.0), (10.0, 10.0))
    assert inside[0] == pytest.approx((1.0, 0.0, 1.0))
    assert inside[1] == pytest.approx((2.0, 0.0, 2.0))


def test_clip_shortens_a_segment_crossing_an_edge():
    clipped = geometry.clip_to_rect((-5.0, 0.0, 5.0), (5.0, 0.0, 5.0),
                                    (0.0, 0.0), (10.0, 10.0))
    assert clipped[0][0] == pytest.approx(0.0)
    assert clipped[1][0] == pytest.approx(5.0)


def test_clip_drops_a_segment_that_misses():
    assert geometry.clip_to_rect((20.0, 0.0, 20.0), (30.0, 0.0, 30.0),
                                 (0.0, 0.0), (10.0, 10.0)) is None


def test_clip_drops_a_line_parallel_to_an_edge_and_outside_it():
    assert geometry.clip_to_rect((-1.0, 0.0, 0.0), (-1.0, 0.0, 10.0),
                                 (0.0, 0.0), (10.0, 10.0)) is None


def test_clip_cuts_a_diagonal_to_both_corners():
    clipped = geometry.clip_to_rect((-10.0, 0.0, -10.0), (20.0, 0.0, 20.0),
                                    (0.0, 0.0), (10.0, 10.0))
    assert clipped[0] == pytest.approx((0.0, 0.0, 0.0))
    assert clipped[1] == pytest.approx((10.0, 0.0, 10.0))


# ── units, and the diameter/radius halving the X scale depends on ──────────

def test_millimetres_round_trip():
    assert to_mm(mm(52.0)) == pytest.approx(52.0)
    assert mm(25.4) == pytest.approx(1.0)


def test_polyline_expands_to_endpoint_pairs():
    points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0)]
    assert geometry.polyline(points) == [
        points[0], points[1], points[1], points[2]]


def test_polyline_closed_returns_to_the_start():
    points = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.0, 1.0)]
    assert geometry.polyline(points, closed=True)[-2:] == [points[2],
                                                           points[0]]


def test_fan_to_triangles_covers_every_edge():
    loop = geometry.circle_loop(1.0, 8)
    triangles = geometry.fan_to_triangles(loop, centre=(0.0, 0.0))
    assert len(triangles) == 8 * 3
    assert triangles[0] == (0.0, 0.0)


def test_circle_loop_is_on_the_circle():
    for point in geometry.circle_loop(3.0, 16):
        assert math.hypot(*point) == pytest.approx(3.0)


# ── the ring: a filled outline with the hole left open ─────────────────────

def test_ray_hit_lands_on_the_outline():
    square = [(1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)]
    east = geometry.ray_hit(square, 0.0)
    assert east == pytest.approx((1.0, 0.0))
    north = geometry.ray_hit(square, math.pi / 2)
    assert north == pytest.approx((0.0, 1.0))


def test_ray_hit_takes_the_forward_crossing_not_the_backward_one():
    square = [(1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)]
    assert geometry.ray_hit(square, math.pi)[0] == pytest.approx(-1.0)


def test_ring_leaves_the_hole_empty():
    """No triangle vertex falls inside the hole - which is what makes what is
    behind the insert show through it."""
    loop = geometry.circle_loop(5.0, 64)
    triangles = geometry.ring_triangles(loop, 2.0, 32)
    assert triangles
    for x, y in triangles:
        assert math.hypot(x, y) >= 2.0 - 1e-9


def test_ring_reaches_the_outline():
    loop = geometry.circle_loop(5.0, 64)
    triangles = geometry.ring_triangles(loop, 2.0, 32)
    assert max(math.hypot(x, y) for x, y in triangles) == pytest.approx(
        5.0, rel=1e-2)


def test_ring_covers_every_bearing():
    """Two triangles per spoke, and a spoke for every bearing the ring is
    built on - so it closes all the way round rather than leaving a wedge open
    at the seam."""
    loop = geometry.circle_loop(5.0, 64)
    spokes = geometry._ring_spokes(loop, 32)
    assert len(geometry.ring_triangles(loop, 2.0, 32)) == len(spokes) * 6


def test_the_ring_reaches_every_point_of_the_outline():
    """The bug this is here for: built on evenly spaced bearings alone, the
    outer boundary is a chord between samples, and a chord cuts the corner
    off - worst where the outline turns fastest, which on an insert is the
    nose radius. The fill stopped short of its own outline by the better part
    of half a millimetre on a DCMT 11."""
    insert = inserts.Insert("DCMT", 1, 0.4)
    loop = geometry.rounded_polygon(insert.outline()[0], insert.nose_radius)
    filled = set(geometry.ring_triangles(loop, insert.hole()[0] / 2, 64))

    for vertex in loop:
        nearest = min(math.hypot(vertex[0] - p[0], vertex[1] - p[1])
                      for p in filled)
        assert nearest == pytest.approx(0.0, abs=1e-12)


def test_ring_spokes_carry_both_the_vertices_and_the_even_bearings():
    rhombus = [(6.0, 0.0), (0.0, 3.0), (-6.0, 0.0), (0.0, -3.0)]
    spokes = geometry._ring_spokes(rhombus, 16)
    angles = [angle for angle, _point in spokes]

    assert angles == sorted(angles), "not walked in order round the outline"
    carried = [point for _angle, point in spokes if point is not None]
    for vertex in rhombus:
        assert vertex in carried


def test_a_generated_bearing_landing_on_a_vertex_keeps_the_vertex():
    """Otherwise the outline is reached only to within the ray cast's own
    precision at exactly the points that matter most."""
    square = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]
    spokes = geometry._ring_spokes(square, 4)
    # Four vertices at 0/90/180/270 and four generated bearings at the same
    # angles: one spoke each, and each carrying its vertex.
    assert len(spokes) == 4
    assert all(point is not None for _angle, point in spokes)


def test_ring_of_a_rhombus_still_has_a_round_hole():
    """The reason the spokes are sampled by angle instead of reusing the
    outline's vertices: a rhombus puts nearly all of them on its corners."""
    rhombus = [(6.0, 0.0), (0.0, 3.0), (-6.0, 0.0), (0.0, -3.0)]
    triangles = geometry.ring_triangles(rhombus, 1.5, 48)
    inner = [p for p in triangles if math.hypot(*p) < 1.5 + 1e-6]
    assert len(inner) >= 48
    for point in inner:
        assert math.hypot(*point) == pytest.approx(1.5, abs=1e-9)


def test_ring_without_a_hole_is_a_solid_fan():
    loop = geometry.circle_loop(5.0, 16)
    assert geometry.ring_triangles(loop, 0.0, 32) == \
        geometry.fan_to_triangles(loop, centre=(0.0, 0.0))


def test_a_hole_wider_than_the_outline_falls_back_to_a_solid_body():
    """Bad data - a ring built from it would turn inside out."""
    loop = geometry.circle_loop(2.0, 16)
    assert geometry.ring_triangles(loop, 5.0, 32) == \
        geometry.fan_to_triangles(loop, centre=(0.0, 0.0))
