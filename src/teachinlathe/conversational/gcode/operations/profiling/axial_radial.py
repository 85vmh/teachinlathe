"""Axial and radial passes: one level at a time, each from the stock face until it
meets the profile, off it at 45° and back to the start point's Z (X, radial)."""

from __future__ import annotations

from shapely.geometry import Point

from .shapes import GRID, TOLERANCE


class AxialRadialPasses:
    """Axial and radial passes - one part of _Planner (planner.py)."""

    def _passes(self, at, u_start, u_far, v_start, v_end):
        """Passes along u, from u_start toward u_far (of the level), one level
        of v at a time from v_start down to v_end - (u, v) is (z, r) for
        axial passes and (r, z) for radial ones; ``at`` turns (u, v) into
        (z, r). Each one: in along v at the start point's u, along the pass,
        off it at 45° by the retract - for ID as for OD - and
        back along u to the start point's u, at the level just cut plus the
        retract. Where it cannot leave at 45° - the profile in the way - it
        goes on along the profile up to the level of the pass before, and
        off from there."""
        ret = self.retract
        position = self._start_at(self.start_point)
        v_of = (lambda p: p[1]) if at(0, 1)[1] == 1 else (lambda p: p[0])
        u_of = (lambda p: p[0]) if at(1, 0)[0] == 1 else (lambda p: p[1])
        # where the tool goes back to between passes, and in from: the start
        # point's u - never inside the stock face
        u_back = max(u_of(self.start_point), u_start)
        v_before = v_start                     # the level of the pass before
        for v in self._levels(v_start, v_end):
            start = at(u_start, v)
            runs = self._free_runs(start, at(u_far(v), v))
            if not runs and v == v_end:
                # the last level on the edge of what is planned - the end
                # wall for radial passes: a hair inside it
                v = v + 2 * TOLERANCE
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
            # in along v at the start point's u, then along u to the stock face
            entry = at(u_back, v)
            if not self._go(position, entry):
                continue
            # the lead-in at the feed when it touches material left there
            self._lead_in(entry, start)
            # drawn at the nose's edge toward the next level
            self._add_pass(start, end, at(0, -1))
            # off the cut at 45°, by the retract - for ID as for OD; the
            # profile in the way: on along it up to the level before, and off
            # from there
            leaves = self._rapid_clear(end, (end[0] + ret, end[1] + ret))
            if not leaves:
                for a, b, da, db in self._step_up(end, v_before, v_of):
                    self._add_drawn(a, b, da, db)
                    end = b
            off = (end[0] + ret, end[1] + ret)
            v_before = v
            self.pass_no += 1
            if leaves or self._rapid_clear(end, off):
                self._add(end, off, False)
                position = off
            else:
                position = end
            # back along u to the start point's u, at the level it left off at
            back = at(u_back, v_of(position))
            if self._rapid_clear(position, back):
                self._add(position, back, False)
                position = back
            else:
                position = self._lift(position)
            self._end_pass()
        self.position = position
