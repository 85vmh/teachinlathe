"""The work offsets, by the index linuxcnc.stat() has them (g5x_index)."""

WORK_OFFSETS = {1: "G54", 2: "G55", 3: "G56", 4: "G57", 5: "G58", 6: "G59", 7: "G59.1", 8: "G59.2", 9: "G59.3"}


def work_offset_name(index: int) -> str:
    """"G54" ... for work offset ``index``; G54 for one unknown."""
    return WORK_OFFSETS.get(int(index or 1), "G54")
