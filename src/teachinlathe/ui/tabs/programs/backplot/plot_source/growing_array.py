"""A numpy array that grows at its end and drops at its front, as the position
logger's buffer does: what the trail notes for each point (plot_source.trail)
and the points the plot draws (actors.trail) follow the logger with it."""

from __future__ import annotations

import numpy as np


class GrowingArray:
    """A numpy array that grows at its end without being copied each time -
    its storage doubles - and drops points at its front (``drop_front``), as
    the position logger's buffer does."""

    def __init__(self, dtype):
        self._a = np.zeros(0, dtype=dtype)
        self.n = 0

    def resize(self, n: int):
        """``n`` long - what was there kept - and the whole of it, a view."""
        if n > len(self._a):
            grown = np.zeros(max(n, 2 * len(self._a), 1024), dtype=self._a.dtype)
            grown[:self.n] = self._a[:self.n]
            self._a = grown
        self.n = n
        return self._a[:n]

    def view(self):
        return self._a[:self.n]

    def drop_front(self, count: int) -> None:
        count = min(int(count), self.n)
        if count > 0:
            self._a[:self.n - count] = self._a[count:self.n]
            self.n -= count

    def clear(self) -> None:
        self.n = 0

    @property
    def nbytes(self) -> int:
        """What its storage takes, bytes."""
        return int(self._a.nbytes)
