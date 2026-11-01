"""M6, G28 and G30 targets, in the machine frame."""

import math

from teachinlathe.ui.tabs.programs.backplot.actors import screen, text
from teachinlathe.ui.tabs.programs.backplot.actors.base import Actor

# The Machine Limits canvas uses these colors for the three machine targets.
COLORS = {
    "M6": (0.902, 0.318, 0.000),   # #e65100
    "G28": (0.416, 0.106, 0.604),  # #6a1b9a
    "G30": (0.000, 0.514, 0.561),  # #00838f
}

RADIUS_PX = 7.0
CROSS_SCALE = 1.6
FONT = "axis"


class PresetPositionsActor(Actor):
    """Draw machine preset targets like the Machine Limits screen does."""

    FOLLOW_PROGRAM_ORIGIN = False
    MULTISAMPLE = True
    LINE_WIDTH = 1.5

    def __init__(self, host=None):
        super().__init__(host)

    def draw(self, ctx):
        positions = getattr(self._host, "preset_positions", ())
        if not positions:
            return

        mvp = ctx.mv.mvp()
        scale = screen.pixels_per_unit(ctx, mvp)
        if scale is None:
            return
        px_per_z, px_per_x = scale
        radius_z = RADIUS_PX / px_per_z
        radius_x = RADIUS_PX / px_per_x

        labels = {name: [] for name in COLORS}
        placed = []
        for name, x, z in positions:
            point = ctx.to_internal_units((x, 0.0, z))
            x_model, z_model = point[0], point[2]
            color = COLORS.get(name)
            if color is None:
                continue

            ring = []
            for step in range(48):
                angle = 2.0 * math.pi * step / 48
                ring.extend([
                    (x_model + radius_x * math.sin(angle), 0.0,
                     z_model + radius_z * math.cos(angle)),
                    (x_model + radius_x * math.sin(angle + 2.0 * math.pi / 48),
                     0.0,
                     z_model + radius_z * math.cos(angle + 2.0 * math.pi / 48)),
                ])
            cross_x = radius_x * CROSS_SCALE
            cross_z = radius_z * CROSS_SCALE
            cross = [
                (x_model - cross_x, 0.0, z_model),
                (x_model + cross_x, 0.0, z_model),
                (x_model, 0.0, z_model - cross_z),
                (x_model, 0.0, z_model + cross_z),
            ]
            self.stroke(ctx, ring, color, mvp)
            self.stroke(ctx, cross, color, mvp)

            corner = 0
            for old_x, old_z, old_corner in placed:
                if abs(old_x - x_model) < 1e-9 and abs(old_z - z_model) < 1e-9:
                    corner = old_corner + 1
            placed.append((x_model, z_model, corner))
            projected = text.to_screen(mvp, (x_model, 0.0, z_model),
                                       (ctx.width, ctx.height))
            if projected is None:
                continue
            # The canvas starts with the label at the target's top right;
            # rotate through the other corners when targets coincide.
            corners = (
                (text.LEFT, text.BOTTOM, 1, 1),
                (text.LEFT, text.TOP, 1, -1),
                (text.RIGHT, text.BOTTOM, -1, 1),
                (text.RIGHT, text.TOP, -1, -1),
            )
            align_x, align_y, sign_x, sign_y = corners[corner % len(corners)]
            labels[name].append((name,
                                 projected[0] + sign_x * RADIUS_PX,
                                 projected[1] + sign_y * RADIUS_PX,
                                 align_x, align_y))

        for name, color in COLORS.items():
            text.draw(ctx, labels[name], color, FONT)
