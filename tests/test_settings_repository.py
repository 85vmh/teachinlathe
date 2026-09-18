"""Tests for SettingsRepository.

The jog speed and its percentage are two views of one value; most of what can
go wrong here is the two drifting apart.
"""

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt5.QtCore import QCoreApplication  # noqa: E402

from teachinlathe.repositories.settings_repository import (  # noqa: E402
    JOG_SPEED, JOG_SPEED_PERCENTAGE, RAPID_PERCENTAGE,
    SettingSpec, SettingsRepository,
)


class FakeIni:
    """Matches the sim lathe: 3 units/s default, 10 units/s maximum."""

    def __init__(self, config_dir, default=180.0, maximum=600.0):
        self.config_dir = str(config_dir)
        self.default_jog_velocity = default
        self.max_jog_velocity = maximum


@pytest.fixture(scope="session")
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


@pytest.fixture
def repo(qt_app, tmp_path):
    def _make(**ini_kwargs):
        return SettingsRepository(path=str(tmp_path / "settings.json"),
                                  ini=FakeIni(tmp_path, **ini_kwargs))
    return _make


# -- defaults and bounds ----------------------------------------------------

def test_an_unwritten_setting_reads_its_default(repo):
    r = repo()
    assert r.get(RAPID_PERCENTAGE) == 50
    assert r.get(JOG_SPEED) == pytest.approx(180.0)


def test_an_undeclared_setting_reads_the_caller_default(repo):
    r = repo()
    assert r.get("nothing.here", 7) == 7
    assert r.get("nothing.here") is None


def test_values_are_clamped_to_their_bounds(repo):
    r = repo()
    r.set(RAPID_PERCENTAGE, 250)
    assert r.get(RAPID_PERCENTAGE) == 100

    r.set(RAPID_PERCENTAGE, -10)
    assert r.get(RAPID_PERCENTAGE) == 0


def test_values_are_coerced_to_the_declared_type(repo):
    r = repo()
    r.set(RAPID_PERCENTAGE, "75")
    assert r.get(RAPID_PERCENTAGE) == 75
    assert isinstance(r.get(RAPID_PERCENTAGE), int)


def test_a_value_that_cannot_be_read_falls_back_to_the_default(repo):
    r = repo()
    r.set(RAPID_PERCENTAGE, "not a number")
    assert r.get(RAPID_PERCENTAGE) == 50


# -- the jog speed / percentage pair ----------------------------------------

def test_the_percentage_is_a_view_of_the_speed(repo):
    r = repo()                       # max 600 u/min
    r.set(JOG_SPEED, 300.0)
    assert r.get(JOG_SPEED_PERCENTAGE) == 50


def test_setting_the_percentage_moves_the_speed(repo):
    r = repo()
    r.set(JOG_SPEED_PERCENTAGE, 25)
    assert r.get(JOG_SPEED) == pytest.approx(150.0)
    assert r.get(JOG_SPEED_PERCENTAGE) == 25


def test_the_percentage_is_clamped_before_it_moves_the_speed(repo):
    r = repo()
    r.set(JOG_SPEED_PERCENTAGE, 500)
    assert r.get(JOG_SPEED) == pytest.approx(600.0)


def test_changing_the_speed_announces_both(repo):
    r = repo()
    seen = []
    r.settingChanged.connect(lambda name, value: seen.append((name, value)))

    r.set(JOG_SPEED, 600.0)

    assert (JOG_SPEED, 600.0) in seen
    assert (JOG_SPEED_PERCENTAGE, 100) in seen


def test_a_machine_with_no_maximum_does_not_divide_by_zero(repo):
    r = repo(maximum=0.0)
    assert r.get(JOG_SPEED_PERCENTAGE) == 0


# -- notification -----------------------------------------------------------

def test_notify_only_fires_for_its_own_setting(repo):
    r = repo()
    seen = []
    r.notify(RAPID_PERCENTAGE, seen.append)

    r.set(JOG_SPEED, 300.0)
    assert seen == []

    r.set(RAPID_PERCENTAGE, 75)
    assert seen == [75]


def test_writing_the_same_value_again_stays_quiet(repo):
    r = repo()
    r.set(RAPID_PERCENTAGE, 75)
    seen = []
    r.notify(RAPID_PERCENTAGE, seen.append)
    r.set(RAPID_PERCENTAGE, 75)
    assert seen == []


# -- persistence ------------------------------------------------------------

def test_a_persistent_setting_survives_a_restart(repo, tmp_path):
    r = repo()
    r.set(RAPID_PERCENTAGE, 75)

    again = SettingsRepository(path=r.path, ini=FakeIni(tmp_path))
    assert again.get(RAPID_PERCENTAGE) == 75


def test_the_derived_percentage_is_not_written_to_the_file(repo, tmp_path):
    r = repo()
    r.set(JOG_SPEED_PERCENTAGE, 50)
    stored = json.loads(Path(r.path).read_text())
    assert JOG_SPEED in stored
    assert JOG_SPEED_PERCENTAGE not in stored, "it is derived, not stored"


def test_a_stored_value_out_of_bounds_is_clamped_on_load(repo, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({RAPID_PERCENTAGE: 999}))
    r = SettingsRepository(path=str(path), ini=FakeIni(tmp_path))
    assert r.get(RAPID_PERCENTAGE) == 100


def test_a_corrupt_settings_file_falls_back_to_defaults(repo, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ this is not json")
    r = SettingsRepository(path=str(path), ini=FakeIni(tmp_path))
    assert r.get(RAPID_PERCENTAGE) == 50


def test_a_settings_file_holding_a_list_is_ignored(repo, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("[1, 2, 3]")
    r = SettingsRepository(path=str(path), ini=FakeIni(tmp_path))
    assert r.get(RAPID_PERCENTAGE) == 50


def test_a_missing_settings_file_is_not_an_error(repo, tmp_path):
    r = SettingsRepository(path=str(tmp_path / "never" / "written.json"),
                           ini=FakeIni(tmp_path))
    assert r.get(RAPID_PERCENTAGE) == 50


# -- declaring new settings -------------------------------------------------

def test_a_setting_can_be_declared_at_runtime(repo):
    r = repo()
    r.declare("chuck.pressure", SettingSpec(default=4.0, value_type=float,
                                            min_value=0.0, max_value=10.0))
    assert r.get("chuck.pressure") == 4.0
    r.set("chuck.pressure", 99)
    assert r.get("chuck.pressure") == 10.0
