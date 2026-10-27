"""What Facing will cut, for drawing on the profile canvas.

facing_passes is the one place Facing's moves are worked out: the G-code
(facing.py) writes them and the preview draws them, so the two cannot drift
apart. All X values are diameters.
"""

from ..helpers.utils import get_float


def facing_passes(x_start, z_start, x_end, z_end, doc, retract):
    """Facing's passes, in order, each a list of moves (feed, x, z) going on
    from where the one before ended - the first from (x_start, z_start).
    Every pass but the last ends back at X Start, on the face it cut; the
    last ends clear of the part, at Z End. None without a depth of cut.
    """
    if doc <= 0:
        return []
    # a retract of zero would leave the tool rubbing the face it just cut on
    # the way back out: the depth of cut instead
    if retract <= 0:
        retract = doc

    passes = []
    z = z_start
    # with a tolerance: Z End a whole number of cuts away, rounding must not
    # make the last of them a second pass at Z End
    while z > z_end + doc + 1e-6:
        z -= doc
        # away at 45 degrees: X a diameter, so 2R on X is R on the part
        passes.append([(True, x_start, z), (True, x_end, z),
                       (False, x_end + retract * 2, z + retract),
                       (False, x_start, z + retract), (False, x_start, z)])
    passes.append([(True, x_start, z_end), (True, x_end, z_end),
                   (False, x_end + retract * 2, z_end + retract),
                   (False, x_start + retract * 2, z_end + retract),
                   (False, x_start + retract * 2, z_end)])
    return passes


def facing_moves(x_start, z_start, x_end, z_end, doc, retract):
    """Facing's moves, as (feeds, rapids), each [{x0, z0, x1, z1}], leaving
    out the approach to the start point. A feed also carries ``pass``,
    counting the passes from 0, and ``contour``, always false.
    """
    feeds, rapids = [], []
    x0, z0 = x_start, z_start
    for pass_no, moves in enumerate(facing_passes(x_start, z_start, x_end, z_end, doc, retract)):
        for feed, x, z in moves:
            if feed:
                feeds.append({"x0": x0, "z0": z0, "x1": x, "z1": z, "pass": pass_no, "contour": False})
            else:
                rapids.append({"x0": x0, "z0": z0, "x1": x, "z1": z})
            x0, z0 = x, z
    return feeds, rapids


def build_facing_preview(op):
    """{profile, offset, feeds, rapids, error} for a Facing operation (or its
    dict), as build_profile_roughing_preview gives them; there is no profile,
    so profile and offset are empty.
    """
    if hasattr(op, "to_dict"):
        op = op.to_dict()
    geometry = op.get("geometry_parameters", {}) or {}
    cutting = op.get("cutting_parameters", {}) or {}
    doc = get_float(cutting, "doc", 0.0)
    if doc <= 0:
        return {"profile": [], "offset": [], "feeds": [], "rapids": [], "error": "no depth of cut"}
    feeds, rapids = facing_moves(get_float(geometry, "x_start", 0.0), get_float(geometry, "z_start", 0.0),
                                 get_float(geometry, "x_end", 0.0), get_float(geometry, "z_end", 0.0),
                                 doc, get_float(cutting, "retract", 0.0))
    return {"profile": [], "offset": [], "feeds": feeds, "rapids": rapids, "error": ""}
