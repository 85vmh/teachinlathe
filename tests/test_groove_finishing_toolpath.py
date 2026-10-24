"""Groove Finishing's G-code against the groove it finishes, as
test_groove_roughing_toolpath checks the roughing's: on every move the blade,
its corners rounded, swept from where it was to where it goes, never enters
the part - the finished profile, no stock left on it."""

import re

import pytest

from teachinlathe.conversational.gcode.operations.groove_finishing import generate_groove_finishing_gcode

from test_groove_roughing_toolpath import BLADES, GROOVES, MAX_OVERLAP, _blade, _moves, _op, _part
from shapely.ops import unary_union

STRATEGIES = ["towards_center", "towards_left", "towards_right"]

#: What the Groove Roughing above leaves, radial / axial, mm.
ROUGHING_STOCK = {"none": (0.0, 0.0), "0.5 / 0.2": (0.5, 0.2)}


def _finishing(groove, blade, strategy, stock=(0.0, 0.0), clearance=1.0, profile_type="od"):
    op = _op(groove, blade, None, clearance=clearance, profile_type=profile_type)
    op.update(type="grooveFinishing",
              finishing_parameters={"profile_id": 1, "strategy": strategy},
              _resolved_roughing_stock={"radial": stock[0], "axial": stock[1]})
    return op


def _gouges(op):
    lines = generate_groove_finishing_gcode(op)
    assert not [line for line in lines if "ERROR" in line], lines
    part, sign = _part(op)
    blade = op["_resolved_tool"]
    found = []
    for move in _moves(lines):
        x0, z0, x1, z1 = move
        swept = unary_union([_blade(x0, z0, blade, sign), _blade(x1, z1, blade, sign)]).convex_hull
        area = swept.intersection(part).area
        if area > MAX_OVERLAP:
            found.append((move, round(area, 5)))
    return found


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize("blade", list(BLADES))
@pytest.mark.parametrize("groove", list(GROOVES))
def test_no_move_takes_the_blade_into_the_part(groove, blade, strategy):
    assert _gouges(_finishing(GROOVES[groove], BLADES[blade], strategy)) == []


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_an_id_groove_is_finished_inside_it_too(strategy):
    groove = GROOVES["filleted"]
    groove = dict(groove, right_flank=dict(groove["right_flank"], x_start=12.0),
                  left_flank=dict(groove["left_flank"], x_start=12.0),
                  bottom=dict(groove["bottom"], x_end_right=30.0, x_end_left=30.0))

    assert _gouges(_finishing(groove, BLADES["1.5 touched off middle"], strategy, profile_type="id")) == []


@pytest.mark.parametrize("stock", list(ROUGHING_STOCK))
def test_the_blade_starts_the_clearance_out_from_the_roughings_start_diameter(stock):
    """The start diameter is the pulley's outside with the radial stock the
    roughing above left; the blade starts the clearance out from that, twice
    the radial values on the diameter."""
    radial = ROUGHING_STOCK[stock][0]
    op = _finishing(GROOVES["filleted"], BLADES["1.5 touched off middle"], "towards_center",
                    ROUGHING_STOCK[stock], clearance=1.0)
    first = next(line for line in generate_groove_finishing_gcode(op) if line.startswith("G0 X"))

    assert float(first[4:]) == pytest.approx(GROOVES["filleted"]["right_flank"]["x_start"] + 2 * radial + 2 * 1.0)


@pytest.mark.parametrize("blade", list(BLADES))
@pytest.mark.parametrize("groove", ["plain", "filleted", "angled"])
def test_the_two_sides_overlap_past_the_middle(groove, blade):
    """Toward the centre, each side ends with the blade's middle half its
    width past the groove's: the two overlap by a blade's width."""
    tool = BLADES[blade]
    lines = generate_groove_finishing_gcode(_finishing(GROOVES[groove], tool, "towards_center"))
    middle = (GROOVES[groove]["right_flank"]["z_start"] + GROOVES[groove]["left_flank"]["z_start"]) / 2
    ends = {}
    section = None
    for line in lines:
        if "Contour Z+" in line:
            section = "right"
        elif "Contour Z-" in line:
            section = "left"
        elif section and line.startswith(("G1", "G2", "G3")):
            z = float(re.search(r"Z(-?[\d.]+)", line).group(1))
            ends[section] = z - tool["control"] * tool["width"] / 2      # the blade's middle

    assert ends["right"] == pytest.approx(middle - tool["width"] / 2, abs=1e-3)
    assert ends["left"] == pytest.approx(middle + tool["width"] / 2, abs=1e-3)


@pytest.mark.parametrize("strategy", ["towards_left", "towards_right"])
def test_a_pass_across_the_bottom_goes_straight_on(strategy):
    """Going on from one side to the other, the blade does not go back over
    the bottom where it changes from one corner to the other."""
    tool = BLADES["1.5 touched off left"]
    moves = _moves(generate_groove_finishing_gcode(_finishing(GROOVES["plain"], tool, strategy)))
    bottom = [(z0, z1) for x0, z0, x1, z1 in moves if x0 == x1 == 12.0 and z0 != z1]
    way = 1 if strategy == "towards_right" else -1

    assert bottom and all((z1 - z0) * way > 0 for z0, z1 in bottom)
