"""The GL state the actors leave behind them.

The scene draws every part inside its own ``scope()`` and establishes a
baseline once per frame - and that baseline covers depth and blend only, not
face culling. So a part that switches culling on and does not switch it back
off has changed the conditions every later part draws under.

That is not a hypothetical. It happened here: the insert's scope restored
culling by enabling it, the insert is drawn tenth of eleven parts, and the
annotation appended after it fills flat triangles whose winding is whatever
its geometry came out as. The Z arrow's head and two of the origin symbol's
four quadrants were wound the other way from the rest and silently vanished.
Lines were unaffected, so the plot looked almost right.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytest.importorskip(
    "rs274.glcanon_scene",
    reason="needs a LinuxCNC with the split-out preview renderer")

from teachinlathe.widgets.backplot.actors import base  # noqa: E402
from teachinlathe.widgets.backplot.actors import insert_tool  # noqa: E402
from teachinlathe.widgets.backplot.actors.grid import GridActor  # noqa: E402
from teachinlathe.widgets.backplot.actors.origin import OriginActor  # noqa: E402

from test_backplot_actors_draw import FakeHost, lathe_frame  # noqa: E402


class GLRecorder:
    """Stands in for the GL entry points a scope touches, remembering the
    last thing each was told."""

    def __init__(self):
        self.cull = None
        self.depth_func = []
        self.depth_mask = []
        self.widths = []

    def install(self, monkeypatch, module, *, cull=True, width=True):
        if cull:
            monkeypatch.setattr(module, "glEnable", self._enable, raising=False)
            monkeypatch.setattr(module, "glDisable", self._disable,
                                raising=False)
        monkeypatch.setattr(module, "glDepthFunc", self.depth_func.append,
                            raising=False)
        monkeypatch.setattr(module, "glDepthMask", self.depth_mask.append,
                            raising=False)
        monkeypatch.setattr(module, "glUseProgram", lambda *a: None,
                            raising=False)
        monkeypatch.setattr(module, "glBindVertexArray", lambda *a: None,
                            raising=False)
        if width:
            monkeypatch.setattr(module, "line_width", self.widths.append,
                                raising=False)

    def _enable(self, cap):
        if cap == insert_tool.GL_CULL_FACE:
            self.cull = True

    def _disable(self, cap):
        if cap == insert_tool.GL_CULL_FACE:
            self.cull = False


# ── the bug that cost the Z arrow and the origin's quadrants ───────────────

def test_the_insert_leaves_face_culling_off(monkeypatch):
    """The whole point. The baseline never turns culling on, so "restore"
    means off - and every part drawn after the insert fills flat geometry."""
    recorder = GLRecorder()
    recorder.install(monkeypatch, insert_tool)
    ctx = lathe_frame()

    with insert_tool.InsertActor(FakeHost()).scope(ctx):
        assert recorder.cull is False, "culled while drawing the insert"
    assert recorder.cull is False, "culling was left on for the parts after"


def test_the_insert_leaves_culling_off_even_when_drawing_raises(monkeypatch):
    recorder = GLRecorder()
    recorder.install(monkeypatch, insert_tool)
    ctx = lathe_frame()

    with pytest.raises(RuntimeError):
        with insert_tool.InsertActor(FakeHost()).scope(ctx):
            raise RuntimeError("boom")
    assert recorder.cull is False


def test_the_insert_puts_the_depth_test_back(monkeypatch):
    """Depth-always while it draws, so it reads over the toolpath; back to
    GL_LESS after, which is the baseline."""
    recorder = GLRecorder()
    recorder.install(monkeypatch, insert_tool)
    ctx = lathe_frame()

    with insert_tool.InsertActor(FakeHost()).scope(ctx):
        assert recorder.depth_func[-1] == insert_tool.GL_ALWAYS
    assert recorder.depth_func[-1] == insert_tool.GL_LESS


def test_the_insert_leaves_the_matrix_stack_where_it_found_it(monkeypatch):
    recorder = GLRecorder()
    recorder.install(monkeypatch, insert_tool)
    ctx = lathe_frame()
    before = len(ctx.mv)

    with insert_tool.InsertActor(FakeHost()).scope(ctx):
        ctx.mv.translate(1.0, 2.0, 3.0)
    assert len(ctx.mv) == before


# ── the background actors' own state ───────────────────────────────────────

def test_a_background_actor_turns_depth_writes_off_and_back_on(monkeypatch):
    """The grid lies in the toolpath's own plane; writing depth there would
    have whichever drew first reject the other."""
    recorder = GLRecorder()
    recorder.install(monkeypatch, base, cull=False)
    ctx = lathe_frame()

    actor = GridActor()
    assert actor.DEPTH_WRITE is False
    with actor.scope(ctx):
        assert recorder.depth_mask[-1] == base.GL_FALSE
    assert recorder.depth_mask[-1] == base.GL_TRUE


def test_an_overlay_actor_does_not_touch_depth_writes(monkeypatch):
    recorder = GLRecorder()
    recorder.install(monkeypatch, base, cull=False)
    ctx = lathe_frame()

    assert OriginActor().DEPTH_WRITE is True
    with OriginActor().scope(ctx):
        pass
    assert recorder.depth_mask == []


def test_an_actor_puts_the_line_width_back(monkeypatch):
    recorder = GLRecorder()
    recorder.install(monkeypatch, base, cull=False)
    ctx = lathe_frame()

    with OriginActor().scope(ctx):
        pass
    assert recorder.widths[0] == OriginActor.LINE_WIDTH
    assert recorder.widths[-1] == 1.0


# ── line widths, and the display scaling they are written against ──────────

def test_line_width_is_scaled_to_the_framebuffer(monkeypatch):
    """The weights are in the Canvas' logical pixels; the framebuffer is in
    device ones."""
    asked = []
    monkeypatch.setattr(base, "_set_line_width", asked.append)
    monkeypatch.setattr(base, "_DEVICE_PIXEL_RATIO", 2.0)
    base.line_width(1.5)
    assert asked == [3.0]


def test_the_pixel_ratio_defaults_to_one():
    assert base.device_pixel_ratio() == 1.0


@pytest.mark.parametrize("bad", [0, -1, None, "two"])
def test_a_nonsense_pixel_ratio_is_ignored(bad, monkeypatch):
    monkeypatch.setattr(base, "_DEVICE_PIXEL_RATIO", 1.0)
    base.set_device_pixel_ratio(bad)
    assert base.device_pixel_ratio() == 1.0


# ── multisampling: on for the insert, off for everything else ──────────────

def test_the_insert_turns_multisampling_on_and_back_off(monkeypatch):
    """The insert's edge is the boundary of a filled shape and needs the
    rasteriser to smooth it. The frame's baseline is off, so it owns the flag
    for the length of its own draw and no longer."""
    flags = []
    monkeypatch.setattr(insert_tool, "multisample", flags.append)
    monkeypatch.setattr(insert_tool, "glDisable", lambda *a: None,
                        raising=False)
    monkeypatch.setattr(insert_tool, "glDepthFunc", lambda *a: None,
                        raising=False)
    monkeypatch.setattr(insert_tool, "glUseProgram", lambda *a: None,
                        raising=False)
    monkeypatch.setattr(insert_tool, "glBindVertexArray", lambda *a: None,
                        raising=False)
    monkeypatch.setattr(insert_tool, "line_width", lambda *a: None,
                        raising=False)
    ctx = lathe_frame()

    with insert_tool.InsertActor(FakeHost()).scope(ctx):
        assert flags == [True]
    assert flags == [True, False]


# ── multisampling follows the shape, not the part ──────────────────────────

def test_straight_axis_aligned_actors_are_not_multisampled():
    """A grid line or a tick lands on whole pixels; antialiasing only spreads
    it over two at half strength, which reads as thin and follows the zoom."""
    from teachinlathe.widgets.backplot.actors import centerline, grid, stock
    from teachinlathe.widgets.backplot.actors.ticks import TicksActor

    from teachinlathe.widgets.backplot.actors.rapids import RapidsActor

    for actor_type in (grid.GridActor, stock.StockActor,
                       centerline.CenterlineActor, TicksActor, RapidsActor):
        assert actor_type.MULTISAMPLE is False, actor_type.__name__


def test_curved_actors_are_multisampled():
    """A 16-pixel circle has no whole pixels to land on."""
    from teachinlathe.widgets.backplot.actors import origin

    assert origin.OriginActor.MULTISAMPLE is True


def test_text_no_longer_needs_multisampling():
    """It did while it was Hershey strokes at arbitrary angles. A glyph quad
    is axis-aligned and carries its own coverage in the atlas texture, so the
    rasteriser has nothing to smooth."""
    import inspect

    from teachinlathe.widgets.backplot.actors import axis_letters, ticks
    from teachinlathe.widgets.backplot.actors.axis_letters import (
        AxisLettersActor)

    assert AxisLettersActor.MULTISAMPLE is False
    assert ticks.TicksActor.MULTISAMPLE is False
    for module in (ticks, axis_letters):
        assert "multisample" not in inspect.getsource(module), module.__name__


# ── the width does not follow the zoom ─────────────────────────────────────

def test_the_requested_width_is_the_same_at_every_zoom(monkeypatch):
    """A line is a drawn thing, not a part of the workpiece: zooming in covers
    more of the part at the same weight on screen."""
    asked = []
    monkeypatch.setattr(base, "_set_line_width", asked.append)

    for projection_scale in (0.01, 1.0, 100.0):
        ctx = lathe_frame()
        ctx.mv.projection = ctx.mv.projection * projection_scale
        with GridActor().scope(ctx):
            pass

    entered = asked[0::2]
    assert len(set(entered)) == 1, "the width followed the zoom"
    assert entered[0] == GridActor.LINE_WIDTH


def test_the_width_scale_is_one_knob_over_every_weight(monkeypatch):
    from teachinlathe.widgets.backplot.actors import palette

    asked = []
    monkeypatch.setattr(base, "_set_line_width", asked.append)
    monkeypatch.setattr(palette, "WIDTH_SCALE", 2.0)
    base.line_width(1.5)
    assert asked == [3.0]


def test_a_pixel_ratio_below_one_never_thins_a_line(monkeypatch):
    """A framebuffer smaller than the item it fills is a bad reading, not a
    display to thin lines for."""
    monkeypatch.setattr(base, "_DEVICE_PIXEL_RATIO", 1.0)
    base.set_device_pixel_ratio(0.5)
    assert base.device_pixel_ratio() == 1.0


# ── text is drawn heavier than the marks beside it ─────────────────────────

def test_text_has_no_line_weight_at_all():
    """It is not drawn with lines any more. A glyph is a textured quad, so its
    weight is the font's and there is nothing here to set."""
    from teachinlathe.widgets.backplot.actors import palette

    assert not hasattr(palette, "WIDTH_LABEL")
    assert not hasattr(palette, "WIDTH_AXIS_LETTER")


def test_the_insert_edge_is_derived_from_its_body():
    """So the two cannot drift into a clash when the body colour changes.

    Within one 8-bit step: the derived value is rounded to a hex byte so it
    can be written down as one beside the body it came from.
    """
    from teachinlathe.widgets.backplot.actors import palette

    for edge, body in zip(palette.INSERT_EDGE, palette.INSERT_BODY):
        assert edge == pytest.approx(body * 0.45, abs=1 / 255)


def test_the_insert_body_is_the_colour_it_was_asked_for():
    from teachinlathe.widgets.backplot.actors import palette

    assert palette.INSERT_BODY == pytest.approx(
        (0xE5 / 255, 0xA9 / 255, 0x3B / 255), abs=0.001)


# ── the font is measured in the framebuffer's pixels, like everything else ──

@pytest.mark.parametrize("ratio,tick,axis", [
    (1.0, "Sans 12px", "Sans Bold 14px"),
    (1.5, "Sans 18px", "Sans Bold 21px"),
    (2.0, "Sans 24px", "Sans Bold 28px"),
])
def test_the_font_is_asked_for_in_framebuffer_pixels(ratio, tick, axis,
                                                     monkeypatch):
    """The bug this is here for. A glyph is rasterised once and drawn one
    texel to one framebuffer pixel - the atlas is sampled GL_NEAREST, so it
    has to be. Ask Pango for 12 on a 2x panel and the glyph covers 12 device
    pixels, which is six logical ones: half size, with its one-pixel stems
    halved with it. Small and thin, which is exactly how it looked.
    """
    from teachinlathe.widgets.backplot.actors import text

    monkeypatch.setattr(base, "_DEVICE_PIXEL_RATIO", ratio)
    assert text.description_of("tick") == tick
    assert text.description_of("axis") == axis


def test_the_font_size_is_stated_in_logical_pixels():
    """As the profile editor's canvas states its - "10px sans-serif" - so the
    two are comparable without doing the scaling in your head."""
    from teachinlathe.widgets.backplot.actors import text

    for family, size in text.FONTS.values():
        assert isinstance(family, str)
        assert isinstance(size, int)


def test_line_weights_and_the_font_scale_together(monkeypatch):
    """They are both drawn into the same framebuffer, so a ratio that applied
    to one and not the other is what left the text alone among them."""
    from teachinlathe.widgets.backplot.actors import palette, text

    asked = []
    monkeypatch.setattr(base, "_set_line_width", asked.append)
    monkeypatch.setattr(base, "_DEVICE_PIXEL_RATIO", 2.0)

    base.line_width(palette.WIDTH_TICK)
    assert asked == [palette.WIDTH_TICK * 2.0]
    assert text.description_of("tick") == "Sans 24px"


def test_a_change_of_scaling_gets_a_new_atlas(monkeypatch):
    """Keyed by the description, which carries the size - so the old texture
    at the old size cannot be handed back."""
    from teachinlathe.widgets.backplot.actors import text

    monkeypatch.setattr(base, "_DEVICE_PIXEL_RATIO", 1.0)
    first = text.description_of("tick")
    monkeypatch.setattr(base, "_DEVICE_PIXEL_RATIO", 2.0)
    assert text.description_of("tick") != first


# ── the cutting moves carry a weight of their own ──────────────────────────

def test_the_trajectory_is_upstreams_part_with_a_width_on_it():
    """Subclassed, not rewritten: the trajectory's buffer is upstream's fast
    path and the only thing wanted from it is that it sets a line width."""
    from rs274 import glcanon_scene

    from teachinlathe.widgets.backplot.actors.cutting import CuttingMovesPart

    assert issubclass(CuttingMovesPart, glcanon_scene.ProgramPart)


def test_installing_it_keeps_the_same_program_resource():
    """GlCanonDraw binds its picker to scene.program.resource and the
    highlight is a second draw of those same buffers. A part with different
    ones leaves what is picked pointing at geometry nobody draws."""
    from rs274 import glcanon_scene

    from teachinlathe.widgets.backplot.actors import cutting

    scene = glcanon_scene.PreviewScene()
    before = scene.program
    resource = before.resource
    highlight_at = scene.index_of(scene.highlight)

    installed = cutting.install(scene)
    assert installed is scene.program
    assert scene.program is not before
    assert scene.program.resource is resource
    assert scene.highlight.resource is resource
    # Position preserved, and the highlight still immediately after.
    assert scene.index_of(scene.highlight) == highlight_at
    assert scene.index_of(scene.program) == highlight_at - 1


def test_the_cutting_part_sets_and_restores_its_width(monkeypatch):
    from teachinlathe.widgets.backplot.actors import cutting, palette

    asked = []
    monkeypatch.setattr(cutting, "line_width", asked.append)
    ctx = lathe_frame()
    ctx.program_alpha = False

    part = cutting.CuttingMovesPart()
    try:
        with part.scope(ctx):
            pass
    except Exception:                      # upstream's scope wants GL
        pass
    assert palette.WIDTH_FEED in asked


@pytest.mark.parametrize("name,expected", [
    ("WIDTH_CENTERLINE", 1.0),
    ("WIDTH_HATCH", 1.0),
    ("WIDTH_FEED", 1.5),
])
def test_the_weights_are_what_was_asked_for(name, expected):
    from teachinlathe.widgets.backplot.actors import palette

    assert getattr(palette, name) == expected


def test_the_centreline_is_not_heavier_than_the_toolpath():
    """As a centre line is on any drawing: it marks where something is, it is
    not the thing. It was the heaviest of the three, which was backwards.

    Compared on what is *drawn*, not on what is asked for - set_line_width
    floors a request at one pixel, so 0.9 and 1.0 are the same line and the
    requested numbers do not order the way the screen does.
    """
    from teachinlathe.widgets.backplot.actors import palette

    drawn = lambda width: max(1.0, width)        # noqa: E731
    assert drawn(palette.WIDTH_CENTERLINE) <= drawn(palette.WIDTH_TRAVERSE)
    assert drawn(palette.WIDTH_CENTERLINE) < drawn(palette.WIDTH_FEED)


def test_the_tick_font_matches_the_profile_editors_weight():
    """Regular, as that canvas draws it. It was bold for a while, and that was
    compensating for the alpha bug rather than for a design - bold has more
    fully-covered pixels, which were the only ones surviving. With the alpha
    sealed the compensation is weight twice over."""
    from teachinlathe.widgets.backplot.actors import text

    assert text.FONTS["tick"] == ("Sans", 12)
    assert text.FONTS["axis"] == ("Sans Bold", 14)
