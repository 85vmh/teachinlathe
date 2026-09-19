"""Shapes the actors build, kept apart from the actors that draw them.

Everything here returns plain vertex lists in model space. Nothing touches GL
or the frame; an actor decides when and in what transform to draw them, which
is what keeps each actor's file about its own concern.
"""

import math


def side_of(direction):
    """The other in-plane axis, so a shape opens in the XZ plane a lathe view
    looks at: across for a Z-going thing, along for an X-going one."""
    return (0.0, 0.0, 1.0) if direction[0] else (1.0, 0.0, 0.0)


def scaled(direction, length):
    """``direction`` scaled to ``length``."""
    return tuple(component * length for component in direction)


def arrow_head(direction, length, head_length, head_width):
    """The three corners of a solid arrow head, tip first.

    The tip is at ``length`` along ``direction``; the base sits one
    ``head_length`` back from it, ``head_width`` to either side.
    """
    tip = scaled(direction, length)
    base = scaled(direction, length - head_length)
    side = side_of(direction)

    def corner(sign):
        return tuple(base[i] + side[i] * head_width * sign for i in range(3))

    return [tip, corner(+1), corner(-1)]


def circle_point(radius, angle):
    """A point on a circle lying in the XZ plane.

    Angle 0 is +Z and a quarter turn is +X, so the quadrants line up with the
    axes as they are drawn: +Z to the right, +X downwards.
    """
    return (radius * math.sin(angle), 0.0, radius * math.cos(angle))


def circle_outline(radius, segments):
    """A closed circle as GL_LINES endpoint pairs."""
    points = []
    for i in range(segments):
        points.append(circle_point(radius, 2 * math.pi * i / segments))
        points.append(circle_point(radius, 2 * math.pi * (i + 1) / segments))
    return points


def circle_sector(radius, start_angle, span, segments):
    """A filled sector as GL_TRIANGLES, fanned from the centre."""
    points = []
    steps = max(2, segments)
    for i in range(steps):
        a0 = start_angle + span * i / steps
        a1 = start_angle + span * (i + 1) / steps
        points.extend([(0.0, 0.0, 0.0),
                       circle_point(radius, a0),
                       circle_point(radius, a1)])
    return points
