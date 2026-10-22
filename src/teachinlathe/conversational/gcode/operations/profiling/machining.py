"""Tool-aware profile roughing: what the tool can reach, and the moves that reach it.

The tool is the insert in the holder, at its real size and nose radius, turned
the way the backplot turns it (``tool_source._describe`` + ``insert_tool._build``)
and hung from its control point. Everything is planned against one shape, the
*obstacle*: the set of positions the control point must never enter, which is
the finished part, grown by the stock to leave, swept by the tool turned round
(a Minkowski sum). Outside it the insert touches neither the part nor the
stock left on it, so

* a pass runs from the stock face until it meets the obstacle - the first
  thing in its way, not the deepest point of the profile at that diameter,
  which is what cut through the finished diameter in front of a DIN 509
  relief;
* the contour pass is the obstacle's edge: the profile offset by the nose
  radius, and bridged over a pocket the insert does not fit into;
* a pocket - material the passes from the face cannot reach - is cut only
  where the insert can be plunged into it, and is otherwise left, as residual
  material for another operation with another tool.

Geometry is in radius space: z, and r = X / 2. ID is planned as OD with r
mirrored (r -> -r), tool and all, and mirrored back: the material then always
lies below the profile and the tool comes from above.

What is not modelled: the holder. The insert stands for it with its two
cutting edges carried on, past their ends, as straight lines (``EDGE_REACH``):
the lead and the back angle the tool is set at. So the tool goes down no slope
steeper than its back angle, and is never taken to fit into a neck behind a
peak because the insert alone is short enough to - what the holder behind it
would not. A holder wider than those lines can still hit a shoulder.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import unary_union

from teachinlathe.conversational.model.data_types import PassType, ProfilingType

from .geometry import StartPoint, ToolpathArc

Pt = Tuple[float, float]

#: Far enough to stand for "everything that way", in mm.
FAR = 1000.0
#: How far a chord of a discretised arc may stray from it, in mm.
ARC_TOLERANCE = 0.002
#: Material thinner than this is not worth a move, and overlaps smaller than
#: this are rounding, not collisions; in mm and mm².
TOLERANCE = 0.005
MIN_AREA = 1e-3
#: A cut taking off less than this, on average along it, is not worth making;
#: in mm.
MIN_CUT = 0.01
#: How far round the insert is swung either way to keep clear of what it
#: passes, in degrees.
CLEARANCE_DEGREES = 2.0
#: The insert's nose rounded with this many chords per corner.
NOSE_SEGMENTS = 24
#: How far the insert's cutting edges are carried on past their ends, to
#: stand for the holder behind them; in mm.
EDGE_REACH = 200.0


# ── the tool ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ToolShape:
    """The insert as an outline around its control point, in (z, r), as the
    real tool sits - not mirrored for ID."""
    outline: Tuple[Pt, ...]          # the insert itself, for drawing
    envelope: Tuple[Pt, ...]         # outline with its edges carried on, swung by the clearance, convex
    nose_radius: float
    label: str
    known: bool = True               # False: no insert to go by (see square_tool)
    #: the nose's centre, from the control point
    centre: Pt = (0.0, 0.0)


def insert_tool_shape(tool, clearance_degrees: float = CLEARANCE_DEGREES) -> Optional[ToolShape]:
    """The shape of a Tool Library TurningTool (boring bars too); None for
    any other kind of tool."""
    from teachinlathe.tooling.model import insert_catalog, tool_angles
    from teachinlathe.tooling.model.data_types import TurningTool
    from teachinlathe.ui.tabs.programs.backplot.actors.geometry import circle_loop, rounded_polygon

    if not isinstance(tool, TurningTool):
        return None
    insert = insert_catalog.insert_for(tool.insert)
    tip = insert.active_tip()
    rotation = math.radians(tool_angles.insert_rotation(
        tool.orientation, tool.front_angle, tool.back_angle,
        tool_angles.direction_degrees(tip)))
    edges = []                          # the cutting corner's two neighbours
    if insert.is_round:
        loop = circle_loop(insert.ic / 2.0, 8 * NOSE_SEGMENTS)
    else:
        verts, _cutting = insert.outline()
        loop = rounded_polygon(verts, insert.nose_radius, NOSE_SEGMENTS)
        index = verts.index(tip)
        edges = [verts[(index - 1) % len(verts)], verts[(index + 1) % len(verts)]]
    nose = insert.nose_centre()
    radius = insert.ic / 2.0 if insert.is_round else insert.nose_radius

    def place(point):
        # backplot.actors.insert_tool: hung from the sharp tip, turned, then
        # the drawing's y is minus X
        x, y = point[0] - tip[0], point[1] - tip[1]
        c, s = math.cos(rotation), math.sin(rotation)
        x, y = x * c - y * s, x * s + y * c
        return x, -y                                  # (z, r)

    outline = [place(p) for p in loop]
    centre = place(nose)
    tip_dir = (-centre[0], -centre[1])               # nose centre -> sharp tip
    control = _control_point(centre, radius, tip_dir)
    outline = [(z - control[0], r - control[1]) for z, r in outline]
    centre = (centre[0] - control[0], centre[1] - control[1])
    reach = list(outline)
    corner = place(tip)
    for neighbour in map(place, edges):
        dz, dr = neighbour[0] - corner[0], neighbour[1] - corner[1]
        length = math.hypot(dz, dr)
        reach += [(z + EDGE_REACH * dz / length, r + EDGE_REACH * dr / length) for z, r in outline]
    envelope = _swung(reach, centre, clearance_degrees)
    return ToolShape(tuple(outline), tuple(envelope), radius, insert.iso_code, centre=centre)


def square_tool() -> ToolShape:
    """Stands in for a tool there is nothing known about: a square corner
    reaching far up and toward the tailstock. Cutting with it is roughing
    along the profile's monotonic hull - no pocket, no undercut is entered,
    since nothing proves the real tool would fit."""
    size = 50.0
    outline = ((0.0, 0.0), (size, 0.0), (size, size), (0.0, size))
    return ToolShape(outline, outline, 0.0, "unknown tool", known=False)


def _control_point(centre: Pt, radius: float, tip_dir: Pt) -> Pt:
    """The point the tool is programmed to: where touching off in X and in Z
    measures it - the nose's tangent in each direction the tip points. A tip
    pointing straight along X has its Z on the centre."""
    sz = 0.0 if abs(tip_dir[0]) < 1e-3 * math.hypot(*tip_dir) else math.copysign(1.0, tip_dir[0])
    sr = 0.0 if abs(tip_dir[1]) < 1e-3 * math.hypot(*tip_dir) else math.copysign(1.0, tip_dir[1])
    return centre[0] + sz * radius, centre[1] + sr * radius


def _swung(points: Sequence[Pt], centre: Pt, degrees: float) -> List[Pt]:
    """``points`` and the same turned ``degrees`` either way about ``centre``,
    as one convex outline: the insert with its clearance."""
    swept = list(points)
    for angle in (-degrees, degrees):
        a = math.radians(angle)
        c, s = math.cos(a), math.sin(a)
        for z, r in points:
            dz, dr = z - centre[0], r - centre[1]
            swept.append((centre[0] + dz * c - dr * s, centre[1] + dz * s + dr * c))
    hull = MultiPoint(swept).convex_hull
    return list(hull.exterior.coords)[:-1]


# ── shapes ──────────────────────────────────────────────────────────────────

def minkowski(shape, convex: Sequence[Pt]):
    """``shape`` (a Polygon or MultiPolygon) grown by the convex outline
    ``convex``: every point of the one plus every point of the other."""
    pieces = []
    polygons = getattr(shape, "geoms", [shape])
    for polygon in polygons:
        if polygon.is_empty:
            continue
        pieces.append(Polygon([(x + convex[0][0], y + convex[0][1])
                               for x, y in polygon.exterior.coords]))
        for ring in [polygon.exterior, *polygon.interiors]:
            coords = list(ring.coords)
            for (ax, ay), (bx, by) in zip(coords, coords[1:]):
                pieces.append(MultiPoint(
                    [(ax + x, ay + y) for x, y in convex]
                    + [(bx + x, by + y) for x, y in convex]).convex_hull)
    return unary_union(pieces)


def sweep(shape: Sequence[Pt], a: Pt, b: Pt):
    """What the convex ``shape`` covers moving from ``a`` to ``b``."""
    return MultiPoint([(a[0] + x, a[1] + y) for x, y in shape]
                      + [(b[0] + x, b[1] + y) for x, y in shape]).convex_hull


def path_points(path) -> List[Pt]:
    """A render path (X as diameter) as (z, r) points, arcs as chords no more
    than ARC_TOLERANCE off, their extremes in Z and X among the points."""
    points = [(path[0].z, path[0].x / 2.0)]
    for element in path[1:]:
        if isinstance(element, ToolpathArc):
            points.extend(_arc_points(points[-1], element)[1:])
        else:
            points.append((element.end_z, element.end_x / 2.0))
    return points


def _arc_points(start: Pt, arc) -> List[Pt]:
    cz, cr = arc.center_z, arc.center_x / 2.0
    radius = math.hypot(start[0] - cz, start[1] - cr)
    a0 = math.atan2(start[1] - cr, start[0] - cz)
    a1 = math.atan2(arc.end_x / 2.0 - cr, arc.end_z - cz)
    sweep_angle = a1 - a0
    if arc.anticlockwise:           # as the preview reads it: angle falling
        while sweep_angle > 0:
            sweep_angle -= 2 * math.pi
    else:
        while sweep_angle < 0:
            sweep_angle += 2 * math.pi
    if radius < 1e-9:
        return [start, (arc.end_z, arc.end_x / 2.0)]
    step = 2 * math.acos(max(-1.0, 1 - ARC_TOLERANCE / radius))
    count = max(1, int(math.ceil(abs(sweep_angle) / step)))
    fractions = {k / count for k in range(count + 1)}
    # the quadrant points - where the arc is furthest in Z or in X
    for k in range(-8, 9):
        q = k * math.pi / 2
        t = (q - a0) / sweep_angle if sweep_angle else 0.0
        if 0.0 < t < 1.0:
            fractions.add(t)
    points = [(cz + radius * math.cos(a0 + sweep_angle * t),
               cr + radius * math.sin(a0 + sweep_angle * t)) for t in sorted(fractions)]
    points[-1] = (arc.end_z, arc.end_x / 2.0)
    return points


# ── the plan ────────────────────────────────────────────────────────────────

@dataclass
class Move:
    """One straight move of the control point, in (z, r) as the machine has
    them (not mirrored). ``feed`` False is a rapid."""
    z0: float
    r0: float
    z1: float
    r1: float
    feed: bool
    pass_no: int = -1
    contour: bool = False
    pocket: bool = False
    #: the last move of a pass, its retract included: where an M1 stop goes
    pass_end: bool = False
    #: a contour move as the profile drawing shows it, (z0, r0, z1, r1): where
    #: the nose touches - along the profile and its stock - rather than the
    #: compensated point the machine is programmed to
    drawn: Optional[Tuple[float, float, float, float]] = None


@dataclass
class RoughingPlan:
    moves: List[Move] = field(default_factory=list)
    #: the profile offset by the stock to leave, from its start to its end, as
    #: (z, r) points: the line the contour keeps to
    allowance: List[Pt] = field(default_factory=list)
    #: what is left to cut once the operation is done, beyond the stock to
    #: leave: (z, r) outlines, as the machine has them
    residual: List[List[Pt]] = field(default_factory=list)
    #: the material before the operation, less the stock to leave
    to_remove: object = None
    #: the material once the operation is done, as a shapely shape in (z, r)
    remaining_stock: object = None
    tool: Optional[ToolShape] = None
    warnings: List[str] = field(default_factory=list)
    error: str = ""


@dataclass(frozen=True)
class RoughingSetup:
    x_start: float
    z_start: float
    doc: float
    retract: float
    stock_x: float
    stock_z: float
    profiling_type: ProfilingType
    pass_type: PassType


def plan_roughing(setup: RoughingSetup, profile_path, tool: Optional[ToolShape],
                  stock_before=None, rest: bool = False,
                  sliver_radius: float = 0.0) -> RoughingPlan:
    """The moves of a Profile Roughing against ``profile_path`` - the finished
    profile as build_render_path gives it - with ``tool`` (None: square_tool).

    ``stock_before`` is the material there is to cut, as a shapely shape in
    (z, r); by default from X Start to the profile's smallest diameter (OD) or
    its largest (ID), from Z Start back. ``rest``: what is left by another
    roughing - the contour then runs only where there is material - and
    ``sliver_radius`` the nose radius of the tool that left it: what that
    nose's corners and the slivers between its passes leave is not cut again.
    """
    return _Planner(setup, profile_path, tool, stock_before, rest, sliver_radius).plan()


def plan_leftover(setup: RoughingSetup, profile_path, stock_before,
                  nose_radius: float = 0.0) -> RoughingPlan:
    """No moves, only what there is to cut - for a rest roughing that has no
    tool yet. ``nose_radius``: the last tool's, whose corners are not counted
    as left over."""
    return _Planner(setup, profile_path, None, stock_before, True, nose_radius)._result()


class _Planner:
    def __init__(self, setup, profile_path, tool, stock_before, rest=False, sliver_radius=0.0):
        self.setup = setup
        self.rest = rest
        self.sliver_radius = sliver_radius
        self.is_id = setup.profiling_type == ProfilingType.ID
        self.sign = -1.0 if self.is_id else 1.0
        self.tool = tool or square_tool()
        # a known insert is mirrored with everything else for ID; the square
        # stand-in is drawn in the planning frame already
        self.envelope = ([self._m(p) for p in self.tool.envelope] if self.tool.known
                         else list(self.tool.envelope))
        self.doc = setup.doc if setup.doc > 0 else 0.5
        self.retract = abs(setup.retract)

        self.z_start = setup.z_start
        self.r_start = self.sign * setup.x_start / 2.0       # mirrored frame
        self.r_safe = self.r_start + self.retract

        points = [self._m(p) for p in path_points(profile_path)]
        if points[0][0] < points[-1][0]:
            points.reverse()                    # from the face toward the chuck
        self.profile = points
        self.part = self._part(points)
        allowance = [(-setup.stock_z, -setup.stock_x), (setup.stock_z, -setup.stock_x),
                     (setup.stock_z, setup.stock_x), (-setup.stock_z, setup.stock_x)]
        self.part_allow = minkowski(self.part, allowance) if (setup.stock_x or setup.stock_z) else self.part
        grown = MultiPoint([(az - tz, ar - tr) for az, ar in allowance for tz, tr in self.envelope]).convex_hull
        # past the profile's end nothing is known: the control point stops
        # there (less the axial stock), whatever the insert's shape
        z_end_limit = points[-1][0] + setup.stock_z
        self.z_end_limit = z_end_limit
        self.obstacle = unary_union([
            minkowski(self.part, list(grown.exterior.coords)[:-1]),
            box(z_end_limit - FAR, -FAR, z_end_limit, FAR)])
        # what touching is allowed and overlapping is not: rounding aside
        self.part_inside = self.part.buffer(-TOLERANCE)
        self.part_allow_inside = self.part_allow.buffer(-TOLERANCE)

        if stock_before is None:
            # as deep as the profile goes and no deeper: what is in front of
            # the face below that is facing's to cut
            r_floor = min(r for _z, r in points)
            material = box(points[-1][0] + setup.stock_z, r_floor, self.z_start, self.r_start)
            z_face, r_face = points[0]
            if r_face > r_floor:
                material = material.difference(box(z_face, r_floor, self.z_start + 1.0, r_face))
        else:
            material = _mirror(stock_before) if self.is_id else stock_before
            # what another operation left, without the rounding slivers its
            # cuts leave along their edges
            material = material.buffer(-MIN_CUT).buffer(MIN_CUT)
        self.material = material
        self.to_remove = _difference(material, self.part_allow)
        if stock_before is not None:
            # only what the roughing before reports as left (see _result)
            self.to_remove = unary_union([
                piece for piece in getattr(self.to_remove, "geoms", [self.to_remove])
                if self._worth_cutting(piece)]) if not self.to_remove.is_empty else self.to_remove
        self.remaining = self.to_remove
        self.moves: List[Move] = []
        self.pass_no = 0
        self.warnings: List[str] = []

    # mirrored frame <-> machine
    def _m(self, p: Pt) -> Pt:
        return p[0], self.sign * p[1]

    def _part(self, points):
        """The finished part below the profile, carried on at its last
        diameter past its far end, toward the chuck."""
        z0, zn = points[0][0], points[-1][0]
        outline = points + [(zn - FAR, points[-1][1]), (zn - FAR, -FAR), (z0, -FAR)]
        return Polygon(outline).buffer(0)

    # ── moves ───────────────────────────────────────────────────────────────

    def _end_pass(self):
        if self.moves:
            self.moves[-1].pass_end = True

    def _add(self, a: Pt, b: Pt, feed: bool, **kind):
        if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-9:
            return
        if feed:
            self.remaining = _difference(self.remaining, sweep(self.envelope, a, b))
        self.moves.append(Move(a[0], self.sign * a[1], b[0], self.sign * b[1], feed, **kind))

    def _rapid_clear(self, a: Pt, b: Pt) -> bool:
        """Whether a rapid from ``a`` to ``b`` meets neither the part nor the
        material still there."""
        swept = sweep(self.envelope, a, b)
        return (swept.intersection(self.remaining).area < MIN_AREA
                and swept.intersection(self.part_inside).area < MIN_AREA)

    def _feed_clear(self, a: Pt, b: Pt) -> bool:
        """Whether a cut from ``a`` to ``b`` stays off the stock to leave."""
        swept = sweep(self.envelope, a, b)
        return swept.intersection(self.part_allow_inside).area < MIN_AREA

    def _removes(self, a: Pt, b: Pt) -> float:
        return sweep(self.envelope, a, b).intersection(self.remaining).area

    def _cuts(self, a: Pt, b: Pt) -> bool:
        """Whether a move from ``a`` to ``b`` takes off anything worth it: on
        average at least MIN_CUT thick along it, not a rounding sliver."""
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        return self._removes(a, b) >= max(MIN_AREA, length * MIN_CUT)

    def _free_runs(self, a: Pt, b: Pt) -> List[Tuple[Pt, Pt]]:
        """The stretches of the line from ``a`` to ``b`` outside the obstacle,
        each from its end nearer ``a``."""
        line = LineString([a, b])
        free = line.difference(self.obstacle)
        runs = []
        for piece in getattr(free, "geoms", [free]):
            if piece.is_empty or piece.length < TOLERANCE:
                continue
            p, q = list(piece.coords)[0], list(piece.coords)[-1]
            if line.project(Point(p)) > line.project(Point(q)):
                p, q = q, p
            runs.append((p, q))
        runs.sort(key=lambda run: line.project(Point(run[0])))
        return runs

    # ── passes ──────────────────────────────────────────────────────────────

    def plan(self) -> RoughingPlan:
        # The insert has to stand on its control point: nothing of it under
        # the point it is programmed to (over it, for ID). A tool held the
        # other way round - an OD tool on an ID profile - cannot cut this.
        if min(r for _z, r in self.envelope) < -max(0.05, self.tool.nose_radius):
            side = "away from the axis" if self.is_id else "toward the axis"
            return RoughingPlan(tool=self.tool, error=(
                f"{self.tool.label}: its tip does not point {side} - "
                "check the tool's orientation"))
        if not self.tool.known:
            self.warnings.append("No turning tool in a Change Tool above: roughing only what "
                                 "any tool reaches, pockets and undercuts left")
        if self.setup.pass_type == PassType.RADIAL:
            self._passes(lambda u, v: (v, u), u_start=self.r_start, u_far=self._r_min() - 1.0,
                         v_start=self.z_start, v_end=self._z_min())
        elif self.setup.pass_type in (PassType.DIAGONAL_INTERIOR, PassType.DIAGONAL_EXTERIOR):
            self._diagonal_passes()
        else:
            self._passes(lambda u, v: (u, v), u_start=self.z_start, u_far=self._z_min() - 1.0,
                         v_start=self.r_start, v_end=self._r_min())
        chain = self._contour_chain()
        self._pockets(chain)
        self._contour(chain)
        return self._result()

    def _z_min(self):
        return self.to_remove.bounds[0] if not self.to_remove.is_empty else self.z_start

    def _r_min(self):
        return self.to_remove.bounds[1] if not self.to_remove.is_empty else self.r_start

    def _levels(self, v_start, v_end):
        levels, k = [], 1
        while v_start - k * self.doc > v_end - 1e-9:
            levels.append(v_start - k * self.doc)
            k += 1
        if not levels or levels[-1] > v_end + TOLERANCE:
            levels.append(v_end)
        return levels

    def _passes(self, at, u_start, u_far, v_start, v_end):
        """Passes along u, from u_start toward u_far, one level of v at a
        time from v_start down to v_end - (u, v) is (z, r) for axial passes
        and (r, z) for radial ones; ``at`` turns (u, v) into (z, r)."""
        ret = self.retract
        position = at(u_start + ret, v_start + ret)
        self.moves.append(Move(position[0], self.sign * position[1],
                               position[0], self.sign * position[1], False))
        for v in self._levels(v_start, v_end):
            start = at(u_start, v)
            runs = self._free_runs(start, at(u_far, v))
            if not runs or Point(runs[0][0]).distance(Point(start)) > 1e-6:
                continue                       # the stock face is out of reach here
            end = runs[0][1]
            if not self._cuts(start, end):
                continue
            if not self._feed_clear(start, end):
                self.warnings.append(f"pass at {v:.3f} skipped: it would cut into the stock to leave")
                continue
            u_end = end[0] if at(1, 0)[0] == 1 else end[1]
            entry = at(u_start + ret, v + ret)
            exit_ = at(u_end + ret, v + ret)
            if not self._go(position, entry):
                continue
            # the lead-in at the feed when it touches material left there
            self._add(entry, start, not self._rapid_clear(entry, start), pass_no=self.pass_no)
            self._add(start, end, True, pass_no=self.pass_no)
            self.pass_no += 1
            if self._rapid_clear(end, exit_):
                self._add(end, exit_, False)
                position = exit_
            else:
                position = end
            back = at(u_start + ret, v + ret)
            if self._rapid_clear(position, back):
                self._add(position, back, False)
                position = back
            else:
                position = self._lift(position)
            self._end_pass()
        self.position = position

    def _go(self, a: Pt, b: Pt):
        """Rapid from ``a`` to ``b`` by the first of these whose every leg is
        clear: straight; out in front of the face at this diameter, along it,
        in; out to the safe diameter, across, in; out, over to the safe Z in
        front of the face, along it, in. False, and no move, when none is."""
        z_safe = self.z_start + self.retract
        routes = [
            [a, b],
            [a, (z_safe, a[1]), (z_safe, b[1]), b],
            [a, (a[0], self.r_safe), (b[0], self.r_safe), b],
            [a, (a[0], self.r_safe), (z_safe, self.r_safe), (z_safe, b[1]), b],
        ]
        for route in routes:
            if all(self._rapid_clear(p, q) for p, q in zip(route, route[1:])):
                for p, q in zip(route, route[1:]):
                    self._add(p, q, False)
                return True
        # nothing gets there without going through material: no rapid at all,
        # the move it was for is not made
        return False

    def _lift(self, a: Pt) -> Pt:
        """Straight out to the safe diameter, the way a pass leaves; toward
        the face first when that is in the way."""
        safe = (a[0], self.r_safe)
        if not self._rapid_clear(a, safe):
            front = (self.z_start + self.retract, a[1])
            if self._rapid_clear(a, front):
                self._add(a, front, False)
                a, safe = front, (front[0], self.r_safe)
            else:
                self.warnings.append(f"no clear way out from {self._label(a)}")
        self._add(a, safe, False)
        return safe

    def _label(self, p: Pt) -> str:
        return f"X{2 * self.sign * p[1]:.3f} Z{p[0]:.3f}"

    def _diagonal_passes(self):
        """45° passes, as profiling.diagonal lays them out, each run from the
        stock edge until it meets the obstacle."""
        ret = self.retract
        z_min, r_min = self._z_min(), self._r_min()
        span = max(self.r_start - r_min, self.z_start - z_min)
        position = (self.z_start + ret, self.r_safe)
        self.moves.append(Move(position[0], self.sign * position[1], position[0],
                               self.sign * position[1], False))
        exterior = self.setup.pass_type == PassType.DIAGONAL_EXTERIOR
        step = self.doc
        while step < 2 * span + self.doc:
            a = (self.z_start - step, self.r_start)            # X Start side
            b = (self.z_start, self.r_start - step)            # face side
            far_a = (a[0] - FAR, a[1] + FAR)
            far_b = (b[0] + FAR, b[1] - FAR)
            # from the X Start side down toward the face, inside the stock box
            segment = LineString([far_a, far_b]).intersection(
                box(z_min - 1.0, r_min - 1.0, self.z_start, self.r_start))
            step += self.doc
            if segment.is_empty or segment.length < TOLERANCE:
                continue
            p, q = list(segment.coords)[0], list(segment.coords)[-1]
            if p[1] < q[1]:
                p, q = q, p                                    # p: the outer end
            for run in self._free_runs(p, q):
                start, end = (run[1], run[0]) if exterior else run
                if not self._cuts(start, end) or not self._feed_clear(start, end):
                    continue
                entry = (start[0] + ret, start[1] + ret)
                if not self._go(position, entry):
                    continue
                self._add(entry, start, not self._rapid_clear(entry, start), pass_no=self.pass_no)
                self._add(start, end, True, pass_no=self.pass_no)
                self.pass_no += 1
                position = self._lift(end)
                self._end_pass()
                break
        self.position = position

    # ── pockets ─────────────────────────────────────────────────────────────

    def _pockets(self, chain):
        """What the passes from the face do not reach and is more than a
        pass's depth from the contour - a pocket behind a rise or a groove -
        cut where the tool can be plunged in: level by level from the
        pocket's top, along Z, plunging in X (toward the axis for OD, away
        from it for ID). The stair steps the passes leave in front of a
        shoulder are not pockets: the contour takes those."""
        if not self.tool.known:
            return
        # the contour cuts at most a pass's depth: what lies deeper than that
        # under it is a pocket, roughed out first
        band = LineString(chain).buffer(self.doc) if len(chain) > 1 else Polygon()
        left = _difference(self.remaining, band)
        z_face = self.profile[0][0]
        pockets = [p for p in getattr(left, "geoms", [left])
                   if p.area >= MIN_AREA and p.bounds[0] < z_face - TOLERANCE]
        for core in sorted(pockets, key=lambda p: -p.bounds[2]):
            # the pocket: what is left around its deep core, up to its top
            pocket = core.buffer(self.doc).intersection(self.remaining)
            if pocket.is_empty:
                continue
            z_lo, r_lo, z_hi, r_hi = pocket.bounds
            # on the same levels as the passes from the face
            for r in [v for v in self._levels(self.r_start, core.bounds[1]) if v < r_hi]:
                if self.remaining.intersection(core).area < MIN_AREA:
                    break
                # in and out over the pocket, not from the bar's diameter
                top = min(self.r_safe, r_hi + self.retract)
                for run in self._free_runs((z_hi + 1.0, r), (z_lo - 1.0, r)):
                    self._pocket_pass(run, r, pocket, top)

    def _pocket_pass(self, run, r, pocket, top):
        """One level of a pocket: plunged into at the run's highest point the
        tool goes straight down to, then along the run. It comes from where
        the pass before left it - still in the pocket, just off its cut -
        along at that height to over this plunge, or else from ``top``, just
        over the pocket; and it leaves the cut just off it, for the next."""
        start, end = run
        if sweep(self.envelope, start, end).intersection(
                self.remaining.intersection(pocket)).area < MIN_AREA:
            return
        # the highest point of the run it can be plunged to straight from above
        length = start[0] - end[0]
        for k in range(0, 21):
            z = start[0] - length * k / 20.0
            plunge_top = (z, top)
            if self.obstacle.intersection(LineString([plunge_top, (z, r)])).length < 1e-6:
                break
        else:
            return
        entry, bottom = (z, top), (z, r)
        # over the plunge: straight across from where the last pass left the
        # tool when that is still in this pocket and the way is clear,
        # otherwise over the pocket
        here = self.position
        over = (z, here[1])
        across = (r < here[1] <= top + 1e-9
                  and self.obstacle.intersection(LineString([over, bottom])).length < 1e-6
                  and self._rapid_clear(here, over))
        high = over if across else entry
        # down fast to just over what is still there, then at the feed
        low = min(r + self.retract, high[1])
        lo, hi = low, high[1]
        if not self._rapid_clear(high, (z, lo)):
            for _ in range(12):
                mid = (lo + hi) / 2
                if self._rapid_clear(high, (z, mid)):
                    hi = mid
                else:
                    lo = mid
            low = hi
        if not (self._feed_clear((z, low), bottom) and self._feed_clear(bottom, end)):
            return
        if across:
            self._add(here, over, False)
        elif not self._go(self.position, entry):
            return
        self._add(high, (z, low), False)
        self._add((z, low), bottom, True, pass_no=self.pass_no, pocket=True)
        self._add(bottom, end, True, pass_no=self.pass_no, pocket=True)
        self.pass_no += 1
        # out: just off the cut, as a pass from the face leaves it - the next
        # pass goes on from there; the way it came in when that is in the way
        lifted = (end[0] + self.retract, r + self.retract)
        if lifted[1] <= top and self._rapid_clear(end, lifted):
            self._add(end, lifted, False)
            self.position = lifted
        else:
            if self._rapid_clear(end, bottom):
                self._add(end, bottom, False)
            self._add(bottom, entry, False)
            self.position = entry
        self._end_pass()

    # ── the contour ─────────────────────────────────────────────────────────

    def _contour_approach(self, chain) -> Pt:
        if not chain:
            return (self.z_start + self.retract, self.r_safe)
        approach = (self.z_start + self.retract, chain[0][1])
        if approach[0] < chain[0][0]:
            approach = (chain[0][0] + self.retract, chain[0][1])
        return approach

    def _contour(self, chain):
        """Along the obstacle's edge: the profile, offset by the stock to leave
        and compensated for the nose, bridged over what the tool cannot enter.
        From the top of the profile's start to its end point."""
        if len(chain) < 2:
            self.warnings.append("no contour: the tool reaches none of the profile")
            return
        drawn = self._drawn(chain)
        approach = self._contour_approach(chain)
        segments = list(zip(chain, chain[1:], drawn, drawn[1:]))
        if not self.rest:
            if not self._go(self.position, approach):
                self.warnings.append("no contour: no clear way to its start")
                return
            self._add_drawn(approach, chain[0], approach, drawn[0])
            for a, b, da, db in segments:
                self._add_drawn(a, b, da, db)
            self.pass_no += 1
            self.position = self._lift(chain[-1])
            return
        # rest material: only the stretches with something left to cut, each
        # gone to and left as a pass is
        cuts = [self._cuts(a, b) for a, b, _da, _db in segments]
        k = 0
        while k < len(segments):
            if not cuts[k]:
                k += 1
                continue
            # from the stretch before it, which cuts nothing: the tool goes in
            # at the feed rather than being stood on what is left
            run = [segments[k - 1]] if k > 0 else []
            while k < len(segments) and cuts[k]:
                run.append(segments[k])
                k += 1
            start = run[0][0]
            if not self._go(self.position, start):
                # from straight over it, down at the feed
                over = (start[0], start[1] + self.retract)
                if not self._go(self.position, over):
                    continue
                self._add(over, start, True, pass_no=self.pass_no, contour=True)
            for a, b, da, db in run:
                self._add_drawn(a, b, da, db)
            self.pass_no += 1
            self.position = self._lift(run[-1][1])

    def _add_drawn(self, a: Pt, b: Pt, da: Pt, db: Pt):
        self._add(a, b, True, pass_no=self.pass_no, contour=True)
        if self.moves and self.moves[-1].contour:
            self.moves[-1].drawn = (da[0], self.sign * da[1], db[0], self.sign * db[1])

    def _drawn(self, chain: List[Pt]) -> List[Pt]:
        """Where the nose touches along ``chain``: its centre, pushed its
        radius toward what it cuts - the obstacle lies to the left of the
        chain. On the profile that is the profile and its stock; where the
        tool bridges what it cannot enter, the edge of what it cuts."""
        if not self.tool.known:
            return list(chain)
        centre = self._m(self.tool.centre)
        radius = self.tool.nose_radius
        normals = []
        for a, b in zip(chain, chain[1:]):
            dz, dr = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dz, dr) or 1.0
            normals.append((-dr / length, dz / length))
        points = []
        for i, p in enumerate(chain):
            around = normals[max(0, i - 1):i + 1] or normals[-1:]
            nz = sum(n[0] for n in around)
            nr = sum(n[1] for n in around)
            length = math.hypot(nz, nr) or 1.0
            points.append((p[0] + centre[0] + radius * nz / length,
                           p[1] + centre[1] + radius * nr / length))
        return points

    def _contour_chain(self) -> List[Pt]:
        return self._boundary_chain(self.obstacle)

    def allowance_chain(self) -> List[Pt]:
        """The profile offset by the stock to leave, from its start to its
        end, as the machine has it."""
        return [self._m(p) for p in self._boundary_chain(self.part_allow)]

    def _boundary_chain(self, shape) -> List[Pt]:
        """The edge of ``shape`` along the profile: from the top of its start
        to its end point, the tailstock side first."""
        polygons = getattr(shape, "geoms", [shape])
        main = max(polygons, key=lambda p: p.area)
        ring = list(main.exterior.coords)[:-1]
        if not Polygon(ring).exterior.is_ccw:
            ring.reverse()
        r_first = self.profile[0][1] + self.setup.stock_x - TOLERANCE
        inner = [i for i, (z, r) in enumerate(ring) if abs(r) < FAR / 2]
        if not inner:
            return []
        z_wall = self.z_end_limit
        candidates = [i for i in inner if ring[i][1] >= r_first and ring[i][0] <= self.z_start + 1e-9]
        if not candidates:
            return []
        start = max(candidates, key=lambda i: (ring[i][0], -ring[i][1]))
        # up to the profile's end point - over the top of a shoulder it ends with
        r_last = self.profile[-1][1] + self.setup.stock_x - TOLERANCE
        chain = []
        n = len(ring)
        for k in range(n):
            point = ring[(start + k) % n]
            if k and point[0] <= z_wall + TOLERANCE and point[1] >= r_last:
                # at the end: up the edge only as far as the profile goes
                chain.append((point[0], max(chain[-1][1], r_last + TOLERANCE)))
                break
            chain.append(point)
        return _simplify(chain)

    # ── what is left ────────────────────────────────────────────────────────

    def _worth_cutting(self, piece) -> bool:
        """Whether a piece of what is left is left for another tool: not in
        front of the face (facing's), not a sliver nor the corner a nose
        leaves - this tool's or the one's before it."""
        if piece.is_empty or piece.area < MIN_AREA:
            return False
        if piece.bounds[0] >= self.profile[0][0] - TOLERANCE:
            return False
        sliver = max(self.tool.nose_radius if self.tool.known else 0.0, self.sliver_radius)
        return not piece.buffer(-max(0.05, sliver / 2)).is_empty

    def _result(self) -> RoughingPlan:
        remaining = self.remaining
        residual = []
        for piece in getattr(remaining, "geoms", [remaining]):
            if self._worth_cutting(piece):
                residual.append([self._m(p) for p in piece.exterior.coords])
        stock_after = _difference(self.material, _difference(self.to_remove, self.remaining))
        if residual:
            count = len(residual)
            self.warnings.append(f"{count} region{'' if count == 1 else 's'} left for another tool")
        return RoughingPlan(
            moves=self.moves,
            allowance=self.allowance_chain(),
            residual=residual,
            to_remove=_mirror(self.to_remove) if self.is_id else self.to_remove,
            remaining_stock=_mirror(stock_after) if self.is_id else stock_after,
            tool=self.tool,
            warnings=self.warnings,
        )


def _difference(a, b):
    """``a`` less ``b``. Cut by many moves, a shape picks up slivers GEOS
    cannot always work with; mended and tried again, they go away."""
    from shapely.errors import TopologicalError
    try:
        result = a.difference(b)
    except (TopologicalError, ValueError):
        result = a.buffer(0).difference(b.buffer(0))
    return result if result.is_valid else result.buffer(0)


def _mirror(shape):
    from shapely import affinity
    return affinity.scale(shape, xfact=1.0, yfact=-1.0, origin=(0, 0))


def _simplify(points: List[Pt]) -> List[Pt]:
    """Points in a straight line dropped, the rest kept."""
    if len(points) < 3:
        return points
    out = [points[0]]
    for i in range(1, len(points) - 1):
        a, b, c = out[-1], points[i], points[i + 1]
        cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cross) > 1e-9 * max(1.0, math.hypot(c[0] - a[0], c[1] - a[1])):
            out.append(b)
    out.append(points[-1])
    return out
