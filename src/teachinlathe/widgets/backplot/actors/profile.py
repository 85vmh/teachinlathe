"""The finished profile, read off the program's cutting moves.

The stock outline is what the bar started as; this is what it ends as, and it
is what the hatching has to stop at - otherwise the material is drawn straight
over the toolpath that removes it.

Nothing in the G-code states the profile, so it is derived: **for each Z, the
smallest radius any cutting move reached.** That is the assumption every
simple backplot makes about turning - the tool comes in from outside, so
everything outboard of where it passed is gone - and it is exactly right for
an OD operation.

**It is not right for boring**, where the tool comes from the inside out and
the material left is on the far side of the path. That case is not
distinguished here: doing it needs to know which side the tool approached
from, which is not in the geometry, and guessing it wrong erases the part.
Until it is, a bored feature hatches as though it had been turned.

Traverse moves are excluded - a rapid over the bar cuts nothing. A feed move
through air is not excluded, because nothing tells it apart from a cut; an
approach programmed at feed rate will pull the profile in with it.
"""

import logging

LOG = logging.getLogger(__name__)

try:
    import numpy as np
    from rs274.glcanon_bake import KIND_ARC, KIND_FEED
    LIB_GOOD = True
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot profile: preview modules unavailable: %s", exc)
    KIND_FEED, KIND_ARC = 1, 2
    LIB_GOOD = False

#: How many ``(column, radius)`` pairs one pass may build at a time.
#:
#: The columns a move spans are written in one vectorised go, which needs them
#: all in memory at once. A finishing pass runs the length of the bar and so
#: touches every column; a few thousand of those would be tens of millions of
#: pairs. This caps a pass and the moves are worked through in slices, which
#: is a handful of iterations rather than one per move.
CHUNK = 2_000_000

#: How many Z columns the profile is sampled into across the stock.
#:
#: The hatch is a diagonal every twelve pixels, so this only has to be finer
#: than that to place its ends on the right side of a shoulder. 512 is well
#: past it for any bar this machine turns, and it keeps the arithmetic to one
#: numpy slice per cutting move.
SAMPLES = 512


def machine_to_actor(ctx):
    """The transform from the program's vertices to the frame an actor draws
    in, or ``None``.

    The program's points are in machine coordinates - the C renderer bakes the
    offsets into them, which is why upstream draws them with the plain camera.
    An actor draws after ``place()`` has pushed the g5x offset, the XY rotation
    and g92 on top of that camera.

    Rather than re-deriving that chain and getting the order or a sign wrong,
    it is recovered from the two matrices the frame already carries: the
    actor's own MVP is the camera's with ``place`` applied, so dividing one
    out of the other leaves exactly ``place``, and its inverse is what brings
    a machine point into the actor's frame.
    """
    if not LIB_GOOD:
        return None
    try:
        camera = ctx.preview_mvp()
        place = np.linalg.inv(camera) @ ctx.mv.mvp()
        return np.linalg.inv(place)
    except (AttributeError, np.linalg.LinAlgError) as exc:
        LOG.debug("backplot profile: no usable frame: %s", exc)
        return None


class Profile:
    """The finished radius at every Z across the stock.

    Sampled onto a uniform grid so a lookup is an index rather than a search,
    and so a shoulder lands on a column rather than between two.
    """

    def __init__(self, z_start, z_end, radii):
        self._z_start = z_start
        self._span = z_end - z_start
        self._radii = radii

    def at(self, z):
        """The finished radius at ``z``, clamped to the ends."""
        if self._span <= 0 or not len(self._radii):
            return self._radii[0] if len(self._radii) else 0.0
        position = (z - self._z_start) / self._span * (len(self._radii) - 1)
        index = int(round(position))
        return float(self._radii[max(0, min(index, len(self._radii) - 1))])


def finished(ctx, z_start, z_end, outer_radius):
    """The profile between ``z_start`` and ``z_end``, in the actor's frame.

    Everything is a length in the scene's model unit. ``outer_radius`` is what
    the profile is where no cutting move reached - the bar is still full size
    there.

    ``None`` when there is no program to read, which is not a failure: it
    means the stock hatches whole, as it did before any of this.
    """
    if not LIB_GOOD or ctx.canon is None or z_end <= z_start:
        return None
    program = getattr(ctx.canon, "program_geometry", None)
    if program is None:
        return None
    transform = machine_to_actor(ctx)
    if transform is None:
        return None

    try:
        points = program.positions(0)
        kinds = program.kinds
    except (AttributeError, IndexError, TypeError) as exc:
        LOG.debug("backplot profile: no usable program geometry: %s", exc)
        return None
    if len(points) < 2:
        return None

    cutting = (kinds[1:] == KIND_FEED) | (kinds[1:] == KIND_ARC)
    if not cutting.any():
        return None

    local = _to_actor(points, transform)
    starts = local[:-1][cutting]
    ends = local[1:][cutting]

    radii = np.full(SAMPLES, float(outer_radius))
    step = (z_end - z_start) / (SAMPLES - 1)
    _cut(radii, z_start, step, starts, ends)
    np.clip(radii, 0.0, outer_radius, out=radii)
    return Profile(z_start, z_end, radii)


def _to_actor(points, transform):
    """Every point through ``transform``, as an ``(N, 3)`` array."""
    homogeneous = np.empty((len(points), 4))
    homogeneous[:, 0:3] = points
    homogeneous[:, 3] = 1.0
    moved = homogeneous @ transform.T
    return moved[:, 0:3] / moved[:, 3:4]


def _cut(radii, z_start, step, starts, ends):
    """Pull ``radii`` in to wherever the moves passed.

    **All of them at once.** This was a Python loop over every cutting move,
    and the profile was rebuilt on every frame, so a program of any size sat
    on the processor: ten thousand points measured a whole core at the redraw
    rate, fifty thousand five of them. Both halves of that are fixed - the
    caller caches, and this is arithmetic over arrays.

    A move at constant Z - a plunge - spans no columns to interpolate across
    and lands on the single one it is at, so those are done separately.
    """
    x0, z0 = starts[:, 0].astype(float), starts[:, 2].astype(float)
    x1, z1 = ends[:, 0].astype(float), ends[:, 2].astype(float)

    plunge = np.abs(z1 - z0) < 1e-12
    if plunge.any():
        index = np.rint((z0[plunge] - z_start) / step).astype(np.int64)
        inside = (index >= 0) & (index < len(radii))
        np.minimum.at(radii, index[inside],
                      np.minimum(x0[plunge], x1[plunge])[inside])

    along = ~plunge
    if not along.any():
        return
    x0, z0, x1, z1 = x0[along], z0[along], x1[along], z1[along]

    low = np.minimum(z0, z1)
    high = np.maximum(z0, z1)
    first = np.maximum(0, np.ceil((low - z_start) / step)).astype(np.int64)
    last = np.minimum(len(radii) - 1,
                      np.floor((high - z_start) / step)).astype(np.int64)
    counts = np.maximum(0, last - first + 1)

    # Worked through in slices, so one pass never holds more than CHUNK pairs
    # however far the moves in it reach. See CHUNK.
    edges = _slices(counts)
    for begin, stop in zip(edges, edges[1:]):
        _cut_slice(radii, z_start, step,
                   first[begin:stop], counts[begin:stop],
                   x0[begin:stop], z0[begin:stop],
                   x1[begin:stop], z1[begin:stop])


def _slices(counts):
    """Where to cut the move list so no slice builds more than ``CHUNK``."""
    if not len(counts):
        return [0]
    running = np.cumsum(counts)
    edges = [0]
    while edges[-1] < len(counts):
        taken = running[edges[-1] - 1] if edges[-1] else 0
        following = int(np.searchsorted(running, taken + CHUNK, side="right"))
        edges.append(max(following, edges[-1] + 1))
    return edges


def _cut_slice(radii, z_start, step, first, counts, x0, z0, x1, z1):
    """One slice of moves, expanded to ``(column, radius)`` pairs and written.

    The expansion is the standard ragged-repeat: every move is repeated as
    many times as it has columns, and the offset within each run comes from
    subtracting each run's own start from a flat count.
    """
    total = int(counts.sum())
    if total <= 0:
        return
    run_start = np.repeat(np.cumsum(counts) - counts, counts)
    columns = np.repeat(first, counts) + (np.arange(total) - run_start)

    z = z_start + columns * step
    fraction = (z - np.repeat(z0, counts)) / np.repeat(z1 - z0, counts)
    np.minimum.at(radii, columns,
                  np.repeat(x0, counts)
                  + fraction * np.repeat(x1 - x0, counts))
