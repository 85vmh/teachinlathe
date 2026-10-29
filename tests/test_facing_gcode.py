"""Facing's G-code, written out move by move by facing_toolpath.

The retract was once in the UI and the JSON but never reached the cut, which
backed off by the depth of cut instead: nothing errored, a smaller depth of
cut quietly meant a smaller clearance. These check the moves use the retract,
leave at 45 degrees, and are the moves the preview draws - the moves kept as
they were written.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.model.data_types import (  # noqa: E402
    CuttingParameters, Facing, GeometryParameters, InspectPosition, M1Parameters,
    SpindleMode, SpeedsAndFeeds,
)
from teachinlathe.conversational.gcode.operations.facing \
    import facing_preview, facing_toolpath, generate_facing_gcode  # noqa: E402
from teachinlathe.conversational.gcode.toolpath import GcodeEmitter  # noqa: E402
from teachinlathe.tooling.model.data_types import SpindleDirection  # noqa: E402

X_START, Z_START, X_END, Z_END = 42.0, 1.0, -0.4, -2.0


def facing(doc=1.0, retract=2.0, optional=False, new_datum=False, include_m1=False):
    return Facing(
        order=1, type="facing", generate_gcode=True,
        is_optional_block=optional,
        speedsAndFeeds=SpeedsAndFeeds(
            direction=SpindleDirection.M4, mode=SpindleMode.RPM, rpm_value=1200, feed_rate=0.1),
        cuttingParameters=CuttingParameters(retract=retract, doc=doc),
        geometryParameters=GeometryParameters(
            xStart=X_START, zStart=Z_START, xEnd=X_END, zEnd=Z_END),
        m1Parameters=M1Parameters(
            include_m1=include_m1, inspect_position=InspectPosition.G30, stop_spindle=False),
        zEndBecomesNewZ0=new_datum,
    )


def moves(op):
    """The G0 / G1 moves, as (word, x, z): a word left out where it does
    not change."""
    found, x, z = [], None, None
    for line in generate_facing_gcode(op):
        m = re.match(r"/?(G[01])((?: [XZ]\S+)+)$", line)
        if m:
            words = dict((w[0], float(w[1:])) for w in m.group(2).split())
            x, z = words.get("X", x), words.get("Z", z)
            found.append((m.group(1), x, z))
    return found


def diagonal_exits(op):
    """Rapids off the end of a cut - from X End - moving both axes at once."""
    found, previous = [], None
    for move in moves(op):
        if (move[0] == "G0" and previous is not None and previous[0] == "G1"
                and previous[1] == pytest.approx(X_END)):
            found.append((move[1] - previous[1], move[2] - previous[2]))
        previous = move
    return found


# ── how it leaves the cut ──────────────────────────────────────────────────

def test_it_leaves_every_cut_at_45_degrees_by_the_retract():
    """X a diameter, so 2R on X is R on the part."""
    exits = diagonal_exits(facing(retract=2.0))
    assert exits
    for dx, dz in exits:
        assert dx == pytest.approx(4.0)
        assert dz == pytest.approx(2.0)


def test_the_retract_is_not_the_depth_of_cut():
    for dx, dz in diagonal_exits(facing(doc=0.5, retract=3.0)):
        assert dz == pytest.approx(3.0)


def test_a_zero_retract_falls_back_to_the_depth_of_cut():
    """Left at zero in the UI it would otherwise rub the face on the way out."""
    for dx, dz in diagonal_exits(facing(doc=0.5, retract=0.0)):
        assert dz == pytest.approx(0.5)


# ── the passes ─────────────────────────────────────────────────────────────

def test_it_cuts_down_to_z_end_by_the_depth_of_cut():
    cuts = [z for word, x, z in moves(facing(doc=1.0)) if word == "G1" and x == pytest.approx(X_END)]
    assert cuts == pytest.approx([0.0, -1.0, -2.0])


def test_the_moves_are_the_ones_the_preview_draws():
    """The preview is drawn from the moves the G-code was written with: the
    same, in the same order - the first, the approach, left out."""
    op = facing(doc=0.7, retract=1.5)
    path = GcodeEmitter()
    facing_toolpath(op, path)
    kept = path.moves
    preview = facing_preview(op)
    drawn = [("G1", f.x1, f.z1) for f in preview.feeds] + [("G0", r.x1, r.z1) for r in preview.rapids]
    assert sorted(drawn) == sorted(("G1" if m.feed else "G0", 2 * m.r1, m.z1) for m in kept)
    assert [("G1" if m.feed else "G0", 2 * m.r1, m.z1) for m in kept] == moves(op)[1:]


def test_a_word_that_does_not_change_is_left_out():
    """Down to the next pass is along Z only: no X written for it."""
    assert "G1 Z0.000" in generate_facing_gcode(facing(doc=1.0))


def test_no_depth_of_cut_is_an_error_not_an_endless_loop():
    lines = generate_facing_gcode(facing(doc=0.0))
    assert any("ERROR" in line for line in lines)


# ── pause to inspect ───────────────────────────────────────────────────────

def m1_calls(op):
    return [line for line in generate_facing_gcode(op) if line.startswith("M1")]


def test_no_m1_handling_unless_it_is_included():
    assert m1_calls(facing(include_m1=False)) == []


def test_m1_handling_after_every_pass_but_the_last():
    """At G30 (P2), the tool at X Start on the face just cut: where the remap
    of M1 brings it back to."""
    lines = generate_facing_gcode(facing(doc=1.0, include_m1=True))
    stops = [i for i, line in enumerate(lines) if line.startswith("M1")]
    assert [lines[i] for i in stops] == ["M1 P2 (Pause to inspect and retract to G30 position)"] * 2
    assert [lines[i - 2:i] for i in stops] == [[f"G0 X{X_START:.3f}", "G0 Z0.000"],
                                               [f"G0 X{X_START:.3f}", "G0 Z-1.000"]]


# ── what was already there stays ───────────────────────────────────────────

def test_the_optional_block_prefix_applies_to_every_move():
    lines = [line for line in generate_facing_gcode(facing(optional=True, include_m1=True)) if line]
    assert all(line.startswith("/") for line in lines)


def test_the_datum_line_is_still_emitted():
    lines = generate_facing_gcode(facing(new_datum=True))
    assert any("G10 L20" in line for line in lines)
