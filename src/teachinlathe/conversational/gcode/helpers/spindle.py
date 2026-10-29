from teachinlathe.conversational.model.data_types import SpeedsAndFeeds, SpindleMode

from ..config import fmt



def build_spindle_gcode(spindle: SpeedsAndFeeds, prefix: str, force_rpm: bool = False) -> list:
    """The spindle start's G-code line from an operation's speeds and feeds;
    ``force_rpm`` G97 at the RPM whatever its mode."""
    direction = spindle.direction
    mode = SpindleMode.RPM if force_rpm else spindle.mode
    rpm_value = 0 if spindle.rpm_value is None else int(spindle.rpm_value)
    css_value = 0 if spindle.css_value is None else int(spindle.css_value)
    css_max = 0 if spindle.css_max_speed is None else int(spindle.css_max_speed)

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


def build_feed_gcode(feed_rate, prefix: str = "") -> str:
    """The feed's G-code line, G95 F in mm a turn: written right after the
    spindle's, then again in an operation only where its feed changes."""
    return f"{prefix}G95 F{fmt(feed_rate)}"
