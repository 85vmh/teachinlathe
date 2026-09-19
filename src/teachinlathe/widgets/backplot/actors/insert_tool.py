"""The tool marker: the actual insert, where the cone used to be.

Upstream's ``ToolPart`` draws one of four things at the current position. On a
lathe it is either a cone - when the tool table's diameter is under
``GCODE_VIEW_TOOL_MIN_DIA``, which on this machine it always is - or the
``lathetool`` profile swept from the front and back angles. Neither is the
insert in the holder; the second is a wedge that happens to have the right
included angle.

This draws the insert instead: the same ISO outline the tool list renders from
``widgets/tool_shapes``, at its real size, rounded to its real nose radius,
turned to the orientation the tool table gives, and with its clamping hole
open so the toolpath and the stock show through it.

It subclasses ``ToolPart`` rather than replacing it, so where the marker goes
stays upstream's answer - the position logger, the rotary tilt, the foam
cutter's second cone. Only what is drawn once the stack is there is ours.
"""

import logging
import math
from contextlib import contextmanager

from teachinlathe.widgets.backplot.actors import geometry, inserts, palette
from teachinlathe.widgets.backplot.actors.base import (Actor, line_width,
                                                       multisample)
from teachinlathe.widgets.backplot.actors.units import mm, to_mm

LOG = logging.getLogger(__name__)

try:
    from OpenGL.GL import (GL_ALWAYS, GL_CULL_FACE, GL_LESS,
                           glBindVertexArray, glDepthFunc, glDisable,
                           glUseProgram)
    from rs274 import glcanon_scene
    _TOOL_PART = glcanon_scene.ToolPart
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot insert: LinuxCNC preview modules unavailable: %s", exc)
    _TOOL_PART = object

#: The insert drawn when the tool carries no choice of its own.
DEFAULT_FAMILY = "DCMT"
DEFAULT_SIZE_INDEX = 1          # DCMT 11
DEFAULT_NOSE_RADIUS_MM = 0.4

#: Segments a full circle is drawn with - the round insert, the hole, the
#: countersink, and the spokes the ring is built on.
CIRCLE_SEGMENTS = 64

#: Segments each rounded corner is built from.
CORNER_SEGMENTS = 10

#: Below this the nose radius is treated as sharp. A tool table left at zero
#: is the usual reason, and rounding to nothing is better than refusing to
#: draw.
MIN_NOSE_RADIUS_MM = 0.01


class InsertActor(_TOOL_PART):
    """The insert at the programmed point.

    ``host`` is the backplot item, read for a per-tool insert choice if it
    grows one; the tool list is where that will be set. Until then every tool
    draws the default.
    """

    def __init__(self, host=None):
        self._host = host
        #: The last insert built, and the key it was built for. The shape in
        #: its own frame does not change while the tool does not, and the
        #: position it is drawn at rides on the matrix stack rather than on
        #: these vertices - so this is rebuilt on a tool change, not on a
        #: move. Without it the ring's ray casting would run at the poll rate.
        self._cached_key = None
        self._cached = None

    # ── state ───────────────────────────────────────────────────────────────

    @contextmanager
    def scope(self, ctx):
        """Plain state, not upstream's.

        ``ToolPart`` enters a GL_ONE/GL_CONSTANT_ALPHA blend and face culling
        kept for pixel parity with the immediate-mode marker it replaced. The
        insert is an opaque solid drawn in its own colours, so it wants
        neither: the blend would wash the body out against the plot, and the
        outline is a flat polygon with no consistent winding to cull by.

        **Culling is left off on the way out, not switched back on.** The
        scene's baseline does not set it - ``Scene.apply_baseline`` covers
        depth and blend only - so "restore" here means restore to off, which
        is what every other part draws under. Enabling it on exit leaks onto
        the parts drawn after this one, and the flat annotation they fill
        (the arrow heads, the origin's quadrants) is wound whichever way its
        geometry came out: half of it silently disappears.

        **Multisampling on, for this part alone.** The insert is the one
        thing on the plot whose edge is the boundary of a filled shape rather
        than a stroked line, and a rounded corner a few millimetres across
        staircases badly without it. The frame's baseline is off - see
        ``LatheBackplotCanon._set_multisample_baseline`` for why lines are
        worse with it - so this turns it on and back off again, which is the
        same bargain every other flag in this scope is making.

        Depth-always, so the insert reads over the toolpath it sits on.
        """
        with ctx.mv.push():
            glDepthFunc(GL_ALWAYS)
            glDisable(GL_CULL_FACE)
            multisample(True)
            try:
                yield
            finally:
                multisample(False)
                glDisable(GL_CULL_FACE)
                glDepthFunc(GL_LESS)
                line_width(1.0)
                glUseProgram(0)
                glBindVertexArray(0)

    # ── what is drawn, once upstream has placed the stack ───────────────────

    def _draw_at_tool(self, ctx, pos, rx, ry, rz):
        """Upstream's hook, with the cone/lathetool choice taken out.

        Everything before the last line is upstream's ``_draw_at_tool``
        verbatim: translate to the position the logger reports, then tilt by
        the rotary axes in GEOMETRY order.
        """
        ctx.mv.translate(*pos)
        self._apply_rotary(ctx, rx, ry, rz)
        self._draw_insert(ctx)

    def _draw_insert(self, ctx):
        shape = self._shape(ctx)
        if shape is None:
            return
        mvp = ctx.mv.mvp()

        Actor.fill(ctx, shape["body"], palette.INSERT_BODY, mvp)
        line_width(palette.WIDTH_INSERT_EDGE)
        Actor.stroke(ctx, shape["edge"], palette.INSERT_EDGE, mvp)
        if shape["countersink"]:
            line_width(palette.WIDTH_INSERT_HOLE)
            Actor.stroke(ctx, shape["countersink"], palette.INSERT_EDGE, mvp)
        if shape["hole"]:
            line_width(palette.WIDTH_INSERT_HOLE)
            Actor.stroke(ctx, shape["hole"], palette.INSERT_EDGE, mvp)

    # ── building the shape, once per tool ───────────────────────────────────

    def _shape(self, ctx):
        """The insert's vertices in model space, built or reused."""
        insert = self._insert(ctx)
        angle = self._angle(ctx, insert)
        key = (insert.family, insert.size_index, insert.nose_radius,
               insert.active_corner, round(angle, 9))
        if key != self._cached_key:
            self._cached = _build(insert, angle)
            self._cached_key = key
        return self._cached

    # ── which insert, and which way round ───────────────────────────────────

    def _insert(self, ctx):
        """The insert to draw for the tool in the spindle.

        The nose radius comes from the tool table, where LinuxCNC keeps it as
        a diameter - the same reading ``_draw_lathetool_geometry`` takes of
        it. Family and size have nowhere to come from yet; the tool list is
        where they will be chosen.
        """
        chosen = getattr(self._host, "insert", None) or {}
        family = chosen.get("family", DEFAULT_FAMILY)
        size_index = chosen.get("size_index", DEFAULT_SIZE_INDEX)
        nose_radius = chosen.get("nose_radius")

        if nose_radius is None:
            nose_radius = DEFAULT_NOSE_RADIUS_MM
            tool = ctx.current_tool()
            if tool is not None:
                try:
                    nose_radius = to_mm(
                        ctx.to_internal_linear_unit(tool.diameter)) / 2.0
                except (AttributeError, TypeError, ValueError):
                    pass
        if nose_radius < MIN_NOSE_RADIUS_MM:
            nose_radius = 0.0

        try:
            return inserts.Insert(family, size_index, nose_radius,
                                  chosen.get("active_corner", 0))
        except KeyError:
            return inserts.Insert(DEFAULT_FAMILY, DEFAULT_SIZE_INDEX,
                                  nose_radius)

    def _angle(self, ctx, insert):
        """How far to turn the insert, in radians, for the tool in the
        spindle. The arithmetic is in ``turn_angle``; this is the lookup."""
        tool = ctx.current_tool()
        orientation = getattr(tool, "orientation", 0) or 0
        try:
            shape = self.LATHE_SHAPES[int(orientation)]
        except (IndexError, TypeError, ValueError):
            return 0.0
        return turn_angle(shape, insert.active_tip())


def _build(insert, angle):
    """The insert's model-space vertices: body, outline, hole, countersink.

    Built in the insert's own 2D frame and placed once at the end, because
    every step of the geometry - the rounding, the ring's ray casting, the
    circles - is written in that frame and reads as the drawing it came from.
    """
    loop = _outline(insert)
    if len(loop) < 3:
        return None

    hole = insert.hole()
    hole_radius = hole[0] / 2.0 if hole else 0.0
    countersink_radius = hole[1] / 2.0 if hole else 0.0
    reach = min(math.hypot(x, y) for x, y in loop)
    if countersink_radius >= reach:
        countersink_radius = 0.0        # would spill out past the edge

    tip = insert.active_tip()

    def place(point):
        return _to_plane(_rotate(_offset(point, tip), angle))

    def ring(radius):
        if radius <= 0:
            return []
        return geometry.polyline(
            [place(point)
             for point in geometry.circle_loop(radius, CIRCLE_SEGMENTS)],
            closed=True)

    body = geometry.ring_triangles(loop, hole_radius, CIRCLE_SEGMENTS)
    return {
        "body": [place(point) for point in body],
        "edge": geometry.polyline([place(point) for point in loop],
                                  closed=True),
        "hole": ring(hole_radius),
        "countersink": ring(countersink_radius),
    }


def _outline(insert):
    """The insert's closed outline in its own frame, corners rounded."""
    if insert.is_round:
        return geometry.circle_loop(insert.ic / 2.0, CIRCLE_SEGMENTS)
    verts, _cutting = insert.outline()
    return geometry.rounded_polygon(verts, insert.nose_radius,
                                    CORNER_SEGMENTS)


# ── the insert's frame, and the lathe's ────────────────────────────────────

def turn_angle(shape, tip):
    """How far to turn an insert whose active corner points at ``tip`` so that
    it sits at the tool-table orientation ``shape``, in radians.

    ``shape`` is upstream's ``ToolPart.LATHE_SHAPES[q]``: ``(along X, along
    Z)``, read that way round by ``_draw_lathetool_geometry``, and it points
    at **the body**, not at the tip. That is the trap here. Upstream builds
    the nose arc centred at ``(r*dx, r*dy)`` *from the current position*, and
    the current position is the programmed point - the tip. So the material
    lies that way and the tip points the other: the direction wanted is
    ``(-dx, -dz)``.

    Getting the sign wrong turns the insert through half a revolution, which
    still looks like an insert and still has its tip on the path - it is just
    cutting from the far side of the work.

    Orientation 9 is a centred tool with no direction, and 0 is no tool; both
    turn by nothing.
    """
    if shape is None or tuple(shape) == (0, 0):
        return 0.0
    if math.hypot(tip[0], tip[1]) < 1e-9:
        return 0.0

    along_x, along_z = shape
    # The tip direction, in the insert's frame: the plane mapping run
    # backwards (u is model Z, v is minus model X - see ``_to_plane``) applied
    # to ``(-dx, -dz)``.
    target = math.atan2(along_x, -along_z)
    return target - math.atan2(tip[1], tip[0])


def _offset(point, tip):
    """``point`` moved so the active tip sits at the origin."""
    return point[0] - tip[0], point[1] - tip[1]


def _rotate(point, angle):
    if not angle:
        return point
    sin, cos = math.sin(angle), math.cos(angle)
    return (point[0] * cos - point[1] * sin,
            point[0] * sin + point[1] * cos)


def _to_plane(point):
    """An insert-frame ``(x, y)`` in millimetres, as a model-space triple.

    The insert is drawn with x to the right and y up, as any flat drawing is.
    The lathe view has Z to the right and X *down* the screen - growing
    radius - so y maps to negative X. Getting this sign wrong mirrors the
    insert about the spindle axis, which looks plausible and cuts the wrong
    side.
    """
    return mm(-point[1]), 0.0, mm(point[0])
