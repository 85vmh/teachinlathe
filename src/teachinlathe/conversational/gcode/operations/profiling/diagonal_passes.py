"""Diagonal passes - at DIAGONAL_ANGLE from the Z axis, 45° by default: walked
along the stock's edge - its face and the profile, or X Start and the profile
back - a depth of cut on from one to the next."""

from __future__ import annotations

import math

from shapely.geometry import LineString, box
from teachinlathe.conversational.model.data_types import PassType

from .geometry import RESOLUTION
from .shapes import FAR, TOLERANCE
from .edge_walk import EdgeWalk


class DiagonalPasses:
    """Diagonal passes - one part of _Planner (planner.py)."""

    def _diagonal_off_face(self, p):
        """Off ``p`` along Z, toward the face, by as much as keeps the way
        back alongside a pass parallel to it: the retract at 45°."""
        return (p[0] + self.retract * math.sqrt(0.5) / self.diagonal_sin, p[1])

    def _diagonal_off_start(self, p):
        """Off ``p`` along X, toward X Start, likewise: the retract at 45°.
        Both lie a retract times sin 45° off the pass, square to it."""
        return (p[0], p[1] + self.retract * math.sqrt(0.5) / self.diagonal_cos)

    def _diagonal_passes(self):
        """45° passes on fixed lines from the X Start corner, each run from the
        stock edge until it meets the obstacle, and toward the profile's
        largest diameter no further than it (less the radial stock). What a
        rest roughing cuts with 45° passes, the walk along the profile
        (_diagonal_passes_along_profile) needing the bar whole.

        Each pass comes in and leaves along an axis, a retract off its ends:
        at its end on the face side along Z, at its end on the X Start side
        along X. Between the two, back the way it cut, a retract off it - in
        line with both - for the next pass."""
        ret = self.retract
        z_min, r_min = self._z_min(), self._r_min()
        r_limit = min(r for _z, r in self.profile) + self.setup.stock_x
        span = max(self.r_start - r_min, self.z_start - z_min)
        position = self._start_at((self.z_start + ret, self.r_safe))
        toward_x_start = self.setup.pass_type == PassType.DIAGONAL_INTERIOR
        off_face, off_start = self._diagonal_off_face, self._diagonal_off_start

        step = self.doc
        while step < 2 * span + self.doc:
            b = (self.z_start, self.r_start - step)            # face side
            far_a = (b[0] - FAR * self.diagonal_cos, b[1] + FAR * self.diagonal_sin)
            far_b = (b[0] + FAR * self.diagonal_cos, b[1] - FAR * self.diagonal_sin)
            # from the X Start side down toward the face, inside the stock box
            segment = LineString([far_a, far_b]).intersection(
                box(z_min - 1.0, r_limit, self.z_start, self.r_start))
            step += self.doc
            if segment.is_empty or segment.length < TOLERANCE:
                continue
            p, q = list(segment.coords)[0], list(segment.coords)[-1]
            if p[1] < q[1]:
                p, q = q, p                                    # p: the outer end
            for run in self._free_runs(p, q):
                # run[0] on the X Start side, run[1] on the face side
                if toward_x_start:
                    start, end = run[1], run[0]
                    entry, exit_ = off_face(start), off_start(end)
                else:
                    start, end = run
                    entry, exit_ = off_start(start), off_face(end)
                if not self._cuts(start, end) or not self._feed_clear(start, end):
                    continue
                if not self._go(position, entry):
                    continue
                self._lead_in(entry, start)
                self._add_pass(start, end)
                self.pass_no += 1
                position = self._leave_pass(start, end, [exit_], [entry])
                break
        self.position = position

    def _diagonal_passes_along_profile(self):
        """45° passes, each on a line through a point on the edge of the
        stock: down its face at Z Start, then out along the profile - offset
        by the stock to leave, compensated, carried on to Z Start along the
        axis - each a depth of cut (square to the passes) on from the one
        before. Each runs between that point and the X Start diameter, or
        where it meets the profile before it.

        Toward the X Start side - toward the interior, ↖ (DIAGONAL_INTERIOR) -
        a pass starts at its
        point. Down the face it comes in along Z, a retract in front of it; on
        the profile it comes from where the pass before it started, along the
        profile at the feed, a contour, to its own start. Each leaves along X,
        a retract off its end, and comes back the way it cut, a retract off
        it, to the diameter it started at, a retract in front of its start.

        Toward the profile - toward the exterior, ↘ (DIAGONAL_EXTERIOR) - the
        edge is walked the other
        way round: along the X Start diameter toward Z- to over the profile's
        end, then back along the profile toward the face - into what the
        passes from X Start do not reach behind a shoulder. A pass starts at
        its point and runs toward the face until it meets the profile or Z
        Start. On X Start it comes in along X, a retract over it; on the
        profile it comes from where the pass before it started, along the
        profile, a contour. Each leaves along Z by a retract - along X where
        Z is in the way - and comes back the way it cut, a retract off it, to
        its start.

        With no point on the profile a depth of cut on from the last pass,
        the contour goes on from where that pass started to the profile's
        end: the profile is then contoured whole, a stretch at a time. True
        when it is, False when the tool could not get on with it (the contour
        is then still to do, from the start)."""
        chain = self._contour_chain()
        if self.rest or len(chain) < 2:
            self._diagonal_passes()
            return False
        toward_x_start = self.setup.pass_type == PassType.DIAGONAL_INTERIOR
        walk = self._edge_walk(chain, toward_x_start)
        position = self._start_at((self.z_start + self.retract, self.r_safe))
        if toward_x_start:
            return self._walk_toward_x_start(walk, position)
        return self._walk_toward_profile(walk, position)

    def _edge_walk(self, chain, toward_x_start: bool) -> EdgeWalk:
        """The edge the passes are walked along, and each stretch of it as
        drawn: the profile's where the nose touches it, the face at Z Start
        and X Start where they are. Toward X Start: down the face, then the
        profile; toward the profile: along X Start to over the profile's end,
        then back along it."""
        profile_drawn = self._drawn(chain)
        if toward_x_start:
            edge = [(self.z_start, self.r_start)] + chain
            touch = [(edge[0], edge[1])] + profile_drawn
        else:
            over_end = (chain[-1][0], self.r_start)
            back_along = list(reversed(chain))
            touch = [((self.z_start, self.r_start), over_end)]
            if math.hypot(back_along[0][0] - over_end[0], back_along[0][1] - over_end[1]) <= TOLERANCE:
                back_along = back_along[1:]
            else:
                touch.append((over_end, back_along[0]))
            touch += [(db, da) for da, db in reversed(profile_drawn)]
            edge = [(self.z_start, self.r_start), over_end] + back_along
        return EdgeWalk(self, edge, touch)

    def _walk_toward_x_start(self, walk: EdgeWalk, position) -> bool:
        """The passes toward X Start (↖) along ``walk``, and the contour a
        stretch at a time - see _diagonal_passes_along_profile."""
        level, at, along, next_start, edge = walk.level, walk.at, walk.along, walk.next_start, walk.edge
        off_face, off_start = self._diagonal_off_face, self._diagonal_off_start

        def on_face(p):
            return p[0] >= self.z_start - TOLERANCE

        i, t = 0, 0.0
        prev = edge[0]
        after = level(prev)
        here = position                      # where the tool is
        made = True                          # the last pass cut what it was for
        while True:
            found = next_start(i, t, after, made)
            if found is None:
                break
            k, u = found
            start = at(k, u)
            if on_face(start):
                entry = off_face(start)
                if not self._go(here, entry):
                    i, t, prev, after = k, u, start, level(start)
                    made = False
                    continue
                self._lead_in(entry, start)
            else:
                if here != prev and not self._back_onto(here, prev, [off_face(prev), off_start(prev)]):
                    # no way back onto the profile where the last pass
                    # started: on to this one's start over the cut instead,
                    # the stretch between them left to the contour
                    if not self._go(here, off_face(start)):
                        i, t, prev, after = k, u, start, level(start)
                        made = False
                        continue
                    self._lead_in(off_face(start), start)
                else:
                    # along the profile, from where the last pass started to this one
                    along(i, t, k, u)
            here = start
            i, t, prev, after = k, u, start, level(start)
            made = False
            if start[1] >= self.r_start - TOLERANCE:
                continue
            far = (start[0] - (self.r_start - start[1]) * self.diagonal_cos / self.diagonal_sin, self.r_start)
            runs = self._free_runs(start, far)
            if not runs or math.hypot(runs[0][0][0] - start[0], runs[0][0][1] - start[1]) > RESOLUTION:
                continue                     # the profile in the way straight away
            end = runs[0][1]
            if not self._cuts(start, end) or not self._feed_clear(start, end):
                continue
            self._add_pass(start, end)
            self.pass_no += 1
            made = True
            # off its end along X - along Z where it ends against the profile
            # and X is in the way: either way on the line back, a retract off
            # the pass
            # - in front of its start, or where the profile is in the way
            # there, over it; failing both, back down the cut itself
            here = self._leave_pass(start, end, [off_start(end), off_face(end)],
                                    [off_face(start), off_start(start)], down_the_cut=True)
        # on from where the last pass started, to the profile's end
        if here != prev and not self._back_onto(here, prev, [off_face(prev), off_start(prev)]):
            self.position = here
            return False
        along(i, t, len(edge) - 2, 1.0)
        self.pass_no += 1
        self.position = self._lift(edge[-1])
        return True

    def _walk_toward_profile(self, walk: EdgeWalk, position) -> bool:
        """The passes toward the profile (↘) along ``walk`` - X Start, then the
        profile back toward the face (see _diagonal_passes_along_profile) -
        and the contour, a stretch at a time. True when the profile is
        contoured whole, False when the tool could not get on with it."""
        level, at, along, next_start, edge = walk.level, walk.at, walk.along, walk.next_start, walk.edge
        off_face, off_start = self._diagonal_off_face, self._diagonal_off_start

        # no deeper than the contour runs out to Z Start, in front of the face
        r_limit = max(min(r for _z, r in self.profile) + self.setup.stock_x, self._extension_r())

        def on_x_start(i):
            return i == 0

        def onto_profile(here):
            """From over X Start down onto the profile's end, at its start."""
            if not self._go(here, off_start(edge[1])):
                return None
            self._lead_in(off_start(edge[1]), edge[1])
            return edge[1]

        def back_to(here, p):
            """Back to ``p`` on the profile, from just off it - or around."""
            if here == p:
                return p
            near = math.hypot(here[0] - p[0], here[1] - p[1]) <= 1.5 * self.retract + TOLERANCE
            if not near:
                if not self._go(here, off_start(p)):
                    return None
                here = off_start(p)
            self._lead_in(here, p)
            return p

        i, t = 0, 0.0
        prev = edge[0]
        after = level(prev)
        here = position
        made = True
        while True:
            found = next_start(i, t, after, made)
            if found is None:
                break
            k, u = found
            start = at(k, u)
            # to its start: over it on X Start, or along the profile
            if on_x_start(k):
                entry = off_start(start)
                ready = self._go(here, entry)
                if ready:
                    here = entry
            else:
                if on_x_start(i):
                    here = onto_profile(here)
                    from_i, from_t = 1, 0.0
                else:
                    here = back_to(here, prev)
                    from_i, from_t = i, t
                if here is None:
                    self.position = position
                    return False
                along(from_i, from_t, k, u)
                here = start
                ready = True
            i, t, prev, after = k, u, start, level(start)
            made = False
            if not ready or start[0] >= self.z_start - TOLERANCE:
                continue
            # toward the face, until the profile, Z Start or the profile's
            # largest diameter (less the radial stock), whichever comes first
            z_to = min(self.z_start, start[0] + (start[1] - r_limit) * self.diagonal_cos / self.diagonal_sin)
            if z_to <= start[0] + TOLERANCE:
                continue
            runs = self._free_runs(start, (z_to, start[1] - (z_to - start[0]) * self.diagonal_sin / self.diagonal_cos))
            if not runs or math.hypot(runs[0][0][0] - start[0], runs[0][0][1] - start[1]) > RESOLUTION:
                continue                     # the profile in the way straight away
            end = runs[0][1]
            if not self._cuts(start, end) or not self._feed_clear(start, end):
                continue
            if here != start:
                self._lead_in(here, start)
            self._add_pass(start, end)
            self.pass_no += 1
            made = True
            # off its end along Z - along X where Z is in the way - and back
            # the way it cut, a retract off it, to its start
            here = self._leave_pass(start, end, [off_face(end), off_start(end)],
                                    [off_start(start), off_face(start)])
        # the contour, on to the face from where the last pass started
        if on_x_start(i):
            here = onto_profile(here)
            from_i, from_t = 1, 0.0
        else:
            here = back_to(here, prev)
            from_i, from_t = i, t
        if here is None:
            self.position = position
            return False
        along(from_i, from_t, len(edge) - 2, 1.0)
        self.pass_no += 1
        self.position = self._lift(edge[-1])
        return True
