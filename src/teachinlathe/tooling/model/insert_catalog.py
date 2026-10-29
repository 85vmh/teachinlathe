"""The ISO inserts the tool editor offers, and how an InsertSpec reads them.

The catalogue itself is the one the backplot draws from,
``tooling/model/inserts.py`` - families, sizes and nose radii -
which ``tests/test_inserts.py`` keeps in step with the QML drawing. This only
translates between it and the codes stored in cutting_tools.json: "ccmt",
"06", "04".
"""

from __future__ import annotations

from typing import List, Optional

from teachinlathe.tooling.model.data_types import InsertSpec
from teachinlathe.tooling.model.inserts import FAMILIES, NOSE_RADII, Insert

#: Corner angles are read off the drawn outline; the trigon's comes out a
#: hair under 80 degrees from its approximated flank radius.
_ANGLE_DECIMALS = 1


def families() -> List[str]:
    return list(FAMILIES)


def family_of(spec: InsertSpec) -> str:
    """The catalogue family a spec names, or the first one if it names none
    the catalogue knows."""
    family = spec.geometry.upper()
    return family if family in FAMILIES else families()[0]


def size_codes(family: str) -> List[str]:
    return list(FAMILIES[family]["codes"])


def size_index_of(spec: InsertSpec) -> int:
    codes = size_codes(family_of(spec))
    return codes.index(spec.size) if spec.size in codes else 0


def thickness_code(spec: InsertSpec) -> str:
    """The ISO thickness code of the spec's size, e.g. "02" for CCMT 06."""
    return FAMILIES[family_of(spec)]["thickness"][size_index_of(spec)]


#: What ISO prints in the corner-radius place of a round insert.
ROUND_CORNER_CODE = "M0"


def nose_radii() -> List[float]:
    return list(NOSE_RADII)


def nose_radius_code(radius_mm: float) -> str:
    """ISO nose-radius code: 0.4 mm is "04"."""
    return f"{round(radius_mm * 10):02d}"


def nose_radius_codes() -> List[str]:
    return [nose_radius_code(r) for r in NOSE_RADII]


def nose_radius_of(spec: InsertSpec) -> float:
    try:
        return int(spec.radius) / 10.0
    except ValueError:
        return NOSE_RADII[0]


def make_spec(family: str, size_index: int, radius_mm: float) -> InsertSpec:
    codes = size_codes(family)
    size_index = max(0, min(size_index, len(codes) - 1))
    return InsertSpec(geometry=family.lower(), size=codes[size_index],
                      radius=nose_radius_code(radius_mm))


def insert_for(spec: InsertSpec) -> Insert:
    return Insert(family_of(spec), size_index_of(spec), nose_radius_of(spec))


#: The insert drawings that share one scale are scaled to fit, at any turn.
#: Not the catalogue's biggest - VBMT 22 would leave the small ones a few
#: pixels - so the rare bigger inserts run past the frame.
SCALE_REFERENCE = ("VBMT", "16")


def scale_reach_mm() -> float:
    """How far SCALE_REFERENCE reaches from its centre, sharp corners, in mm."""
    family, code = SCALE_REFERENCE
    return Insert(family, size_codes(family).index(code), 0.0).max_radius()


def corner_angle(spec: InsertSpec) -> Optional[float]:
    """The insert's included angle at the cutting corner; None when round."""
    angle = insert_for(spec).corner_angle
    return None if angle is None else round(angle, _ANGLE_DECIMALS)