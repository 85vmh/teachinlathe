"""Parting off at Z Pos: the part is as long as from Z0 to Z Pos.

Reported 2026-11-25: a part came off a blade's width shorter than the
Parting's Z Pos said. The point LinuxCNC moves is the one the blade was touched
off on - its left corner, its middle or its right corner (the holder's
z_offset_place) - and the G-code took Z Pos as where that point goes. The part
is on the blade's Z+ side: its Z+ edge is what has to be at Z Pos.

What is pinned down here:

* The blade's Z+ edge cuts at Z Pos whatever point of it was touched off on:
  the point touched off on goes to Z Pos less its width (left corner), less
  half of it (middle), or to Z Pos itself (right corner).
* An edge break is cut on the part's side all the same: every Z moves with it.
* A tool that is not a blade, or none (the editor's drawing), cuts at Z Pos.
* The program's G-code is written for the blade it cuts with.
"""

import re
from types import SimpleNamespace

import pytest

from teachinlathe.conversational.gcode import gcode_builder
from teachinlathe.conversational.gcode.operations.parting import part_side_offset, parting_toolpath
from teachinlathe.conversational.gcode.toolpath import GcodeEmitter
from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase
from teachinlathe.conversational.model.data_types import BlendType
from teachinlathe.conversational.model.factories import make_default_operation, make_new_program
from teachinlathe.tooling.model.data_types import (
    BladeTool, InsertSpec, MountedTool, ToolHolder, TurningTool, ZOffsetPlace,
)
from teachinlathe.tooling.model.tool_snapshot import ToolSnapshot

WIDTH = 3.0
Z_POS = -40.0


def _parting(x_start=50.0, x_end=-1.0, z_pos=Z_POS):
    op = make_default_operation("parting")
    p = op.partingParameters
    p.xStart, p.xEnd, p.zPos, p.second_feed_x_pos = x_start, x_end, z_pos, x_end
    return op


def _blade(place, width=WIDTH):
    return MountedTool(3, BladeTool(cutting_tool_id=3, blade_width=width, orientation=6), place)


def _moves(op, tool):
    path = GcodeEmitter()
    parting_toolpath(op, path, tool)
    return path.moves


def _feed_zs(op, tool):
    return {round(m.z1, 4) for m in _moves(op, tool) if m.feed}


@pytest.mark.parametrize("place,touched_off_z", [
    (ZOffsetPlace.LEFT, Z_POS - WIDTH),
    (ZOffsetPlace.MIDDLE, Z_POS - WIDTH / 2),
    (ZOffsetPlace.RIGHT, Z_POS),
])
def test_the_blades_part_side_edge_cuts_at_z_pos(place, touched_off_z):
    blade = _blade(place)

    zs = _feed_zs(_parting(), blade)

    assert zs == {touched_off_z}
    # its Z+ edge, from the point touched off on
    assert touched_off_z + part_side_offset(blade) == Z_POS


def test_a_blade_whose_place_is_not_known_is_taken_by_its_middle():
    assert _feed_zs(_parting(), _blade(None)) == {Z_POS - WIDTH / 2}


@pytest.mark.parametrize("tool", [
    None,
    MountedTool(1, TurningTool(cutting_tool_id=1, insert=InsertSpec("ccmt", "06", "02"), orientation=2,
                               front_angle=95, back_angle=5), ZOffsetPlace.LEFT),
])
def test_no_blade_cuts_at_z_pos(tool):
    assert _feed_zs(_parting(), tool) == {Z_POS}


@pytest.mark.parametrize("blend", [BlendType.CHAMFER, BlendType.FILLET])
def test_an_edge_break_moves_with_the_blade(blend):
    op = _parting()
    op.edgeBreak.blend_type = blend
    op.edgeBreak.chamfer_width = op.edgeBreak.fillet_radius = 1.0

    at_edge, from_left = _moves(op, _blade(ZOffsetPlace.RIGHT)), _moves(op, _blade(ZOffsetPlace.LEFT))

    # the same moves, a blade's width along Z-
    assert [(m.z0 - WIDTH, m.z1 - WIDTH) for m in at_edge] == pytest.approx([(m.z0, m.z1) for m in from_left])


# ── the program ─────────────────────────────────────────────────────────

def _library(place):
    tools = {3: BladeTool(cutting_tool_id=3, blade_width=WIDTH, orientation=6)}
    holders = {3: ToolHolder(tool_holder_id=3, cutting_tool_id=3, z_offset_place=place)}
    return ToolSnapshot(holders=holders, tools=tools)


@pytest.mark.parametrize("place,z", [(ZOffsetPlace.LEFT, Z_POS - WIDTH), (ZOffsetPlace.RIGHT, Z_POS)])
def test_the_programs_gcode_is_written_for_the_blade_it_cuts_with(tmp_path, place, z):
    library = _library(place)
    use_case = ConversationalUseCase(programs_dir=str(tmp_path), ini=SimpleNamespace(), tools=library)
    program = make_new_program(str(tmp_path))
    program.operations = [_parting()]
    use_case.use_tool(program, 0, 3)

    lines = gcode_builder.program_toolpath(program, library).lines

    plunges = [line for line in lines if re.search(rf"Z{z:.3f}\b", line)]
    assert plunges, f"nothing at Z{z:.3f} in:\n" + "\n".join(lines)
    # the operator is told which point of the blade the program is written for
    corner = "left corner" if place is ZOffsetPlace.LEFT else "right corner"
    assert f"( blade touch point: {corner} )" in lines
