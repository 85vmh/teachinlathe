"""Machine point and tool-offset dimensions, toggled from the backplot."""

import math

from teachinlathe.ui.tabs.programs.backplot.actors import geometry, palette, screen, text
from teachinlathe.ui.tabs.programs.backplot.actors.base import Actor
from teachinlathe.ui.tabs.programs.backplot.actors.units import to_mm

OFFSET_COLOR = (69 / 255.0, 90 / 255.0, 100 / 255.0)  # Machine Limits #455a64
MACHINE_MARK_RADIUS_PX = 8.0
DIMENSION_ARROW_LENGTH_PX = 14.0
DIMENSION_ARROW_HALF_WIDTH_PX = 3.2
DASH_PATTERN_PX = (12.0, 4.0)
FONT = "offset_dimension"


class ToolChangeOffsetsActor(Actor):
    """Show the G53 point and the two tool offsets while enabled."""

    FOLLOW_PROGRAM_ORIGIN = False
    MULTISAMPLE = True
    DEPTH_WRITE = False
    LINE_WIDTH = 1.0

    def draw(self, ctx):
        host = self._host
        if not getattr(host, "show_tool_change_offsets", False):
            return

        machine = ctx.to_internal_units(ctx.stat.actual_position)[:3]
        offset = ctx.to_internal_units(ctx.stat.tool_offset)[:3]
        tip = tuple(machine[i] - offset[i] for i in range(3))

        mvp = ctx.mv.mvp()
        scale = screen.pixels_per_unit(ctx, mvp)
        if scale is None:
            return
        px_per_z, px_per_x = scale
        tip_point = (tip[0], 0.0, tip[2])
        machine_point = (machine[0], 0.0, machine[2])

        # Dashed projection guides from the tip to the two axes through the
        # machine-coordinate point, as on Machine Coordinates.
        self.stroke(ctx, geometry.dashed(
            tip_point, (machine[0], 0.0, tip[2]), DASH_PATTERN_PX,
            px_per_x), OFFSET_COLOR, mvp)
        self.stroke(ctx, geometry.dashed(
            tip_point, (tip[0], 0.0, machine[2]), DASH_PATTERN_PX,
            px_per_z), OFFSET_COLOR, mvp)

        # Dimension arrows run from the edge of the machine-position sign to
        # the corresponding dashed projection.
        x_offset = machine[0] - tip[0]
        z_offset = machine[2] - tip[2]
        radius_x = MACHINE_MARK_RADIUS_PX / px_per_x
        radius_z = MACHINE_MARK_RADIUS_PX / px_per_z
        if abs(x_offset) > 1e-12:
            direction = -1.0 if x_offset > 0 else 1.0
            start = (machine[0] + direction * radius_x, 0.0, machine[2])
            end = (tip[0], 0.0, machine[2])
            self._dimension(ctx, start, end, (direction, 0.0, 0.0),
                            (0.0, 0.0, 1.0), px_per_x, px_per_z, mvp)
            midpoint = ((start[0] + end[0]) / 2.0, 0.0, machine[2])
            self._label(ctx, "X: %.3f" % to_mm(x_offset), midpoint,
                        (ctx.width, ctx.height), mvp,
                        x=8.0 if direction < 0 else -8.0,
                        align_x=text.LEFT if direction < 0 else text.RIGHT,
                        align_y=text.CENTRE)

        if abs(z_offset) > 1e-12:
            direction = -1.0 if z_offset > 0 else 1.0
            start = (machine[0], 0.0, machine[2] + direction * radius_z)
            end = (machine[0], 0.0, tip[2])
            self._dimension(ctx, start, end, (0.0, 0.0, direction),
                            (1.0, 0.0, 0.0), px_per_z, px_per_x, mvp)
            midpoint = (machine[0], 0.0, (start[2] + end[2]) / 2.0)
            self._label(ctx, "Z: %.3f" % to_mm(z_offset), midpoint,
                        (ctx.width, ctx.height), mvp, y=-10.0,
                        align_x=text.CENTRE, align_y=text.TOP)

        self._machine_mark(ctx, machine_point, px_per_z, mvp)

    def _dimension(self, ctx, start, end, direction, perpendicular,
                   px_along, px_across, mvp):
        """A line with inward-facing arrowheads at both ends."""
        along = 0 if direction[0] else 2
        span = abs(end[along] - start[along])
        head = DIMENSION_ARROW_LENGTH_PX / px_along
        half = DIMENSION_ARROW_HALF_WIDTH_PX / px_across
        if span <= 2 * head:
            self.stroke(ctx, [start, end], OFFSET_COLOR, mvp)
            return

        unit = direction
        reverse = tuple(-part for part in unit)
        line_start = tuple(start[i] + unit[i] * head for i in range(3))
        line_end = tuple(end[i] + reverse[i] * head for i in range(3))
        self.stroke(ctx, [line_start, line_end], OFFSET_COLOR, mvp)
        self.fill(ctx, _arrow(start, unit, perpendicular, head, half),
                  OFFSET_COLOR, mvp)
        self.fill(ctx, _arrow(end, reverse, perpendicular, head, half),
                  OFFSET_COLOR, mvp)

    @staticmethod
    def _label(ctx, value, point, viewport, mvp, x=0.0, y=0.0,
               align_x=text.LEFT, align_y=text.CENTRE):
        projected = text.to_screen(mvp, point, viewport)
        if projected is None:
            return
        text.draw(ctx, [(value, projected[0] + x, projected[1] + y,
                         align_x, align_y)], OFFSET_COLOR, FONT)

    def _machine_mark(self, ctx, point, px_per_z, mvp):
        """The four-quadrant G53 position sign used on Machine Coordinates."""
        radius = MACHINE_MARK_RADIUS_PX / px_per_z
        width = 1.0 / px_per_z
        outer = radius + width / 2.0
        disc = _at(geometry.circle_sector(outer, 0.0, 2 * math.pi, 48), point)
        quadrant = _at(geometry.circle_sector(
            radius, -math.pi / 2, math.pi / 2, 12), point)
        ring = _at(geometry.annulus(radius, width, 48), point)
        self.fill(ctx, disc, palette.BACK, mvp)
        self.fill(ctx, quadrant, palette.ORIGIN, mvp)
        self.fill(ctx, ring, palette.ORIGIN, mvp)

        # Keep both diameters visible across the filled and empty quadrants.
        self.stroke(ctx, [
            (point[0] - radius, point[1], point[2]),
            (point[0] + radius, point[1], point[2]),
            (point[0], point[1], point[2] - radius),
            (point[0], point[1], point[2] + radius),
        ], palette.ORIGIN, mvp)


def _arrow(tip, direction, perpendicular, length, half_width):
    base = tuple(tip[i] + direction[i] * length for i in range(3))
    left = tuple(base[i] + perpendicular[i] * half_width for i in range(3))
    right = tuple(base[i] - perpendicular[i] * half_width for i in range(3))
    return [tip, left, right]


def _at(points, origin):
    return [(x + origin[0], y + origin[1], z + origin[2])
            for x, y, z in points]
