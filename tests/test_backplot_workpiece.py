"""Finding the conversational header beside a generated G-code file.

The stock outline is the only thing on the backplot that cannot be recovered
from the program itself, so this lookup is what stands between the operator
and a plot with no bar on it. It fails quietly by design - a hand-written file
has no header and must still preview - which is exactly why the cases where it
should succeed are pinned down here.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.widgets.backplot import workpiece  # noqa: E402

HEADER = {"header": {"workpiece": {"material": "C45",
                                   "external_diameter": 40.0,
                                   "internal_diameter": 0.0,
                                   "stock_length": 120.0}}}


@pytest.fixture
def program(tmp_path):
    """A generated file and the programs directory beside it, as the machine
    lays them out: ``<root>/ngc/part.ngc`` and ``<root>/Conversational Json``.
    """
    ngc_dir = tmp_path / "ngc"
    ngc_dir.mkdir()
    json_dir = tmp_path / workpiece.JSON_SUBDIRECTORY
    json_dir.mkdir()
    return ngc_dir, json_dir


def write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_found_by_the_header_comment(program):
    ngc_dir, json_dir = program
    gcode = ngc_dir / "part.ngc"
    gcode.write_text("(Program: shaft.json)\nG0 X0\n", encoding="utf-8")
    write(json_dir / "shaft.json", HEADER)

    found = workpiece.for_program(str(gcode))
    assert found["external_diameter"] == 40.0
    assert found["stock_length"] == 120.0


def test_found_by_the_file_name_when_there_is_no_comment(program):
    ngc_dir, json_dir = program
    gcode = ngc_dir / "part.ngc"
    gcode.write_text("G0 X0\n", encoding="utf-8")
    write(json_dir / "part.json", HEADER)

    assert workpiece.for_program(str(gcode))["stock_length"] == 120.0


def test_found_beside_the_gcode(program):
    ngc_dir, _json_dir = program
    gcode = ngc_dir / "part.ngc"
    gcode.write_text("G0 X0\n", encoding="utf-8")
    write(ngc_dir / "part.json", HEADER)

    assert workpiece.for_program(str(gcode))["stock_length"] == 120.0


def test_the_header_comment_wins_over_the_file_name(program):
    ngc_dir, json_dir = program
    gcode = ngc_dir / "part.ngc"
    gcode.write_text("(Program: shaft.json)\nG0 X0\n", encoding="utf-8")
    write(json_dir / "shaft.json", HEADER)
    write(json_dir / "part.json",
          {"header": {"workpiece": {"external_diameter": 999.0}}})

    assert workpiece.for_program(str(gcode))["external_diameter"] == 40.0


def test_a_comment_naming_a_path_is_taken_as_a_name(program):
    """The generator writes whatever path it had; only the basename is used."""
    ngc_dir, json_dir = program
    gcode = ngc_dir / "part.ngc"
    gcode.write_text("(Program: /some/old/path/shaft.json)\n",
                     encoding="utf-8")
    write(json_dir / "shaft.json", HEADER)

    assert workpiece.for_program(str(gcode))["stock_length"] == 120.0


def test_stickout_stands_in_for_a_missing_stock_length(program):
    ngc_dir, json_dir = program
    gcode = ngc_dir / "part.ngc"
    gcode.write_text("G0 X0\n", encoding="utf-8")
    write(json_dir / "part.json",
          {"header": {"workpiece": {"external_diameter": 40.0,
                                    "stickout_length": 55.0}}})

    assert workpiece.for_program(str(gcode))["stock_length"] == 55.0


# ── the quiet failures, which must stay quiet ──────────────────────────────

def test_a_hand_written_file_has_no_workpiece(program):
    ngc_dir, _json_dir = program
    gcode = ngc_dir / "byhand.ngc"
    gcode.write_text("G0 X0 Z0\nM2\n", encoding="utf-8")
    assert workpiece.for_program(str(gcode)) == {}


def test_unreadable_json_is_not_an_error(program):
    ngc_dir, json_dir = program
    gcode = ngc_dir / "part.ngc"
    gcode.write_text("G0 X0\n", encoding="utf-8")
    (json_dir / "part.json").write_text("{ not json", encoding="utf-8")
    assert workpiece.for_program(str(gcode)) == {}


def test_json_without_a_workpiece_is_not_an_error(program):
    ngc_dir, json_dir = program
    gcode = ngc_dir / "part.ngc"
    gcode.write_text("G0 X0\n", encoding="utf-8")
    write(json_dir / "part.json", {"header": {}})
    assert workpiece.for_program(str(gcode)) == {}


def test_no_file_at_all():
    assert workpiece.for_program("") == {}
    assert workpiece.for_program("/nonexistent/part.ngc") == {}


def test_the_comment_is_only_looked_for_in_the_header(program):
    """A line that looks like the header comment, far enough down the file,
    is not one - the scan stops after HEADER_LINES."""
    ngc_dir, json_dir = program
    gcode = ngc_dir / "part.ngc"
    body = "G0 X0\n" * (workpiece.HEADER_LINES + 5)
    gcode.write_text(body + "(Program: shaft.json)\n", encoding="utf-8")
    write(json_dir / "shaft.json", HEADER)
    write(json_dir / "part.json",
          {"header": {"workpiece": {"external_diameter": 999.0}}})

    assert workpiece.for_program(str(gcode))["external_diameter"] == 999.0
