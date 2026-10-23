"""The profile's edge as the tool runs along it: the contour chain - the obstacle's
edge, carried on to Z Start along the axis - where the nose touches along it as
the canvas draws it, cuts drawn at the edge they leave, and the way up it from
where a pass ends to the pass before."""

from __future__ import annotations

import math

from typing import List, Tuple
from shapely.geometry import LineString, Point, Polygon

from .shapes import Pt, FAR, TOLERANCE, _simplify


class Edge:
    """The profile's edge as the tool runs along it - one part of _Planner (planner.py)."""

    def _extension_r(self) -> float:
        """The radius (mirrored frame) the contour runs out to Z Start at:
        no pass goes deeper than it in front of the face."""
        chain = self._contour_chain()
        return chain[0][1] if chain else min(r for _z, r in self.profile) + self.setup.stock_x

    def _contour_chain(self) -> List[Pt]:
        # the obstacle does not change: worked out once
        if getattr(self, "_chain", None) is None:
            self._chain = self._extended(self._boundary_chain(self.obstacle))
        return list(self._chain)

    def _extended(self, chain: List[Pt]) -> List[Pt]:
        """``chain`` carried on from the profile's face out to Z Start along
        the axis, at the diameter it starts at the face with - Z Start is the
        profile extended toward Z+ - rather than around the tool's shape."""
        if len(chain) < 2:
            return chain
        z_face = self.profile[0][0] + self.setup.stock_z
        if chain[0][0] > z_face + TOLERANCE:
            # in front of the face around the tool: from where it meets it
            for i in range(len(chain) - 1):
                a, b = chain[i], chain[i + 1]
                if b[0] <= z_face + TOLERANCE:
                    t = (a[0] - z_face) / (a[0] - b[0]) if a[0] - b[0] > 1e-12 else 1.0
                    face = (z_face, a[1] + t * (b[1] - a[1]))
                    near = math.hypot(b[0] - face[0], b[1] - face[1]) <= TOLERANCE
                    chain = [face] + chain[i + 2 if near else i + 1:]
                    break
        if chain[0][0] < self.z_start - TOLERANCE:
            chain = [(self.z_start, chain[0][1])] + chain
        return chain

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

    def _drawn(self, chain: List[Pt]) -> List[Tuple[Pt, Pt]]:
        """Where the nose touches along ``chain``, a pair of ends for each of
        its stretches: its centre, pushed its radius toward what it cuts -
        the obstacle lies to the left of the chain. On the profile that is
        the profile and its stock; where the tool bridges what it cannot
        enter, the edge of what it cuts.

        Each stretch is drawn parallel to its own, as the machine moves along
        it - a wall the tool runs straight along drawn straight - and joined
        to the next where the two lines meet (a mitre), each trimmed or
        carried on to there; only where they would meet further off than the
        nose is wide, at a very sharp turn, are they left apart."""
        pairs = list(zip(chain, chain[1:]))
        if not self.tool.known:
            return pairs
        centre = self._m(self.tool.centre)
        radius = self.tool.nose_radius
        normals = []
        for a, b in pairs:
            dz, dr = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dz, dr) or 1.0
            normals.append((-dr / length, dz / length))

        def pushed(p, n):
            return (p[0] + centre[0] + radius * n[0], p[1] + centre[1] + radius * n[1])

        drawn = [[pushed(a, n), pushed(b, n)] for (a, b), n in zip(pairs, normals)]
        for j in range(1, len(pairs)):
            p0, q0 = drawn[j - 1]
            p1, q1 = drawn[j]
            d0 = (q0[0] - p0[0], q0[1] - p0[1])
            d1 = (q1[0] - p1[0], q1[1] - p1[1])
            cross = d0[0] * d1[1] - d0[1] * d1[0]
            if abs(cross) < 1e-12:
                continue                       # in line: they meet already, or never
            # where the line of the one before meets the line of this one
            u = ((p1[0] - p0[0]) * d1[1] - (p1[1] - p0[1]) * d1[0]) / cross
            meet = (p0[0] + u * d0[0], p0[1] + u * d0[1])
            if math.hypot(meet[0] - q0[0], meet[1] - q0[1]) <= 2.0 * radius + TOLERANCE:
                drawn[j - 1][1] = drawn[j][0] = meet
        return [tuple(d) for d in drawn]

    def _add_drawn(self, a: Pt, b: Pt, da: Pt, db: Pt):
        self._add(a, b, True, pass_no=self.pass_no, contour=True)
        if self.moves and self.moves[-1].contour:
            self.moves[-1].drawn = (da[0], self.sign * da[1], db[0], self.sign * db[1])

    def _add_pass(self, a: Pt, b: Pt, toward: Pt = (-math.sqrt(0.5), -math.sqrt(0.5))):
        """A pass from ``a`` to ``b``, drawn at the edge it leaves: where the
        nose reaches furthest ``toward`` what is still to cut (a unit vector
        square to the pass; a 45° pass's by default) - not at the control
        point, which lies outside the nose wherever the pass ends against a
        slope or an arc."""
        self._add(a, b, True, pass_no=self.pass_no)
        if not self.tool.known or not self.moves:
            return
        centre = self._m(self.tool.centre)
        radius = self.tool.nose_radius
        dz, dr = centre[0] + radius * toward[0], centre[1] + radius * toward[1]
        self.moves[-1].drawn = (a[0] + dz, self.sign * (a[1] + dr), b[0] + dz, self.sign * (b[1] + dr))

    def _step_up(self, end: Pt, v_before: float, v_of) -> List[Tuple[Pt, Pt, Pt, Pt]]:
        """From ``end``, where a pass meets the profile, along the contour
        the way the level ``v_of`` comes back up, to ``v_before`` - the level
        of the pass before - or to where the profile turns away from it
        again: the stretches (a, b) with where the nose touches (da, db).
        None when the pass does not end on the contour."""
        chain = self._contour_chain()
        if len(chain) < 2:
            return []
        drawn = self._drawn(chain)
        best, at_i = None, -1
        for i, (a, b) in enumerate(zip(chain, chain[1:])):
            d = LineString([a, b]).distance(Point(end))
            if best is None or d < best:
                best, at_i = d, i
        if best is None or best > 1e-3:
            return []
        a, b = chain[at_i], chain[at_i + 1]
        length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        t = ((end[0] - a[0]) * (b[0] - a[0]) + (end[1] - a[1]) * (b[1] - a[1])) / (length * length)
        t = min(1.0, max(0.0, t))
        tol = 1e-9

        def point(i, u):
            p, q = chain[i], chain[i + 1]
            return (p[0] + u * (q[0] - p[0]), p[1] + u * (q[1] - p[1]))

        def touch(i, u):
            p, q = drawn[i]
            return (p[0] + u * (q[0] - p[0]), p[1] + u * (q[1] - p[1]))

        # which way along the chain the level comes back up
        forward = v_of(b) > v_of(end) + tol
        backward = v_of(a) > v_of(end) + tol
        if not forward and not backward:
            return []
        step = 1 if forward and (not backward or v_of(b) >= v_of(a)) else -1
        out = []
        i, u = at_i, t
        while 0 <= i < len(chain) - 1:
            u_to = 1.0 if step > 0 else 0.0
            here, there = point(i, u), point(i, u_to)
            if v_of(there) < v_of(here) - tol:
                break                          # turning away from it again
            if v_of(there) >= v_before - tol:
                span = v_of(there) - v_of(here)
                u_to = u + (u_to - u) * ((v_before - v_of(here)) / span if span > tol else 1.0)
                there = point(i, u_to)
                if math.hypot(there[0] - here[0], there[1] - here[1]) > 1e-9:
                    out.append((here, there, touch(i, u), touch(i, u_to)))
                break
            if math.hypot(there[0] - here[0], there[1] - here[1]) > 1e-9:
                out.append((here, there, touch(i, u), touch(i, u_to)))
            i += step
            u = 0.0 if step > 0 else 1.0
        return out
