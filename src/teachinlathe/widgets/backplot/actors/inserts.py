"""ISO turning-insert geometry, in millimetres.

A port of ``widgets/tool_shapes/TurningInsertBase.qml`` and the family files
beside it. The QML stays where it is - it is what the tool list renders - so
this is a second implementation of the same rules, and the two have to agree.
They are kept honest by ``tests/test_inserts.py``, which checks this module
against the numbers the QML produces.

The reason for the port rather than reuse: the backplot is a
``QQuickFramebufferObject`` drawing OpenGL into the scene graph, and the QML
insert is a ``Canvas`` - a software rasteriser. A Canvas cannot be drawn
inside the framebuffer. What crosses over is the geometry, which is plain
arithmetic in both.

Everything here is 2D and in the insert's own frame: +x and +y as the QML
lays them out, origin at the centre of the inscribed circle. Placing that on
a lathe's XZ plane is the actor's job, not this module's.
"""

import math

#: Families, as the QML files declare them: the ISO shape letter, whether the
#: insert is positive (T, single-sided) or negative (G, double-sided), the
#: inscribed-circle diameters offered, and the size code printed for each.
#:
#: Ordered as the QML ``Size`` enums are, so an index means the same thing on
#: both sides.
FAMILIES = {
    "CCMT": {"shape": "C", "type": "T",
             "ic": (6.35, 9.525, 12.7, 15.875),
             "codes": ("06", "09", "12", "16")},
    "DCMT": {"shape": "D", "type": "T",
             "ic": (6.35, 9.525, 12.7),
             "codes": ("07", "11", "15")},
    "VBMT": {"shape": "V", "type": "T",
             "ic": (6.35, 9.525),
             "codes": ("11", "16")},
    "TCMT": {"shape": "T", "type": "T",
             "ic": (6.35, 9.525, 12.7),
             "codes": ("11", "16", "22")},
    "WNMG": {"shape": "W", "type": "G",
             "ic": (9.525, 12.7, 15.875),
             "codes": ("06", "08", "10")},
    "SNMG": {"shape": "S", "type": "G",
             "ic": (9.525, 12.7, 15.875, 19.05),
             "codes": ("09", "12", "15", "19")},
    "RCMT": {"shape": "R", "type": "T",
             "ic": (8, 10, 12, 16),
             "codes": ("08", "10", "12", "16")},
}

#: Nose radii offered, the same list for every family.
NOSE_RADII = (0.2, 0.4, 0.8, 1.2, 1.6)

#: Included angle of the rhombic shapes, at the cutting corners.
RHOMBIC_ANGLE = {"C": 80.0, "D": 55.0, "V": 35.0}

#: Hole and countersink diameters, by inscribed circle and insert type. As in
#: the QML: entries marked there as measured from a DXF are the T rows for
#: 6.35, 9.525 and 12.7.
HOLES = {
    6.35:   {"T": (2.85, 4.46), "G": (2.80, 4.10)},
    9.525:  {"T": (4.40, 6.33), "G": (3.81, 5.50)},
    12.7:   {"T": (5.50, 7.85), "G": (5.16, 7.40)},
    15.875: {"T": (6.60, 9.20), "G": (6.35, 9.00)},
    19.05:  {"T": (7.93, 11.0), "G": (7.93, 11.0)},
    8:      {"T": (3.40, 5.00), "G": (3.40, 5.00)},
    10:     {"T": (4.40, 6.33), "G": (4.40, 6.33)},
    12:     {"T": (5.50, 7.85), "G": (5.50, 7.85)},
    16:     {"T": (6.60, 9.20), "G": (6.60, 9.20)},
}


class Insert:
    """One insert: a family, a size and a nose radius.

    Built from the family name rather than a shape letter so it reads as the
    thing the operator picked in the tool list, and so the size index means
    what that screen's list means by it.
    """

    def __init__(self, family="DCMT", size_index=1, nose_radius=0.4,
                 active_corner=0):
        if family not in FAMILIES:
            raise KeyError("no such insert family: %s" % family)
        spec = FAMILIES[family]
        self.family = family
        self.shape = spec["shape"]
        self.insert_type = spec["type"]
        index = max(0, min(size_index, len(spec["ic"]) - 1))
        self.size_index = index
        self.ic = float(spec["ic"][index])
        self.size_code = spec["codes"][index]
        self.nose_radius = float(nose_radius)
        self.active_corner = int(active_corner)

    @property
    def iso_code(self):
        """The printed designation, e.g. ``DCMT 11 .. 04``."""
        tenths = int(round(self.nose_radius * 10))
        return "%s %s .. %02d" % (self.family, self.size_code, tenths)

    @property
    def is_round(self):
        return self.shape == "R"

    def hole(self):
        """``(hole diameter, countersink diameter)``, or ``None``."""
        row = HOLES.get(self.ic)
        if row is None:
            return None
        return row.get(self.insert_type) or row.get("T") or row.get("G")

    def outline(self):
        """``(vertices, cutting_indices)`` - the sharp outline, corners not yet
        rounded, walked in order around the shape.

        In order is load-bearing: ``geometry.rounded_polygon`` builds each
        corner against its neighbours, and a vertex list that jumps produces a
        star. The trigon is the one that looks wrong written down - its six
        vertices alternate between two radii, and they are listed by angle.
        """
        radius = self.ic / 2.0

        if self.shape == "R":
            return [], []

        if self.shape == "S":
            circum = radius / math.cos(math.radians(45))
            verts = [_polar(45 + 90 * k, circum) for k in range(4)]
            return verts, [0, 1, 2, 3]

        if self.shape == "T":
            circum = radius / math.cos(math.radians(60))    # == ic
            verts = [_polar(90 + 120 * k, circum) for k in range(3)]
            return verts, [0, 1, 2]

        if self.shape == "W":
            corner = self.ic / 1.286
            flank = 0.6527 * corner
            spec = ((30, flank), (90, corner), (150, flank),
                    (210, corner), (270, flank), (330, corner))
            return [_polar(angle, r) for angle, r in spec], [1, 3, 5]

        # C, D and V: a rhombus, its cutting corners the sharp pair on +-x.
        alpha = RHOMBIC_ANGLE[self.shape]
        side = (radius * 2) / math.sin(math.radians(alpha))
        dx = side * math.cos(math.radians(alpha / 2))
        dy = side * math.sin(math.radians(alpha / 2))
        return [(dx, 0.0), (0.0, dy), (-dx, 0.0), (0.0, -dy)], [0, 2]

    def edge_length(self):
        """Cutting-edge length, in millimetres."""
        if self.shape == "S":
            return self.ic
        if self.shape == "T":
            return self.ic * math.sqrt(3)
        if self.shape in RHOMBIC_ANGLE:
            return self.ic / math.sin(math.radians(RHOMBIC_ANGLE[self.shape]))
        if self.shape == "W":
            return 0.879 * (self.ic / 1.286)
        return math.pi * self.ic                    # round: the circumference

    def _active_index(self, cutting):
        return cutting[min(self.active_corner, len(cutting) - 1)]

    def active_tip(self):
        """The sharp theoretical corner - the point the toolpath is programmed
        to, and so the point the marker is hung from."""
        verts, cutting = self.outline()
        if not verts:
            return 0.0, self.ic / 2.0
        return verts[self._active_index(cutting)]

    def nose_centre(self):
        """Centre of the nose radius - the point that is actually on the path
        when cutter compensation is on."""
        verts, cutting = self.outline()
        if not verts:
            return 0.0, 0.0
        count = len(verts)
        index = self._active_index(cutting)
        vertex = verts[index]
        before = verts[(index - 1) % count]
        after = verts[(index + 1) % count]

        to_before = _unit(before[0] - vertex[0], before[1] - vertex[1])
        to_after = _unit(after[0] - vertex[0], after[1] - vertex[1])
        bisector_x = to_before[0] + to_after[0]
        bisector_y = to_before[1] + to_after[1]
        length = math.hypot(bisector_x, bisector_y)
        if length < 1e-9:
            return vertex

        dot = max(-1.0, min(1.0, to_before[0] * to_after[0]
                                 + to_before[1] * to_after[1]))
        half_angle = math.acos(dot) / 2.0
        if abs(math.sin(half_angle)) < 1e-9:
            return vertex
        distance = self.nose_radius / math.sin(half_angle)
        return (vertex[0] + bisector_x / length * distance,
                vertex[1] + bisector_y / length * distance)

    def max_radius(self):
        """How far the insert reaches from its centre, nose radius included."""
        verts, _cutting = self.outline()
        reach = self.ic / 2.0
        for vertex in verts:
            reach = max(reach, math.hypot(vertex[0], vertex[1]))
        return reach


def _polar(degrees, radius):
    angle = math.radians(degrees)
    return radius * math.cos(angle), radius * math.sin(angle)


def _unit(x, y):
    length = math.hypot(x, y)
    if length < 1e-12:
        return 0.0, 0.0
    return x / length, y / length
