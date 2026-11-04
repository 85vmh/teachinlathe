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

#: The tooth by size and pitch - ThreadingInsert.qml's ``pitchTable``: tip radius ``r``, V
#: angle ``a``, the bisector's distance ``X`` from the long side, the
#: rounded tip's distance ``Y`` along that side from the theoretical corner,
#: and the tooth's height ``h``.
TEETH = {
    "11": {
        0.5: (0.11, 60.767, 0.7278, 0.5998, 0.414),
        0.6: (0.11, 60.767, 0.6639, 0.5998, 0.467),
        0.7: (0.11, 60.767, 0.6, 0.5998, 0.52),
        0.75: (0.11, 60.767, 0.6, 0.5998, 0.601),
        0.8: (0.12, 60.767, 0.6, 0.5998, 0.66),
        1.0: (0.15, 60.8, 0.6932, 0.65, 0.742),
        1.25: (0.16, 60.84, 0.9, 0.7992, 0.8836),
        1.5: (0.1931, 60.84, 1.0, 0.8066, 1.1193),
        1.75: (0.2262, 60.84, 1.2145, 0.814, 1.55),
        2.0: (0.2593, 60.84, 1.2483, 0.8214, 1.673),
    },
    "16": {
        0.35: (0.0448, 60.652, 0.6003, 0.5795, 0.3345),
        0.4: (0.0534, 60.691, 0.6001, 0.5825, 0.361),
        0.45: (0.062, 60.729, 0.6001, 0.5854, 0.3875),
        0.5: (0.0706, 60.767, 0.6, 0.5883, 0.414),
        0.6: (0.0878, 60.844, 0.6, 0.5941, 0.467),
        0.7: (0.105, 60.92, 0.6, 0.6, 0.52),
        0.75: (0.1003, 60.767, 0.6, 0.5929, 0.601),
        0.8: (0.1022, 60.774, 0.6382, 0.614, 0.66),
        1.0: (0.11, 60.8, 0.7008, 0.6982, 0.742),
        1.25: (0.157, 60.84, 0.9, 0.8, 0.8836),
        1.5: (0.189, 60.84, 1.15, 0.9, 1.1193),
        1.75: (0.221, 60.84, 1.2, 0.9, 1.55),
        2.0: (0.25, 60.8, 1.3, 1.0, 1.673),
        2.5: (0.3428, 60.767, 1.5, 1.1501, 1.9199),
        3.0: (0.378, 60.84, 1.6, 1.2, 2.238),
        3.5: (0.5169, 60.91, 1.5999, 1.2666, 2.629),
    },
    "22": {
        1.5: (0.1856, 61.132, 1.2111, 1.4381, 1.1193),
        1.75: (0.2199, 61.096, 1.4648, 1.4584, 1.55),
        2.0: (0.2542, 61.059, 1.5366, 1.4786, 1.673),
        2.5: (0.3228, 60.986, 1.6806, 1.5191, 1.9199),
        3.0: (0.3914, 60.913, 1.866, 1.5596, 2.238),
        3.5: (0.46, 60.84, 2.3, 1.6001, 2.629),
        4.0: (0.5286, 60.767, 2.3, 1.6406, 3.013),
        4.5: (0.5893, 60.767, 2.4, 1.7077, 3.3872),
        5.0: (0.6499, 60.767, 2.5, 1.7748, 3.7615),
        5.5: (0.7106, 60.767, 2.6448, 1.8419, 4.1357),
        6.0: (0.7712, 60.767, 2.8643, 1.909, 4.51),
    },
}



def tooth(size: str, pitch: float):
    """The tooth of the ``size`` insert nearest ``pitch``: (tip radius, V
    angle, X, Y, height), as TEETH has them."""
    teeth = TEETH[size if size in TEETH else DEFAULT_SIZE]
    return teeth[min(teeth, key=lambda p: abs(p - pitch))]


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
