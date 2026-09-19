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

LOG = logging.getLogger(__name__)

try:
    from OpenGL.GL import (GL_ALWAYS, GL_LESS, GL_TRIANGLES, glBindVertexArray,
                           glDepthFunc, glUseProgram)
    from rs274 import glcanon_scene
    from rs274.glcanon_gl import set_line_width
    _PART = glcanon_scene.Part
    #: Which plane the camera looks down, as the frame reports it. Re-exported
    #: so an actor never reaches into glcanon_scene, and so the names still
    #: exist where it is not installed.
    VX, VY, VZ = glcanon_scene.VX, glcanon_scene.VY, glcanon_scene.VZ
    LIB_GOOD = True
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot actors: LinuxCNC preview modules unavailable: %s", exc)
    _PART = object
    GL_ALWAYS = GL_LESS = GL_TRIANGLES = None
    VX, VY, VZ = 0, 1, 2
    LIB_GOOD = False


class Actor(_PART):
    """One drawable concern on the backplot."""

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
        set_line_width(self.LINE_WIDTH)

    def leave_gl_state(self, ctx):
        """Put back what ``enter_gl_state`` changed, and release the shader
        and vertex array so the next actor starts from the scene's baseline."""
        set_line_width(1.0)
        glDepthFunc(GL_LESS)
        glUseProgram(0)
        glBindVertexArray(0)

    # ── drawing ─────────────────────────────────────────────────────────────

    def draw(self, ctx):
        raise NotImplementedError

    @staticmethod
    def stroke(ctx, points, color, mvp=None):
        """Draw ``points`` as GL_LINES endpoint pairs."""
        if not points:
            return
        ctx.prim.draw_lines(ctx, points, color,
                            mvp=ctx.mv.mvp() if mvp is None else mvp)

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
