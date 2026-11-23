"""What a new operation starts with from the last ones of its type.

Some fields of the operation last edited - the spindle mode and speeds, the
feeds, Pause to Inspect, the passes, the AP, the stock to leave, the retract,
a drill's peck - are what the next operation of the same type starts with,
so that only what is new about it is typed in. They are kept per type of
operation (``defaults_key``), a Profile Roughing's and a Profile Contour's
apart for OD and ID, as a patch in the operation's own shape - what its
editor sends (``{"speeds_and_feeds": {"feed_rate": 0.2}}``) and its updater
takes.

``REMEMBERED`` names the fields; ``remembered_values`` takes them from an
operation. Whenever one is edited, all of them are taken from it, as it is
then - the last operation of the type edited wins, the values it had before
with the one changed. Operations made from another one (a duplicate, a rest roughing, a
contour or a finish of a roughing or a turning) keep what they take from it.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from teachinlathe.conversational.model.data_types import ProfilingType

#: The speeds and feeds every operation that has them keeps.
_SPEEDS = ("speeds_and_feeds", ("mode", "rpm_value", "css_value", "css_max_speed",
                                "feed_rate", "feed_rate_2"))
_M1 = ("m1_parameters", ("include_m1", "inspect_position"))
_STOCK = ("stock_to_leave", ("radial", "axial"))

#: Per operation type: the fields remembered, as (section, (field, ...)) -
#: a section None for a field at the operation's top level.
REMEMBERED: Dict[str, Tuple[Tuple[Optional[str], Tuple[str, ...]], ...]] = {
    "facing": (_SPEEDS, _M1, ("cutting_parameters", ("doc", "retract"))),
    "turning": (_SPEEDS, _M1, _STOCK, ("cutting_parameters", ("ap", "tool_clearance")),
                ("profile_roughing_strategy", ("pass_type",))),
    "turningFinish": (_SPEEDS, _M1, (None, ("passes_count",))),
    "profileRoughing": (_SPEEDS, _M1, _STOCK, ("cutting_parameters", ("doc", "retract")),
                        ("profile_roughing_strategy", ("pass_type", "diagonal_angle"))),
    "profileContour": (_SPEEDS, _M1, (None, ("passes_count",))),
    "drilling": (_SPEEDS, _M1, ("drilling_parameters", ("peck_depth", "tool_clearance"))),
    "tapping": (_SPEEDS,),
    "parting": (_SPEEDS, ("parting_parameters", ("x_clearance",))),
    "grooveRoughing": (_SPEEDS, _M1, _STOCK, ("cutting_parameters", ("peck_depth", "retract"))),
    "grooveBidirectional": (_SPEEDS, _M1, _STOCK, ("cutting_parameters", ("doc", "retract"))),
    "grooveFinishing": (_SPEEDS, ("cutting_parameters", ("retract",))),
    "knurling": (_SPEEDS, _M1, ("cutting_parameters", ("doc", "retract"))),
}

#: The types remembered apart for an OD and an ID profile.
_BY_PROFILE_TYPE = ("profileRoughing", "profileContour")


def defaults_key(op_type: str, profiling_type: Optional[ProfilingType] = None) -> Optional[str]:
    """Where the last values of an operation of ``op_type`` are kept - a
    Profile Roughing's and a Profile Contour's apart for OD and ID
    (``profileRoughing.id``); None for a type nothing is kept of."""
    if op_type not in REMEMBERED:
        return None
    if op_type in _BY_PROFILE_TYPE:
        return f"{op_type}.{(profiling_type or ProfilingType.OD).value}"
    return op_type


def profiling_type_of(op) -> Optional[ProfilingType]:
    """Whether a Profile Roughing or Contour cuts OD or ID; None for another."""
    strategy = getattr(op, "profileRoughingStrategy", None) or getattr(op, "profileContourStrategy", None)
    return getattr(strategy, "profiling_type", None)


def remembered_values(op_type: str, operation: Dict[str, Any]) -> Dict[str, Any]:
    """The fields remembered for ``op_type`` that ``operation`` (its dict)
    has, as a patch. {} for none."""
    out: Dict[str, Any] = {}
    for section, fields in REMEMBERED.get(op_type, ()):
        have = operation if section is None else operation.get(section)
        if not isinstance(have, dict):
            continue
        values = {name: have[name] for name in fields if name in have}
        if section is None:
            out.update(values)
        elif values:
            out[section] = values
    return out
