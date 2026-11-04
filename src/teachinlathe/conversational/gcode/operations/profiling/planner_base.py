"""The roughing planner's state - the part, the obstacle, what is still to cut -
the checks every move goes through, and the plan put together and its result."""

from __future__ import annotations

import math

from typing import List, Optional, Tuple
from shapely.affinity import translate
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import unary_union
from teachinlathe.conversational.model.data_types import PassType, ProfilingType

from .geometry import ROUNDING
from .shapes import Pt, FAR, TOLERANCE, MIN_AREA, MIN_CUT, MIN_SLIVER, minkowski, path_points, _difference, _intersection, _mirror
from .tool_shape import square_tool
from .plan import Move, RoughingPlan


class PlannerBase:
    """The planner's state and the checks every move goes through - one part of _Planner (planner.py)."""

    def __init__(self, setup, profile_path, tool, stock_before, rest=False, sliver_radius=0.0, air_before=None):
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
        # the diagonal passes run along (-cos, sin) - toward Z- and X Start -
        # and the other way; (sin, cos) is square to them
        angle = math.radians(setup.diagonal_angle)
        self.diagonal_sin, self.diagonal_cos = math.sin(angle), math.cos(angle)

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

        known_air = air_before is not None and not air_before.is_empty
        if stock_before is None:
            # as deep as the profile goes and no deeper: what is in front of
            # the face below that is facing's to cut
            r_floor = min(r for _z, r in points)
            material = box(points[-1][0] + setup.stock_z, r_floor, self.z_start, self.r_start)
            z_face, r_face = points[0]
            if r_face > r_floor:
                material = material.difference(box(z_face, r_floor, self.z_start + 1.0, r_face))
            if known_air:
                # less what the operations above are known to have cut
                material = _difference(material, _mirror(air_before) if self.is_id else air_before)
        else:
            material = _mirror(stock_before) if self.is_id else stock_before
        from_other = stock_before is not None or known_air
        if from_other:
            # what another operation left, without the rounding slivers its
            # cuts leave along their edges
            material = material.buffer(-MIN_CUT).buffer(MIN_CUT)
        self.material = material
        self.to_remove = _difference(material, self.part_allow)
        if from_other:
            # only what the roughing before reports as left (see _result)
            self.to_remove = unary_union([
                piece for piece in getattr(self.to_remove, "geoms", [self.to_remove])
                if self._worth_cutting(piece)]) if not self.to_remove.is_empty else self.to_remove
        self.remaining = self.to_remove
        # the insert, as one polygon: every move's sweep is it, moved
        self._envelope_polygon = Polygon(self.envelope)
        self.moves: List[Move] = []
        self.pass_no = 0
        self.warnings: List[str] = []
        # where the tool is between the strategies (None until the first is
        # under way), and the contour chain once worked out (edge.py)
        self.position: Optional[Pt] = None
        self._chain: Optional[List[Pt]] = None

    # mirrored frame <-> machine
    def _m(self, p: Pt) -> Pt:
        return p[0], self.sign * p[1]

    def _part(self, points):
        """The finished part below the profile, carried on at its last
        diameter past its far end, toward the chuck."""
        z0, zn = points[0][0], points[-1][0]
        outline = points + [(zn - FAR, points[-1][1]), (zn - FAR, -FAR), (z0, -FAR)]
        return Polygon(outline).buffer(0)

    @property
    def remaining(self):
        """What is still to cut: the material less every cut made so far -
        the cuts since it was last asked for taken off together, now."""
        if self._pending:
            self._remaining = _difference(self._remaining, unary_union(self._pending))
            self._pending = []
        return self._remaining

    @remaining.setter
    def remaining(self, shape):
        self._remaining = shape
        self._pending = []

    def _sweep(self, a: Pt, b: Pt):
        """What the insert covers moving from ``a`` to ``b``: its polygon at
        both ends, and between them - its outline built once, only moved."""
        p = self._envelope_polygon
        return unary_union([translate(p, a[0], a[1]), translate(p, b[0], b[1])]).convex_hull

    def _start_at(self, p: Pt) -> Pt:
        """The plan's first position, ``p``: a move to it from nowhere."""
        self.moves.append(Move(p[0], self.sign * p[1], p[0], self.sign * p[1], False))
        return p

    def _end_pass(self):
        if self.moves:
            self.moves[-1].pass_end = True

    def _add(self, a: Pt, b: Pt, feed: bool, **kind):
        if math.hypot(b[0] - a[0], b[1] - a[1]) < ROUNDING:
            return
        if feed:
            # taken off when what is left is next asked for - a run of cuts
            # in one go, not one difference each
            self._pending.append(self._sweep(a, b))
        self.moves.append(Move(a[0], self.sign * a[1], b[0], self.sign * b[1], feed, **kind))

    def _rapid_clear(self, a: Pt, b: Pt) -> bool:
        """Whether a rapid from ``a`` to ``b`` meets neither the part - with
        the stock it is to be left with, material as much as the rest - nor
        the material still to cut."""
        swept = self._sweep(a, b)
        return (_intersection(swept, self.remaining).area < MIN_AREA
                and _intersection(swept, self.part_allow_inside).area < MIN_AREA)

    def _feed_clear(self, a: Pt, b: Pt) -> bool:
        """Whether a cut from ``a`` to ``b`` stays off the stock to leave."""
        swept = self._sweep(a, b)
        return _intersection(swept, self.part_allow_inside).area < MIN_AREA

    def _removes(self, a: Pt, b: Pt) -> float:
        return _intersection(self._sweep(a, b), self.remaining).area

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

    def _wrong_way_round(self) -> Optional[RoughingPlan]:
        """The plan's error when the tool cannot cut this side of the part,
        else None. The insert has to stand on its control point: nothing of it
        under the point it is programmed to (over it, for ID). A tool held the
        other way round - an OD tool on an ID profile - cannot cut this."""
        if min(r for _z, r in self.envelope) < -max(MIN_SLIVER, self.tool.nose_radius):
            side = "away from the axis" if self.is_id else "toward the axis"
            return RoughingPlan(tool=self.tool, error=(
                f"{self.tool.label}: its tip does not point {side} - "
                "check the tool's orientation"))
        return None

    def plan(self) -> RoughingPlan:
        wrong = self._wrong_way_round()
        if wrong is not None:
            return wrong
        if not self.tool.known:
            self.warnings.append("No turning tool chosen: roughing only what "
                                 "any tool reaches, pockets and undercuts left")
        if self.setup.pass_type == PassType.RADIAL:
            # in front of the face no deeper than the contour runs out to Z
            # Start; behind it the profile stops them
            z_face = self.profile[0][0] + self.setup.stock_z
            self._passes(lambda u, v: (v, u), u_start=self.r_start,
                         u_far=lambda v: self._extension_r() if v > z_face + TOLERANCE else self._r_min() - 1.0,
                         v_start=self.z_start, v_end=self._z_min())
        elif self.setup.pass_type in (PassType.DIAGONAL_INTERIOR, PassType.DIAGONAL_EXTERIOR):
            self._diagonal_passes_along_profile()
        else:
            # no level deeper than the contour runs out to Z Start: one would
            # cut only in front of the face, past it
            self._passes(lambda u, v: (u, v), u_start=self.z_start, u_far=lambda v: self._z_min() - 1.0,
                         v_start=self.r_start, v_end=max(self._r_min(), self._extension_r()))
        chain = self._contour_chain()
        # 45° passes leave nothing to be cut along the axes
        if self.setup.pass_type not in (PassType.DIAGONAL_INTERIOR, PassType.DIAGONAL_EXTERIOR):
            self._pockets(chain)
        # after the 45° passes - the profile contoured along the way - a
        # contour of its own still, from the back to the front
        self._contour(chain)
        return self._result()

    def plan_contour_only(self) -> RoughingPlan:
        """The contour alone - Profile Contour: from Z Start along the profile,
        offset by the stock to leave, compensated for the nose, bridged over
        what the tool cannot enter - the rest roughed already."""
        wrong = self._wrong_way_round()
        if wrong is not None:
            return wrong
        if not self.tool.known:
            self.warnings.append("No turning tool chosen: the contour keeps to what "
                                 "any tool reaches, pockets and undercuts bridged")
        self.position = self._start_at((self.z_start + self.retract, self.r_safe))
        self._contour(self._contour_chain())
        return self._result()

    def _z_min(self):
        return self.to_remove.bounds[0] if not self.to_remove.is_empty else self.z_start

    def _r_min(self):
        return self.to_remove.bounds[1] if not self.to_remove.is_empty else self.r_start

    def _levels(self, v_start, v_end):
        levels, k = [], 1
        while v_start - k * self.doc > v_end - ROUNDING:
            levels.append(v_start - k * self.doc)
            k += 1
        if not levels or levels[-1] > v_end + TOLERANCE:
            levels.append(v_end)
        return levels

    def _label(self, p: Pt) -> str:
        return f"X{2 * self.sign * p[1]:.3f} Z{p[0]:.3f}"

    def _worth_cutting(self, piece) -> bool:
        """Whether a piece of what is left is left for another tool: not in
        front of the face (facing's), not a sliver nor the corner a nose
        leaves - this tool's or the one's before it."""
        if piece.is_empty or piece.area < MIN_AREA:
            return False
        if piece.bounds[0] >= self.profile[0][0] - TOLERANCE:
            return False
        sliver = max(self.tool.nose_radius if self.tool.known else 0.0, self.sliver_radius)
        return not piece.buffer(-max(MIN_SLIVER, sliver / 2)).is_empty

    def _result(self) -> RoughingPlan:
        remaining = self.remaining
        residual = []
        for piece in getattr(remaining, "geoms", [remaining]):
            if self._worth_cutting(piece):
                residual.append([self._m(p) for p in piece.exterior.coords])
        if residual:
            count = len(residual)
            self.warnings.append(f"{count} region{'' if count == 1 else 's'} left for another tool")
        return RoughingPlan(
            moves=self.moves,
            allowance=self.allowance_chain(),
            residual=residual,
            to_remove=_mirror(self.to_remove) if self.is_id else self.to_remove,
            tool=self.tool,
            warnings=self.warnings,
        )
