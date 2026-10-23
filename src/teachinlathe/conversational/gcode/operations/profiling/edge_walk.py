"""The stock's edge as the 45° passes walk it: points along it, the contour
along a stretch of it, and where on it the next pass starts - a depth of cut on
from the one before, square to the passes, or into what is left over a point
past a shoulder the passes before did not reach."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple

from shapely.geometry import LineString, Point

from .shapes import Pt, TOLERANCE, _intersection


class EdgeWalk:
    """``edge``: the points walked along, in the planning frame; ``touch``: for
    each stretch of it, where the nose touches as the canvas draws it (the
    profile's) or the stretch itself (the face at Z Start, X Start). A place
    on it is (i, t): ``t`` of the way along its stretch ``i``."""

    def __init__(self, planner, edge: List[Pt], touch: List[Tuple[Pt, Pt]]):
        self.planner = planner
        self.edge = edge
        self.touch = touch
        tool = planner.tool
        self.reach = (tool.nose_radius if tool.known else 0.0) + 0.1
        self.across = (1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0))   # square to the passes, off the profile
        # How far short of its control line, square to it, a pass cuts: at
        # 45° the control point lies outside the nose. What is left over a
        # point is measured to the edge the last pass left; less this, it is
        # measured to that pass's line - the depth of cut, as down X Start
        self.shortfall = max(0.0, min(e[0] * self.across[0] + e[1] * self.across[1]
                                      for e in planner.envelope))
        self.sample = min(0.2, planner.doc / 4.0)

    @staticmethod
    def level(p: Pt) -> float:
        """Constant along a pass: which of the parallel 45° lines ``p`` is on."""
        return p[0] + p[1]

    def at(self, i: int, t: float) -> Pt:
        a, b = self.edge[i], self.edge[i + 1]
        if t <= 0.0:
            return a
        if t >= 1.0:
            return b
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))

    def drawn_at(self, i: int, t: float) -> Pt:
        (a, b) = self.touch[i]
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))

    def along(self, i: int, t: float, k: int, u: float):
        """At the feed along the edge from (i, t) to (k, u), as a contour."""
        for j in range(i, k + 1):
            t0 = t if j == i else 0.0
            t1 = u if j == k else 1.0
            if t1 - t0 > 1e-12:
                self.planner._add_drawn(self.at(j, t0), self.at(j, t1), self.drawn_at(j, t0), self.drawn_at(j, t1))

    def thickness(self, p: Pt) -> float:
        """How thick what is left over ``p`` is, square to the passes: up
        to where it has been cut away already. Past a shoulder the passes
        before did not reach, that is the last one that did."""
        far = 3.0 * self.planner.doc + self.reach
        ray = LineString([p, (p[0] + self.across[0] * far, p[1] + self.across[1] * far)])
        left = _intersection(ray, self.planner.remaining)
        for piece in getattr(left, "geoms", [left]):
            if piece.is_empty or piece.length < TOLERANCE:
                continue
            coords = list(piece.coords)
            near = min(Point(c).distance(Point(p)) for c in coords)
            if near <= self.reach:
                return max(Point(c).distance(Point(p)) for c in coords) - self.shortfall
        return 0.0

    def depth(self, p: Pt, after: float, made: bool) -> float:
        """The depth a pass from ``p`` would cut: past the last pass's
        line (``after`` its level), or into what is left over it, the
        larger. With the last pass not made (``made`` False) nothing was
        cut there: past its line only, or the walk would stand still."""
        beyond = (after - self.level(p)) / math.sqrt(2.0)
        return max(beyond, self.thickness(p)) if made else beyond

    def next_start(self, i: int, t: float, after: float, made: bool) -> Optional[Tuple[int, float]]:
        """The first point on the edge after (i, t) a depth of cut deep."""
        doc = self.planner.doc
        for k in range(i, len(self.edge) - 1):
            u0 = t if k == i else 0.0
            a, b = self.edge[k], self.edge[k + 1]
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            if length < 1e-12:
                continue
            n = max(1, int(math.ceil((1.0 - u0) * length / self.sample)))
            lo = u0
            for j in range(1, n + 1):
                u = u0 + (1.0 - u0) * j / n
                if self.depth(self.at(k, u), after, made) >= doc - 1e-6:
                    for _ in range(12):
                        mid = (lo + u) / 2
                        if self.depth(self.at(k, mid), after, made) >= doc - 1e-6:
                            u = mid
                        else:
                            lo = mid
                    return k, u
                lo = u
        return None
