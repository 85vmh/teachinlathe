"""Axial and radial passes: one level at a time, each from the stock face until it
meets the profile, then along it to the level of the pass before."""

from __future__ import annotations

from shapely.geometry import Point

from .shapes import GRID


class AxialRadialPasses:
    """Axial and radial passes - one part of _Planner (planner.py)."""

    def _passes(self, at, u_start, u_far, v_start, v_end):
        """Passes along u, from u_start toward u_far (of the level), one level
        of v at a time from v_start down to v_end - (u, v) is (z, r) for
        axial passes and (r, z) for radial ones; ``at`` turns (u, v) into
        (z, r). Where a pass ends on the profile it goes on along it, a
        contour, back up to the level of the pass before - the step between
        them cut there, not left to the contour at the end."""
        ret = self.retract
        position = self._start_at(at(u_start + ret, v_start + ret))
        v_of = (lambda p: p[1]) if at(0, 1)[1] == 1 else (lambda p: p[0])
        v_before = v_start                     # the level of the pass before
        for v in self._levels(v_start, v_end):
            start = at(u_start, v)
            runs = self._free_runs(start, at(u_far(v), v))
            if not runs or Point(runs[0][0]).distance(Point(start)) > GRID:
                continue                       # the stock face is out of reach here
            end = runs[0][1]
            if not self._cuts(start, end):
                continue
            if not self._feed_clear(start, end):
                self.warnings.append(f"pass at {v:.3f} skipped: it would cut into the stock to leave")
                continue
            u_end = end[0] if at(1, 0)[0] == 1 else end[1]
            # in along the pass's own axis - for ID from a retract in front of
            # its start only, got to along the axes; for OD off both
            entry = at(u_start + ret, v) if self.is_id else at(u_start + ret, v + ret)
            exit_ = at(u_end + ret, v + ret)
            if not self._go(position, entry):
                continue
            # the lead-in at the feed when it touches material left there
            self._lead_in(entry, start)
            # drawn at the nose's edge toward the next level
            self._add_pass(start, end, at(0, -1))
            # on along the profile up to the level before, when it ends on it
            for a, b, da, db in self._step_up(end, v_before, v_of):
                self._add_drawn(a, b, da, db)
                end = b
                exit_ = (b[0] + ret, b[1] + ret)
            v_before = v
            self.pass_no += 1
            # off the cut: for ID along X, then along Z - not both at once
            position = exit_ if self._rapid_along(self._route(end, exit_)) else end
            # straight back out, at the level it left off at
            back = at(u_start + ret, v_of(position))
            if self._rapid_clear(position, back):
                self._add(position, back, False)
                position = back
            else:
                position = self._lift(position)
            self._end_pass()
        self.position = position
