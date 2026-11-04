"""The contour pass that finishes a roughing: along the profile, offset by the stock
to leave and compensated for the nose."""

from __future__ import annotations

from teachinlathe.conversational.model.data_types import PassType

from .shapes import Pt


class FinalContour:
    """The contour that finishes a roughing - one part of _Planner (planner.py)."""

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
        From the top of the profile's start to its end point - after radial
        passes the other way round, from its end out to Z Start."""
        if len(chain) < 2:
            self.warnings.append("no contour: the tool reaches none of the profile")
            return
        drawn = self._drawn(chain)
        approach = self._contour_approach(chain)
        segments = [(a, b, da, db) for (a, b), (da, db) in zip(zip(chain, chain[1:]), drawn)]
        if not self.rest:
            if self.setup.pass_type in (PassType.RADIAL, PassType.DIAGONAL_INTERIOR,
                                        PassType.DIAGONAL_EXTERIOR):
                # after radial and 45° passes from the back to the front: in
                # at the profile's end, along it toward Z+ and out to Z Start
                start, end, where = chain[-1], chain[0], "end"
                cuts = [(b, a, db, da) for a, b, da, db in reversed(segments)]
            else:
                # from the front: in along the axis to the profile's start,
                # drawn where the nose touches, as the chain is
                start, end, where = approach, chain[-1], "start"
                touch = (approach[0] + drawn[0][0][0] - chain[0][0],
                         approach[1] + drawn[0][0][1] - chain[0][1])
                cuts = [(approach, chain[0], touch, drawn[0][0])] + segments
            if not self._go_x_then_z(self.position, start):
                self.warnings.append(f"no contour: no clear way to its {where}")
                return
            for a, b, da, db in cuts:
                self._add_drawn(a, b, da, db)
            self.pass_no += 1
            self.position = self._lift(end)
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
