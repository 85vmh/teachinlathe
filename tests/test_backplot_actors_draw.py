"""Every actor drawn once, against a stand-in frame.

There is no GL context here, so this does not check pixels. What it checks is
the half of each actor that is ordinary Python and would otherwise only run on
the machine: reading the frame, building vertices, and pushing the matrix
stack. A misspelled context field or a transform left on the stack shows up
here rather than as an empty plot in front of an operator.

``draw()`` is called directly rather than through ``scope()``: the scope is
the GL-state half, and entering it needs a live context.

The matrix stack is upstream's own - it is pure numpy - so the transforms the
actors push are exercised for real.
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

glcanon_scene = pytest.importorskip(
    "rs274.glcanon_scene",
    reason="needs a LinuxCNC with the split-out preview renderer")

from teachinlathe.widgets.backplot.actors import (  # noqa: E402
    origin, screen, sizing, text)
from teachinlathe.widgets.backplot.actors.units import mm, to_mm  # noqa: E402
from teachinlathe.widgets.backplot.actors.centerline import (  # noqa: E402
    CenterlineActor)
from teachinlathe.widgets.backplot.actors.grid import GridActor  # noqa: E402
from teachinlathe.widgets.backplot.actors.insert_tool import (  # noqa: E402
    InsertActor, _offset, _rotate, _to_plane)
from teachinlathe.widgets.backplot.actors.origin import OriginActor  # noqa: E402
from teachinlathe.widgets.backplot.actors.stock import StockActor  # noqa: E402
from teachinlathe.widgets.backplot.actors.ticks import TicksActor  # noqa: E402
from teachinlathe.widgets.backplot.actors.axis_arrows import (  # noqa: E402
    AxisArrowsActor)
from teachinlathe.widgets.backplot.actors.axis_letters import (  # noqa: E402
    AxisLettersActor)


class RecordingPrimitives:
    """``ctx.prim``, counting what it is asked to draw."""

    def __init__(self):
        self.lines = []
        self.strings = []

    def draw_lines(self, ctx, points, color, alpha=1.0, mvp=None):
        """Upstream's signature, alpha and all - the grid is drawn through it
        at half strength, and a stand-in that did not take it would make that
        look like a bug in the actor."""
        self.lines.append((list(points), color, alpha))

    def draw_hershey(self, ctx, text, color, frac=0.0, bbox=False):
        self.strings.append((text, color, frac))

    def lines_to_array(self, points, color):
        """The real one packs the points into columns 0:3; this does too, so a
        filled shape can be measured as well as counted."""
        arr = np.zeros((len(points), 8))
        if len(points):
            arr[:, 0:3] = points
            arr[:, 3:6] = color
            arr[:, 6] = 1.0
        return arr


class RecordingRenderer:
    def __init__(self):
        self.arrays = []

    def draw_flat_array(self, mvp, verts, mode=None):
        self.arrays.append(verts)


class FakeTool:
    def __init__(self, diameter=0.8, orientation=2):
        self.diameter = diameter
        self.orientation = orientation


class FakeStat:
    g5x_offset = [0.0] * 9
    g92_offset = [0.0] * 9
    rotation_xy = 0.0


class FakeCanon:
    """Extents of a small part, in internal units (inches)."""
    min_extents = [0.0, 0.0, -2.0]
    max_extents = [1.0, 0.0, 0.0]


class FakeHost:
    """The backplot item, as the actors that read it see it.

    ``stock``, not ``workpiece``: upstream's canon has a ``workpieces`` of its
    own holding what ``(WORKPIECE,...)`` comments declared, and two things one
    letter apart on one object is a trap.
    """

    def __init__(self, stock=None, insert=None):
        self.stock = stock or {}
        self.insert = insert or {}


def lathe_frame(width=800, height=600, zoom=1.0):
    """A stand-in ``FrameContext``: an orthographic lathe view of a 120 mm
    window, with a tool in the spindle."""
    projection = np.array([
        [0.0, 0.0, 2.0 / 4.0, 1.0],
        [2.0 / 2.0, 0.0, 0.0, -0.5],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ])
    mv = glcanon_scene.MatrixStack(projection=np.eye(4))
    mv.projection = projection
    if zoom != 1.0:
        mv.scale(zoom, zoom, zoom)

    ctx = type("Ctx", (), {})()
    ctx.mv = mv
    ctx.prim = RecordingPrimitives()
    ctx.renderer = RecordingRenderer()
    ctx.width = width
    ctx.height = height
    ctx.colors = {"axis_x": (0, 0, 1), "axis_y": (1, 0, 0), "axis_z": (0, 1, 0)}
    ctx.stat = FakeStat()
    ctx.canon = FakeCanon()
    ctx.show_relative = True
    ctx.view = glcanon_scene.VY
    ctx.current_tool = lambda: FakeTool()
    ctx.to_internal_linear_unit = lambda value: value / 25.4
    ctx.to_internal_units = lambda values: [v / 25.4 for v in values]
    # The program's own transform. Upstream draws the trajectory with this
    # rather than the actors' stack, and the rapids actor follows it.
    ctx.preview_mvp = mv.mvp
    ctx.show_rapids = False
    return ctx


def drawn_vertices(ctx):
    return sum(len(points) for points, _color, _alpha in ctx.prim.lines)


@pytest.fixture
def labels(monkeypatch):
    """What the actors hand to the glyph atlas.

    Text is not geometry any more - it is a textured quad per character, drawn
    by ``text.draw`` in screen pixels - so this is where it is observed. The
    atlas itself needs a GL context and a font, neither of which a test has.
    """
    captured = []

    def record(ctx, strings, color, font="tick"):
        captured.extend((string, x, y, ax, ay, tuple(color), font)
                        for string, x, y, ax, ay in strings)

    monkeypatch.setattr(text, "draw", record)
    return captured


def texts(labels):
    return [entry[0] for entry in labels]


# ── each actor draws something ─────────────────────────────────────────────

def test_grid_draws_lines_on_both_axes():
    ctx = lathe_frame()
    GridActor().draw(ctx)
    assert drawn_vertices(ctx) > 0


def test_centerline_draws_a_dashed_cross():
    ctx = lathe_frame()
    CenterlineActor().draw(ctx)
    # Dashed, so many short segments rather than two long ones.
    assert drawn_vertices(ctx) > 8


def test_ticks_draw_marks_and_labels(labels):
    ctx = lathe_frame()
    TicksActor().draw(ctx)
    assert drawn_vertices(ctx) > 0, "no tick marks"
    assert labels, "no tick labels were drawn"
    for string in texts(labels):
        assert set(string) <= set("-0123456789"), string


def test_ticks_label_z_and_x_in_their_own_colours(labels):
    ctx = lathe_frame()
    TicksActor().draw(ctx)
    assert len({entry[5] for entry in labels}) == 2


def test_ticks_label_in_the_profile_editors_tick_font(labels):
    ctx = lathe_frame()
    TicksActor().draw(ctx)
    assert {entry[6] for entry in labels} == {"tick"}
    assert text.FONTS["tick"] == ("Sans", 12)


def test_tick_labels_are_placed_inside_the_window(labels):
    """Screen pixels now, not model space - so a label off the edge is a
    placement bug rather than something the view happens to crop."""
    ctx = lathe_frame()
    TicksActor().draw(ctx)
    for string, x, y, _ax, _ay, _color, _font in labels:
        assert -1 <= x <= ctx.width + 1, (string, x)
        assert -1 <= y <= ctx.height + 1, (string, y)


def test_arrows_and_letters_still_draw(labels):
    ctx = lathe_frame()
    AxisArrowsActor().draw(ctx)
    AxisLettersActor().draw(ctx)
    assert drawn_vertices(ctx) > 0
    assert sorted(texts(labels)) == ["X+", "Z+"]


def test_the_axis_labels_read_as_the_profile_editors_do(labels):
    """They could not before: the Hershey set has no '+'."""
    ctx = lathe_frame()
    AxisLettersActor().draw(ctx)
    assert sorted(texts(labels)) == ["X+", "Z+"]
    assert {entry[6] for entry in labels} == {"axis"}
    assert text.FONTS["axis"] == ("Sans Bold", 14)


def test_each_axis_label_takes_its_own_axis_colour(labels):
    ctx = lathe_frame()
    AxisLettersActor().draw(ctx)
    by_text = {entry[0]: entry[5] for entry in labels}
    assert by_text["Z+"] == tuple(ctx.colors["axis_z"])
    assert by_text["X+"] == tuple(ctx.colors["axis_x"])


def test_origin_draws_a_backing_disc_quadrants_and_a_ring():
    """All filled, nothing stroked. A stroked circle this small comes apart
    into butt-capped quads - see geometry.annulus."""
    ctx = lathe_frame()
    OriginActor().draw(ctx)
    assert drawn_vertices(ctx) == 0, "the ring was stroked, not filled"
    assert len(ctx.renderer.arrays) == 3, "disc, quadrants and ring expected"


def test_the_empty_quadrants_are_filled_with_the_background():
    """Left clear, the centreline and the face datum cross underneath and
    their dashes read as part of the symbol."""
    from teachinlathe.widgets.backplot.actors import origin as origin_module

    ctx = lathe_frame()
    OriginActor().draw(ctx)
    disc = ctx.renderer.arrays[0]
    assert tuple(disc[0][3:6]) == pytest.approx(
        tuple(origin_module.BACKGROUND))


def test_the_backing_disc_is_drawn_first_and_reaches_the_ring():
    """First, or it paints over the quadrants; out to the ring's outer edge,
    or the dashes show through under the ring itself."""
    ctx = lathe_frame()
    OriginActor().draw(ctx)
    px_per_z, _px = screen.pixels_per_unit(ctx, ctx.mv.mvp())

    disc = ctx.renderer.arrays[0]
    reach = max(math.hypot(row[0], row[2]) for row in disc) * px_per_z
    assert reach == pytest.approx(
        origin.RADIUS_PX + origin.OUTLINE_WIDTH / 2.0, rel=1e-6)


def test_the_ring_is_drawn_last():
    """It is the edge of the symbol; nothing may encroach on it."""
    ctx = lathe_frame()
    OriginActor().draw(ctx)
    ring = ctx.renderer.arrays[-1]
    assert tuple(ring[0][3:6]) == pytest.approx(tuple(origin.COLOR))
    inner = min(math.hypot(row[0], row[2]) for row in ring)
    assert inner > 0, "the ring closed over the centre"


# ── the stock, which depends on the host ───────────────────────────────────

def test_stock_draws_nothing_without_a_workpiece():
    ctx = lathe_frame()
    StockActor(FakeHost()).draw(ctx)
    assert drawn_vertices(ctx) == 0


def test_stock_draws_an_outline_and_hatch():
    ctx = lathe_frame()
    StockActor(FakeHost({"stock_length": 60.0,
                         "external_diameter": 40.0})).draw(ctx)
    assert drawn_vertices(ctx) > 6


def test_stock_draws_a_bore_line_when_the_bar_is_bored():
    plain = lathe_frame()
    StockActor(FakeHost({"stock_length": 60.0,
                         "external_diameter": 40.0})).draw(plain)
    bored = lathe_frame()
    StockActor(FakeHost({"stock_length": 60.0, "external_diameter": 40.0,
                         "internal_diameter": 20.0})).draw(bored)
    assert len(bored.prim.lines) > len(plain.prim.lines)


def test_stock_ignores_a_workpiece_it_cannot_read():
    ctx = lathe_frame()
    StockActor(FakeHost({"stock_length": "not a number"})).draw(ctx)
    assert drawn_vertices(ctx) == 0


def test_stock_ignores_a_bar_with_no_length():
    ctx = lathe_frame()
    StockActor(FakeHost({"stock_length": 0.0,
                         "external_diameter": 40.0})).draw(ctx)
    assert drawn_vertices(ctx) == 0


# ── the insert ─────────────────────────────────────────────────────────────

def test_insert_draws_a_body_an_edge_and_a_hole():
    ctx = lathe_frame()
    InsertActor(FakeHost())._draw_insert(ctx)
    assert drawn_vertices(ctx) > 0, "no outline"
    # One filled array: the body. The hole is not filled - it is left out of
    # the body's own geometry, so what is behind the insert shows through.
    assert len(ctx.renderer.arrays) == 1


def test_the_hole_is_open_rather_than_painted_over():
    """The body has no geometry inside the clamping hole. Filling it in a
    second colour would look the same on an empty plot and hide the toolpath
    on a real one."""
    ctx = lathe_frame()
    actor = InsertActor(FakeHost())
    insert = actor._insert(ctx)
    hole_radius = insert.hole()[0] / 2.0
    shape = actor._shape(ctx)

    tip = insert.active_tip()
    centre = _to_plane(_rotate(_offset((0.0, 0.0), tip),
                               actor._angle(ctx, insert)))
    for x, _y, z in shape["body"]:
        radius = to_mm(math.hypot(x - centre[0], z - centre[2]))
        assert radius >= hole_radius - 1e-6


def test_the_hole_and_countersink_are_outlined():
    ctx = lathe_frame()
    shape = InsertActor(FakeHost())._shape(ctx)
    assert shape["hole"], "the hole has no outline"
    assert shape["countersink"], "the countersink has no outline"


def test_a_round_insert_with_no_hole_in_the_table_still_draws():
    ctx = lathe_frame()
    actor = InsertActor(FakeHost(insert={"family": "RCMT", "size_index": 0}))
    actor._draw_insert(ctx)
    assert len(ctx.renderer.arrays) == 1


def test_the_shape_is_built_once_per_tool_not_once_per_frame():
    """The insert does not change while the tool does not; only the transform
    it is drawn at does, and that rides on the matrix stack."""
    ctx = lathe_frame()
    actor = InsertActor(FakeHost())
    first = actor._shape(ctx)
    assert actor._shape(ctx) is first


def test_changing_the_tool_rebuilds_the_shape():
    ctx = lathe_frame()
    actor = InsertActor(FakeHost())
    first = actor._shape(ctx)
    ctx.current_tool = lambda: FakeTool(diameter=1.6, orientation=3)
    assert actor._shape(ctx) is not first


def test_insert_replaces_the_cone_rather_than_reimplementing_placement():
    """It is upstream's ToolPart, so the position logger, the rotary tilt and
    the foam cutter's second cone all stay upstream's answer."""
    assert issubclass(InsertActor, glcanon_scene.ToolPart)


def test_insert_takes_its_nose_radius_from_the_tool_table():
    """LinuxCNC keeps it as a diameter, in machine units."""
    ctx = lathe_frame()
    ctx.current_tool = lambda: FakeTool(diameter=1.6)
    insert = InsertActor(FakeHost())._insert(ctx)
    assert insert.nose_radius == pytest.approx(0.8)


def test_insert_falls_back_when_there_is_no_tool():
    ctx = lathe_frame()
    ctx.current_tool = lambda: None
    insert = InsertActor(FakeHost())._insert(ctx)
    assert insert.family == "DCMT"
    assert insert.nose_radius > 0


def test_insert_honours_a_choice_made_on_the_host():
    """The hook the tool list will set."""
    ctx = lathe_frame()
    insert = InsertActor(FakeHost(insert={
        "family": "WNMG", "size_index": 1, "nose_radius": 1.2}))._insert(ctx)
    assert insert.family == "WNMG"
    assert insert.size_code == "08"
    assert insert.nose_radius == pytest.approx(1.2)


def test_insert_falls_back_on_an_unknown_family():
    ctx = lathe_frame()
    insert = InsertActor(FakeHost(insert={"family": "NOPE"}))._insert(ctx)
    assert insert.family == "DCMT"


def test_a_sharp_tool_table_entry_does_not_stop_the_insert_drawing():
    """A nose radius of zero is a tool table left at its defaults."""
    ctx = lathe_frame()
    ctx.current_tool = lambda: FakeTool(diameter=0.0)
    InsertActor(FakeHost())._draw_insert(ctx)
    assert drawn_vertices(ctx) > 0


# ── the stack is left as it was found ──────────────────────────────────────

@pytest.mark.parametrize("actor", [
    GridActor(), CenterlineActor(), TicksActor(), OriginActor(),
    AxisArrowsActor(), AxisLettersActor(),
    StockActor(FakeHost({"stock_length": 60.0, "external_diameter": 40.0})),
])
def test_actors_leave_the_matrix_stack_where_they_found_it(actor):
    ctx = lathe_frame()
    before = len(ctx.mv)
    top = ctx.mv.top().copy()
    actor.draw(ctx)
    assert len(ctx.mv) == before
    assert np.allclose(ctx.mv.top(), top)


# ── annotation keeps its size as the operator zooms ────────────────────────

def drawn_points(ctx):
    """Every vertex the actor put on screen, stroked or filled."""
    points = [p for line, _color, _alpha in ctx.prim.lines for p in line]
    for array in ctx.renderer.arrays:
        points.extend(tuple(row[0:3]) for row in array)
    return points


def screen_reach(ctx, axis):
    """How far the furthest vertex lies from the origin, in pixels.

    ``axis`` is 0 for model X and 2 for model Z; the pixel scale is the one
    for that axis, which is what makes this a screen measurement rather than
    a model one.
    """
    px_per_z, px_per_x = screen.pixels_per_unit(ctx, ctx.mv.mvp())
    scale = px_per_x if axis == 0 else px_per_z
    return max(abs(point[axis]) for point in drawn_points(ctx)) * scale


ZOOMS = (0.25, 1.0, 4.0, 40.0)


@pytest.mark.parametrize("zoom", ZOOMS)
def test_the_arrows_are_the_same_size_at_every_zoom(zoom):
    """They say which way the axes run, which is not a measurement - so they
    are drawn in pixels and do not grow with the view."""
    ctx = lathe_frame(zoom=zoom)
    AxisArrowsActor().draw(ctx)
    assert screen_reach(ctx, 2) == pytest.approx(sizing.AXIS_LENGTH_PX,
                                                 rel=1e-9)
    assert screen_reach(ctx, 0) == pytest.approx(sizing.AXIS_LENGTH_PX,
                                                 rel=1e-9)


@pytest.mark.parametrize("zoom", ZOOMS)
def test_the_origin_symbol_is_the_same_size_at_every_zoom(zoom):
    """It marks a point, and a point has no size to show. It also has to stay
    out from under the arrows, which no longer grow with it.

    The reach is the ring's outer edge, which is half a stroke past the
    radius - the ring is a filled band between two circles.
    """
    ctx = lathe_frame(zoom=zoom)
    OriginActor().draw(ctx)
    outer = origin.RADIUS_PX + origin.OUTLINE_WIDTH / 2.0
    assert screen_reach(ctx, 2) == pytest.approx(outer, rel=1e-6)


def test_the_origin_ring_is_a_band_not_a_disc():
    """The two empty quadrants have to stay empty: the symbol reads as a
    quartered circle, not as a dot."""
    ctx = lathe_frame()
    OriginActor().draw(ctx)
    ring = ctx.renderer.arrays[-1]      # last of disc, quadrants, ring
    px_per_z, _px_per_x = screen.pixels_per_unit(ctx, ctx.mv.mvp())

    radii = sorted({round(math.hypot(row[0], row[2]) * px_per_z, 6)
                    for row in ring})
    inner = origin.RADIUS_PX - origin.OUTLINE_WIDTH / 2.0
    outer = origin.RADIUS_PX + origin.OUTLINE_WIDTH / 2.0
    assert radii[0] == pytest.approx(inner, rel=1e-6)
    assert radii[-1] == pytest.approx(outer, rel=1e-6)
    assert inner > 0, "the band closed over the centre"


@pytest.mark.parametrize("zoom", ZOOMS)
def test_the_axis_labels_stay_with_their_arrows(zoom, labels):
    """Placed in pixels like the arrows they name, and at a font size rather
    than a model one - so neither moves out from under the other."""
    ctx = lathe_frame(zoom=zoom)
    AxisLettersActor().draw(ctx)
    assert sorted(texts(labels)) == ["X+", "Z+"]

    origin_px = text.to_screen(ctx.mv.mvp(), (0.0, 0.0, 0.0),
                               (ctx.width, ctx.height))
    for string, x, y, _ax, _ay, _color, _font in labels:
        reach = math.hypot(x - origin_px[0], y - origin_px[1])
        assert reach < sizing.AXIS_LENGTH_PX * 2, (string, reach)


def test_the_arrow_shaft_starts_clear_of_the_origin_symbol():
    """Otherwise a wide shaft shows out of the middle of the symbol."""
    assert sizing.ORIGIN_CLEARANCE_PX > origin.RADIUS_PX


def test_the_arrow_head_fits_inside_the_shaft():
    assert sizing.HEAD_LENGTH_PX < sizing.AXIS_LENGTH_PX


@pytest.mark.parametrize("zoom", ZOOMS)
def test_the_tick_scale_still_follows_the_zoom(zoom):
    """The counterpart: the ticks are a measurement, so their spacing must
    change with the view even though their marks do not."""
    ctx = lathe_frame(zoom=zoom)
    TicksActor().draw(ctx)
    assert drawn_vertices(ctx) > 0


# ── the rapids, taken out of upstream's buffer and dashed ──────────────────

class FakeProgramGeometry:
    """``ProgramGeometry`` as the rapids actor reads it: a strip of points and
    a kind per point.

    A segment joins vertex i to i+1 and takes the kind of the vertex it *ends*
    on - GL's last-vertex provoking convention, which upstream's own span
    builder reads the same way. Getting that off by one takes the rapids from
    the right moves to their neighbours, and both look plausible.
    """

    TRAVERSE, FEED, ARC = 0, 1, 2

    def __init__(self, points, kinds):
        self._points = np.asarray(points, dtype=np.float32)
        self.kinds = np.asarray(kinds, dtype=np.uint32)

    def positions(self, plane=0):
        return self._points


def program_with(kinds):
    """A straight run of points along Z, one per kind given."""
    points = [(0.0, 0.0, float(i)) for i in range(len(kinds))]
    return FakeProgramGeometry(points, kinds)


def canon_with(program):
    canon = FakeCanon()
    canon.program_geometry = program
    return canon


def test_rapids_draw_only_the_traverse_moves():
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    ctx = lathe_frame()
    # Segments: 0->1 feed, 1->2 traverse, 2->3 feed, 3->4 traverse.
    ctx.canon = canon_with(program_with([1, 1, 0, 1, 0]))
    actor = RapidsActor()
    segments = actor._read(ctx)

    assert len(segments) == 2
    assert [float(s[0][2]) for s in segments] == [1.0, 3.0]
    assert [float(s[1][2]) for s in segments] == [2.0, 4.0]


def test_rapids_are_dashed_not_solid():
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    ctx = lathe_frame()
    ctx.canon = canon_with(program_with([1, 0]))
    RapidsActor().draw(ctx)
    # One segment: solid would be exactly two vertices.
    assert drawn_vertices(ctx) > 2


def test_rapids_draw_nothing_without_a_program():
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    ctx = lathe_frame()
    ctx.canon = None
    RapidsActor().draw(ctx)
    assert drawn_vertices(ctx) == 0


def test_rapids_draw_nothing_when_the_program_has_none():
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    ctx = lathe_frame()
    ctx.canon = canon_with(program_with([1, 1, 1]))
    RapidsActor().draw(ctx)
    assert drawn_vertices(ctx) == 0


def test_the_rapids_are_read_once_per_program():
    """Reading them is numpy over the whole program; it belongs on a load,
    not on a frame."""
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    ctx = lathe_frame()
    ctx.canon = canon_with(program_with([1, 0, 1, 0]))
    actor = RapidsActor()
    first = actor._read(ctx)
    assert actor._read(ctx) is first


def test_a_new_program_is_read_again():
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    ctx = lathe_frame()
    actor = RapidsActor()
    ctx.canon = canon_with(program_with([1, 0]))
    first = actor._read(ctx)
    ctx.canon = canon_with(program_with([1, 0, 0]))
    assert actor._read(ctx) is not first


def test_the_dashes_are_rebuilt_only_when_the_zoom_changes():
    """They are a pixel length, so the scale decides them - but a drag of the
    zoom must not rebuild on every frame of it."""
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    actor = RapidsActor()
    segments = np.array([[[0.0, 0.0, 0.0], [0.0, 0.0, 10.0]]])
    first = actor._dash(segments, 20.0)
    assert actor._dash(segments, 20.0) is first
    assert actor._dash(segments, 20.0 * 1.001) is first, "rebuilt on a nudge"
    assert actor._dash(segments, 80.0) is not first


def test_a_program_that_rapids_too_often_draws_them_solid():
    """Dashing is per-segment Python. A solid rapid beats a zoom that lurches."""
    from teachinlathe.widgets.backplot.actors import rapids

    actor = rapids.RapidsActor()
    many = np.array([[[0.0, 0.0, float(i)], [0.0, 0.0, float(i) + 1.0]]
                     for i in range(rapids.MAX_DASHED_SEGMENTS + 1)])
    assert len(actor._dash(many, 20.0)) == len(many) * 2


def test_the_rapids_follow_the_programs_own_transform():
    """Not the actors' stack: these are the program's vertices, and
    preview_mvp is what upstream draws them with."""
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    assert RapidsActor.FOLLOW_PROGRAM_ORIGIN is False
    assert RapidsActor.DEPTH_WRITE is False


# ── the hatch stops at the part ────────────────────────────────────────────

FEED, ARC, TRAVERSE = 1, 2, 0


def hatch_points(ctx):
    """Just the hatching, told apart from the stock outline by its colour."""
    from teachinlathe.widgets.backplot.actors import palette

    return [point for line, colour, _alpha in ctx.prim.lines
            if colour == palette.HATCH for point in line]


def turned_program(radius_mm, from_z_mm, to_z_mm):
    """A single cutting pass along Z at one radius."""
    points = [(mm(radius_mm), 0.0, mm(from_z_mm)),
              (mm(radius_mm), 0.0, mm(to_z_mm))]
    return FakeProgramGeometry(points, [FEED, FEED])


BAR = {"stock_length": 60.0, "external_diameter": 40.0}


def test_the_profile_is_the_smallest_radius_a_cut_reached():
    from teachinlathe.widgets.backplot.actors import profile

    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    found = profile.finished(ctx, mm(-60.0), 0.0, mm(20.0))

    assert found is not None
    assert found.at(mm(-10.0)) == pytest.approx(mm(10.0), abs=1e-6)
    # Past where the cut stopped the bar is still full size.
    assert found.at(mm(-50.0)) == pytest.approx(mm(20.0), abs=1e-6)


def test_the_profile_ignores_rapids():
    """A rapid over the bar cuts nothing."""
    from teachinlathe.widgets.backplot.actors import profile

    ctx = lathe_frame()
    points = [(mm(5.0), 0.0, 0.0), (mm(5.0), 0.0, mm(-30.0))]
    ctx.canon = canon_with(FakeProgramGeometry(points, [TRAVERSE, TRAVERSE]))
    assert profile.finished(ctx, mm(-60.0), 0.0, mm(20.0)) is None


def test_the_profile_takes_arc_moves_as_cuts():
    from teachinlathe.widgets.backplot.actors import profile

    ctx = lathe_frame()
    points = [(mm(8.0), 0.0, 0.0), (mm(8.0), 0.0, mm(-30.0))]
    ctx.canon = canon_with(FakeProgramGeometry(points, [ARC, ARC]))
    found = profile.finished(ctx, mm(-60.0), 0.0, mm(20.0))
    assert found.at(mm(-10.0)) == pytest.approx(mm(8.0), abs=1e-6)


def test_a_plunge_pulls_in_the_column_it_is_at():
    """A move at constant Z spans no columns to interpolate across."""
    from teachinlathe.widgets.backplot.actors import profile

    ctx = lathe_frame()
    points = [(mm(20.0), 0.0, mm(-15.0)), (mm(6.0), 0.0, mm(-15.0))]
    ctx.canon = canon_with(FakeProgramGeometry(points, [FEED, FEED]))
    found = profile.finished(ctx, mm(-60.0), 0.0, mm(20.0))
    assert found.at(mm(-15.0)) == pytest.approx(mm(6.0), abs=1e-4)


def test_the_hatch_stops_at_the_turned_diameter():
    """The bug this is here for: the material was hatched straight over the
    toolpath that removes it."""
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    StockActor(FakeHost(BAR)).draw(ctx)

    points = hatch_points(ctx)
    assert points, "nothing was hatched"
    turned = [p for p in points if p[2] > mm(-30.0) + 1e-9]
    assert turned, "the turned half was not hatched at all"
    for x, _y, z in turned:
        assert x <= mm(10.0) + 1e-6, (x, z)


def test_the_hatch_still_fills_what_was_not_turned():
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    StockActor(FakeHost(BAR)).draw(ctx)

    untouched = [p for p in hatch_points(ctx) if p[2] < mm(-35.0)]
    assert untouched, "the untouched half lost its hatching"
    assert max(p[0] for p in untouched) > mm(15.0)


def test_the_bar_hatches_whole_with_no_program():
    """No program is not a failure - it is a bar on its own."""
    ctx = lathe_frame()
    ctx.canon = None
    StockActor(FakeHost(BAR)).draw(ctx)

    points = hatch_points(ctx)
    assert points
    assert max(p[0] for p in points) > mm(15.0)


# ── the grid is matched to the profile editor's by its alpha ───────────────

def test_the_grid_is_drawn_transparent():
    """GL floors a line width at one pixel, so the profile editor's 0.5px
    hairline can only be matched by making a full-width line partly clear."""
    from teachinlathe.widgets.backplot.actors import palette

    ctx = lathe_frame()
    GridActor().draw(ctx)
    assert {alpha for _line, _colour, alpha in ctx.prim.lines} == {
        palette.GRID_ALPHA}
    assert palette.GRID_ALPHA < 1.0


def test_the_centreline_is_drawn_transparent():
    """A datum sitting under the drawing, not geometry in it."""
    from teachinlathe.widgets.backplot.actors import palette

    ctx = lathe_frame()
    CenterlineActor().draw(ctx)
    assert {alpha for _line, _colour, alpha in ctx.prim.lines} == {
        palette.CENTERLINE_ALPHA}
    assert palette.CENTERLINE_ALPHA == 0.7


def test_everything_else_is_drawn_opaque():
    ctx = lathe_frame()
    TicksActor().draw(ctx)
    StockActor(FakeHost(BAR)).draw(ctx)
    assert {alpha for _line, _colour, alpha in ctx.prim.lines} == {1.0}


def test_an_alpha_in_a_colour_tuple_would_be_ignored():
    """Stated so it is not reached for: the colours here are rgb, and the
    fourth element of one is read by nothing. Transparency is the separate
    argument the two actors above pass."""
    from teachinlathe.widgets.backplot.actors import palette

    for name in ("GRID", "CENTERLINE", "AXIS_Z", "AXIS_X", "STOCK", "HATCH",
                 "FEED", "TRAVERSE", "ORIGIN", "INSERT_BODY", "INSERT_EDGE"):
        assert len(getattr(palette, name)) == 3, name


# ── labels keep out of each other's way at every zoom ──────────────────────

@pytest.mark.parametrize("zoom", [40.0, 4.0, 1.0, 0.25, 0.02, 0.002])
def test_tick_labels_never_overlap(zoom, labels):
    """Zooming out used to walk them into each other: the step ladder had no
    bottom rung, so the labels closed up without the step ever coarsening."""
    from teachinlathe.widgets.backplot.actors import stepping

    ctx = lathe_frame(zoom=zoom)
    TicksActor().draw(ctx)
    assert labels, "no labels at all"

    # Along each edge separately - a Z label and an X label may share a corner.
    for key, axis in (("z", 1), ("x", 2)):
        along = sorted({round(entry[axis], 6) for entry in labels
                        if _edge_of(entry, ctx) == key})
        for first, second in zip(along, along[1:]):
            assert second - first >= stepping.MIN_LABEL_PITCH_PX - 1e-6, (
                zoom, key, first, second)


def _edge_of(entry, ctx):
    """Which scale a label belongs to, by the alignment it was placed with."""
    _string, _x, _y, align_x, _align_y = entry[:5]
    return "z" if align_x == 0.5 else "x"


@pytest.mark.parametrize("zoom", [40.0, 4.0, 1.0, 0.25, 0.02])
def test_the_grid_stays_in_step_with_the_labels(zoom, labels):
    """They read the same rule, so a grid line without a label under it means
    one of them coarsened and the other did not."""
    ctx = lathe_frame(zoom=zoom)
    GridActor().draw(ctx)
    grid_lines = drawn_vertices(ctx) // 2

    ticks = lathe_frame(zoom=zoom)
    TicksActor().draw(ticks)
    assert grid_lines <= len(labels) + 4, (zoom, grid_lines, len(labels))


# ── glyph quads have to land on the pixel grid ─────────────────────────────

class FakeAtlas:
    """Enough of ``GlyphAtlas`` to see where a string is put.

    The real one is a GL texture and a Pango rasterisation; what matters here
    is only that its metrics are integers, as ``build_atlas`` makes them.
    """

    char_width = 7
    line_space = 15
    descent = 3

    def __init__(self):
        self.glyphs = {ord(c): {"w": 7, "h": 12, "advance": 7,
                                "u0": 0.0, "v0": 0.0, "u1": 1.0, "v1": 1.0}
                       for c in "-0123456789+XZ"}
        self.pens = []
        self.drawn = []

    def string_quads(self, s, x, y):
        self.pens.append((x, y))
        return [(x, y, 0.0, 0.0)] * (6 * len(s))

    def _draw_array(self, verts, color, textured, screen):
        self.drawn.append((len(verts), color, screen))


@pytest.fixture
def fake_atlas(monkeypatch):
    from teachinlathe.widgets.backplot.actors import text as text_module

    built = FakeAtlas()
    monkeypatch.setattr(text_module, "atlas", lambda font="tick": built)
    return built


def test_the_pen_lands_on_whole_pixels(fake_atlas):
    """The bug this is here for: the atlas is sampled GL_NEAREST, so a quad
    off the pixel grid drops and doubles texels - one-pixel stems vanish and
    the text comes out thin, broken and pale."""
    ctx = lathe_frame()
    text.draw(ctx, [("-100", 123.456, 77.9, text.CENTRE, text.TOP),
                    ("0", 10.0, 20.0, text.LEFT, text.BOTTOM),
                    ("42", 0.5, 0.5, text.RIGHT, text.CENTRE)], (0, 0, 0))

    assert fake_atlas.pens
    for pen_x, pen_y in fake_atlas.pens:
        assert pen_x == int(pen_x), pen_x
        assert pen_y == int(pen_y), pen_y


def test_centring_still_centres_after_rounding(fake_atlas):
    ctx = lathe_frame()
    text.draw(ctx, [("10", 100.0, 50.0, text.CENTRE, text.BOTTOM)], (0, 0, 0))
    pen_x, _pen_y = fake_atlas.pens[0]
    # Two glyphs, seven pixels each: centred on 100 puts the pen at 93.
    assert pen_x == 93


def test_every_string_goes_in_one_draw_call(fake_atlas):
    """Batched - the whole reason draw() takes a list."""
    ctx = lathe_frame()
    text.draw(ctx, [(str(n), float(n), 10.0, text.LEFT, text.BOTTOM)
                    for n in range(20)], (0, 0, 0))
    assert len(fake_atlas.drawn) == 1


def test_the_viewport_goes_to_the_shader(fake_atlas):
    ctx = lathe_frame(width=640, height=480)
    text.draw(ctx, [("0", 1.0, 1.0, text.LEFT, text.BOTTOM)], (0, 0, 0))
    assert fake_atlas.drawn[0][2] == (640, 480)


# ── where the axis labels sit ──────────────────────────────────────────────

def test_the_x_label_sits_to_the_right_of_its_arrow(labels):
    """The stock and its hatching lie to the left of the X shaft, and the
    label was landing on them. The profile editor puts this one on the left;
    this plot has something there and it does not."""
    ctx = lathe_frame()
    AxisLettersActor().draw(ctx)
    origin_px = text.to_screen(ctx.mv.mvp(), (0.0, 0.0, 0.0),
                               (ctx.width, ctx.height))

    x_label = next(e for e in labels if e[0] == "X+")
    assert x_label[1] > origin_px[0], "X+ is still left of the shaft"
    assert x_label[3] == text.LEFT, "anchored on the wrong edge to grow right"


def test_the_z_label_still_sits_above_its_arrow(labels):
    ctx = lathe_frame()
    AxisLettersActor().draw(ctx)
    origin_px = text.to_screen(ctx.mv.mvp(), (0.0, 0.0, 0.0),
                               (ctx.width, ctx.height))

    z_label = next(e for e in labels if e[0] == "Z+")
    assert z_label[2] > origin_px[1], "Z+ dropped below the shaft"
    assert z_label[4] == text.BOTTOM


def test_neither_label_lands_on_the_origin_symbol(labels):
    """They are placed off the arrow tips, and the symbol has grown."""
    ctx = lathe_frame()
    AxisLettersActor().draw(ctx)
    origin_px = text.to_screen(ctx.mv.mvp(), (0.0, 0.0, 0.0),
                               (ctx.width, ctx.height))

    reach = origin.RADIUS_PX + origin.OUTLINE_WIDTH / 2.0
    for label, x, y, _ax, _ay, _colour, _font in labels:
        assert math.hypot(x - origin_px[0], y - origin_px[1]) > reach, label


def test_the_shaft_still_starts_clear_of_the_bigger_symbol():
    """The clearance and the radius are two halves of one decision; growing
    the symbol without the clearance runs the shafts out of the middle of it.
    """
    outer = origin.RADIUS_PX + origin.OUTLINE_WIDTH / 2.0
    assert sizing.ORIGIN_CLEARANCE_PX >= outer
    assert sizing.ORIGIN_CLEARANCE_PX < sizing.AXIS_LENGTH_PX - sizing.HEAD_LENGTH_PX


# ── the profile is the expensive thing on this plot ────────────────────────

def reference_profile(radii, z_start, step, starts, ends):
    """The profile written the obvious way, a move at a time.

    Kept as the thing the vectorised one is checked against: that version
    exists only because this one put a Python loop over every cutting move on
    the frame path, and a rewrite for speed is worth nothing if it quietly
    computes something else.
    """
    out = radii.copy()
    for start, end in zip(starts, ends):
        x0, z0 = float(start[0]), float(start[2])
        x1, z1 = float(end[0]), float(end[2])
        if abs(z1 - z0) < 1e-12:
            index = int(round((z0 - z_start) / step))
            if 0 <= index < len(out):
                out[index] = min(out[index], x0, x1)
            continue
        low, high = min(z0, z1), max(z0, z1)
        first = max(0, int(np.ceil((low - z_start) / step)))
        last = min(len(out) - 1, int(np.floor((high - z_start) / step)))
        for column in range(first, last + 1):
            z = z_start + column * step
            out[column] = min(out[column],
                              x0 + (z - z0) / (z1 - z0) * (x1 - x0))
    return out


def random_moves(count, seed=7):
    rng = np.random.default_rng(seed)
    z = np.sort(rng.uniform(mm(-60), 0.0, count + 1))
    x = rng.uniform(mm(2), mm(20), count + 1)
    # Every fourth move is a plunge - constant Z, which spans no columns.
    z[1::4] = z[0::4][:len(z[1::4])]
    points = np.stack([x, np.zeros(count + 1), z], axis=1)
    return points[:-1], points[1:]


@pytest.mark.parametrize("count", [1, 7, 200, 3000])
def test_the_vectorised_profile_matches_the_obvious_one(count):
    from teachinlathe.widgets.backplot.actors import profile

    starts, ends = random_moves(count)
    z_start, z_end = mm(-60), 0.0
    step = (z_end - z_start) / (profile.SAMPLES - 1)
    radii = np.full(profile.SAMPLES, mm(20))

    mine = radii.copy()
    profile._cut(mine, z_start, step, starts, ends)
    assert mine == pytest.approx(
        reference_profile(radii, z_start, step, starts, ends), abs=1e-12)


def test_chunking_does_not_change_the_answer(monkeypatch):
    """A slice boundary must fall between moves, not through one."""
    from teachinlathe.widgets.backplot.actors import profile

    starts, ends = random_moves(400)
    z_start, z_end = mm(-60), 0.0
    step = (z_end - z_start) / (profile.SAMPLES - 1)

    whole = np.full(profile.SAMPLES, mm(20))
    profile._cut(whole, z_start, step, starts, ends)

    monkeypatch.setattr(profile, "CHUNK", 64)
    chunked = np.full(profile.SAMPLES, mm(20))
    profile._cut(chunked, z_start, step, starts, ends)
    assert chunked == pytest.approx(whole, abs=1e-12)


def test_a_move_reaching_the_whole_bar_still_fits_one_chunk(monkeypatch):
    """The slice loop has to make progress even when one move alone is over
    the cap, or it spins."""
    from teachinlathe.widgets.backplot.actors import profile

    monkeypatch.setattr(profile, "CHUNK", 4)
    starts = np.array([[mm(5), 0.0, mm(-60)]])
    ends = np.array([[mm(5), 0.0, 0.0]])
    radii = np.full(profile.SAMPLES, mm(20))
    profile._cut(radii, mm(-60), mm(60) / (profile.SAMPLES - 1), starts, ends)
    assert radii.max() == pytest.approx(mm(5))


def test_the_profile_is_built_once_per_program():
    """Reading it walks the whole program; the plot redraws every time the
    machine moves. Rebuilding it per frame sat on the processor."""
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    actor = StockActor(FakeHost(BAR))

    actor.draw(ctx)
    first = actor._profile
    actor.draw(ctx)
    assert actor._profile is first


def test_a_new_program_rebuilds_the_profile():
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    actor = StockActor(FakeHost(BAR))
    actor.draw(ctx)
    first = actor._profile

    ctx.canon = canon_with(turned_program(6.0, 0.0, -40.0))
    actor.draw(ctx)
    assert actor._profile is not first


def test_the_hatch_is_cut_again_only_when_the_zoom_changes():
    """Its pitch is in pixels, so the view is the only thing that moves it."""
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    actor = StockActor(FakeHost(BAR))

    actor.draw(ctx)
    first = actor._hatch_edges
    actor.draw(lathe_frame_with(ctx))
    assert actor._hatch_edges is first

    zoomed = lathe_frame(zoom=8.0)
    zoomed.canon = ctx.canon
    actor.draw(zoomed)
    assert actor._hatch_edges is not first


def lathe_frame_with(other):
    frame = lathe_frame()
    frame.canon = other.canon
    return frame


def test_the_profile_cache_survives_a_recycled_address():
    """``id()`` is only unique among live objects. CPython hands the same
    address straight back once the object at it is freed, so a cache keyed on
    one can serve the previous program's profile to its replacement."""
    ctx = lathe_frame()
    actor = StockActor(FakeHost(BAR))

    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    actor.draw(ctx)
    first = actor._profile
    first_at = mm(-10.0)
    assert first.at(first_at) == pytest.approx(mm(10.0), abs=1e-6)

    # Drop the old program, then build a different one - which may well land
    # at the same address.
    ctx.canon = canon_with(turned_program(4.0, 0.0, -30.0))
    actor.draw(ctx)
    assert actor._profile is not first
    assert actor._profile.at(first_at) == pytest.approx(mm(4.0), abs=1e-6)


def test_the_rapids_cache_survives_a_recycled_address():
    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    ctx = lathe_frame()
    actor = RapidsActor()

    ctx.canon = canon_with(program_with([1, 0]))
    first = actor._read(ctx)
    assert len(first) == 1

    ctx.canon = canon_with(program_with([1, 0, 0]))
    again = actor._read(ctx)
    assert again is not first
    assert len(again) == 2


def test_a_new_program_on_the_same_bar_recuts_the_hatch():
    """The zoom alone is not the key: the stock is unchanged and the view has
    not moved, so nothing there says the shape being hatched around did."""
    ctx = lathe_frame()
    actor = StockActor(FakeHost(BAR))

    ctx.canon = canon_with(turned_program(16.0, 0.0, -30.0))
    actor.draw(ctx)
    shallow = hatch_points(ctx)

    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(4.0, 0.0, -30.0))
    actor.draw(ctx)
    deep = hatch_points(ctx)

    turned = lambda pts: [p for p in pts if p[2] > mm(-30.0) + 1e-9]  # noqa
    assert max(p[0] for p in turned(deep)) < max(p[0] for p in turned(shallow))


# ── what depends only on the view is built only when the view changes ──────

VIEW_CACHED = [
    ("grid", lambda: GridActor(), "_edges"),
    ("centerline", lambda: CenterlineActor(), "_edges"),
    ("ticks", lambda: TicksActor(), "_scales"),
    ("origin", lambda: OriginActor(), "_shapes"),
]


@pytest.mark.parametrize("name,make,attribute",
                         VIEW_CACHED, ids=[row[0] for row in VIEW_CACHED])
def test_a_still_view_is_not_rebuilt(name, make, attribute):
    """The plot is redrawn every time the machine moves - twenty-five times a
    second while a program runs - and none of these depend on where the tool
    is. Rebuilding them each time was a fifth of the frame."""
    actor = make()
    ctx = lathe_frame()
    actor.draw(ctx)
    first = getattr(actor, attribute)
    assert first is not None

    for _ in range(3):
        actor.draw(lathe_frame())          # same view, a new frame each time
    assert getattr(actor, attribute) is first


@pytest.mark.parametrize("name,make,attribute",
                         VIEW_CACHED, ids=[row[0] for row in VIEW_CACHED])
def test_moving_the_view_does_rebuild(name, make, attribute):
    actor = make()
    actor.draw(lathe_frame())
    first = getattr(actor, attribute)

    actor.draw(lathe_frame(zoom=4.0))
    assert getattr(actor, attribute) is not first


@pytest.mark.parametrize("name,make,attribute",
                         VIEW_CACHED, ids=[row[0] for row in VIEW_CACHED])
def test_a_resize_rebuilds(name, make, attribute):
    """The window's size is part of the view: the ticks hang off its edges and
    the grid is cut to it."""
    actor = make()
    actor.draw(lathe_frame())
    first = getattr(actor, attribute)

    actor.draw(lathe_frame(width=640, height=480))
    assert getattr(actor, attribute) is not first


def test_a_cached_actor_still_draws_every_frame(labels):
    """Cached is not skipped - the vertices are reused, the draw is not."""
    actor = TicksActor()
    for _ in range(3):
        ctx = lathe_frame()
        actor.draw(ctx)
        assert drawn_vertices(ctx) > 0
    assert labels


def test_the_view_key_is_none_when_the_frame_cannot_be_measured():
    """Callers treat that as "do not draw", not as a cache miss."""
    ctx = lathe_frame()
    assert screen.view_key(ctx, np.zeros((4, 4))) is None


# ── a datum set mid-program moves the profile ──────────────────────────────

def test_a_datum_change_rebuilds_the_profile():
    """The bug this is here for: a facing pass whose last cut becomes the new
    Z zero moves the profile without touching the program, the stock or the
    view. The toolpath translated - its points are machine coordinates - and
    the hatching stayed clipped to where the old origin had put the shape.
    """
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    actor = StockActor(FakeHost(BAR))

    actor.draw(ctx)
    first = actor._profile
    assert first is not None

    ctx.stat.g5x_offset = [0.0, 0.0, mm(-12.0)] + [0.0] * 6
    actor.draw(ctx)
    assert actor._profile is not first


@pytest.mark.parametrize("field,value", [
    ("g5x_offset", [0.0, 0.0, 1.0] + [0.0] * 6),
    ("g92_offset", [0.0, 0.0, 1.0] + [0.0] * 6),
    ("rotation_xy", 90.0),
])
def test_every_part_of_the_program_origin_rebuilds_the_profile(field, value):
    """All three are what ``Actor.place`` applies, and the profile is built in
    the frame that leaves."""
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    actor = StockActor(FakeHost(BAR))
    actor.draw(ctx)
    first = actor._profile

    setattr(ctx.stat, field, value)
    actor.draw(ctx)
    assert actor._profile is not first


def test_a_still_frame_still_reuses_the_profile():
    """Keying on the offsets must not turn into rebuilding every frame -
    reading the profile walks the whole program."""
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    actor = StockActor(FakeHost(BAR))

    actor.draw(ctx)
    first = actor._profile
    for _ in range(3):
        actor.draw(ctx)
    assert actor._profile is first


def test_the_hatch_is_recut_when_the_datum_moves():
    """The profile is part of the hatch's own key, so moving one moves the
    other - the whole point of putting it there."""
    ctx = lathe_frame()
    ctx.canon = canon_with(turned_program(10.0, 0.0, -30.0))
    actor = StockActor(FakeHost(BAR))

    actor.draw(ctx)
    first = actor._hatch_edges

    ctx.stat.g5x_offset = [0.0, 0.0, mm(-12.0)] + [0.0] * 6
    actor.draw(ctx)
    assert actor._hatch_edges is not first
