"""The static layer: what is cached, and what drops it.

Upstream draws every part on every frame, because it must - the framebuffer
is cleared first, so there is no redrawing only what moved. This splits the
scene in two: what is still until the operator moves the view is drawn once
into its own framebuffer and copied back each frame; the trace, the tool and
the annotation over it are drawn as before.

The failure mode is the reason these tests exist. Nothing here raises when it
goes wrong: a split in the wrong place freezes the tool marker, and a
signature missing a field leaves the plot showing an old picture. Both look
like a working plot.
"""

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

from teachinlathe.widgets.backplot.lathe_backplot_item import (  # noqa: E402
    STATIC_MAX_AGE_S, LatheBackplotCanon)


# ── where the scene is cut ─────────────────────────────────────────────────

def scene_with_actors():
    """A real preview scene with our actors installed into it."""
    from teachinlathe.widgets.backplot.actors import scene as our_scene

    scene = glcanon_scene.PreviewScene()

    class Host:
        pass

    host = Host()
    host.scene = scene
    our_scene.install(host)
    return scene


def names_before_and_after(scene):
    split = scene.index_of(scene.backplot)
    before = [type(part).__name__ for part, _gate in scene.parts[:split]]
    after = [type(part).__name__ for part, _gate in scene.parts[split:]]
    return before, after


def test_everything_that_moves_is_after_the_split():
    """The trace grows and the tool marker moves every frame. Cached, the
    plot would freeze with the tool wherever it was when the layer was last
    drawn - and nothing would raise."""
    scene = scene_with_actors()
    _before, after = names_before_and_after(scene)

    assert "BackplotPart" in after, "the live trace would be frozen"
    assert any("Insert" in name or "Tool" in name for name in after), \
        "the tool marker would be frozen"


def test_the_tool_marker_is_the_last_thing_drawn():
    """It says where the tool is; nothing on the plot goes over it. Upstream
    leaves it mid-order with its own overlay after it, and this plot used to
    put the whole scale and the origin symbol on top of it as well."""
    scene = scene_with_actors()

    assert scene.index_of(scene.tool) == len(scene.parts) - 1
    assert scene.parts[-1][0] is scene.tool, \
        "scene.tool must be the part the scene draws - GlCanonDraw reaches " \
        "it by name"


def test_the_annotation_is_cached_with_the_still_picture():
    """It depends on the view and nothing else, so once it is no longer
    stacked on top of the tool it belongs in the layer, not in every frame."""
    scene = scene_with_actors()
    before, after = names_before_and_after(scene)

    for name in ("TicksActor", "AxisArrowsActor", "AxisLettersActor",
                 "OriginActor"):
        assert name in before, name
        assert name not in after


def test_the_annotation_still_draws_over_the_toolpath():
    """Under the trace and the tool now, but over the geometry it annotates -
    moving it must not put it beneath the program."""
    scene = scene_with_actors()
    order = [type(part).__name__ for part, _gate in scene.parts]

    assert order.index("CuttingMovesPart") < order.index("TicksActor")
    assert order.index("OriginActor") < order.index("BackplotPart")


def test_the_expensive_still_parts_are_before_the_split():
    """The point of the exercise: the toolpath and everything drawn under it
    change only when the view or the program does."""
    scene = scene_with_actors()
    before, _after = names_before_and_after(scene)

    for name in ("ProgramPart", "CuttingMovesPart", "GridActor", "StockActor",
                 "CenterlineActor", "RapidsActor"):
        assert name in before or name == "ProgramPart", name
    assert "CuttingMovesPart" in before
    assert "StockActor" in before


def test_the_highlight_stays_with_the_program():
    """It is a second draw of the program's own buffers and must follow them
    immediately - so it belongs on the same side of the split."""
    scene = scene_with_actors()
    before, _after = names_before_and_after(scene)
    assert "HighlightPart" in before


# ── the gate and scope of each part survive the split ──────────────────────

class RecordingPart:
    def __init__(self, name, log):
        self.name = name
        self.log = log

    def scope(self, ctx):
        from contextlib import contextmanager

        @contextmanager
        def entered():
            self.log.append(("enter", self.name))
            try:
                yield
            finally:
                self.log.append(("leave", self.name))

        return entered()

    def draw(self, ctx):
        self.log.append(("draw", self.name))


def test_drawing_a_slice_keeps_gates_and_scopes():
    """``_draw_parts`` is ``Scene.draw``'s loop over a slice of it. A part
    whose gate is false must not be entered at all - upstream is explicit that
    a hidden part is never scoped."""
    log = []
    parts = [(RecordingPart("shown", log), lambda ctx: True),
             (RecordingPart("hidden", log), lambda ctx: False)]

    LatheBackplotCanon._draw_parts(None, parts)
    assert log == [("enter", "shown"), ("draw", "shown"), ("leave", "shown")]


# ── what drops the cached layer ────────────────────────────────────────────

class StubStat:
    g5x_offset = [0.0] * 9
    g92_offset = [0.0] * 9
    tool_offset = [0.0] * 9
    rotation_xy = 0.0
    g5x_index = 1


class StubCtx:
    width, height = 800, 600
    highlight_line = None
    limits = ([0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
    grid_size = 0.0
    program_alpha = False
    show_program = show_rapids = show_extents = True
    show_limits = show_relative = show_workpiece = True

    def __init__(self):
        self.stat = StubStat()
        self.canon = type("Canon", (), {"program_geometry": object()})()


class StubCanon:
    """Only what ``_static_signature`` reads."""

    def __init__(self):
        self.stock = {}
        self.insert = {}
        self._mvp = np.eye(4)

    def _preview_mvp(self):
        return self._mvp


def signature(canon, ctx):
    return LatheBackplotCanon._static_signature(canon, ctx)


def test_an_unchanged_frame_keeps_the_layer():
    canon, ctx = StubCanon(), StubCtx()
    assert signature(canon, ctx) == signature(canon, ctx)


def test_moving_the_view_drops_the_layer():
    """Pan and zoom both come out as a different camera matrix, which is why
    the matrix is in the signature rather than a list of view flags."""
    canon, ctx = StubCanon(), StubCtx()
    before = signature(canon, ctx)
    canon._mvp = np.eye(4) * 2.0
    assert signature(canon, ctx) != before


def test_resizing_drops_the_layer():
    canon, ctx = StubCanon(), StubCtx()
    before = signature(canon, ctx)
    ctx.width = 1024
    assert signature(canon, ctx) != before


def test_a_new_program_drops_the_layer():
    canon, ctx = StubCanon(), StubCtx()
    before = signature(canon, ctx)
    ctx.canon.program_geometry = object()
    assert signature(canon, ctx) != before


def test_moving_the_highlighted_line_drops_the_layer():
    canon, ctx = StubCanon(), StubCtx()
    before = signature(canon, ctx)
    ctx.highlight_line = 42
    assert signature(canon, ctx) != before


@pytest.mark.parametrize("field,value", [
    ("g5x_offset", [1.0] + [0.0] * 8),
    ("g92_offset", [1.0] + [0.0] * 8),
    ("tool_offset", [1.0] + [0.0] * 8),
    ("rotation_xy", 30.0),
    ("g5x_index", 2),
])
def test_an_offset_change_drops_the_layer(field, value):
    """They move where everything in the layer is drawn."""
    canon, ctx = StubCanon(), StubCtx()
    before = signature(canon, ctx)
    setattr(ctx.stat, field, value)
    assert signature(canon, ctx) != before


@pytest.mark.parametrize("field,value", [
    ("show_program", False), ("show_rapids", False), ("show_extents", False),
    ("show_limits", False), ("show_relative", False), ("show_workpiece", False),
    ("grid_size", 5.0), ("program_alpha", True),
    ("limits", ([0.0, 0.0, 0.0], [2.0, 2.0, 2.0])),
])
def test_a_flag_change_drops_the_layer(field, value):
    canon, ctx = StubCanon(), StubCtx()
    before = signature(canon, ctx)
    setattr(ctx, field, value)
    assert signature(canon, ctx) != before


def test_new_stock_dimensions_drop_the_layer():
    """Compared by value, not identity - the dict is rebuilt on every load and
    may well be equal."""
    canon, ctx = StubCanon(), StubCtx()
    before = signature(canon, ctx)
    canon.stock = {"stock_length": 60.0, "external_diameter": 40.0}
    assert signature(canon, ctx) != before

    canon2 = StubCanon()
    canon2.stock = dict(canon.stock)
    assert signature(canon2, ctx) == signature(canon, ctx)


def test_a_new_insert_choice_drops_the_layer():
    canon, ctx = StubCanon(), StubCtx()
    before = signature(canon, ctx)
    canon.insert = {"family": "WNMG"}
    assert signature(canon, ctx) != before


def test_invalidate_static_drops_the_layer():
    canon = StubCanon()
    canon._static_key = "something"
    LatheBackplotCanon.invalidate_static(canon)
    assert canon._static_key is None


def test_the_layer_is_rebuilt_periodically_whatever_the_signature_says():
    """The net under the signature. Anything not named in it would otherwise
    leave the plot frozen on an old picture, looking entirely normal."""
    assert 0 < STATIC_MAX_AGE_S <= 5.0


# ── the layer's own alpha, and the frame baseline ──────────────────────────

def source_of(method):
    import inspect

    return inspect.getsource(method)


def test_the_layer_is_cleared_with_alpha_writes_enabled():
    """The frame masks alpha for its whole length, and this buffer is not the
    one that was sealed. Cleared under that mask it keeps the nothing it was
    made with, and the blit carries that into the frame: the plot composites
    premultiplied against the page and vanishes - every frame drawn, no error
    anywhere. That is exactly how it shipped."""
    body = source_of(LatheBackplotCanon._render_static)
    clear = body.index("glClear(")
    enabled = body.index("_set_alpha_writes(True)")
    disabled = body.index("_set_alpha_writes(False)")
    assert enabled < clear < disabled, \
        "the clear must run with alpha writes on, and only the clear"


def test_the_live_pass_starts_from_the_frame_baseline():
    """On a cached frame nothing else sets it, and upstream guarantees every
    part is entered from the baseline."""
    body = source_of(LatheBackplotCanon.redraw)
    assert "apply_baseline" in body


def test_the_layer_can_be_turned_off_without_editing_anything():
    """Its failures are silent by nature - an old picture or none - so there
    has to be a way back to a working plot that is not an edit and a restart.
    """
    from teachinlathe.widgets.backplot import lathe_backplot_item as module

    assert isinstance(module.STATIC_LAYER, bool)
    body = source_of(LatheBackplotCanon.redraw)
    assert "not STATIC_LAYER" in body
    assert "scene.draw(ctx)" in body, "no path back to drawing every part"
