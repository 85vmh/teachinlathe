"""Real text, from the renderer's own glyph atlas.

Everything on this plot used to be drawn with ``draw_hershey`` - the Hershey
vector fonts, digitised for pen plotters in 1967. They are *skeletons*, not
letterforms: a '0' is sixteen straight segments chained round a curve, a '8'
twenty-eight. At the size a tick label is drawn, each segment is about two
pixels long, there is no hinting to snap a stem onto the pixel grid, and the
only antialiasing available is MSAA's five coverage levels against a font
rasteriser's 256. Hence text that could not be made to look sharp by adjusting
anything.

``glcanon_gl.GlyphAtlas`` is the alternative, and the renderer already has it -
it is what the DRO overlay draws with. Pango rasterises each glyph once into
one ``GL_R8`` texture; drawing a string is one textured quad per character.

It is also *cheaper* than what it replaces. Twelve typical labels are 330 line
segments and 5280 floats as Hershey, against 30 quads and 720 floats here, and
none of the per-label Python that built those polylines and pushed a matrix
for each one. Strings are batched by font and colour, so a screenful of labels
is two draw calls rather than eighty.

**Screen space, origin bottom-left**, which is what the atlas shader wants -
see ``TEXT_VERTEX_SHADER``. Model-space callers project first; ``to_screen``
is here for that.
"""

import logging
import os

LOG = logging.getLogger(__name__)

#: Set TEACHINLATHE_TEXT=1 to have each atlas dump a glyph as it was
#: rasterised, to the usual log.
#:
#: This is here because the one thing that cannot be checked from anywhere but
#: the machine itself is what its font stack produces. The atlas is drawn by
#: Pango through Cairo with the system's own font options - which font "Sans"
#: resolves to, what hinting and antialiasing are configured - and a thin,
#: sparse glyph there comes out thin and sparse on the plot however correct
#: everything after it is.
GLYPH_DEBUG = bool(os.environ.get("TEACHINLATHE_TEXT"))

try:
    import numpy as np
    from rs274 import glcanon_gl
    from teachinlathe.widgets.backplot.actors.base import device_pixel_ratio
    LIB_GOOD = True
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot text: preview modules unavailable: %s", exc)

    def device_pixel_ratio():
        return 1.0

    LIB_GOOD = False

#: The fonts, by the name callers ask for them by: ``(family, size)``, the
#: size in **logical** pixels - the ones a window is measured in, and the ones
#: the profile editor's canvas draws with.
#:
#: The families and weights are that canvas's, so the two drawings read as one
#: screen: its ``TicksActor`` uses ``"10px sans-serif"`` and its ``AxesActor``
#: ``"bold 11px sans-serif"``. The sizes are a couple larger because this plot
#: is read from further away.
#: The tick numbers regular and the axis labels bold, which is the profile
#: editor's own pairing - its ``TicksActor`` uses ``"10px sans-serif"`` and
#: its ``AxesActor`` ``"bold 11px sans-serif"``.
#:
#: The tick font was bold for a while, and it is worth saying why it is not
#: any more. It was compensating for a bug rather than for a design: the
#: framebuffer's alpha channel was left at each pixel's coverage and Qt
#: composites it premultiplied, so a glyph's antialiased edge was being blown
#: out to the page colour and only the fully covered core of each stroke
#: survived. Bold has more of that core, so bold looked better. With the alpha
#: sealed - see ``LatheBackplotCanon._seal_alpha`` - the edges are there
#: again, and the extra weight is weight twice over.
FONTS = {
    "tick": ("Sans", 12),
    "axis": ("Sans Bold", 14),
}


def description_of(font):
    """A font as Pango's description string, sized for the framebuffer.

    **This is where the text was going wrong, and it is worth writing down.**

    A glyph is rasterised once, at a fixed size, and then drawn one texel to
    one *framebuffer* pixel - it has to be, because the atlas is sampled
    GL_NEAREST. But the framebuffer is in device pixels, and on a scaled
    display there are more of those than there are of the logical pixels a
    size like "12px" means. Ask Pango for 12 and the glyph covers 12 device
    pixels, which on a 2x panel is six logical ones: half the size it should
    be, with its one-pixel stems halved too. Small and thin, exactly.

    Line weights already went through this - ``base.line_width`` multiplies by
    the same ratio - and the font was the one thing left measuring in the
    wrong pixels. The profile editor's canvas never had the problem because Qt
    scales a Canvas for the display itself.

    The ``px`` suffix is what makes the size absolute. Without it "Sans 12" is
    twelve *points*, a third bigger again, and it would then also move with
    the system's DPI.
    """
    family, logical = FONTS.get(font) or FONTS["tick"]
    return "%s %dpx" % (family, max(1, round(logical * device_pixel_ratio())))

#: Glyphs rasterised into each atlas: ASCII, which covers every digit, sign
#: and axis letter this plot draws.
FIRST_GLYPH = 0
GLYPH_COUNT = 128

#: Alignment fractions. The pen is moved back by this much of the string's
#: own width or height, so 0 anchors the left/bottom edge, 0.5 the middle and
#: 1.0 the right/top.
LEFT = BOTTOM = 0.0
CENTRE = 0.5
RIGHT = TOP = 1.0

#: Built atlases, by font description. Keyed by description rather than by
#: name so two names sharing a font share its texture.
_ATLASES = {}

#: Set once when an atlas cannot be built, so the log carries the reason
#: rather than one line per frame.
_REPORTED = set()


def reset():
    """Drop every atlas, for a GL context that has gone away.

    The textures belong to the context that built them; keeping the handles
    across one would draw from whatever now lives at those names.
    """
    _ATLASES.clear()
    _REPORTED.clear()


def atlas(font="tick"):
    """The atlas for a font name, built on first use, or ``None``.

    Built here rather than up front because ``build_atlas`` ends in
    ``glTexImage2D``: it needs a current context, and the only place this
    package is guaranteed one is inside a draw.
    """
    if not LIB_GOOD:
        return None
    # Keyed by the description, so a font shared by two names shares its
    # texture - and so a change of display scaling asks for a new size and
    # gets a new atlas rather than the old one at the old size.
    description = description_of(font)
    if description in _ATLASES:
        return _ATLASES[description]
    try:
        built = glcanon_gl.build_atlas(description, FIRST_GLYPH, GLYPH_COUNT)
    except Exception as exc:  # pragma: no cover - Pango/GL at runtime
        return _disable(description, "could not build the atlas for", exc)
    _ATLASES[description] = built
    _report(description, built)
    return built


def _report(description, built):
    """What this machine's font stack actually produced, once per atlas."""
    glyph = built.glyphs.get(ord("0"), {})
    LOG.info("backplot text: %r at a pixel ratio of %.2f -> %s, digit "
             "%gx%g advance %g, line %d descent %d",
             description, device_pixel_ratio(), _resolved(description),
             glyph.get("w", 0), glyph.get("h", 0), glyph.get("advance", 0),
             built.line_space, built.descent)
    if GLYPH_DEBUG:
        for line in _glyph_art(description, "0"):
            LOG.info("backplot text:   %s", line)


def _resolved(description):
    """The font ``description`` actually loads, as the font map reports it."""
    try:
        import gi
        gi.require_version("Pango", "1.0")
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import Pango, PangoCairo

        font_map = PangoCairo.font_map_get_default()
        font = font_map.load_font(font_map.create_context(),
                                  Pango.FontDescription(description))
        return font.describe().to_string()
    except Exception as exc:  # pragma: no cover - Pango at runtime
        return "unresolved (%s)" % exc


def _glyph_art(description, character):
    """One glyph as text, rasterised exactly as ``build_atlas`` does it.

    A solid, connected shape here means the atlas is good and any thinness is
    further down; a sparse one means the font stack is where to look.
    """
    try:
        import cairo
        import gi
        gi.require_version("Pango", "1.0")
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import Pango, PangoCairo

        surface = cairo.ImageSurface(cairo.FORMAT_A8, 256, 256)
        context = cairo.Context(surface)
        pango_context = PangoCairo.create_context(context)
        layout = PangoCairo.create_layout(context)
        layout.set_font_description(Pango.FontDescription(description))
        layout.set_text(character, -1)
        w, h = layout.get_size()
        w, h = int(w / Pango.SCALE), int(h / Pango.SCALE)

        context.save()
        context.set_operator(cairo.OPERATOR_CLEAR)
        context.paint()
        context.restore()
        context.save()
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(1, 1, 1, 1)
        context.move_to(0, 0)
        PangoCairo.update_context(context, pango_context)
        PangoCairo.show_layout(context, layout)
        context.restore()
        surface.flush()

        stride = surface.get_stride()
        data = bytes(surface.get_data())
        ramp = " .:-=+*#%@"
        rows = ["|%s|" % "".join(
            ramp[min(9, data[row * stride + column] * 10 // 256)]
            for column in range(w)) for row in range(h)]
        covered = sum(1 for row in range(h) for column in range(w)
                      if data[row * stride + column] > 128)
        return rows + ["%dx%d, %d texels over half coverage" % (w, h, covered)]
    except Exception as exc:  # pragma: no cover - Pango at runtime
        return ["could not rasterise: %s" % exc]


def _disable(description, what, exc):
    """Turn a font off for this context, and say why - once."""
    _ATLASES[description] = None
    if description not in _REPORTED:
        _REPORTED.add(description)
        LOG.error("backplot text: %s %r: %s", what, description, exc)
    return None


def width(text, font="tick"):
    """How wide ``text`` is in pixels, in this font."""
    built = atlas(font)
    if built is None or not text:
        return 0.0
    total = 0.0
    for character in text:
        glyph = built.glyphs.get(ord(character))
        total += built.char_width if glyph is None else glyph["advance"]
    return total


def line_height(font="tick"):
    """The font's line height in pixels."""
    built = atlas(font)
    return 0.0 if built is None else float(built.line_space)


def draw(ctx, strings, color, font="tick"):
    """Draw ``strings`` - ``(text, x, y, align_x, align_y)`` in screen pixels.

    Batched: every string goes into one vertex array and one draw call, which
    is the whole reason this takes a list rather than a string. Colour is per
    call, because the shader carries it as a uniform.

    **Nothing here is allowed to raise.** It runs inside a frame, and a frame
    that raises renders nothing at all - which is how a missing attribute on
    the canon once turned into an empty plot and a log full of the same line.
    The atlas builds its shader lazily on the first draw, so the first draw is
    where a broken one shows up; it is turned off and reported once, and the
    plot keeps its geometry.
    """
    built = atlas(font)
    if built is None or not strings:
        return

    verts = []
    for string, x, y, align_x, align_y in strings:
        if not string:
            continue
        # The pen is the left end of the baseline. string_quads puts a glyph
        # at [y - descent, y - descent + h], so the line's box starts a
        # descent below the origin - which is what the vertical alignment has
        # to be measured against.
        #
        # **Rounded to whole pixels, and that is not tidiness.** The atlas is
        # sampled GL_NEAREST - build_atlas sets both filters - so a glyph quad
        # only reproduces what Pango drew if its texels land one to one on
        # screen pixels. Off the grid by a fraction, every output pixel takes
        # whichever texel it happens to be nearest: one-pixel stems drop out
        # or double, and the text comes out thin, broken and pale. Upstream's
        # own caller never hit it because the DRO overlay places strings at
        # integer coordinates and every metric in the atlas is an int; ours
        # are projected model positions and a half-width for centring, so they
        # land wherever they land unless they are put back on the grid here.
        pen_x = round(x - width(string, font) * align_x)
        pen_y = round(y - built.line_space * align_y + built.descent)
        verts.extend(built.string_quads(string, pen_x, pen_y))
    if not verts:
        return

    try:
        built._draw_array(np.asarray(verts, dtype=np.float32),
                          _rgba(color), True, (ctx.width, ctx.height))
    except Exception as exc:  # pragma: no cover - GL at runtime
        _disable(description_of(font), "could not draw with", exc)


def to_screen(mvp, point, viewport):
    """A model-space point as screen pixels, origin bottom-left.

    ``None`` behind the eye, which an orthographic lathe view never produces
    but a caller should not have to assume.
    """
    if not LIB_GOOD:
        return None
    clip = mvp @ np.array([point[0], point[1], point[2], 1.0])
    w = clip[3]
    if abs(w) < 1e-9:
        return None
    return ((clip[0] / w + 1.0) / 2.0 * viewport[0],
            (clip[1] / w + 1.0) / 2.0 * viewport[1])


def _rgba(color):
    """An rgb triple as the rgba the atlas shader takes."""
    if len(color) >= 4:
        return tuple(color[:4])
    return (color[0], color[1], color[2], 1.0)
