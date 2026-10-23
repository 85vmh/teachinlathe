"""G-code generator for Profile Roughing (OD and ID).

The moves are planned by profiling/machining.py, tool and all, for the
ProfilingType (OD/ID) and PassType (AXIAL / RADIAL / DIAGONAL_*); this reads
the operation, finds its profile and tool, keeps the plans made, and writes the
G-code of a plan.
"""

import dataclasses
import logging

from teachinlathe.conversational.model.data_types import PassType, ProfileRoughingConfig, ProfilingType

from ..helpers.spindle import build_spindle_gcode
from ..config import fmt
from ..helpers.utils import get_float
from .profiling.geometry import (
    StartPoint,
    build_shifted_path_clipped_to_x_boundary,
    build_profile_segments,
    build_render_path,
)
from .profiling.context import make_id_context, make_od_context

log = logging.getLogger(__name__)


def _pass_type_label(pass_type: PassType) -> str:
    angle = f"{_diagonal_angle():g}°"
    return {
        PassType.AXIAL: "Axial Passes",
        PassType.RADIAL: "Radial Passes",
        PassType.DIAGONAL_INTERIOR: f"{angle} Passes toward interior",
        PassType.DIAGONAL_EXTERIOR: f"{angle} Passes toward exterior",
    }.get(pass_type, str(pass_type.value if hasattr(pass_type, "value") else pass_type))


def _diagonal_angle() -> float:
    """The angle diagonal passes run at: the constant for now (profiling.plan),
    read when planning, not when this module was loaded."""
    from .profiling import plan
    return plan.DIAGONAL_ANGLE


def parse_profile_roughing_config(op) -> ProfileRoughingConfig:
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    cutting = op.get("cutting_parameters", {}) or {}
    params = op.get("profiling_parameters", {}) or {}
    strategy = op.get("profile_roughing_strategy", {}) or {}
    stock = op.get("stock_to_leave", {}) or {}

    resolved = op.get("_resolved_profile") or {}
    if resolved:
        try:
            profiling_type = ProfilingType(str(resolved.get("profile_type", "od")).lower())
        except ValueError:
            profiling_type = ProfilingType.OD
    else:
        try:
            profiling_type = ProfilingType(str(strategy.get("profiling_type", "od")).lower())
        except ValueError:
            profiling_type = ProfilingType.OD

    try:
        pass_type = PassType(str(strategy.get("pass_type", "axial")).lower())
    except ValueError:
        pass_type = PassType.AXIAL

    return ProfileRoughingConfig(
        x_start=get_float(params, "x_start", 0.0),
        z_start=get_float(params, "z_start", 0.0),
        doc=get_float(cutting, "doc", 0.5),
        retract=get_float(cutting, "retract", 1.0),
        feed_rate=get_float(cutting, "feed_rate", 0.1),
        stock_x=get_float(stock, "radial", 0.0),
        stock_z=get_float(stock, "axial", 0.0),
        profiling_type=profiling_type,
        pass_type=pass_type,
        optional_prefix="/" if bool(op.get("is_optional_block", False)) else "",
    )


def _resolve_profile(op):
    resolved = op.get("_resolved_profile") or {}
    primitives = resolved.get("profile_primitives", []) or []
    profile_type = str(resolved.get("profile_type", "od")).lower()
    segments = build_profile_segments(primitives)
    path = build_render_path(segments, profile_type)
    return segments, path


def _profile_extents(path):
    """Return (x_min, x_max, z_min) across all rendered path endpoints."""
    x_vals, z_vals = [], []
    for element in path:
        if isinstance(element, StartPoint):
            x_vals.append(element.x)
            z_vals.append(element.z)
        else:
            x_vals.append(element.end_x)
            z_vals.append(element.end_z)
    x_min = min(x_vals) if x_vals else 0.0
    x_max = max(x_vals) if x_vals else 0.0
    z_min = min(z_vals) if z_vals else 0.0
    return x_min, x_max, z_min


_NO_PROFILE = "no valid profile found"
_NO_ROUGHING_PROFILE = "no valid roughing profile after stock/clipping"


def build_roughing_setup(op, config):
    """The roughing context and the path every pass is cut against: the profile
    offset by stock-to-leave and clipped to X Start. Returns (ctx, roughing_path,
    error); error names what is missing when there is nothing to rough.
    """
    segments, path = _resolve_profile(op)
    if not segments or not isinstance(segments[0], StartPoint):
        return None, None, _NO_PROFILE

    x_min, x_max, _ = _profile_extents(path)

    if config.profiling_type == ProfilingType.OD:
        ctx = make_od_context(config, x_min)
        keep_side = "lte"
    else:
        ctx = make_id_context(config, x_max)
        keep_side = "gte"

    roughing_path = build_shifted_path_clipped_to_x_boundary(
        path,
        ctx.geo_x_shift,
        ctx.geo_z_shift,
        ctx.x_start,
        keep_side,
    )

    if not roughing_path or not isinstance(roughing_path[0], StartPoint):
        return ctx, None, _NO_ROUGHING_PROFILE
    return ctx, roughing_path, None


def generate_profile_roughing_gcode(op):
    """The G-code of a Profile Roughing: the moves of its tool-aware plan
    (plan_profile_roughing) as the machine makes them - compensated for the
    insert's nose, every one checked against the part and what is left of
    the stock. The profile canvas draws the same plan."""
    if hasattr(op, "to_dict"):
        op = op.to_dict()

    config = parse_profile_roughing_config(op)
    spindle = op.get("spindle_parameters", {}) or {}
    m1_params = op.get("m1_parameters", {}) or {}
    spindle_direction = int(spindle.get("direction", 0) or 0)
    prefix = config.optional_prefix

    lines = []
    lines.extend(build_spindle_gcode(spindle, prefix))
    lines.append(f"{prefix}G95 F{config.feed_rate}")
    lines.append("")

    plan = plan_profile_roughing(op)
    if plan.error:
        lines.append(_comment(f"ERROR: Profile Roughing -- {plan.error}"))
        return lines

    if plan.tool is not None and plan.tool.known:
        lines.append(_comment(f"Planned for {plan.tool.label}, nose R{fmt(plan.tool.nose_radius)}"))
    for warning in plan.warnings:
        lines.append(_comment(warning))
    lines.append(f"(----------Profiling Type: {_pass_type_label(config.pass_type)}----------)")
    _emit_moves(lines, plan.moves, prefix, config, m1_params, spindle_direction)
    return lines


def _comment(text):
    """``text`` as a G-code comment. LinuxCNC refuses a comment with another
    one in it, so the brackets ``text`` may have are made square."""
    return "( " + str(text).replace("(", "[").replace(")", "]") + " )"


def _emit_moves(lines, moves, prefix, config, m1_params, spindle_direction):
    """``moves`` as G0 / G1, the contour's runs of short chords fitted back
    into G2 / G3 arcs where they lie on one."""
    from ..helpers.m1 import inspect_position_int

    include_m1 = bool(m1_params.get("include_m1", False)) if m1_params else False
    position = None
    contour = []                    # (z, r) points of the contour run under way

    def flush_contour():
        if len(contour) > 1:
            for gcode in _fit_arcs(contour):
                lines.append(f"{prefix}{gcode}")
        contour.clear()

    in_contour = False
    for move in moves:
        if move.contour and move.feed:
            if not in_contour:
                lines.append(f"( Contour with StockToLeave[radial={fmt(config.stock_x)} "
                             f"axial={fmt(config.stock_z)}] )")
                in_contour = True
            if not contour:
                if position != (move.z0, move.r0):
                    lines.append(f"{prefix}G0 X{fmt(2 * move.r0)} Z{fmt(move.z0)}")
                contour.append((move.z0, move.r0))
            contour.append((move.z1, move.r1))
            position = (move.z1, move.r1)
            continue
        flush_contour()
        if (move.z0, move.r0) == (move.z1, move.r1):
            if position is None:                    # the start position
                lines.append(f"{prefix}G0 X{fmt(2 * move.r1)} Z{fmt(move.z1)}")
                position = (move.z1, move.r1)
            continue
        if position != (move.z0, move.r0):
            lines.append(f"{prefix}G0 X{fmt(2 * move.r0)} Z{fmt(move.z0)}")
        word = "G1" if move.feed else "G0"
        lines.append(f"{prefix}{word} X{fmt(2 * move.r1)} Z{fmt(move.z1)}")
        position = (move.z1, move.r1)
        if move.pass_end:
            if include_m1:
                lines.append(
                    f"{prefix}o<m1_handling> call "
                    f"[{inspect_position_int(m1_params)}] "
                    f"[{fmt(2 * move.r1)}] "
                    f"[{fmt(move.z1)}] "
                    f"[{spindle_direction}]"
                )
            lines.append("")
    flush_contour()
    lines.append("")


#: How far a chord of the contour may be from the arc it is written as, in mm.
ARC_FIT_TOLERANCE = 0.003


def _fit_arcs(points):
    """G1 / G2 / G3 words along ``points`` [(z, r)]: each longest run of
    four or more points on one circle - within ARC_FIT_TOLERANCE, turning
    one way - as an arc, the rest as lines. X as a diameter, I and K as
    radial and axial distances from the arc's start to its centre."""
    import math

    words = []
    i, n = 0, len(points)
    while i < n - 1:
        best = None
        j = i + 3
        while j < n:
            arc = _circle(points[i], points[(i + j) // 2], points[j])
            if arc is None or not _on_arc(points[i:j + 1], arc):
                break
            best = (j, arc)
            j += 1
        if best is not None and _straight(points[i:best[0] + 1]):
            # on a line as much as on a circle - a radius of tens of mm
            # through chords barely bent: a line it is
            j = best[0]
            z1, r1 = points[j]
            words.append(f"G1 X{fmt(2 * r1)} Z{fmt(z1)}")
            i = j
        elif best is not None:
            j, (cz, cr, radius, clockwise) = best
            z0, r0 = points[i]
            z1, r1 = points[j]
            word = "G2" if clockwise else "G3"
            words.append(f"{word} X{fmt(2 * r1)} Z{fmt(z1)} I{fmt(cr - r0)} K{fmt(cz - z0)}")
            i = j
        else:
            z1, r1 = points[i + 1]
            words.append(f"G1 X{fmt(2 * r1)} Z{fmt(z1)}")
            i += 1
    return words


def _straight(points):
    """Whether every point lies on the line from the first to the last,
    within ARC_FIT_TOLERANCE."""
    import math
    (az, ar), (bz, br) = points[0], points[-1]
    length = math.hypot(bz - az, br - ar)
    if length < 1e-12:
        return False
    return all(abs((z - az) * (br - ar) - (r - ar) * (bz - az)) / length <= ARC_FIT_TOLERANCE
               for z, r in points)


def _circle(a, b, c):
    """The circle through three (z, r) points as (cz, cr, radius, clockwise),
    clockwise as seen with Z to the right and X up; None when they are in a
    line or the circle is too big to be worth an arc."""
    import math
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    radius = math.hypot(ax - ux, ay - uy)
    if radius > 500.0:
        return None
    cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
    return ux, uy, radius, cross < 0


def _on_arc(points, arc):
    """Whether every point, and every chord's middle, is on ``arc`` within
    the tolerance, the points going round it one way only."""
    import math
    cz, cr, radius, clockwise = arc
    previous = None
    for k, (z, r) in enumerate(points):
        if abs(math.hypot(z - cz, r - cr) - radius) > ARC_FIT_TOLERANCE:
            return False
        if k:
            pz, pr = points[k - 1]
            mz, mr = (z + pz) / 2, (r + pr) / 2
            if abs(math.hypot(mz - cz, mr - cr) - radius) > ARC_FIT_TOLERANCE:
                return False
            turn = math.atan2(r - cr, z - cz) - math.atan2(pr - cr, pz - cz)
            turn = (turn + math.pi) % (2 * math.pi) - math.pi
            if (turn < 0) != clockwise or abs(turn) > math.pi / 2:
                return False
            if previous is not None and abs(turn) < 1e-9:
                return False
            previous = turn
    return True


def resolve_tool_shape(op):
    """The insert the Change Tool above puts in, as ``_resolved_cutting_tool``
    carries it (the Tool Library's JSON); None when there is none to go by."""
    from teachinlathe.tooling.model.data_types import CuttingTool
    from .profiling.machining import insert_tool_shape

    raw = op.get("_resolved_cutting_tool") or None
    if not raw:
        return None
    try:
        return insert_tool_shape(CuttingTool.from_json(raw))
    except Exception:
        # planned with the stand-in square tool then: say why
        log.warning("roughing plan: the tool could not be read, planned without it", exc_info=True)
        return None


#: Plans already worked out, by everything that went into them: a rest
#: roughing plans each roughing above it first, and the editor asks again for
#: every value changed.
_PLANS = {}
_PLANS_KEPT = 16

_NO_SOURCE = "rest material, but no Profile Roughing of this profile above it"
_CHOOSE_TOOL = "Choose the tool in the Change Tool above to cut what is left"


def plan_profile_roughing(op):
    """The tool-aware plan of a Profile Roughing - see profiling.machining -
    for an operation dict carrying its profile in ``_resolved_profile`` and
    its tool in ``_resolved_cutting_tool``.

    Rest material (``rest_material``): it starts from what the Profile
    Roughings above it on the same profile leave - given, in order, as
    ``_resolved_previous_roughing``, each an operation dict as this takes -
    and keeps to the stock to leave and the start position of the last one
    that is not rest material itself, its source."""
    import json

    if hasattr(op, "to_dict"):
        op = op.to_dict()
    key = json.dumps([op, _diagonal_angle()], sort_keys=True, default=str)
    plan = _PLANS.get(key)
    if plan is None:
        plan = _plan(op)
        if len(_PLANS) >= _PLANS_KEPT:
            _PLANS.pop(next(iter(_PLANS)))
        _PLANS[key] = plan
    return plan


def _plan(op):
    from .profiling.machining import RoughingPlan, RoughingSetup, plan_leftover, plan_roughing

    config = parse_profile_roughing_config(op)
    segments, path = _resolve_profile(op)
    if not segments or not isinstance(segments[0], StartPoint) or len(path) < 2:
        return RoughingPlan(error=_NO_PROFILE)
    rest = bool(op.get("rest_material", False))
    stock_before, last_tool = None, None
    if rest:
        source, stock_before, last_tool = _rest_start(op.get("_resolved_previous_roughing") or [])
        if source is None:
            return RoughingPlan(error=_NO_SOURCE)
        # the source's stock to leave and start position: the same finished
        # size, and the same bar
        source_config = parse_profile_roughing_config(source)
        config = dataclasses.replace(
            config, x_start=source_config.x_start, z_start=source_config.z_start,
            stock_x=source_config.stock_x, stock_z=source_config.stock_z)
    setup = RoughingSetup(
        x_start=config.x_start, z_start=config.z_start, doc=config.doc,
        retract=config.retract, stock_x=config.stock_x, stock_z=config.stock_z,
        profiling_type=config.profiling_type, pass_type=config.pass_type,
        diagonal_angle=_diagonal_angle())
    tool = resolve_tool_shape(op)
    if rest and tool is None:
        plan = plan_leftover(setup, path, stock_before,
                             last_tool.nose_radius if last_tool is not None else 0.0)
        plan.warnings.insert(0, _CHOOSE_TOOL)
        return plan
    return plan_roughing(setup, path, tool, stock_before, rest=rest,
                         sliver_radius=last_tool.nose_radius if rest and last_tool is not None else 0.0)


def _rest_start(previous):
    """(source, stock, tool) for a rest roughing below the roughings
    ``previous``: the last of them that is not rest material, the material all
    of them together leave and the last tool that cut it - or
    (None, None, None) with no source."""
    source, stock, tool = None, None, None
    for index, prev in enumerate(previous):
        if not prev.get("rest_material", False):
            source, stock = prev, None
        elif source is None:
            continue
        else:
            # a rest roughing too: it starts from those above it in turn
            prev = {**prev, "_resolved_previous_roughing": previous[:index]}
        plan = plan_profile_roughing(prev)
        if plan.error or plan.remaining_stock is None:
            continue
        stock = plan.remaining_stock
        tool = plan.tool
    return source, stock, tool
