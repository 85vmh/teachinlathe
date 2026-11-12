"""What the plot does while the run is away from the work - at the tool change
position for an M6, at G28 or G30 for Pause to Inspect (programs.model
.excursions) - and as it comes back.

Away, the tool offsets show (the TLO button's drawing) whether the button is
on or not, till the tool starts back - unless the operator turns them off
for that trip. As it goes, the view zooms out, in a short animation, to take
in the target as well as what was on screen; on the way back it zooms in
again as the tool nears the work, to be the view of before it left once it
is back. A zoom, a pan or a fit by hand leaves the view to the operator for
the rest of the trip. The views are ortho_view's.
"""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from teachinlathe.programs.model.excursions import ExcursionMoment, Phase
from teachinlathe.ui.tabs.programs.backplot.ortho_view import View, between, copy

#: How long the zoom out takes, seconds.
ZOOM_OUT_SECONDS = 0.4


class ExcursionView:
    """Follows the run's trips away, for one plot."""

    def __init__(self):
        self._phase: Optional[Phase] = None
        self._saved: Optional[View] = None      # the view before it went away
        self._away: Optional[View] = None       # the view zoomed out
        self._touched = False                   # the operator moved the view
        self._animation: Optional[Tuple[float, View, View]] = None
        self._offsets_dismissed = False

    @property
    def show_offsets(self) -> bool:
        """Whether the trip shows the tool offsets now: on the way there and
        there, till the tool starts back."""
        return self._phase is Phase.AWAY and not self._offsets_dismissed

    def dismiss_offsets(self) -> None:
        """The operator turned the tool offsets off: off for this trip."""
        if self._phase is Phase.AWAY:
            self._offsets_dismissed = True

    def touched(self) -> None:
        """The operator zoomed, panned or fitted the view: the trip leaves it
        to them."""
        if self._phase is not None:
            self._touched = True
            self._animation = None

    def update(self, moment: Optional[ExcursionMoment], view: View,
               zoomed_out: Callable[[], Optional[View]], now: float) -> Optional[View]:
        """The run at ``moment`` (None: on no trip), the plot showing
        ``view``; ``zoomed_out()`` makes the view that takes in the target.
        Returns the view to show, None to leave it as it is."""
        phase = moment.phase if moment is not None else None
        before, self._phase = self._phase, phase

        if phase is None:
            if before is None:
                return None
            back = None if self._touched else self._saved
            self._saved = self._away = self._animation = None
            self._touched = self._offsets_dismissed = False
            return back

        if phase is Phase.AWAY and before is not Phase.AWAY:
            # a new trip: from the view of before - the one of before the
            # last trip, if it is not back in it yet and the view was not moved
            if before is None or self._touched or self._saved is None:
                self._saved = copy(view)
            self._touched = self._offsets_dismissed = False
            self._away = zoomed_out()
            self._animation = (now, copy(view), self._away) if self._away is not None else None

        if self._touched or self._away is None or self._saved is None:
            return None

        if phase is Phase.AWAY:
            if self._animation is None:
                return None
            started, start, end = self._animation
            t = (now - started) / ZOOM_OUT_SECONDS
            if t >= 1.0:
                self._animation = None
                return end
            return between(start, end, _ease(t))

        # on its way back: from the zoomed out view to the one of before
        self._animation = None
        return between(self._away, self._saved, moment.progress)



def _ease(t: float) -> float:
    """Slow out of the start and into the end."""
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)
