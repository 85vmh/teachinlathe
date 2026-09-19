"""The facing call, and the retract it was not passing.

The operation had a retract in the UI, saved in the program's JSON, and the
subroutine had no parameter for it: the call passed seven arguments and the
subroutine retracted by the depth of cut instead. Nothing errored - a smaller
depth of cut quietly meant a smaller clearance - so this checks the call and
the subroutine agree on both the count and the order.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.data_types import (  # noqa: E402
    CuttingParameters, Facing, GeometryParameters, M1Parameters,
    PredefinedPosition, SpindleMode, SpindleParameters,
)
from teachinlathe.widgets.conversational_qml.gcode_builder.operations.facing \
    import generate_facing_gcode  # noqa: E402

SUBROUTINE = ROOT / "subroutines" / "facing.ngc"


def facing(doc=1.0, retract=2.0, optional=False, new_datum=False):
    return Facing(
        order=1, type="facing", generate_gcode=True,
        is_optional_block=optional,
        spindleParameters=SpindleParameters(
            direction=-1, mode=SpindleMode.RPM, rpm_value=1200),
        cuttingParameters=CuttingParameters(
            feedRate=0.1, retract=retract, doc=doc),
        geometryParameters=GeometryParameters(
            xStart=42.0, zStart=1.0, xEnd=-0.4, zEnd=-2.0),
        m1Parameters=M1Parameters(
            include_m1=False,
            inspect_position=PredefinedPosition.NONE
            if hasattr(PredefinedPosition, "NONE")
            else list(PredefinedPosition)[0],
            stop_spindle=False),
        zEndBecomesNewZ0=new_datum,
    )


def call_line(op=None):
    lines = generate_facing_gcode(op or facing())
    return next(line for line in lines if "o<facing> call" in line)


def arguments(line):
    return re.findall(r"\[([^\]]*)\]", line)


def numbers(line):
    """The call's arguments as floats.

    Compared as numbers, not as the strings ``fmt`` happens to produce - a
    test that pins the formatter's decimal places fails the next time someone
    changes it, for no reason connected to what it is checking.
    """
    return [float(argument) for argument in arguments(line)]


# ── the call ───────────────────────────────────────────────────────────────

def test_the_retract_is_passed():
    """The whole bug: it never reached the subroutine."""
    assert numbers(call_line(facing(retract=3.0)))[-1] == pytest.approx(3.0)


def test_the_retract_is_the_last_argument():
    """Positional, so its place is the contract with the subroutine."""
    assert numbers(call_line(facing(retract=2.5)))[7] == pytest.approx(2.5)


def test_the_retract_is_not_the_depth_of_cut():
    """They were the same value by accident of the subroutine reusing doc."""
    args = numbers(call_line(facing(doc=0.5, retract=3.0)))
    assert args[5] == pytest.approx(0.5)
    assert args[7] == pytest.approx(3.0)


def test_the_earlier_arguments_did_not_move():
    args = numbers(call_line())
    assert args[0] == pytest.approx(42.0)    # x start
    assert args[1] == pytest.approx(1.0)     # z start
    assert args[2] == pytest.approx(-0.4)    # x end
    assert args[3] == pytest.approx(-2.0)    # z end


# ── the call and the subroutine agree ──────────────────────────────────────

def subroutine_parameters():
    """``#<name> = #N`` in the subroutine, in N order."""
    found = {}
    for name, number in re.findall(r"#<(\w+)>\s*=\s*#(\d+)",
                                   SUBROUTINE.read_text()):
        found[int(number)] = name
    return [found[n] for n in sorted(found)]


def test_the_call_passes_exactly_what_the_subroutine_reads():
    names = subroutine_parameters()
    assert len(arguments(call_line())) == len(names), \
        "the call and the subroutine disagree on how many arguments there are"
    assert names[-1] == "retract"


def test_the_subroutine_numbers_its_parameters_without_a_gap():
    names = subroutine_parameters()
    text = SUBROUTINE.read_text()
    for index, name in enumerate(names, start=1):
        assert re.search(r"#<%s>\s*=\s*#%d\b" % (name, index), text), name


# ── how it leaves the cut ──────────────────────────────────────────────────

def diagonal_exits():
    """Rapids that move both axes at once - a 45 degree exit."""
    return [line.strip() for line in SUBROUTINE.read_text().splitlines()
            if re.match(r"\s*G0 X\[.*\] Z\[", line)]


def test_it_leaves_the_cut_at_45_degrees():
    """As every other toolpath does. Two separate moves - out in Z, then back
    in X - is what it did before."""
    assert diagonal_exits(), "no move that changes both axes at once"


def test_the_exit_is_45_degrees_on_the_part_not_on_the_numbers():
    """The subroutine runs in diameter mode, so a diameter step of 2R is a
    radial step of R: X has to move twice what Z does."""
    for line in diagonal_exits():
        assert "#<retract> * 2" in line, line
        assert re.search(r"Z\[[^\]]*\+ #<retract>\]", line), line


def test_the_retracts_no_longer_use_the_depth_of_cut():
    """``G0 Z[#<z_start> + #<doc>]`` was the retract, and it is why a fine
    depth of cut gave a clearance of a few hundredths."""
    for line in SUBROUTINE.read_text().splitlines():
        if line.strip().startswith("G0") and "#<doc>" in line:
            pytest.fail("a rapid still retracts by the depth of cut: %s"
                        % line.strip())


def test_a_zero_retract_falls_back_to_the_depth_of_cut():
    """Left at zero in the UI it would otherwise rub the face on the way out.
    """
    text = SUBROUTINE.read_text()
    assert re.search(r"IF \[#<retract> LE 0\]", text)
    assert re.search(r"#<retract>\s*=\s*#<doc>", text)


# ── what was already there stays ───────────────────────────────────────────

def test_the_optional_block_prefix_still_applies_to_the_call():
    assert call_line(facing(optional=True)).startswith("/")


def test_the_datum_line_is_still_emitted():
    lines = generate_facing_gcode(facing(new_datum=True))
    assert any("G10 L20" in line for line in lines)
