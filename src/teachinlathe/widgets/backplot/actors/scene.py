"""The cast, and the order it is drawn in.

Every actor the backplot shows is named here once - the ones in this package
and the ones LinuxCNC already provides - so the composition of the scene is
readable in one file rather than inferred from where each was registered.

There are three kinds of edit, and they are not interchangeable:

    background   inserted before the program, with depth writes off, so the
                 toolpath draws over them: grid, stock, centreline
    overlay      appended, so they draw over everything: ticks, arrows,
                 letters, origin
    replacement  swapped in place for an upstream part, keeping its position
                 and its gate: the insert, for the tool marker

**The toolpath and the live trace stay upstream's, deliberately.**
``ProgramPart`` draws the toolpath and ``BackplotPart`` the trace. Re-writing
them here would fork the renderer, and the trace especially: its
``BackplotRing`` uploads only the points that are new, growing by doubling,
and drawing it naively instead re-uploads the whole trail every frame - a cost
that climbs with the trail, which is the shape of the stutter this screen was
cured of.

Panning and zooming are not an actor's concern. The camera is on the
model-view stack the frame carries, so every actor draws in model space and is
moved and scaled together with the rest.
"""

import logging

from teachinlathe.widgets.backplot.actors.axis_arrows import AxisArrowsActor
from teachinlathe.widgets.backplot.actors.axis_letters import AxisLettersActor
from teachinlathe.widgets.backplot.actors.base import LIB_GOOD, InertActor
from teachinlathe.widgets.backplot.actors import cutting
from teachinlathe.widgets.backplot.actors.centerline import CenterlineActor
from teachinlathe.widgets.backplot.actors.grid import GridActor
from teachinlathe.widgets.backplot.actors.insert_tool import InsertActor
from teachinlathe.widgets.backplot.actors.origin import OriginActor
from teachinlathe.widgets.backplot.actors.rapids import RapidsActor
from teachinlathe.widgets.backplot.actors.stock import StockActor
from teachinlathe.widgets.backplot.actors.ticks import TicksActor

LOG = logging.getLogger(__name__)

#: Under the toolpath, in this order - the grid furthest back, the rapids
#: nearest the front, immediately under the cutting moves they are hidden from
#: upstream's buffer to make room for.
BACKGROUND_ACTORS = (GridActor, StockActor, CenterlineActor, RapidsActor)

#: The annotation, in this order - the last drawn sits over the ones before
#: it, which is why the origin symbol comes after the shafts that run through
#: it.
#:
#: Drawn over the toolpath but **under the live trace and the tool**. It used
#: to be appended after everything, which put the tick marks and the origin
#: symbol over the tool marker - the wrong way round for a marker whose whole
#: job is to say where the tool is. Moving it below the trace also puts it in
#: the part of the scene that does not change while a program runs, so it is
#: cached with the rest of the still picture rather than redrawn every frame.
OVERLAY_ACTORS = (TicksActor, AxisArrowsActor, AxisLettersActor, OriginActor)


def install(canon):
    """Compose the scene around upstream's parts.

    ``canon`` is the backplot item - upstream's ``GlCanonDraw`` grafted onto
    it - so it is both the thing holding the scene and the host the actors
    read the stock and the insert choice from.
    """
    if not LIB_GOOD:
        return []
    try:
        scene = canon.scene
    except AttributeError as exc:
        LOG.warning("backplot actors: no scene to install into: %s", exc)
        return []

    # Upstream's own axes, emptied rather than removed - the scene's order is
    # load-bearing and the part is reached by name from its parent.
    scene.relative_coords.axes = InertActor()

    installed = []

    # Before the program, so the toolpath draws over them. insert_before keeps
    # the rest of the order intact; a remove-then-add would not.
    for actor_type in BACKGROUND_ACTORS:
        try:
            installed.append(
                scene.insert_before(scene.program, actor_type(canon)))
        except Exception as exc:
            LOG.warning("backplot actors: could not insert %s: %s",
                        actor_type.__name__, exc)

    # The trajectory, so the cutting moves carry a weight of their own rather
    # than whatever the part before them left set.
    try:
        installed.append(cutting.install(scene))
    except Exception as exc:
        LOG.warning("backplot actors: could not set the cutting weight: %s",
                    exc)

    # The annotation, immediately before the live trace: over the toolpath,
    # under the trace and the tool. The depth mode each one sets is what stops
    # the geometry already drawn from rejecting its fragments - position and
    # depth mode are two halves of the same decision, see ``Actor.scope``.
    for actor_type in OVERLAY_ACTORS:
        try:
            installed.append(
                scene.insert_before(scene.backplot, actor_type(canon)))
        except Exception as exc:
            LOG.warning("backplot actors: could not add %s: %s",
                        actor_type.__name__, exc)

    # The tool marker. Both the attribute and the list position are updated -
    # upstream's replace() returns the new part precisely so that is one
    # statement, because doing only one of the two leaves the scene drawing a
    # different part from the one GlCanonDraw reaches by name.
    try:
        replaced = scene.replace(scene.tool, InsertActor(canon))
        scene.tool = _move_last(scene, replaced)
        installed.append(scene.tool)
    except Exception as exc:
        LOG.warning("backplot actors: could not replace the tool marker: %s",
                    exc)
    return installed


def _move_last(scene, part):
    """Move ``part`` to the end of the draw order, keeping its gate.

    The tool marker is the top of the picture - it says where the tool is, and
    nothing on the plot should be drawn over it. Upstream leaves it mid-order,
    with its own overlay after it.

    Removed and re-added rather than regated, because the attribute has to go
    on pointing at the part the scene draws: ``GlCanonDraw`` reaches this one
    by name. ``scene.tool`` is reassigned by the caller from what this
    returns.
    """
    gate = scene.parts[scene.index_of(part)][1]
    scene.remove(part)
    return scene.add(part, gate)
