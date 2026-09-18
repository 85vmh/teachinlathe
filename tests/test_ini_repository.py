import os
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.repositories import AxisLimits, IniRepository  # noqa: E402


@pytest.fixture
def ini(tmp_path):
    """Build an INI file from *body* and return its IniRepository."""
    def _make(body, **env):
        path = tmp_path / "machine.ini"
        path.write_text(textwrap.dedent(body))
        old = {k: os.environ.get(k) for k in ("INI_FILE_NAME", "CONFIG_DIR")}
        os.environ["CONFIG_DIR"] = env.get("config_dir", str(tmp_path))
        os.environ["INI_FILE_NAME"] = str(path)
        try:
            return IniRepository(str(path))
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    return _make


def test_axis_limits_are_parsed(ini):
    repo = ini("""
        [AXIS_X]
        MIN_LIMIT = -1.5
        MAX_LIMIT = 150.0
        [AXIS_Z]
        MIN_LIMIT = 0
        MAX_LIMIT = 400
    """)
    assert repo.axis_limits("X") == AxisLimits(-1.5, 150.0)
    assert repo.axis_limits("z") == AxisLimits(0.0, 400.0)


def test_axis_limits_missing_entry_returns_none(ini):
    repo = ini("[AXIS_X]\nMIN_LIMIT = 0\n")
    assert repo.axis_limits("X") is None    # MAX_LIMIT absent
    assert repo.axis_limits("Y") is None    # section absent


def test_axis_limits_supports_index_and_attribute_access(ini):
    limits = ini("[AXIS_X]\nMIN_LIMIT = 2\nMAX_LIMIT = 8\n").axis_limits("X")
    assert (limits.min, limits.max) == (2.0, 8.0)
    assert (limits[0], limits[1]) == (2.0, 8.0)


def test_tool_table_relative_path_resolves_against_config_dir(ini, tmp_path):
    repo = ini("[EMCIO]\nTOOL_TABLE = lathe.tbl\n")
    assert repo.tool_table_file == str(tmp_path / "lathe.tbl")


def test_tool_table_defaults_when_unset(ini, tmp_path):
    assert ini("[DISPLAY]\n").tool_table_file == str(tmp_path / "tool.tbl")


def test_program_prefix_falls_back_when_path_missing(ini, tmp_path):
    repo = ini("[DISPLAY]\nPROGRAM_PREFIX = %s\n" % (tmp_path / "nope"))
    # The configured path does not exist, so it must not be returned.
    assert repo.program_prefix != str(tmp_path / "nope")
    assert os.path.exists(repo.program_prefix)


def test_program_prefix_is_used_when_it_exists(ini, tmp_path):
    (tmp_path / "nc").mkdir()
    repo = ini("[DISPLAY]\nPROGRAM_PREFIX = nc\n")
    assert repo.program_prefix == str(tmp_path / "nc")


def test_subroutine_search_dirs_start_with_program_prefix(ini, tmp_path):
    (tmp_path / "nc").mkdir()
    (tmp_path / "subs").mkdir()
    repo = ini("""
        [DISPLAY]
        PROGRAM_PREFIX = nc
        [RS274NGC]
        SUBROUTINE_PATH = subs:%s
    """ % (tmp_path / "other"))
    assert repo.subroutine_search_dirs == [
        str(tmp_path / "nc"),
        str(tmp_path / "subs"),
        str(tmp_path / "other"),
    ]


def test_subroutine_search_dirs_without_entry(ini, tmp_path):
    (tmp_path / "nc").mkdir()
    repo = ini("[DISPLAY]\nPROGRAM_PREFIX = nc\n")
    assert repo.subroutine_search_dirs == [str(tmp_path / "nc")]


def test_unreadable_ini_falls_back_instead_of_raising():
    repo = IniRepository("/nonexistent/machine.ini")
    assert repo.axis_limits("X") is None
    assert repo.find("DISPLAY", "PROGRAM_PREFIX") is None
    assert os.path.exists(repo.program_prefix)
