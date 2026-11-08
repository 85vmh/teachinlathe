"""M6, G28 and G30 targets, in the machine frame."""

import math

from teachinlathe.ui.tabs.programs.backplot.actors import screen, text
from teachinlathe.ui.tabs.programs.backplot.actors.base import Actor

# The Machine Limits canvas's colours for the three machine targets - Theme.qml's
# positionToolChange, positionG28, positionG30: change them there and here.
COLORS = {
    "M6": (0.902, 0.318, 0.000),   # #e65100
    "G28": (0.416, 0.106, 0.604),  # #6a1b9a
    "G30": (0.000, 0.514, 0.561),  # #00838f
}

RADIUS_PX = 7.0
CROSS_SCALE = 1.6
FONT = "machine_label"
LABEL_GAP_PX = 4.0


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
        label_bounds = []
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

            projected = text.to_screen(mvp, (x_model, 0.0, z_model),
                                       (ctx.width, ctx.height))
            if projected is None:
                continue
            # Prefer the target's top right, then choose the first corner
            # whose text box does not collide with a previously placed label.
            corners = (
                (text.LEFT, text.BOTTOM, 1, 1),
                (text.RIGHT, text.BOTTOM, -1, 1),
                (text.LEFT, text.TOP, 1, -1),
                (text.RIGHT, text.TOP, -1, -1),
            )
            best = None
            best_collisions = None
            width = text.width(name, FONT)
            height = text.line_height(FONT)
            for align_x, align_y, sign_x, sign_y in corners:
                label_x = projected[0] + sign_x * (RADIUS_PX + 2.0)
                label_y = projected[1] + sign_y * (RADIUS_PX + 2.0)
                bounds = (
                    label_x - width * align_x - LABEL_GAP_PX,
                    label_y - height * align_y - LABEL_GAP_PX,
                    label_x + width * (1.0 - align_x) + LABEL_GAP_PX,
                    label_y + height * (1.0 - align_y) + LABEL_GAP_PX,
                )
                collisions = sum(_overlaps(bounds, old)
                                 for old in label_bounds)
                if best is None or collisions < best_collisions:
                    best = (name, label_x, label_y, align_x, align_y)
                    best_collisions = collisions
                    best_bounds = bounds
                if collisions == 0:
                    break
            labels[name].append(best)
            label_bounds.append(best_bounds)

        for name, color in COLORS.items():
            text.draw(ctx, labels[name], color, FONT)


def _overlaps(first, second):
    return (first[0] < second[2] and first[2] > second[0]
            and first[1] < second[3] and first[3] > second[1])
