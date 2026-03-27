from teachinlathe.conversational.data_types import SpindleMode

from .utils import get_int


def build_spindle_gcode(spindle: dict, prefix: str, force_rpm: bool = False) -> list:
    """Build spindle start G-code line(s) from a spindle_parameters dict.

    force_rpm=True overrides the mode to G97/RPM regardless of spindle settings.
    This is required for operations that cannot use CSS (drilling, tapping).

    Returns a list with one line, or an empty list if mode is unrecognised.
    """
    direction = spindle.get("direction", None)

    if force_rpm:
        mode = SpindleMode.RPM
    else:
        mode_str = str(spindle.get("mode", "")).lower()
        try:
            mode = SpindleMode(mode_str)
        except ValueError:
            return []

    words = []
    if mode == SpindleMode.RPM:
        words.append("G97")
    elif mode == SpindleMode.CSS:
        words.append("G96")

    if direction == -1:
        words.append("M4")
    elif direction == 1:
        words.append("M3")

    if mode == SpindleMode.RPM:
        words.append(f"S{get_int(spindle, 'rpm_value', 0)}")
    elif mode == SpindleMode.CSS:
        css = get_int(spindle, "css_value", 0)
        css_max = get_int(spindle, "css_max_speed", 0)
        words.append(f"S{css} D{css_max}")

    if words:
        return [f"{prefix}{' '.join(words)}"]
    return []
