"""What a model-space length is worth in pixels, and what the window covers.

Three of the actors ported from the QML 2D preview are sized in pixels rather
than in millimetres: the grid picks its spacing from how far apart the lines
would land, the ticks are a few pixels long whatever the zoom, and the hatch
is drawn at a fixed pixel pitch. The Canvas had that for free - it drew in
pixels and converted the other way. Here the actors draw in model space, so
the conversion has to be recovered from the frame.

It is recovered from the model-view-projection rather than from the camera,
because that is the one thing an actor is handed that already accounts for
everything between it and the screen - the pan, the zoom, the program-origin
placement each actor's ``place()`` applied, and the projection glnav folded
the eye translation into.

Everything here is in the frame the caller's ``mvp`` describes, so an actor
placed on the program origin gets bounds in program coordinates, which is what
it then draws in.
"""

import logging

LOG = logging.getLogger(__name__)

try:
    import numpy as np
    LIB_GOOD = True
except ImportError as exc:  # pragma: no cover - numpy ships with the renderer
    LOG.error("backplot screen: numpy unavailable: %s", exc)
    LIB_GOOD = False

#: A scale at or below this is not a measurement - the matrix was degenerate,
#: or the window has not been sized yet. Callers skip drawing rather than
#: dividing by it.
MIN_SCALE = 1e-9


def _clip(mvp, point):
    """``point`` through ``mvp``, as normalised device coordinates."""
    homogeneous = np.array([point[0], point[1], point[2], 1.0])
    clip = mvp @ homogeneous
    w = clip[3]
    if abs(w) < MIN_SCALE:
        return None
    return clip[:3] / w


def pixels_per_unit(ctx, mvp):
    """How many pixels one model unit spans, as ``(along_z, along_x)``.

    Measured rather than read off the matrix: the two are the same for the
    orthographic lathe view this screen is always in, but measuring says what
    it means and survives a view that is not axis-aligned.

    ``None`` when the frame cannot be measured - see ``MIN_SCALE``.
    """
    if not LIB_GOOD or ctx.width <= 0 or ctx.height <= 0:
        return None
    origin = _clip(mvp, (0.0, 0.0, 0.0))
    along_z = _clip(mvp, (0.0, 0.0, 1.0))
    along_x = _clip(mvp, (1.0, 0.0, 0.0))
    if origin is None or along_z is None or along_x is None:
        return None
    # NDC spans 2 across the viewport, hence the halved width and height.
    z_scale = abs(along_z[0] - origin[0]) * ctx.width / 2.0
    x_scale = abs(along_x[1] - origin[1]) * ctx.height / 2.0
    if z_scale <= MIN_SCALE or x_scale <= MIN_SCALE:
        return None
    return z_scale, x_scale


def visible_rect(ctx, mvp):
    """What the window covers, as ``(z_min, z_max, x_min, x_max)`` in model
    space - or ``None`` if the frame cannot be inverted.

    The four NDC corners are mapped back through the inverse, and the bounds
    taken from where they land. The depth they are taken at does not matter
    for an orthographic projection, so they are taken on the near-far midplane
    where the numbers are best conditioned.
    """
    if not LIB_GOOD:
        return None
    try:
        inverse = np.linalg.inv(mvp)
    except np.linalg.LinAlgError:
        return None

    z_values = []
    x_values = []
    for ndc_x in (-1.0, 1.0):
        for ndc_y in (-1.0, 1.0):
            corner = inverse @ np.array([ndc_x, ndc_y, 0.0, 1.0])
            w = corner[3]
            if abs(w) < MIN_SCALE:
                return None
            x_values.append(corner[0] / w)
            z_values.append(corner[2] / w)
    return min(z_values), max(z_values), min(x_values), max(x_values)


def view_key(ctx, mvp):
    """A value that changes when the view does, and not otherwise.

    What the grid, the ticks, the centreline and the origin symbol draw
    depends on the camera and on nothing else - not on where the tool is. But
    the plot is redrawn every time the machine moves, which while a program
    runs is twenty-five times a second, and each of those was rebuilding
    vertices identical to the last frame's.

    ``None`` when the frame cannot be measured, which callers treat as "do not
    draw" rather than as a cache miss.
    """
    bounds = visible_rect(ctx, mvp)
    scale = pixels_per_unit(ctx, mvp)
    if bounds is None or scale is None:
        return None
    # Rounded, so that a matrix rebuilt to the same view compares equal
    # through the last bit of its arithmetic.
    return (tuple(round(value, 9) for value in bounds),
            round(scale[0], 6), round(scale[1], 6), ctx.width, ctx.height)
