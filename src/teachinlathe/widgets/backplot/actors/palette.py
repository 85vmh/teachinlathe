"""The backplot's colours and line weights, in one place.

Ported from the QML 2D preview on ``native_2d_rendering`` - ``ToolpathCanvas``,
``ToolpathStockActor`` and ``toolpath_model.TOOLPATH_STYLES`` - so the GL
backplot and that renderer read as the same drawing. The hex each value came
from is kept beside it: these are somebody's chosen colours, not derived ones,
and the hex is what a designer will compare against.

Colours are rgb triples in 0..1, which is what ``ctx.colors`` and the actors'
``stroke``/``fill`` take. Widths are in pixels, as ``set_line_width`` wants;
see ``Actor.LINE_WIDTH`` for the ceiling the driver imposes on them.
"""

# ── colours ────────────────────────────────────────────────────────────────

#: The ground the whole plot sits on.
BACK = (0.961, 0.961, 0.961)          # #f5f5f5

#: Cutting moves, and the arcs among them.
FEED = (0.200, 0.200, 0.200)          # #333333

#: Rapids. Dashed in the QML renderer; see DASH_TRAVERSE for why they are not
#: dashed here.
TRAVERSE = (0.467, 0.467, 0.467)      # #777777

#: The grid behind everything.
GRID = (0.878, 0.878, 0.878)          # #e0e0e0

#: ...drawn a little transparent, because GL has no line thinner than a pixel
#: and the profile editor's grid is drawn at half of one.
#:
#: What that canvas actually puts on screen was measured rather than reasoned
#: about, by rendering it offscreen and reading the pixels back: over its
#: #f5f5f5 ground, a 0.5px #e0e0e0 line comes out #efefef and a 1.0px one
#: #eaeaea. So its grid is at about 0.3 coverage - far fainter than it looks
#: like it should be, and fainter than a full-strength line here by a long
#: way.
#:
#: 0.3 would reproduce it exactly. This is heavier than that on purpose: at
#: 0.5 the grid disappeared on the machine's own panel, which is the display
#: that matters and not the one the measurement was taken on. Between "too
#: strong" and "not there" this errs towards being seen; it is one value to
#: change if it is still wrong.
GRID_ALPHA = 0.75

#: The two axes, their ticks and their labels.
#:
#: **Z is green and X is blue**, which is the QML renderer's pairing and the
#: reverse of what this backplot used before. Both are named here rather than
#: through ``ctx.colors['axis_x']`` alone so the swap is visible in one place
#: if it ever has to go back.
AXIS_Z = (0.180, 0.490, 0.196)        # #2E7D32
AXIS_X = (0.082, 0.396, 0.753)        # #1565C0

#: The dash-dot cross through the program origin - the spindle centreline and
#: the face datum.
CENTERLINE = (0.600, 0.600, 0.600)    # #999999

#: ...composited at this much, so the cross reads as a datum sitting under the
#: drawing rather than as geometry in it.
#:
#: The colour tuples here are rgb; a fourth element in one is read by nothing
#: and would be ignored. Transparency is a separate argument to
#: ``Actor.stroke``, which is what this is for.
CENTERLINE_ALPHA = 0.7

#: The origin symbol.
ORIGIN = (0.133, 0.133, 0.133)        # #222222

#: The stock outline, the bore line inside it, and the hatching that fills it.
STOCK = (0.612, 0.639, 0.686)         # #9ca3af
STOCK_BORE = (0.682, 0.706, 0.741)    # #aeb4bd
HATCH = (0.835, 0.851, 0.875)         # #d5d9df

#: The insert at the tool tip: the gold of a coated carbide, which is what
#: the operator is looking at in the holder.
#:
#: Not ``TurningInsertBase.qml``'s slate body. That palette is drawn for the
#: dark demo behind it, and on this plot's near-white ground a dark grey
#: insert reads as a hole in the drawing rather than as a tool.
INSERT_BODY = (0.898, 0.663, 0.231)   # #E5A93B

#: The outline round it, and the hole and countersink inside it. Derived from
#: the body rather than chosen - it is the same colour at 45%, so changing the
#: body carries the edge with it and the two cannot drift into a clash.
INSERT_EDGE = (0.404, 0.298, 0.106)   # #674C1B, = INSERT_BODY * 0.45


# ── line weights, in pixels ────────────────────────────────────────────────
#
# In the pixels the QML Canvas measured in - logical ones. ``base.line_width``
# scales them to the framebuffer and is where the two limits that apply to
# them are written down. The short of it:
#
#   * anything under 1.0 comes out at 1.0, because GL has no thinner line.
#     The values the Canvas used are kept below as the comment on each, so the
#     weights it distinguished are still legible even where GL cannot draw
#     them apart;
#   * the program's own trajectory ignores these entirely and draws at one
#     pixel - see WIDTH_FEED.

#: One knob over every weight below, for a panel where they come out too
#: light or too heavy. It is a multiplier on the pixel values, applied in
#: ``base.line_width``, so the relative weights are kept and only the overall
#: hand changes. 1.0 is what the QML Canvas was drawn at, allowing for the
#: floor below.
WIDTH_SCALE = 1.0

#: The cutting moves - the line and arc feeds.
#:
#: Honoured only where the driver grants a wide line natively: they are drawn
#: from upstream's baked buffer, which is explicitly never quad-expanded. One
#: pixel on a strict core profile, this width where wide lines are allowed -
#: which the line-weight report at start-up says. ``actors/cutting.py`` is
#: what asks for it.
WIDTH_FEED = 1.5

#: The rapids. This one *is* honoured: ``RapidsActor`` draws them, not the
#: baked buffer.
WIDTH_TRAVERSE = 0.9

#: The two lightest things on the plot, and the only ones left at the floor:
#: the grid behind everything, and the hatch, which is a texture rather than a
#: line and turns into a solid block as soon as it is heavier.
WIDTH_GRID = 1.0
WIDTH_HATCH = 1.0

#: The scale round the edge, and the stock outline.
WIDTH_TICK = 1.5
WIDTH_STOCK = 1.5

#: The datums. Thinnest of the drawn lines, as a centre line is on any
#: drawing: it marks where something is, it is not the thing.
WIDTH_CENTERLINE = 1.0

#: The annotation the operator reads off the plot. Heaviest, so the hierarchy
#: still runs three deep after the floor flattened its bottom step.
#:
#: Text is not here: it is drawn from the glyph atlas now, so its weight is
#: the font's - see ``text.FONTS`` - not a line width.
WIDTH_ARROW = 2.5
WIDTH_ORIGIN = 2.5

#: The insert's outline, and the hole and countersink inside it.
#:
#: Hairlines, unlike the rest of the annotation. The insert is the one thing
#: on the plot drawn at its true size, so its edge is a real edge and reads as
#: heavy the moment it is drawn as a mark. The hole matches rather than
#: sitting a step lighter as it did on the Canvas: below one pixel there is
#: nowhere lighter to go, and a hole heavier than the outline round it is the
#: only other way that ends.
WIDTH_INSERT_EDGE = 1.0
WIDTH_INSERT_HOLE = 1.0


# ── dash patterns, in pixels ───────────────────────────────────────────────
#
# On/off runs, as the Canvas 2D context takes them. Nothing in the GL renderer
# dashes - upstream says so in ``ProgramPart``: "there is no attribute or
# uniform left to do it with" - so a pattern here is cut into real segments by
# ``geometry.dashed()`` before it is drawn, which only an actor that builds its
# own vertices can do.

#: The centreline cross: long, gap, dot, gap.
DASH_CENTERLINE = (8.0, 5.0, 2.0, 5.0)

#: The rapids. Upstream's baked buffer has no dash path, so the traverse moves
#: are hidden from it and drawn by ``RapidsActor`` instead - which builds the
#: dashes itself, and so can honour this.
DASH_TRAVERSE = (6.0, 3.0)
