"""Pockets: what the passes from the face do not reach, cut where the tool can be
plunged in."""

from __future__ import annotations

from shapely.geometry import LineString, Polygon

from .shapes import TOLERANCE, MIN_AREA, sweep, _difference


class Pockets:
    """Pockets - one part of _Planner (planner.py)."""

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
        # for ID along X, then along Z - not both at once
        if lifted[1] <= top and self._rapid_along(self._route(end, lifted)):
            self.position = lifted
        else:
            if self._rapid_clear(end, bottom):
                self._add(end, bottom, False)
            self._add(bottom, entry, False)
            self.position = entry
        self._end_pass()
