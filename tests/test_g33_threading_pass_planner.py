import math
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from teachinlathe.conversational.data_types import G33ThreadPassType  # noqa: E402
from teachinlathe.conversational.g33_threading_pass_planner import plan_g33_threading_passes  # noqa: E402


def _plan(**overrides):
    args = {
        "xReference": 20.0,
        "zStart": 0.0,
        "zEnd": -12.0,
        "pitch": 1.5,
        "firstRadialDepth": 0.2,
        "finalRadialDepth": 1.0,
        "minimumRadialIncrement": 0.0,
        "springPasses": 0,
        "infeedAngleDegrees": 0.0,
        "threadLocation": "OD",
    }
    args.update(overrides)
    return plan_g33_threading_passes(**args)


@pytest.mark.parametrize(
    ("thread_location", "z_start", "z_end", "expected_x", "expected_z_sign"),
    [
        ("OD", 0.0, -12.0, 18.0, -1.0),
        ("OD", -12.0, 0.0, 18.0, 1.0),
        ("ID", 0.0, -12.0, 22.0, -1.0),
        ("ID", -12.0, 0.0, 22.0, 1.0),
    ],
)
def test_thread_location_and_hand_control_x_and_z_offset_direction(
    thread_location, z_start, z_end, expected_x, expected_z_sign
):
    passes = _plan(
        threadLocation=thread_location,
        zStart=z_start,
        zEnd=z_end,
        infeedAngleDegrees=30.0,
    )

    final_pass = passes[-1]
    assert final_pass.x == pytest.approx(expected_x)
    assert math.copysign(1.0, final_pass.zOffset) == expected_z_sign


@pytest.mark.parametrize("angle", [0.0, 29.0, 29.5, 30.0])
def test_infeed_angle_sets_z_offset(angle):
    passes = _plan(infeedAngleDegrees=angle)

    final_pass = passes[-1]
    assert final_pass.zOffset == pytest.approx(-math.tan(math.radians(angle)))


def test_spring_passes_reuse_final_roughing_geometry():
    passes = _plan(springPasses=3, infeedAngleDegrees=29.0)
    roughing = [p for p in passes if p.type == G33ThreadPassType.ROUGHING]
    springs = [p for p in passes if p.type == G33ThreadPassType.SPRING]

    assert len(springs) == 3
    assert [spring.index for spring in springs] == [1, 2, 3]
    for spring in springs:
        assert spring.radialDepth == pytest.approx(roughing[-1].radialDepth)
        assert spring.radialIncrement == pytest.approx(0.0)
        assert spring.x == pytest.approx(roughing[-1].x)
        assert spring.zOffset == pytest.approx(roughing[-1].zOffset)
        assert spring.zStart == pytest.approx(roughing[-1].zStart)
        assert spring.zEnd == pytest.approx(roughing[-1].zEnd)
        assert spring.pitch == pytest.approx(roughing[-1].pitch)


def test_equal_area_distribution_has_constant_squared_depth_delta():
    passes = _plan(firstRadialDepth=0.25, finalRadialDepth=1.0)
    roughing = [p for p in passes if p.type == G33ThreadPassType.ROUGHING]

    deltas = []
    previous = 0.0
    for thread_pass in roughing:
        deltas.append(thread_pass.radialDepth**2 - previous**2)
        previous = thread_pass.radialDepth

    assert len(roughing) == 16
    assert deltas == pytest.approx([deltas[0]] * len(deltas))


def test_final_depth_is_reached_exactly_on_last_roughing_pass():
    passes = _plan(firstRadialDepth=0.3, finalRadialDepth=1.0)
    roughing = [p for p in passes if p.type == G33ThreadPassType.ROUGHING]

    assert roughing[-1].radialDepth == 1.0


def test_first_pass_does_not_exceed_requested_first_depth():
    first_depth = 0.3
    passes = _plan(firstRadialDepth=first_depth, finalRadialDepth=1.0)

    assert passes[0].radialDepth <= first_depth


def test_trajectory_length_remains_constant_after_z_offset():
    passes = _plan(zStart=2.0, zEnd=-14.0, infeedAngleDegrees=29.5)

    for thread_pass in passes:
        assert abs(thread_pass.zEnd - thread_pass.zStart) == pytest.approx(16.0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"firstRadialDepth": 0.0},
        {"finalRadialDepth": 0.0},
        {"firstRadialDepth": 2.0, "finalRadialDepth": 1.0},
        {"springPasses": -1},
        {"minimumRadialIncrement": -0.1},
        {"zStart": 1.0, "zEnd": 1.0},
        {"pitch": 0.0},
        {"infeedAngleDegrees": -0.1},
        {"infeedAngleDegrees": 30.1},
        {"threadLocation": "UNKNOWN"},
    ],
)
def test_validation(overrides):
    with pytest.raises(ValueError):
        _plan(**overrides)
