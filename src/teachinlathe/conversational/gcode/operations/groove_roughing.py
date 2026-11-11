"""Groove Roughing: a groove plunged with a blade from its middle out to
its flanks, a peck at a time, then its contour from either rim to the middle
with the blade's corner on that side - to the profile with its stock to
leave. What it shares with the other groove operations is groove_common's."""

import dataclasses
from dataclasses import dataclass
from typing import Optional, Tuple

from teachinlathe.conversational.model.data_types import GrooveRoughingStrategy, ProfilingType

from .groove_common import (
    OVER_THE_OUTSIDE,
    Corner,
    begin_gcode,
    blade_control,
    blade_obstacle,
    blade_problem,
    blade_radii,
    blade_start_x,
    blade_width,
    contour_edge,
    drawn_groove,
    emit_contour_section,
    enter,
    front_z,
    groove_path,
    on_diameter,
    operation_error,
    outside_x,
    outward_sign,
    over_x,
    path_bounds,
    pause_to_inspect,
    reverse_path,
    safe_x_for_contour,
    split_path_at_z,
    start_diameter_of,
    stock_allowance,
    stock_to_leave,
    to_middle,
)
from .profiling.geometry import ROUNDING, SAME_MM, StartPoint, ToolpathLine
from .profiling.operation_input import GrooveCut
from .profiling.plan_drawing import flatten_path
from .profiling.shapes import FAR, drop_onto
from ..toolpath import Arrows, DrawnLine, GcodeEmitter, OperationPreview

TITLE = "Groove Roughing"


# ── the pecks ──────────────────────────────────────────────────────────────


def _append_peck(gcode, z_pos, safe_x, final_x, peck_depth, clearance, dwell_time):
    if peck_depth <= 0:
        peck_depth = abs(safe_x - final_x)
    direction = -1 if final_x < safe_x else 1
    outside = -direction
    current_x = safe_x

    gcode.rapid(x=safe_x)
    gcode.rapid(z=z_pos)
    while True:
        remaining = abs(final_x - current_x)
        if remaining <= SAME_MM:
            break
        next_x = current_x + direction * min(abs(peck_depth), remaining)
        # The operation sets G95 F once before its first cut. Keep the feed
        # modal across pecks instead of repeating F on every G1.
        gcode.feed(x=next_x)
        if dwell_time > 0:
            gcode.dwell(dwell_time)
        current_x = next_x
        if abs(final_x - current_x) <= SAME_MM:
            break
        retract_x = current_x + outside * on_diameter(clearance)
        gcode.rapid(x=retract_x)
        gcode.rapid(x=current_x)
    gcode.rapid(x=safe_x)


def _next_depth(current_x, final_x, peck_depth):
    if peck_depth <= 0:
        return final_x
    direction = -1 if final_x < current_x else 1
    next_x = current_x + direction * abs(peck_depth)
    if direction < 0:
        return max(next_x, final_x)
    return min(next_x, final_x)


def _next_center_depth(current_x, final_x, peck_depth):
    return _next_depth(current_x, final_x, abs(peck_depth) * 2.0)


def _is_at_depth(current_x, final_x):
    if final_x < current_x:
        return current_x <= final_x + SAME_MM
    return current_x >= final_x - SAME_MM


def _append_incremental_cut(
    gcode,
    z_pos,
    current_x,
    target_x,
    clearance,
    dwell_time,
    retract_reference_x=None,
):
    if abs(target_x - current_x) <= SAME_MM:
        return
    # out of the cut is back the way it came in, from wherever it goes to
    outward = 1.0 if current_x > target_x else -1.0
    approach_x = current_x + outward * on_diameter(clearance)
    gcode.rapid(x=approach_x)
    gcode.rapid(z=z_pos)
    # G95 F was set once at the start of this operation.
    gcode.feed(x=target_x)
    if dwell_time > 0:
        gcode.dwell(dwell_time)
    # backed off to clear the other plunge too, so the move over to it is
    # in the air: out past the shallower of the two - never deeper than
    # this cut, whatever depth the other is at
    if retract_reference_x is None:
        retract_reference_x = target_x
    shallower = max(retract_reference_x, target_x) if outward > 0 else min(retract_reference_x, target_x)
    retract_x = shallower + outward * on_diameter(clearance)
    gcode.rapid(x=retract_x)


def _append_center_pair_roughing(
    gcode,
    first_z,
    first_final_x,
    second_z,
    second_final_x,
    top_x,
    peck_depth,
    clearance,
    dwell_time,
):
    first_depth = top_x
    second_depth = top_x

    first_target = _next_depth(first_depth, first_final_x, peck_depth)
    _append_incremental_cut(
        gcode,
        first_z,
        first_depth,
        first_target,
        clearance,
        dwell_time,
        retract_reference_x=second_depth,
    )
    first_depth = first_target

    while not (_is_at_depth(first_depth, first_final_x) and _is_at_depth(second_depth, second_final_x)):
        if not _is_at_depth(second_depth, second_final_x):
            next_depth = _next_center_depth(second_depth, second_final_x, peck_depth)
            _append_incremental_cut(
                gcode,
                second_z,
                second_depth,
                next_depth,
                clearance,
                dwell_time,
                retract_reference_x=first_depth,
            )
            second_depth = next_depth

        if not _is_at_depth(first_depth, first_final_x):
            next_depth = _next_center_depth(first_depth, first_final_x, peck_depth)
            _append_incremental_cut(
                gcode,
                first_z,
                first_depth,
                next_depth,
                clearance,
                dwell_time,
                retract_reference_x=second_depth,
            )
            first_depth = next_depth


def _append_unique_position(positions, value, z_min, z_max):
    if value < z_min - SAME_MM or value > z_max + SAME_MM:
        return
    if not any(abs(existing - value) < SAME_MM for existing in positions):
        positions.append(value)


def _center_positions(center, left_limit, right_limit, initial_offset, afterwards_offset):
    positions = []
    if initial_offset > 0:
        right_seed = center + initial_offset / 2.0
        left_seed = center - initial_offset / 2.0
        _append_unique_position(positions, right_seed, left_limit, right_limit)
        _append_unique_position(positions, left_seed, left_limit, right_limit)
    else:
        right_seed = center
        left_seed = center
        _append_unique_position(positions, center, left_limit, right_limit)

    if afterwards_offset <= 0:
        afterwards_offset = initial_offset if initial_offset > 0 else 1.0

    z = right_seed + afterwards_offset
    while z <= right_limit + SAME_MM:
        _append_unique_position(positions, z, left_limit, right_limit)
        z += afterwards_offset

    z = left_seed - afterwards_offset
    while z >= left_limit - SAME_MM:
        _append_unique_position(positions, z, left_limit, right_limit)
        z -= afterwards_offset

    return positions


def _plunge_x(inside, z, start_x, profile_type):
    """How deep the touch-off point plunged at ``z`` from the start diameter
    ``start_x`` goes before the blade meets the part or its stock -
    ``inside``, the blade's obstacle (blade_obstacle) shrunk by SAME_MM, so
    a blade's side flush with a flank goes on down it: the X it stops at."""
    sign = outward_sign(profile_type)
    r_start = sign * start_x / 2.0
    return 2.0 * sign * drop_onto(inside, z, r_start + OVER_THE_OUTSIDE, r_start - FAR, SAME_MM)


def _cut_path(path, profile_type, radial, axial):
    """What the blade cuts to: ``path``, the groove's profile, offset by the
    stock to leave (stock_allowance) - as lines - or itself with none."""
    allowance = stock_allowance(path, profile_type, radial, axial)
    if len(allowance) < 2:
        return path
    z, x = allowance[0]
    return [StartPoint(x, z)] + [ToolpathLine(x, z) for z, x in allowance[1:]]


def _append_contour(gcode, safe_x, obstacle, path, center_z, clearance, profile_type,
                    left_radius, right_radius, half_width, control, enter_at=None):
    """The finish contour: the blade on the part with its stock (``obstacle``)
    from the Z+ rim, its right corner cutting, to the groove's middle - its
    middle past it by the rest of its end - then from the Z- rim, its left
    corner cutting, the same."""
    edge = contour_edge(obstacle, path, 2.0 * half_width)
    z_control = control * half_width
    z_plus = to_middle(edge, center_z - max(half_width - right_radius, 0.0) + z_control)
    z_minus = to_middle(edge[::-1], center_z + max(half_width - left_radius, 0.0) + z_control)
    contour_safe_x = safe_x_for_contour([z_plus, z_minus], safe_x, clearance, profile_type)
    if enter_at is not None and z_plus:
        # nothing plunged before it: in from wherever the blade is
        enter_at(contour_safe_x, z_plus[0][0])

    gcode.begin_contour()
    gcode.code("(---Groove Roughing Contour Z+ to Center---)")
    emit_contour_section(gcode, contour_safe_x, z_plus, profile_type, Corner.RIGHT)

    gcode.code("(---Groove Roughing Contour Z- to Center---)")
    emit_contour_section(gcode, contour_safe_x, z_minus, profile_type, Corner.LEFT)


def groove_roughing_toolpath(cut: GrooveCut, gcode: GcodeEmitter):
    """The G-code of a Groove Roughing, as it is cut (``cut``), onto ``gcode``."""
    op = cut.op
    cutting = op.cuttingParameters
    roughing = op.roughingParameters
    tool = cut.tool

    begin_gcode(gcode, op)
    peck_depth = abs(cutting.peckDepth)
    clearance = abs(cutting.retract)
    dwell_time = cutting.dwellTime
    initial_offset = abs(roughing.initial_offset)
    afterwards_offset = abs(roughing.afterwards_offset)
    strategy = roughing.strategy
    stock_radial, stock_axial = stock_to_leave(op)

    if strategy is not GrooveRoughingStrategy.START_CENTER:
        gcode.error(f"{TITLE} -- only start_center strategy is implemented")
        return
    path, profile_type, error = groove_path(cut)
    error = error or blade_problem(tool)
    if error:
        gcode.error(f"{TITLE} -- {error}")
        return

    _x_min, _x_max, z_min, z_max = path_bounds(path)
    center_z = (z_min + z_max) / 2.0
    width = blade_width(tool)
    half_width = width / 2.0

    # the pulley's outside; the start diameter, the plunges' start: that with
    # its radial stock to leave on; where the blade starts and backs off to:
    # the clearance out from the start diameter
    top_x = outside_x(path, profile_type)
    start_x = start_diameter_of(path, profile_type, stock_radial)
    safe_x = blade_start_x(start_x, profile_type, clearance)
    # where the blade may not go: into the part, or the stock it is to be
    # left with - radial off the bottom, axial off the flanks - nor, past the
    # groove's ends, below the outside with its stock
    obstacle = blade_obstacle(tool, path, profile_type, stock_radial, stock_axial)
    inside = obstacle.buffer(-SAME_MM)

    def _plunges_into(target_x):
        """Whether a plunge to ``target_x`` goes into the groove at all."""
        if target_x is None:
            return False
        return target_x > top_x + SAME_MM if profile_type is ProfilingType.ID else target_x < top_x - SAME_MM

    right_limit = z_max - stock_axial - half_width
    left_limit = z_min + stock_axial + half_width
    if left_limit > right_limit:
        gcode.error("Groove Roughing -- blade is wider than available groove after axial stock")
        return

    positions = _center_positions(center_z, left_limit, right_limit, initial_offset, afterwards_offset)
    # the plunges are planned for the blade's middle; the G-code is written
    # for the point it was touched off on
    control = blade_control(tool)
    z_control = control * half_width
    left_radius, right_radius = blade_radii(tool)

    # in from wherever the blade is, before its first plunge; out to pause
    # after each plunge (Pause to Inspect)
    over = over_x(cut, safe_x, clearance, profile_type)
    front = front_z(cut, clearance)
    entered = []

    def _enter(x, z):
        if not entered:
            enter(gcode, x, z, profile_type, over)
            entered.append(True)

    def _pause():
        if op.m1Parameters.include_m1:
            pause_to_inspect(gcode, op.m1Parameters, safe_x, profile_type, over, front)

    gcode.code(
        f"(---Groove Roughing: Start Center P{op.radial_profile_id}---)"
    )
    start_index = 0
    if len(positions) >= 2 and initial_offset > 0:
        first_z = positions[0]
        second_z = positions[1]
        first_target_x = _plunge_x(inside, first_z + z_control, start_x, profile_type)
        second_target_x = _plunge_x(inside, second_z + z_control, start_x, profile_type)
        if _plunges_into(first_target_x) and _plunges_into(second_target_x):
            _enter(safe_x, first_z + z_control)
            _append_center_pair_roughing(
                gcode,
                first_z + z_control,
                first_target_x,
                second_z + z_control,
                second_target_x,
                start_x,
                peck_depth,
                clearance,
                dwell_time,
            )
            start_index = 2
            _pause()

    for z_pos in positions[start_index:]:
        target_x = _plunge_x(inside, z_pos + z_control, start_x, profile_type)
        if not _plunges_into(target_x):
            continue
        _enter(safe_x, z_pos + z_control)
        _append_peck(gcode, z_pos + z_control, safe_x, target_x, peck_depth, clearance, dwell_time)
        _pause()

    _append_contour(gcode, safe_x, obstacle, path, center_z, clearance, profile_type,
                    left_radius, right_radius, half_width, control,
                    enter_at=None if entered else _enter)


def generate_groove_roughing_gcode(cut: GrooveCut):
    """A Groove Roughing's G-code on its own."""
    gcode = GcodeEmitter(cut.op.is_optional_block)
    groove_roughing_toolpath(cut, gcode)
    return gcode.lines


# ── what the editor draws ───────────────────────────────────────────────────
# The pecks the G-code makes (groove_roughing_toolpath's moves), along the
# blade's middle - so the drawing is the program, peck for peck - its finish
# contour on the contour itself, not where the blade's corners are
# compensated to, and the groove's profile offset by the stock to leave.

#: How far from its own plunge toward the other a peck's number in the pair
#: in the middle is put: near enough to say whose it is, far enough from the
#: other's number at the same depth.
ORDER_BY_ITS_PLUNGE = 0.25


@dataclass(frozen=True)
class PeckNumber:
    """A peck of the two plunges in the middle, made a peck at a time each in
    turn: ``n`` its place in that order, drawn at ``z`` - between them, by its
    own plunge - going from ``x0`` to the depth ``x``."""
    n: int
    z: float
    x: float
    x0: float


@dataclass(frozen=True)
class GrooveRoughingPreview(OperationPreview):
    """A Groove Roughing as the editor draws it: its pecks, each its arrow
    where it ends and a line across there as wide as the blade, and the
    finish contour, its arrows along it; ``plunges`` the Z of each plunge in
    the order they are made, ``order`` the pecks of the pair in the middle numbered; the plunges'
    start - the pulley's outside with its radial stock on it - and where the
    blade starts, the clearance out from it."""
    plunges: Tuple[float, ...] = ()
    order: Tuple[PeckNumber, ...] = ()
    start_diameter: Optional[float] = None
    blade_x: Optional[float] = None


def _cut_feeds(moves):
    """The feeds of ``moves`` (Moves) that are not the finish contour's, as
    DrawnLines, a pass counting the cuts from 0 - a cut being the feeds
    between two rapids."""
    feeds, pass_no, last_feed = [], -1, False
    for move in moves:
        if not move.feed:
            last_feed = False
            continue
        if not last_feed:
            pass_no += 1
        last_feed = True
        if not move.contour:
            feeds.append(DrawnLine(2 * move.r0, move.z0, 2 * move.r1, move.z1, pass_no))
    return feeds


def _from_start(feed: DrawnLine, start_x, profile_type):
    """``feed`` from the start diameter ``start_x`` on - the part of it in the
    air above it cut off - or None when it is all in the air."""
    outside = ((lambda x: x < start_x - ROUNDING) if profile_type is ProfilingType.ID
               else (lambda x: x > start_x + ROUNDING))
    if outside(feed.x0) and outside(feed.x1):
        return None
    if outside(feed.x0) and abs(feed.x1 - feed.x0) > ROUNDING:
        t = (start_x - feed.x0) / (feed.x1 - feed.x0)
        return dataclasses.replace(feed, z0=feed.z0 + t * (feed.z1 - feed.z0), x0=start_x)
    return feed


def _contour_feeds(path, cut_path, first_pass):
    """The finish contour as the G-code cuts it, on the contour - the profile
    with the stock to leave (``cut_path``) - not compensated: from the right
    flank's start to the groove's middle, then from the left one's. Each a
    pass of its own, from ``first_pass``, its arrows along it."""
    _x_min, _x_max, z_min, z_max = path_bounds(path)
    z_plus, z_minus = split_path_at_z(cut_path, (z_min + z_max) / 2.0)
    feeds = []
    for n, section in enumerate((z_plus, reverse_path(z_minus))):
        if not section or not isinstance(section[0], StartPoint):
            continue
        points = flatten_path(section)
        for a, b in zip(points, points[1:]):
            feeds.append(DrawnLine(a.x, a.z, b.x, b.z, first_pass + n, True, Arrows.ALONG))
    return feeds


def groove_roughing_preview(cut: GrooveCut) -> GrooveRoughingPreview:
    """What a Groove Roughing - as it is cut, ``cut`` - will cut, as the
    editor draws it (GrooveRoughingPreview)."""
    op = cut.op
    path, profile_type, error = groove_path(cut)
    if path is None:
        return GrooveRoughingPreview(error=error)

    radial, axial = stock_to_leave(op)

    gcode = GcodeEmitter(op.is_optional_block)
    groove_roughing_toolpath(cut, gcode)
    error = operation_error(gcode)
    feeds = [] if error else _cut_feeds(gcode.moves)
    # the G-code is written for the point the blade was touched off on; the
    # pecks are drawn down its middle
    half_width = blade_width(cut.tool) / 2.0
    z_control = blade_control(cut.tool) * half_width
    feeds = [dataclasses.replace(f, z0=f.z0 - z_control, z1=f.z1 - z_control) for f in feeds]
    # the pecks, each with its arrow where it ends - the depth it goes to -
    # from the start diameter on, the pulley's largest with its radial stock
    # to leave: what the G-code feeds through above it is air; the contour
    # drawn on the contour
    start_x = start_diameter_of(path, profile_type, radial)
    feeds = [f for f in (_from_start(dataclasses.replace(f, arrows=Arrows.END), start_x, profile_type)
                         for f in feeds) if f]
    plunges = []
    for f in feeds:
        if not any(abs(f.z0 - z) < SAME_MM for z in plunges):
            plunges.append(f.z0)
    # the two plunges in the middle are made a peck at a time each in turn:
    # each peck's place in that order, between them by its own plunge -
    # ORDER_BY_ITS_PLUNGE of the way to the other, so two at the same depth
    # stay apart - at the depth it goes to
    order = []
    if len(plunges) > 1:
        for f in feeds:
            for own, other in ((plunges[0], plunges[1]), (plunges[1], plunges[0])):
                if abs(f.z1 - own) < SAME_MM:
                    order.append(PeckNumber(len(order) + 1, own + (other - own) * ORDER_BY_ITS_PLUNGE, f.x1, f.x0))
    # where each peck ends, a line across as wide as the blade
    feeds = [dataclasses.replace(f, end_tick=half_width) for f in feeds]
    if not error:
        feeds += _contour_feeds(path, _cut_path(path, profile_type, radial, axial),
                                max([f.pass_no for f in feeds] + [-1]) + 1)
    # from where the blade starts - the clearance out from the start
    # diameter - down its middle to the start diameter, for the first two
    # plunges, the blade's and its outline's on the canvas; not the G-code's
    # rapids: the backing off and in of the pecks, and the moves between them
    # inside the groove, are not drawn
    clearance = abs(op.cuttingParameters.retract)
    blade_x = blade_start_x(start_x, profile_type, clearance)
    rapids = [DrawnLine(blade_x, z, start_x, z) for z in plunges[:2]] if clearance > 0 else []
    return GrooveRoughingPreview(
        feeds=tuple(feeds), rapids=tuple(rapids), **drawn_groove(path, profile_type, radial, axial),
        error=error,
        plunges=tuple(plunges), order=tuple(order),
        start_diameter=start_x, blade_x=blade_x)
