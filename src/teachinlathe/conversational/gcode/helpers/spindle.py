from teachinlathe.conversational.model.data_types import SpeedsAndFeeds, SpindleMode
from teachinlathe.tooling.model.data_types import SpindleDirection

from .utils import get_float, get_int



def build_spindle_gcode(spindle, prefix: str, force_rpm: bool = False) -> list:
    """Build spindle start G-code line(s) from an operation's speeds and feeds.

    Accepts either a parsed SpeedsAndFeeds object or its dict form.
    force_rpm=True overrides the mode to G97/RPM regardless of spindle settings.
    """
    if isinstance(spindle, SpeedsAndFeeds):
        direction = spindle.direction
        mode = SpindleMode.RPM if force_rpm else spindle.mode
        rpm_value = 0 if spindle.rpm_value is None else int(spindle.rpm_value)
        css_value = 0 if spindle.css_value is None else int(spindle.css_value)
        css_max = 0 if spindle.css_max_speed is None else int(spindle.css_max_speed)
    else:
        direction = SpindleDirection.__members__.get(str(spindle.get("direction", "")))
        if force_rpm:
            mode = SpindleMode.RPM
        else:
            mode_str = str(spindle.get("mode", "")).lower()
            try:
                mode = SpindleMode(mode_str)
            except ValueError:
                return []
        rpm_value = get_int(spindle, "rpm_value", 0)
        css_value = get_int(spindle, "css_value", 0)
        css_max = get_int(spindle, "css_max_speed", 0)

    words = []
    if mode == SpindleMode.RPM:
        words.append("G97")
    elif mode == SpindleMode.CSS:
        words.append("G96")

    if direction is not None:
        words.append(direction.name)

    if mode == SpindleMode.RPM:
        words.append(f"S{rpm_value}")
    elif mode == SpindleMode.CSS:
        words.append(f"S{css_value} D{css_max}")

    if words:
        return [f"{prefix}{' '.join(words)}"]
    return []


def direction_sign(op):
    """The spindle's direction of an operation in its dict form, as the
    subroutines take it: 1 M3, -1 M4."""
    speeds = op.get("speeds_and_feeds") or {}
    return 1 if str(speeds.get("direction", "")) == SpindleDirection.M3.name else -1


def feed_rate_of(op, default, key="feed_rate"):
    """The feed - ``key``: "feed_rate", or Parting's "feed_rate_2" - of an
    operation in its dict form, from its speeds and feeds; ``default`` when
    it has none."""
    return get_float(op.get("speeds_and_feeds") or {}, key, default)
