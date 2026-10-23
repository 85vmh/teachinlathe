"""How the tool gets about between cuts: rapids by the first clear route - for ID
along X first, then along Z - onto the profile beside a point, and out to the
safe diameter."""

from __future__ import annotations

from typing import List

from .shapes import Pt


class Moves:
    """How the tool gets about between cuts - one part of _Planner (planner.py)."""

    # ── the rules every move keeps to ──────────────────────────────────────

    @staticmethod
    def _x_then_z(a: Pt, b: Pt) -> List[Pt]:
        """From ``a`` to ``b`` along X first, then along Z."""
        return [a, (a[0], b[1]), b]

    def _route(self, a: Pt, b: Pt) -> List[Pt]:
        """From ``a`` to ``b`` as the tool may go there at once: for ID along X
        first, then along Z, never both together; for OD straight."""
        return self._x_then_z(a, b) if self.is_id else [a, b]

    def _rapid_along(self, route: List[Pt]) -> bool:
        """The rapids along ``route`` when every leg of it is clear - a leg of
        no length is no move; nothing, and False, when one is not."""
        legs = list(zip(route, route[1:]))
        if not all(self._rapid_clear(p, q) for p, q in legs):
            return False
        for p, q in legs:
            self._add(p, q, False)
        return True

    def _first_clear(self, here: Pt, points: List[Pt]):
        """The first of ``points`` a rapid from ``here`` reaches clear, or None."""
        return next((p for p in points if self._rapid_clear(here, p)), None)

    def _off_face(self, p: Pt) -> Pt:
        """A retract off ``p`` along Z, toward the face."""
        return (p[0] + self.retract, p[1])

    def _off_start(self, p: Pt) -> Pt:
        """A retract off ``p`` along X, toward X Start."""
        return (p[0], p[1] + self.retract)

    def _lead_in(self, a: Pt, b: Pt):
        """In from ``a`` to ``b``, where a cut starts: at the feed when it
        touches material left there, else a rapid."""
        self._add(a, b, not self._rapid_clear(a, b), pass_no=self.pass_no)

    # ── getting about ───────────────────────────────────────────────────────

    def _go(self, a: Pt, b: Pt):
        """Rapid from ``a`` to ``b`` by the first of these whose every leg is
        clear: straight - for ID along X first, then along Z, never both at
        once; out in front of the face at this diameter, along it, in; out to
        the safe diameter, across, in; out, over to the safe Z in front of the
        face, along it, in. False, and no move, when none is."""
        z_safe = self.z_start + self.retract
        routes = [
            self._route(a, b),
            [a, (z_safe, a[1]), (z_safe, b[1]), b],
            [a, (a[0], self.r_safe), (b[0], self.r_safe), b],
            [a, (a[0], self.r_safe), (z_safe, self.r_safe), (z_safe, b[1]), b],
        ]
        for route in routes:
            if self._rapid_along(route):
                return True
        # nothing gets there without going through material: no rapid at all,
        # the move it was for is not made
        return False

    def _go_x_then_z(self, a: Pt, b: Pt):
        """Rapid from ``a`` to ``b`` along X first, then along Z - never both
        at once - when both legs are clear; else as _go finds a way."""
        return self._rapid_along(self._x_then_z(a, b)) or self._go(a, b)

    def _back_onto(self, here: Pt, p: Pt, beside: List[Pt]) -> bool:
        """The tool from ``here`` onto ``p`` on the profile, by one of the
        points ``beside`` it - in at the feed from there. True when it is."""
        for near in beside:
            if here == near or self._go(here, near):
                self._lead_in(near, p)
                return True
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
