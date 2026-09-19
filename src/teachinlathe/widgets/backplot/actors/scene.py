"""The cast, and the order it is drawn in.

Every actor the backplot shows is named here once - the ones in this package
and the ones LinuxCNC already provides - so the composition of the scene is
readable in one file rather than inferred from where each was registered.

**The toolpath, the tool and its trace are upstream actors, deliberately.**
They are already Parts with exactly this shape: ``ProgramPart`` draws the
toolpath, ``ToolPart`` the marker at the current position, ``BackplotPart``
the trace it leaves. Re-writing them here would fork the renderer, and the
trace especially: its ``BackplotRing`` uploads only the points that are new,
growing by doubling, and drawing it naively instead re-uploads the whole trail
every frame - a cost that climbs with the trail, which is the shape of the
stutter this screen was cured of. They stay upstream; what this file does is
place our actors around them and leave one place to configure them.

Panning and zooming are not an actor's concern. The camera is on the
model-view stack the frame carries, so every actor draws in model space and is
moved and scaled together with the rest.
"""

import logging

from teachinlathe.widgets.backplot.actors.axis_arrows import AxisArrowsActor
from teachinlathe.widgets.backplot.actors.axis_letters import AxisLettersActor
from teachinlathe.widgets.backplot.actors.base import LIB_GOOD, InertActor
from teachinlathe.widgets.backplot.actors.origin import OriginActor

LOG = logging.getLogger(__name__)

#: Ours, appended in this order - which is also front-to-back, the last drawn
#: sitting over the ones before it.
OVERLAY_ACTORS = (AxisArrowsActor, AxisLettersActor, OriginActor)


def install(canon):
    """Compose the scene: empty the stock axes, append ours after the rest.

    Appending is what puts these actors over the toolpath and the trace; the
    depth test each one sets is what stops the geometry already drawn from
    rejecting their fragments. Both are needed - see ``Actor.scope``.
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
    for actor_type in OVERLAY_ACTORS:
        try:
            installed.append(scene.add(actor_type()))
        except Exception as exc:
            LOG.warning("backplot actors: could not add %s: %s",
                        actor_type.__name__, exc)
    return installed
