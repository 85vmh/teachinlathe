"""The threading inserts the tool editor offers: ER and IR laydown inserts,
by size and pitch.

The pitches are the ones ``ui/tabs/tool_library/shapes/ThreadingInsert.qml`` has a
tooth for (its ``pitchTable``) - the drawing cannot show any other - so the
two lists have to be kept in step by hand.
"""

from __future__ import annotations

from typing import List

#: External (ER) and internal (IR), both right hand. Each is held one way:
#: ER at orientation 6, IR at 8. ThreadingInsert draws an IR as its mirror
#: image, hand "L", turned over by the orientation.
HANDS = ("ER", "IR")

#: The orientation each is held at, and back.
ORIENTATION = {"ER": 6, "IR": 8}
HAND_AT = {orientation: hand for hand, orientation in ORIENTATION.items()}

#: ThreadingInsert's `hand` for each.
DRAWN_HAND = {"ER": "R", "IR": "L"}

#: What each is called.
KIND = {"ER": "External", "IR": "Internal"}

#: Inscribed circle by size code, as ThreadingInsert's `icTable`.
SIZES = {"11": 6.35, "16": 9.525, "22": 12.7}

PITCHES = {
    "11": (0.5, 0.6, 0.7, 0.75, 0.8, 1.0, 1.25, 1.5, 1.75, 2.0),
    "16": (0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.75, 0.8, 1.0, 1.25, 1.5, 1.75,
           2.0, 2.5, 3.0, 3.5),
    "22": (1.5, 1.75, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0),
}

DEFAULT_HAND = "ER"
DEFAULT_SIZE = "16"
DEFAULT_PITCH = 1.5


def hands() -> List[str]:
    return list(HANDS)


def hand_of(geometry: str, orientation: int) -> str:
    """The insert a stored geometry names; one it does not know - an EL
    from before there was IR - is read off the orientation it is held at."""
    hand = geometry.upper()
    if hand in HANDS:
        return hand
    return HAND_AT.get(orientation, DEFAULT_HAND)


def size_codes() -> List[str]:
    return list(SIZES)


def size_of(code: str) -> str:
    return code if code in SIZES else DEFAULT_SIZE


def pitches(size: str) -> List[float]:
    return list(PITCHES[size_of(size)])


def nearest_pitch(size: str, pitch: float) -> float:
    """The size's pitch closest to `pitch`: what a tool keeps when its size
    changes to one that does not have its pitch."""
    return min(pitches(size), key=lambda p: abs(p - pitch))


def pitch_text(pitch: float) -> str:
    """1.0 as "1", 0.75 as "0.75" - as the QML keys its table."""
    return f"{pitch:g}"
