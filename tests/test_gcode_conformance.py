"""The moves the program's emitter keeps are the ones LinuxCNC's interpreter makes.

Random programs are written as the Conversational tab writes them and run
through rs274, LinuxCNC's interpreter on its own, with the subroutines the
machine has. For every operation whose moves the emitter knows
(OperationPath.known), those moves have to be what the interpreter makes,
one after the other, to the 0.1 µm - so what is drawn of a program from its
emitter is what the machine will do. Skipped without rs274 beside the
linuxcnc module on PYTHONPATH.
"""

import copy
import math
import random
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]

linuxcnc = pytest.importorskip("linuxcnc")
RS274 = Path(linuxcnc.__file__).resolve().parents[2] / "bin" / "rs274"
if not RS274.exists():
    pytest.skip(f"no rs274 at {RS274}", allow_module_level=True)

from teachinlathe.conversational.gcode import gcode_builder  # noqa: E402
from teachinlathe.conversational.logic.conversational_use_case import ConversationalUseCase  # noqa: E402
from teachinlathe.conversational.model.data_types import (  # noqa: E402
    InspectPosition, Operation, PassType, PredefinedPosition,
)
from teachinlathe.conversational.model.factories import make_default_operation, make_new_program  # noqa: E402
from teachinlathe.tooling.model.data_types import (  # noqa: E402
    BladeTool, DrillingTool, InsertSpec, TappingTool, ThreadingTool, ToolHolder, TurningTool,
)
from teachinlathe.tooling.model.tool_snapshot import ToolSnapshot  # noqa: E402

PROGRAMS = 40
#: How far a kept move may be from the interpreter's, in mm (it prints 4 decimals).
TOLERANCE = 1e-4

TOOLS = {1: TurningTool(cutting_tool_id=1, insert=InsertSpec("ccmt", "06", "02"), orientation=2,
                        front_angle=95, back_angle=5),
         2: TurningTool(cutting_tool_id=2, insert=InsertSpec("vbmt", "16", "04"), orientation=6,
                        front_angle=72.5, back_angle=72.5),
         3: BladeTool(cutting_tool_id=3, blade_width=3, orientation=6),
         5: DrillingTool(cutting_tool_id=5, diameter=8),
         6: TappingTool(cutting_tool_id=6, diameter=8, pitch=1.25),
         7: ThreadingTool(cutting_tool_id=7, insert=InsertSpec("ER", "16", ""), orientation=6, pitch=1.5)}
LIBRARY = ToolSnapshot(holders={n: ToolHolder(tool_holder_id=n, cutting_tool_id=n) for n in TOOLS},
                       tools=TOOLS)
#: The operations drawn from, and the holders each may cut with.
HOLDERS_OF = {"facing": [1, 3], "drilling": [5], "tapping": [6], "parting": [3], "g33Threading": [7],
              "positionAt": []}


# ── the programs ────────────────────────────────────────────────────────────

def _point(kind, x, z):
    keys = ("x_start", "z_start") if kind == "startPoint" else ("x_end", "z_end")
    return {"type": kind, keys[0]: x, keys[1]: z, "blend": {"type": "none"}}


def _profile_ops(rnd, scale):
    """A profile - a neck behind a peak, a radius on the shoulder - its
    roughing, a rest roughing below it now and then, and its contour."""
    primitives = ([_point("startPoint", 30 * scale, 0)]
                  + [_point("lineTo", x * scale, z) for x, z in ((30, -11), (54, -24), (26, -35), (38, -45))]
                  + [dict(_point("lineTo", 70 * scale, -45), blend={"type": "fillet", "fillet_radius": 3.0})]
                  + [_point("lineTo", 70 * scale, -50)])
    profile = make_default_operation("defineProfile")
    profile = Operation.from_dict({**profile.to_dict(), "profile_id": 1, "profile_primitives": primitives})
    rough = make_default_operation("profileRoughing")
    rough.profilingParameters.profile_id = 1
    rough.profilingParameters.xStart, rough.profilingParameters.zStart = 74 * scale, 1.0
    rough.cuttingParameters.doc, rough.cuttingParameters.retract = rnd.choice([0.8, 1.5]), 0.5
    rough.profileRoughingStrategy.pass_type = rnd.choice([PassType.AXIAL, PassType.RADIAL])
    rough.stockToLeave.stockToLeaveX, rough.stockToLeave.stockToLeaveZ = 0.1, 0.05
    ops = [profile, rough]
    if rnd.random() < 0.5:
        rest = copy.deepcopy(rough)
        rest.restMaterial = True
        ops.append(rest)
    contour = make_default_operation("profileContour")
    contour.profilingParameters.profile_id = 1
    contour.profilingParameters.xStart, contour.profilingParameters.zStart = 74 * scale, 1.0
    ops.append(contour)
    return ops


def _program(rnd, folder):
    use_case = ConversationalUseCase(programs_dir=str(folder), ini=SimpleNamespace(), tools=LIBRARY)
    program = make_new_program(str(folder))
    program.header.datum = rnd.choice([1, 2])
    program.operations = []

    def u(a, b):
        return round(rnd.uniform(a, b), 3)

    for index in range(rnd.randint(2, 7)):
        op_type = rnd.choice(list(HOLDERS_OF))
        op = make_default_operation(op_type, order=index + 1)
        op.is_optional_block = rnd.random() < 0.25
        if hasattr(op, "m1Parameters"):
            op.m1Parameters.include_m1 = rnd.random() < 0.5
            op.m1Parameters.inspect_position = rnd.choice(list(InspectPosition))
        if op_type == "facing":
            g = op.geometryParameters
            g.xStart, g.zStart, g.xEnd = u(20, 60), u(0, 2), u(-1, 5)
            g.zEnd = g.zStart - u(0, 3)
            op.cuttingParameters.doc = rnd.choice([0.3, 0.5, 1.0])
            op.cuttingParameters.retract = rnd.choice([0.0, 1.0])
            op.zEndBecomesNewZ0 = rnd.random() < 0.3
        elif op_type == "drilling":
            d = op.drillingParameters
            d.zStart = u(-1, 2)
            d.zEnd = d.zStart - u(3, 30)
            d.peckDepth = rnd.choice([0, 3, 5])
            d.toolClearance = u(0, 4)
            d.dwellTime = rnd.choice([0, 0.5])
        elif op_type == "tapping":
            t = op.tappingParameters
            t.zStart = u(-1, 2)
            t.zEnd = t.zStart - u(3, 15)
        elif op_type == "g33Threading":
            op.major_diameter = u(10, 30)
            op.minor_diameter = round(op.major_diameter - 1.8, 3)
            op.z_start, op.z_end = 2.0, -u(8, 20)
        program.operations.append(op)
        if HOLDERS_OF[op_type]:
            use_case.use_tool(program, index, rnd.choice(HOLDERS_OF[op_type]), rnd.choice([PredefinedPosition.G28, PredefinedPosition.G30]))
    if rnd.random() < 0.5:
        for op in _profile_ops(rnd, rnd.choice([0.8, 1.0, 1.2])):
            op.order = len(program.operations) + 1
            op.is_optional_block = rnd.random() < 0.2
            if hasattr(op, "m1Parameters"):
                op.m1Parameters.include_m1 = rnd.random() < 0.5
            program.operations.append(op)
            if hasattr(op, "toolRef"):
                use_case.use_tool(program, len(program.operations) - 1,
                                  2 if getattr(op, "restMaterial", False) else rnd.choice([1, 2]))
    if rnd.random() < 0.5:
        # a groove, roughed with the blade, and finished
        for op_type in ("defineRadialProfile", "grooveRoughing", "grooveFinishing"):
            op = make_default_operation(op_type, order=len(program.operations) + 1)
            op.is_optional_block = rnd.random() < 0.2
            if op_type == "grooveRoughing":
                op.stockToLeaveEnabled = rnd.random() < 0.5
                op.cuttingParameters.peckDepth = rnd.choice([2.0, 3.0])
            program.operations.append(op)
            if hasattr(op, "toolRef"):
                use_case.use_tool(program, len(program.operations) - 1, 3)
    return program


def _toolpath(program):
    return gcode_builder.program_toolpath(program, LIBRARY)


# ── the interpreter ─────────────────────────────────────────────────────────

_CALL = re.compile(r"^\s*\d+ N\.\.\.\.\. (\w+)\((.*)\)$")


def _interpreter_moves(ngc: str, folder: Path):
    """The interpreter's moves of ``ngc``: [(feed, z0, r0, z1, r1)], those
    of no length left out; and anything it said that is not a canonical
    call (an error)."""
    (folder / "rs.ini").write_text(
        "[RS274NGC]\n"
        f"SUBROUTINE_PATH = {ROOT / 'subroutines'}\n"
        "REMAP = M6 modalgroup=6 ngc=m6_remap\n"
        "REMAP = M1 modalgroup=4 argspec=p ngc=m1_remap\n"
        "PARAMETER_FILE = rs.var\n"
        "[EMCIO]\nTOOL_TABLE = tool.tbl\n")
    (folder / "rs.var").write_text("")
    (folder / "tool.tbl").write_text("".join(f"T{n} P{n} X0 Z0 D0\n" for n in TOOLS))
    (folder / "program.ngc").write_text(ngc)
    done = subprocess.run([str(RS274), "-i", "rs.ini", "-v", "rs.var", "-t", "tool.tbl", "-g",
                           str(folder / "program.ngc")], cwd=folder, capture_output=True, text=True,
                          timeout=60)
    moves, said = [], []
    r = z = 0.0
    offset = None         # the work offset in use, (r, z)
    for line in (done.stdout + done.stderr).splitlines():
        call = _CALL.match(line)
        if call is None:
            if line.strip() and line.strip() != "executing":
                said.append(line.strip())
            continue
        name, args = call.groups()
        values = [float(v) for v in re.findall(r"-?\d+\.\d+", args)]
        if name == "SET_G5X_OFFSET":
            # its moves are in the work's coordinates: where the machine is,
            # in the new ones - after a G10 L20, Z0 where it stands
            new = (values[0], values[2])
            if offset is not None:
                r, z = r - (new[0] - offset[0]), z - (new[1] - offset[1])
            offset = new
            continue
        if name in ("STRAIGHT_TRAVERSE", "STRAIGHT_FEED"):
            new_r, new_z = values[0], values[2]
        elif name == "ARC_FEED":
            new_z, new_r = values[0], values[1]      # the ZX plane: first Z, then X
        elif name == "RIGID_TAP":
            # G33.1: in along Z with the spindle and back out to where it was
            tapped_z = values[2]
            if abs(tapped_z - z) > TOLERANCE:
                moves.append((True, z, r, tapped_z, r))
                moves.append((True, tapped_z, r, z, r))
            continue
        else:
            continue
        if math.hypot(new_r - r, new_z - z) > TOLERANCE:
            moves.append((name != "STRAIGHT_TRAVERSE", z, r, new_z, new_r))
        r, z = new_r, new_z
    return moves, said


def _same(move, made):
    feed, z0, r0, z1, r1 = made
    return (move.feed == feed
            and all(abs(a - b) <= TOLERANCE for a, b in
                    ((move.z0, z0), (move.r0, r0), (move.z1, z1), (move.r1, r1))))


# ── the test ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("seed", range(PROGRAMS))
def test_the_kept_moves_are_the_interpreters(seed, tmp_path):
    program = _program(random.Random(seed), tmp_path)
    path = _toolpath(program)
    made, said = _interpreter_moves("\n".join(path.lines) + "\n", tmp_path)
    assert said == [], said

    # each known operation's moves, in turn, where the interpreter makes
    # them: from its first on, every one of them and nothing else between
    cursor = 0
    for operation in path.operations:
        if not operation.known or not operation.moves:
            continue
        name = program.operations[operation.index].display_name()
        first = operation.moves[0]
        start = next((i for i in range(cursor, len(made)) if _same(first, made[i])), None)
        assert start is not None, f"#{operation.index + 1} {name}: its first move is not made"
        for offset, move in enumerate(operation.moves):
            assert start + offset < len(made) and _same(move, made[start + offset]), (
                f"#{operation.index + 1} {name}: move {offset} kept as {move}, "
                f"made as {made[start + offset] if start + offset < len(made) else 'nothing'}")
        cursor = start + len(operation.moves)


def test_the_programs_have_known_operations(tmp_path):
    """The test above checks something: most programs have operations whose
    moves are known."""
    known = 0
    for seed in range(PROGRAMS):
        program = _program(random.Random(seed), tmp_path)
        known += any(type(op).__name__ in ("Facing", "Drilling", "ProfileRoughing", "ProfileContour",
                                           "GrooveRoughing", "GrooveFinishing")
                     for op in program.operations)
    assert known > PROGRAMS // 2
