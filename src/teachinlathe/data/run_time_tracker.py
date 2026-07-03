"""Program run-time figures for the completion popup.

NOTE: real timing (movement vs tool-change) will read machine/HAL data later.
For now this returns dummy placeholder values and touches no HAL pins, so it
can't interfere with start-up.
"""

from PyQt5.QtCore import QObject


def format_duration(seconds):
    """Format seconds as e.g. '3m 41s' (or '41s' when under a minute)."""
    seconds = int(round(max(0.0, seconds)))
    minutes, secs = divmod(seconds, 60)
    if minutes:
        return "%dm %02ds" % (minutes, secs)
    return "%ds" % secs


class RunTimeTracker(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    def start(self):
        pass

    def stop(self):
        """Return ``(movement, toolchange, total)`` in seconds (dummy for now)."""
        movement, toolchange, total = 151.0, 70.0, 221.0
        return movement, toolchange, total
