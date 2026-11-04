"""The bar the program cuts from: its outline, and the material inside it.

Ported from ``ToolpathStockActor``. The stock is not something the preview can
work out - nothing in the G-code says how long the bar is or what it started
at - so it comes from the conversational program's own header, which
``backplot.workpiece`` finds beside the loaded file.

**The material left is drawn solid**, under the toolpath: the bar as it stands
now, cut back to wherever the tool has been, with every edge of what is left -
the bore's too, not the axis - as its outline; what is cut away leaves no line
behind. Before a program runs, that is the whole bar. Clearing the plot erases
the live trace while keeping the cuts already made.

**It is drawn where the program started**, not where the work offset is now: a
Facing that makes its Z End the new Z0 moves the origin, not the bar
(``preview_origin``, the offsets the program was read with).

What is left comes from the host's source (``backplot.plot_source``,
``material_left``): for the machine, cut from its live trail - what the
machine actually did, so it follows a run that was stopped, restarted or run
from a line - and for a simulation, from the run. Both are the one model of a tool
taking off material (``simulation.logic.material``): the tool's cutting
outline swept along each cutting move, turned about the axis - or, along a
move synced with the spindle, the threading tooth's V once a turn. A thread
is not the same all round: the half under the toolpath is the part through
the axis on the tool's side, with the trace of each pass's V over it (one V
inside the next) - black where the program will cut it (the host's
``thread_plan``), red once it has; the lines of the passes themselves are
not drawn (lathe_backplot_item.hide_synced_lines, actors.trail). The
mirrored half (``RemainingStockActor``) is the part across the axis, its Vs
half a pitch along on a single start. The static layer
this is drawn in is drawn again when it changes (``_static_signature``); the
solid's triangles are made again only then.
"""

import logging

from teachinlathe.ui.tabs.programs.backplot.actors import geometry, palette
from teachinlathe.ui.tabs.programs.backplot.actors.base import Actor
from teachinlathe.simulation.logic.material import TOOL_SIDE
from teachinlathe.ui.tabs.programs.backplot.actors.units import mm

LOG = logging.getLogger(__name__)

#: How near the axis, in the scene's unit, an edge lies along it.
_ON_AXIS = mm(0.001)


class StockActor(Actor):
    """Drawn under the toolpath, so a cut reads as removing material from it.

    Holds the host rather than reading a context field, because the stock is
    the host's knowledge: ``FrameContext`` is upstream's contract and the
    workpiece is not in it.
    """

    LINE_WIDTH = palette.WIDTH_STOCK
    DEPTH_WRITE = False

    #: Which section of the part this half is (material.TOOL_SIDE / FAR_SIDE),
    #: and whether the threading tooth's trace is drawn over it.
    SIDE = TOOL_SIDE
    TRACE = True

    def __init__(self, host=None):
        super().__init__(host)
        #: The solid's triangles, its outline, and what they were made of:
        #: the material left and its version, or the bar.
        self._solid_points = []
        self._solid_edges = []
        self._trace_edges = []
        self._solid_key = None
        #: the stroke pairs of each line of a trace, by the line - the Vs cut
        #: are the same lines from one cut to the next - and the plan's
        self._line_cache = {}
        self._planned = (None, [])

    def _dimensions(self):
        """``(length, outer diameter, bore diameter)`` in mm, or ``None``."""
        stock = getattr(self._host, "stock", None) or {}
        try:
            length = float(stock.get("stock_length") or 0.0)
            outer = float(stock.get("external_diameter") or 0.0)
            bore = float(stock.get("internal_diameter") or 0.0)
        except (TypeError, ValueError):
            return None
        if length <= 0 or outer <= 0:
            return None
        return length, outer, max(0.0, min(bore, outer))

    def place(self, ctx):
        """Where the program started (the module): the offsets it was read
        with, as ``Actor.place`` applies the ones in effect now."""
        origin = getattr(self._host, "preview_origin", None)
        if origin is None:
            Actor.place(self, ctx)
            return
        if not self.FOLLOW_PROGRAM_ORIGIN or not ctx.show_relative:
            return
        g5x, g92, rotation = origin
        ctx.mv.translate(*ctx.to_internal_units(g5x)[:3])
        ctx.mv.rotate(rotation, 0, 0, 1)
        ctx.mv.translate(*ctx.to_internal_units(g92)[:3])

    def draw(self, ctx):
        dimensions = self._dimensions()
        if dimensions is None:
            return
        length, outer, bore = dimensions
        left = material_left(self._host, ctx)
        if left is not None:
            # the object itself, not its id: one freed can hand its id on
            key = (left, left.version)
        else:
            key = dimensions
        if key != self._solid_key:
            self._trace_edges = []
            if left is not None:
                rings = _rings(left.material.section(self.SIDE))
                if self.TRACE:
                    self._trace_edges = self._edges_of(left.material.trace)
            else:
                # the bar, back from the face at Z zero; X halved because the
                # scene draws radius and the header states diameter
                near, far = 0.0, mm(-length)
                skin, core = mm(outer / 2.0), mm(bore / 2.0)
                rings = [[(far, core), (near, core), (near, skin), (far, skin)]]
            self._solid_points = geometry.solid_triangles(rings)
            self._solid_edges = _outline_edges(rings)
            self._solid_key = key
        mvp = ctx.mv.mvp()
        self.fill(ctx, self._solid_points, palette.MATERIAL, mvp)
        self.stroke(ctx, self._solid_edges, palette.STOCK, mvp)
        if self.TRACE:
            planned = self._planned_edges()
            if planned:
                self.stroke(ctx, planned, palette.THREAD_PLANNED, mvp)
        if self._trace_edges:
            self.stroke(ctx, self._trace_edges, palette.THREAD_TRACE, mvp)

    def _planned_edges(self):
        """The Vs the loaded program will cut, as stroke pairs."""
        find = getattr(self._host, "thread_plan", None)
        try:
            plan = find() if find is not None else None
        except Exception as exc:
            LOG.debug("backplot stock: no thread plan: %s", exc)
            plan = None
        if plan is not self._planned[0]:
            self._planned = (plan, _line_edges(plan.trace) if plan is not None else [])
        return self._planned[1]

    def _edges_of(self, trace):
        """``trace`` - shapely lines - as stroke pairs, each line's worked out
        once."""
        if len(self._line_cache) > 4 * len(trace) + 256:
            self._line_cache = {}
        edges = []
        for line in trace:
            found = self._line_cache.get(id(line))
            if found is None or found[0] is not line:
                found = (line, _line_edges(line))
                self._line_cache[id(line)] = found
            edges.extend(found[1])
        return edges


def material_left(host, ctx):
    """The part as it is being cut, from ``host``'s source - something with
    ``material`` (a shapely (z, r) shape, mm) and ``version`` - or None."""
    find = getattr(host, "material_left", None)
    try:
        return find(ctx) if find is not None else None
    except Exception as exc:
        LOG.debug("backplot stock: no material left: %s", exc)
        return None


def _line_edges(lines):
    """Lines in mm (z, r) - a shapely line, a collection of lines (a point
    in one is left out), or a sequence of those - as stroke pairs in the
    scene's unit."""
    if isinstance(lines, (tuple, list)):
        return [edge for line in lines for edge in _line_edges(line)]
    if hasattr(lines, "geoms"):
        return _line_edges(list(lines.geoms))
    edges = []
    if lines.geom_type in ("LineString", "LinearRing"):
        coords = list(lines.coords)
        for (za, ra), (zb, rb) in zip(coords, coords[1:]):
            edges.extend([(mm(ra), 0.0, mm(za)), (mm(rb), 0.0, mm(zb))])
    return edges


def _polygons(material):
    for polygon in getattr(material, "geoms", [material]):
        if not polygon.is_empty and polygon.geom_type == "Polygon":
            yield polygon


def _rings(material):
    """Every ring of ``material`` - mm (z, r) - in the scene's unit."""
    return [[(mm(z), mm(r)) for z, r in list(ring.coords)[:-1]]
            for polygon in _polygons(material)
            for ring in [polygon.exterior] + list(polygon.interiors)]


def _outline_edges(rings):
    """Every edge of ``rings`` - (z, r) in the scene's unit - as stroke
    pairs, but those along the axis: a solid part is solid to centre, and a
    line there would read as a hole."""
    edges = []
    for ring in rings:
        for (za, ra), (zb, rb) in zip(ring, ring[1:] + ring[:1]):
            if abs(ra) < _ON_AXIS and abs(rb) < _ON_AXIS:
                continue
            edges.extend([(ra, 0.0, za), (rb, 0.0, zb)])
    return edges
