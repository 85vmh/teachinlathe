"""The cutting moves, at the weight this plot asks for.

Upstream's ``ProgramPart`` draws the whole trajectory from a baked buffer and
sets no line width of its own, so the feed and arc moves come out at whatever
``glLineWidth`` happened to be left set - one pixel, since every actor before
them puts it back to that.

The buffer is also never quad-expanded: upstream says so in
``ProgramArrayBuffers._expansion_width``, and it is deliberate, the trajectory
being the one array large enough for the expansion to cost something. So the
width has to come from ``glLineWidth`` natively, and it is granted only where
the driver allows a wide line at all. On a strict core profile - a Pi, say -
these stay at one pixel whatever ``palette.WIDTH_FEED`` says, and there is no
way round it short of drawing the trajectory ourselves.

Subclassed rather than replaced, and handed the *same* ``ProgramResource``:
``GlCanonDraw`` binds its picker to ``scene.program.resource`` and pushes
program uploads through it, and ``scene.highlight`` is a second draw of those
same buffers. A part here that owned different ones would leave what is picked
and what is highlighted pointing at geometry nobody draws.
"""

import logging
from contextlib import contextmanager

from teachinlathe.widgets.backplot.actors import palette
from teachinlathe.widgets.backplot.actors.base import line_width

LOG = logging.getLogger(__name__)

try:
    from rs274 import glcanon_scene
    _PROGRAM_PART = glcanon_scene.ProgramPart
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot cutting: preview modules unavailable: %s", exc)
    _PROGRAM_PART = object


class CuttingMovesPart(_PROGRAM_PART):
    """Upstream's trajectory, drawn a little heavier.

    The width is entered and left in this part's own scope, which is the rule
    every other part here follows - a part owning the state its drawing needs
    rather than setting it for whatever comes next.
    """

    @contextmanager
    def scope(self, ctx):
        with super().scope(ctx):
            line_width(palette.WIDTH_FEED)
            try:
                yield
            finally:
                line_width(1.0)


def install(scene):
    """Swap the trajectory for one that sets its own weight.

    ``replace`` keeps the position, which matters: the highlight is a second
    draw of these buffers and must stay immediately after them.
    """
    program = scene.program
    scene.program = scene.replace(program, CuttingMovesPart(program.resource))
    return scene.program
