from teachinlathe.conversational.data_types import SpindleMode, SpindleParameters

from .utils import get_int



def build_spindle_gcode(spindle, prefix: str, force_rpm: bool = False) -> list:
    """Build spindle start G-code line(s) from spindle parameters.

    Accepts either a parsed SpindleParameters object or the legacy dict form.
    force_rpm=True overrides the mode to G97/RPM regardless of spindle settings.
    """
    if isinstance(spindle, SpindleParameters):
        direction = spindle.direction
        mode = SpindleMode.RPM if force_rpm else spindle.mode
        rpm_value = 0 if spindle.rpm_value is None else int(spindle.rpm_value)
        css_value = 0 if spindle.css_value is None else int(spindle.css_value)
        css_max = 0 if spindle.css_max_speed is None else int(spindle.css_max_speed)
    else:
        direction = spindle.get("direction", None)
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

    if direction == -1:
        words.append("M4")
    elif direction == 1:
        words.append("M3")

    if mode == SpindleMode.RPM:
        words.append(f"S{rpm_value}")
    elif mode == SpindleMode.CSS:
        words.append(f"S{css_value} D{css_max}")

    if words:
        return [f"{prefix}{' '.join(words)}"]
    return []
