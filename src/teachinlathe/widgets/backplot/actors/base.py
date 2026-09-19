"""``Actor``: what every actor on the backplot has in common.

An actor owns one concern and draws it. What it does *not* do is decide where
it appears on screen - panning and zooming reach it as the model-view stack
the frame arrives with, so an actor draws in model space and is moved and
scaled with everything else.

Subclasses override as much or as little as they need:

    draw(ctx)            the one thing every actor must implement
    place(ctx)           where it draws; default is the program origin
    enter_gl_state(ctx)  GL state it needs; default is width + depth mode
    leave_gl_state(ctx)  undoing that; default restores what it changed

and the class attributes below tune the defaults without overriding anything.
Helpers for the two ways an actor puts geometry on screen - ``stroke`` and
``fill`` - are here as well, so no actor packs its own vertex arrays.
"""

import logging
from contextlib import contextmanager

from teachinlathe.widgets.backplot.actors import palette

LOG = logging.getLogger(__name__)

try:
    from OpenGL.GL import (GL_ALWAYS, GL_FALSE, GL_LESS, GL_MULTISAMPLE,
                           GL_TRIANGLES, GL_TRUE, glBindVertexArray,
                           glDepthFunc, glDepthMask, glDisable, glEnable,
                           glUseProgram)
    from rs274 import glcanon_scene
    from rs274.glcanon_gl import set_line_width as _set_line_width
    _PART = glcanon_scene.Part
    #: Which plane the camera looks down, as the frame reports it. Re-exported
    #: so an actor never reaches into glcanon_scene, and so the names still
    #: exist where it is not installed.
    VX, VY, VZ = glcanon_scene.VX, glcanon_scene.VY, glcanon_scene.VZ
    LIB_GOOD = True
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot actors: LinuxCNC preview modules unavailable: %s", exc)
    _PART = object
    GL_ALWAYS = GL_LESS = GL_TRIANGLES = GL_TRUE = GL_FALSE = None
    GL_MULTISAMPLE = None

    def _set_line_width(_width):
        pass

    VX, VY, VZ = 0, 1, 2
    LIB_GOOD = False


#: How many framebuffer pixels there are to one of the pixels the widths in
#: ``palette`` are written in.
#:
#: The framebuffer is sized in device pixels, so on a scaled display a line
#: asked for at 1.0 covers a fraction of the pixel the designer drew on the
#: QML Canvas - which measures in logical ones. The renderer knows the ratio,
#: because it is handed both sizes, and sets it here.
_DEVICE_PIXEL_RATIO = 1.0


def set_device_pixel_ratio(ratio):
    """Told to the actors by the renderer, once per framebuffer.

    Floored at 1.0. The ratio is derived from two sizes the renderer is
    handed, and a value below one would mean the framebuffer is smaller than
    the item - which thins every line on the plot for a reason that is never
    a real display. Logged when it changes, because it is otherwise invisible
    and it is the first thing to check when the weights look wrong.
    """
    global _DEVICE_PIXEL_RATIO
    try:
        ratio = float(ratio)
    except (TypeError, ValueError):
        return
    if ratio <= 0:
        return
    ratio = max(1.0, ratio)
    if ratio != _DEVICE_PIXEL_RATIO:
        LOG.info("backplot: line weights scaled by a pixel ratio of %.2f",
                 ratio)
    _DEVICE_PIXEL_RATIO = ratio


def device_pixel_ratio():
    return _DEVICE_PIXEL_RATIO


def multisample(enabled):
    """Turn multisampled rasterising on or off for what is drawn next.

    The frame's baseline is off. An actor whose geometry is curved or diagonal
    turns it on for its own draw through ``Actor.MULTISAMPLE``; this is here
    for the one that has to do it partway through - the ticks, whose marks are
    axis-aligned and want it off while their labels are glyphs and want it on.
    """
    if GL_MULTISAMPLE is None:
        return
    if enabled:
        glEnable(GL_MULTISAMPLE)
    else:
        glDisable(GL_MULTISAMPLE)


def line_width(pixels):
    """Ask for a line ``pixels`` wide, as the QML Canvas measured them.

    **The width is in screen pixels and does not follow the zoom.** It cannot:
    it never reaches the model-view. Where the driver grants the width it goes
    to ``glLineWidth``, and where it does not, upstream expands the line into
    a quad in the shader - and that expansion is computed in pixels from the
    viewport, not from the projection. Zoom in and a line covers more
    millimetres of the part at the same number of pixels, which is what a
    drawn line should do.

    Three things do happen to the request on the way through:

    **Below 1.0 there is nothing to ask for.** ``set_line_width`` floors it at
    one pixel and GL has no thinner line - the Canvas got its hairlines by
    antialiasing, not by drawing narrower. So the 0.5 the grid was drawn at
    and the 1.0 the ticks were drawn at come out the same, and the only way to
    keep them apart is to make the heavier ones heavier.

    **Above 1.0 it is honoured even where the driver refuses.** A
    forward-compatible core profile - Qt's - caps ``glLineWidth`` at 1.0;
    upstream notices and takes the quad path. That path is deliberately not
    taken for the program's own trajectory, which is why the toolpath draws at
    one pixel whatever ``palette.WIDTH_FEED`` says.

    **It is scaled**, by the display's pixel ratio and by
    ``palette.WIDTH_SCALE``. The ratio is never taken below 1: a framebuffer
    smaller than the item it fills is not something to thin lines for, it is a
    reading that has gone wrong.
    """
    _set_line_width(pixels * palette.WIDTH_SCALE * _DEVICE_PIXEL_RATIO)


class Actor(_PART):
    """One drawable concern on the backplot.

    Every actor takes the host - the backplot item - whether or not it wants
    it, so ``scene.install`` can build them all the same way. Most ignore it;
    the stock and the insert read it for what only the host knows.
    """

    def __init__(self, host=None):
        self._host = host

    #: Line width in pixels while this actor draws.
    #:
    #: **3.0 is the ceiling**, whatever a subclass sets: glcanon_gl's
    #: set_line_width() probes the driver at 3.0 and clamps to what that
    #: granted, so 5.0 and 3.0 draw identically. Filled geometry is unaffected.
    LINE_WIDTH = 3.0

    #: Depth comparison while this actor draws. ``GL_ALWAYS`` puts it over
    #: whatever is already there - which annotation wants and geometry does
    #: not, so a subclass drawing real shape sets ``GL_LESS``.
    #:
    #: Being late in the draw order is not enough on its own: a fragment is
    #: still rejected where the toolpath has written a nearer depth. Order and
    #: depth mode are two halves of the same decision.
    DEPTH_MODE = GL_ALWAYS

    #: Whether ``place()`` moves onto the program origin. False leaves the
    #: actor in machine coordinates.
    FOLLOW_PROGRAM_ORIGIN = True

    #: Whether this actor writes depth as it draws.
    #:
    #: False for anything drawn *under* the toolpath - the grid, the
    #: centreline, the stock. They lie in the same plane the toolpath does, so
    #: with depth writes on, whichever drew first would reject the other
    #: through a GL_LESS test that never fails by more than rounding. Upstream
    #: guards its own grid the same way, in ``GridPart.scope``.
    DEPTH_WRITE = True

    #: Whether this actor is drawn multisampled.
    #:
    #: The frame's baseline is off - see
    #: ``LatheBackplotCanon._set_multisample_baseline``. That is right for the
    #: grid, the ticks and the centreline, which are axis-aligned straight
    #: lines: they land on whole pixels and antialiasing only spreads them
    #: over two at half strength, which is what made them look thin and made
    #: their weight follow the zoom.
    #:
    #: It is wrong for anything curved or diagonal. A glyph stroke and a
    #: 16-pixel circle have no whole pixels to land on, so without
    #: multisampling they staircase - the numbers that "do not look sharp"
    #: and the origin symbol that looks like it is missing pixels. Those set
    #: this True and pay for it over their own draw alone.
    MULTISAMPLE = False

    # ── the frame ───────────────────────────────────────────────────────────

    @contextmanager
    def scope(self, ctx):
        """Everything this actor needs entered, and left on the way out -
        including when an exception unwinds through it."""
        with ctx.mv.push():
            self.place(ctx)
            self.enter_gl_state(ctx)
            try:
                yield
            finally:
                self.leave_gl_state(ctx)

    def place(self, ctx):
        """Move the model-view stack to where this actor draws.

        The default is the program origin - after the g5x offset, the XY
        rotation and the g92 offset - which is the frame upstream's axes are
        drawn in. The body is upstream's, from ``RelativeCoordPart.draw``.
        """
        if not self.FOLLOW_PROGRAM_ORIGIN or not ctx.show_relative:
            return
        s = ctx.stat
        if not (s.g5x_offset[0] or s.g5x_offset[1] or s.g5x_offset[2] or
                s.g92_offset[0] or s.g92_offset[1] or s.g92_offset[2] or
                s.rotation_xy):
            return
        ctx.mv.translate(*ctx.to_internal_units(s.g5x_offset)[:3])
        ctx.mv.rotate(s.rotation_xy, 0, 0, 1)
        ctx.mv.translate(*ctx.to_internal_units(s.g92_offset)[:3])

    def enter_gl_state(self, ctx):
        """GL state this actor draws under."""
        glDepthFunc(self.DEPTH_MODE)
        if not self.DEPTH_WRITE:
            glDepthMask(GL_FALSE)
        if self.MULTISAMPLE:
            multisample(True)
        line_width(self.LINE_WIDTH)

    def leave_gl_state(self, ctx):
        """Put back what ``enter_gl_state`` changed, and release the shader
        and vertex array so the next actor starts from the scene's baseline."""
        line_width(1.0)
        if self.MULTISAMPLE:
            multisample(False)
        if not self.DEPTH_WRITE:
            glDepthMask(GL_TRUE)
        glDepthFunc(GL_LESS)
        glUseProgram(0)
        glBindVertexArray(0)

    # ── drawing ─────────────────────────────────────────────────────────────

    def draw(self, ctx):
        raise NotImplementedError

    @staticmethod
    def stroke(ctx, points, color, mvp=None, alpha=1.0):
        """Draw ``points`` as GL_LINES endpoint pairs.

        ``alpha`` composites against what is already there - the scene's
        baseline blend is source-alpha, and geometry at alpha 1 is unaffected
        by it either way. It is how a line lighter than one pixel is drawn at
        all: GL floors a line width at one, so a hairline can only be had by
        making a full-width line partly transparent.
        """
        if not points:
            return
        ctx.prim.draw_lines(ctx, points, color, alpha,
                            ctx.mv.mvp() if mvp is None else mvp)

    @staticmethod
    def fill(ctx, points, color, mvp=None):
        """Draw ``points`` as triangles.

        Packed in the same (N,8) position-and-colour layout the line path
        uses; draw_flat_array puts it through the flat vertex-colour shader.
        """
        if not points:
            return
        ctx.renderer.draw_flat_array(
            ctx.mv.mvp() if mvp is None else mvp,
            ctx.prim.lines_to_array(points, color),
            mode=GL_TRIANGLES)


class InertActor(Actor):
    """Draws nothing, and touches no state doing it.

    Used to empty an upstream part rather than remove it: the scene's order is
    load-bearing - upstream says so explicitly - and a named part is reached
    directly by its parent, so leaving an inert one in place keeps both true.
    """

    @contextmanager
    def scope(self, ctx):
        yield

    def draw(self, ctx):
        pass
