"""A cutting tool's name, as the screens show it and the G-code writes it:
the one place its words are made.

A title is a list of TitlePart: a piece of text and the role it plays - the
insert's family, its size, its corner radius, the tool's body - which a
screen colours it by. Its texts put together are the title as plain text.

Two titles: the card's, what the tool's card heads it with (card_title_parts:
"CCMT 060204", "16ER 1.5", "3 mm", "Ø6.8 mm", "M10x1.5"), and the list's, what
a list of tools heads its row with, saying what the tool is as well as its
size (list_title_parts: "Turning CCMT 060204", "3mm Grooving/Parting Blade",
"ER16 OD Threading", "RH Tap M10x1.5mm", "118° RH Drill Ø6.8mm",
"6.8mm Reamer").
"""

from dataclasses import dataclass
from typing import List, Optional

from teachinlathe.tooling.model import insert_catalog, threading_catalog
from teachinlathe.tooling.model.data_types import (
    BladeTool, BoringTool, CuttingTool, DrillingTool, ReamingTool, TappingTool, ThreadingTool,
    TurningTool, TwistDirection,
)

#: What a part of a title is, for a screen to colour it by; NONE is the
#: words in between.
NONE = ""
FAMILY = "family"          # an insert's family: CCMT
INSERT = "insert"          # an insert's size, in the insert's colour: 06, 16
THICKNESS = "thickness"    # an insert's thickness code: 02
RADIUS = "radius"          # an insert's corner radius code: 04
HAND = "hand"              # a threading insert's hand: ER, IR
PITCH = "pitch"            # a threading insert's pitch: 1.5
BODY = "body"              # a size in the tool's own colour: a blade's width, a drill's Ø

#: A blade's kind, by its orientation.
_BLADES = {6: "Grooving/Parting Blade", 5: "Trepanning Blade", 7: "Trepanning Blade", 8: "Grooving Blade"}


@dataclass(frozen=True)
class TitlePart:
    text: str
    role: str = NONE


def _number(value, places: int) -> str:
    """25.0 as 25, 6.80 as 6.8, to ``places`` decimals at most."""
    return f"{float(value):.{places}f}".rstrip("0").rstrip(".")


def _mm(value) -> str:
    """A size as the card writes it: "3 mm"."""
    return f"{_number(value, 3)} mm"


def _size(value) -> str:
    """A size as the list writes it: "3mm"."""
    return f"{_number(value, 3)}mm"


def _hand(tool) -> str:
    return "RH" if tool.twist_direction is TwistDirection.RIGHT_HAND else "LH"


def _designation(tool: TappingTool) -> str:
    """As a metric thread is called: "M10x1.5"."""
    return f"M{tool.diameter:g}x{tool.pitch:g}"


def _insert_parts(tool: TurningTool) -> List[TitlePart]:
    """The ISO designation in its parts - "CCMT", "06", "02", "04"."""
    radius = (insert_catalog.ROUND_CORNER_CODE if insert_catalog.insert_for(tool.insert).is_round
              else tool.insert.radius)
    return [TitlePart(insert_catalog.family_of(tool.insert), FAMILY), TitlePart(" "),
            TitlePart(tool.insert.size, INSERT),
            TitlePart(insert_catalog.thickness_code(tool.insert), THICKNESS),
            TitlePart(radius, RADIUS)]


def _thread_hand(tool: ThreadingTool) -> str:
    """"ER" or "IR"."""
    return threading_catalog.hand_of(tool.insert.geometry, tool.orientation)


def _thread_size(tool: ThreadingTool) -> str:
    return threading_catalog.size_of(tool.insert.size)


def card_title_parts(tool: Optional[CuttingTool]) -> List[TitlePart]:
    """What ``tool``'s card heads it with; none for no tool."""
    if tool is None:
        return []
    if isinstance(tool, TurningTool):
        return _insert_parts(tool)
    if isinstance(tool, ThreadingTool):
        pitch = threading_catalog.nearest_pitch(_thread_size(tool), tool.pitch)
        return [TitlePart(_thread_size(tool), INSERT), TitlePart(_thread_hand(tool), HAND), TitlePart(" "),
                TitlePart(threading_catalog.pitch_text(pitch), PITCH)]
    if isinstance(tool, BladeTool):
        return [TitlePart(_mm(tool.blade_width), BODY)]
    if isinstance(tool, (DrillingTool, ReamingTool)):
        return [TitlePart("Ø" + _mm(tool.diameter), BODY)]
    if isinstance(tool, TappingTool):
        return [TitlePart(_designation(tool), BODY)]
    return [TitlePart(tool.summary())]


def list_title_parts(tool: Optional[CuttingTool]) -> List[TitlePart]:
    """What a list of tools heads ``tool``'s row with; none for no tool."""
    if tool is None:
        return []
    if isinstance(tool, TurningTool):
        return [TitlePart("Boring " if isinstance(tool, BoringTool) else "Turning ")] + _insert_parts(tool)
    if isinstance(tool, ThreadingTool):
        side = "ID" if _thread_hand(tool) == "IR" else "OD"
        return [TitlePart(_thread_hand(tool), HAND), TitlePart(_thread_size(tool), INSERT),
                TitlePart(f" {side} Threading")]
    if isinstance(tool, BladeTool):
        return [TitlePart(_size(tool.blade_width), BODY), TitlePart(" " + _BLADES.get(tool.orientation, "Blade"))]
    if isinstance(tool, DrillingTool):
        return [TitlePart(f"{_number(tool.tip_angle, 1)}° {_hand(tool)} Drill "),
                TitlePart("Ø" + _size(tool.diameter), BODY)]
    if isinstance(tool, ReamingTool):
        return [TitlePart(_size(tool.diameter), BODY), TitlePart(" Reamer")]
    if isinstance(tool, TappingTool):
        return [TitlePart(f"{_hand(tool)} Tap "), TitlePart(_designation(tool) + "mm", BODY)]
    return card_title_parts(tool)


def text_of(parts: List[TitlePart]) -> str:
    return "".join(part.text for part in parts)


def list_title(tool: Optional[CuttingTool]) -> str:
    """``tool``'s list title as plain text; "" for no tool."""
    return text_of(list_title_parts(tool))
