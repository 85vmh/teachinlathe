"""What Facing will cut, for drawing on the profile canvas.

Facing hands its cutting to the o<facing> subroutine (subroutines/facing.ngc),
so there is no G-code of its own to read the moves back from: this walks the
same moves the subroutine makes, in the same order, and must change with it.
All X values are diameters.
"""

from ..helpers.utils import get_float


def facing_moves(x_start, z_start, x_end, z_end, doc, retract):
    """The moves of o<facing>, as (feeds, rapids), each [{x0, z0, x1, z1}],
    leaving out the approach to the start point. A feed also carries ``pass``,
    counting the passes from 0, and ``contour``, always false.
    """
    feeds, rapids = [], []
    if doc <= 0:
        return feeds, rapids
    # a retract of zero falls back to the depth of cut, as the subroutine does
    if retract <= 0:
        retract = doc

    pos = [x_start, z_start]
    pass_no = -1

    def feed(x, z):
        feeds.append({"x0": pos[0], "z0": pos[1], "x1": x, "z1": z, "pass": pass_no, "contour": False})
        pos[0], pos[1] = x, z

    def rapid(x, z):
        rapids.append({"x0": pos[0], "z0": pos[1], "x1": x, "z1": z})
        pos[0], pos[1] = x, z

    z = z_start
    while z > z_end + doc:
        z -= doc
        pass_no += 1
        feed(pos[0], z)
        feed(x_end, z)
        rapid(x_end + retract * 2, z + retract)
        rapid(x_start, pos[1])
        rapid(pos[0], z)

    pass_no += 1
    feed(pos[0], z_end)
    feed(x_end, z_end)
    rapid(x_end + retract * 2, z_end + retract)
    rapid(x_start + retract * 2, pos[1])
    rapid(pos[0], z_end)
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
