"""The machine travel box, fixed in machine coordinates."""

from teachinlathe.ui.tabs.programs.backplot.actors.base import Actor, GL_LESS


class MachineLimitsBoxActor(Actor):
    """Draw configured travel limits without applying a tool offset.

    LinuxCNC's stock LimitsBoxPart subtracts the active tool offset. That
    makes physical machine travel appear to move when a tool is changed.
    The limits belong to G53, so the backplot draws their raw machine bounds.
    """

    FOLLOW_PROGRAM_ORIGIN = False
    DEPTH_MODE = GL_LESS
    LINE_WIDTH = 1.0

    def draw(self, ctx):
        minimum, maximum = ctx.limits
        ctx.prim.draw_cube(ctx, minimum, maximum,
                           color=ctx.colors["limits"])
