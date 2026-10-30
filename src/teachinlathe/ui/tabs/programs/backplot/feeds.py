"""Where the backplot's picture comes from: the machine (LiveFeed) or a dry
run of a program (SimulatedFeed). Everything drawn - the toolpath, the
stock, the trail, the tool, the material left - is drawn the same from
either; only these differ.

A feed is what the backplot reads the machine through:

* ``stat`` - what ``linuxcnc.stat`` answers: where the machine is, the tool
  in its spindle and its offset, the work offset, the program;
* ``logger`` - what ``linuxcnc.positionlogger`` answers: the trail, the
  points the tool's tip went through, each in the colour of its motion -
  machine coordinates and units, the tool offset taken out - and the last
  of them, where the tool marker is drawn;
* ``observe()`` - told on every poll of the backplot's, drawn or not;
* ``material_left(ctx, host)`` - the part as it is being cut, a
  simulation.logic.material.MaterialLeft (``material``, a shapely (z, r)
  shape in mm in the work coordinates, and ``version``), or None with no
  stock to cut. Both feeds cut it with the one model of a tool taking off
  material (simulation.logic.material): the machine's from its trail, the
  simulation's from the run.
"""

import logging

LOG = logging.getLogger(__name__)

try:
    import numpy as np
    from rs274.glcanon_bake import LOGGER_DTYPE
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot feeds: preview modules unavailable: %s", exc)
    np = None

#: The position logger's colours, in the order it is given them - and its
#: index of each: the machine's motion type (EMC_MOTION_TYPE_*), 0 a jog.
COLOR_NAMES = ("backplotjog", "backplottraverse", "backplotfeed", "backplotarc",
               "backplottoolchange", "backplotprobing")
TRAVERSE, FEED, ARC, TOOL_CHANGE = 1, 2, 3, 4


def _machine_status():
    """A ``linuxcnc.stat``, polled; the fake one qtvcp has with no machine."""
    import linuxcnc

    stat = linuxcnc.stat()
    try:
        stat.poll()
    except Exception:
        from qtvcp.widgets.fake_status import fakeStatus
        stat = fakeStatus()
    return stat


def _stock_shape(stock):
    """The bar ``stock`` - the conversational header's workpiece, as the
    backplot holds it - as the shapely shape the material left is cut from;
    None with no bar."""
    from teachinlathe.conversational.gcode.stock import header_material
    from teachinlathe.conversational.model.data_types import Workpiece

    if not stock:
        return None
    try:
        shape = header_material(Workpiece.from_dict(dict(stock)))
    except (KeyError, TypeError, ValueError) as exc:
        LOG.debug("backplot: no bar to cut from %s: %s", stock, exc)
        return None
    return None if shape.is_empty else shape


class LiveFeed:
    """The machine: its status and its position logger, and the material
    left cut from the trail it logs, as it logs it."""

    #: Mirrored or not when the plot starts: None, as the operator last left
    #: the machine's plot (lathe_backplot_item._mirror), which this follows.
    MIRROR = None

    def __init__(self):
        self.stat = None
        self.logger = None
        self._material = None
        self._basis = None
        self._done = 0
        self._shapes = {}
        #: the tool in the spindle along the trail: (first point, T number),
        #: noted on every poll - drawn or not, so a trail made while the plot
        #: was not on screen is still cut with the tools that made it
        self._tools = []

    def start(self, colors, geometry, foam):
        """The status handle and the logger, running: ``colors`` as COLOR_NAMES."""
        import _thread

        import linuxcnc

        self.stat = _machine_status()
        self.logger = linuxcnc.positionlogger(linuxcnc.stat(), *colors, geometry, foam)
        _thread.start_new_thread(self.logger.start, (.01,))

    def observe(self):
        """The tool in the spindle from the trail's point it has reached."""
        npts = int(getattr(self.logger, "npts", 0) or 0)
        tool = int(getattr(self.stat, "tool_in_spindle", 0) or 0)
        if self._tools and npts < self._tools[-1][0]:
            self._tools = []            # cleared, or moved down: from here on
        if not self._tools or self._tools[-1][1] != tool:
            self._tools.append((max(0, npts - 1), tool))

    def _tool_at(self, index):
        tool = self._tools[0][1] if self._tools else 0
        for first, held in self._tools:
            if first > index:
                break
            tool = held
        return tool

    def material_left(self, ctx, host):
        """The bar, less what the trail's cutting moves took off it so far -
        each with the tool that made it - brought up to date with the trail."""
        from teachinlathe.simulation.logic.material import MaterialLeft

        stat = ctx.stat
        stock = getattr(host, "stock", None) or {}
        # in the frame the stock is drawn in: where the program started
        # (StockActor.place), else where the work offset is now
        origin = getattr(host, "preview_origin", None) or (
            tuple(stat.g5x_offset), tuple(stat.g92_offset), float(stat.rotation_xy))
        basis = (tuple(sorted(stock.items())) if isinstance(stock, dict) else stock, origin)
        npts = _trail_length(ctx)
        # the bar again when it, or the frame it is in, changed, or the trail
        # was cleared; a full logger moved its points down: read it again
        if basis != self._basis or npts < 2 or self._material is None:
            self._basis, self._done = basis, 0
            shape = _stock_shape(stock)
            self._material = MaterialLeft(shape) if shape is not None else None
        elif npts < self._done:
            self._done = 0
        if self._material is None:
            return None
        # from the start of the last segment read: the logger may have
        # stretched it since; cut twice, it takes nothing more off
        found = cutting_segments(ctx, origin, max(0, self._done - 2))
        if found is None:
            return self._material
        starts, ends, self._done, index = found
        drawing = getattr(host, "insert", None)
        for start, end, at in zip(starts, ends, index):
            tool = self._shape(self._tool_at(int(at)), drawing)
            self._material.cut([tuple(start), tuple(end)], tool)
        return self._material

    def _shape(self, tool, drawing):
        """What cuts of tool ``tool``, as the Tool Library has it now -
        ``drawing`` (tool_source's) is part of the key: the tool in its
        holder can be edited while it stays in the spindle."""
        key = (tool, drawing)
        if key not in self._shapes:
            from teachinlathe.conversational.gcode.operations.profiling.tool_shape import cutting_shape
            from teachinlathe.core.tool_library_repository import tool_library_repository
            from teachinlathe.tooling.model.data_types import MountedTool

            self._shapes[key] = cutting_shape(MountedTool.of(tool_library_repository(), tool)) if tool else None
        return self._shapes[key]


def cutting_segments(ctx, origin, first=0):
    """The trail's cutting moves from point ``first`` on, as ``(starts, ends,
    npts, index)`` - two ``(N, 2)`` arrays of (z, r) in mm, from ``origin``
    (g5x, g92, XY rotation; machine units), the trail's length and, for each
    move, the index of the point it starts at - or None when there is no
    trail to read. A rapid cuts nothing: each segment is in the motion its
    end point was logged in, and one in the rapid colour is left out."""
    if np is None or ctx.lp is None:
        return None
    try:
        raw, npts, is_xyuv = ctx.lp.points()
        colours = ctx.lp.get_colors()
    except (AttributeError, TypeError) as exc:
        LOG.debug("backplot feeds: no trail to read: %s", exc)
        return None
    if is_xyuv:
        return None
    first = max(0, min(first, npts))
    points = np.frombuffer(raw, dtype=LOGGER_DTYPE, count=npts)[first:]
    if len(points) < 2:
        return np.empty((0, 2)), np.empty((0, 2)), npts, np.empty(0, dtype=np.int64)
    rapid = np.asarray(colours[TRAVERSE], dtype=np.uint8)
    cutting = ~np.all(points["c"][1:] == rapid, axis=1)
    # machine units, the work origin taken out, in mm; the XY rotation
    # turns X into Y, which a lathe has none of
    g5x, g92, _rotation = origin
    per_mm = float(getattr(ctx.stat, "linear_units", 1.0) or 1.0)
    pos = points["pos"].astype(float)
    zr = np.column_stack([(pos[:, 2] - g5x[2] - g92[2]) / per_mm,
                          (pos[:, 0] - g5x[0] - g92[0]) / per_mm])
    index = first + np.flatnonzero(cutting)
    return zr[:-1][cutting], zr[1:][cutting], npts, index


def _trail_length(ctx):
    try:
        return int(ctx.lp.npts)
    except (AttributeError, TypeError, ValueError):
        return 0


class SimulatedFeed:
    """A simulation - ``source``, a SimulateViewModel: its run (``run``, a
    ProgramRun) and the moment shown (``moment``) - as the machine running
    it would be: a status, a trail and the material left, each moment.

    What the run does not say is the machine's: the tool table, the units,
    homing and limits come from its own status. The work offset and the tool
    offset are as they were when the run started from it, as the run was
    worked out from them; a G43 or a G10 in the program moves the trail with
    the program, as the machine's would, but not these.
    """

    #: Mirrored when the plot starts - the material left above the centre
    #: line too - whatever the machine's plot is.
    MIRROR = True

    def __init__(self, source):
        self._source = source
        self.stat = None
        self.logger = None
        self._left = None

    def start(self, colors, geometry, foam):
        self.stat = SimulatedStatus(_machine_status())
        self.logger = SimulatedLogger(colors)
        self._source.runChanged.connect(self._follow_run)
        self._source.momentChanged.connect(self._follow)
        self._follow_run()

    def _follow_run(self):
        run = self._source.run
        self.stat.freeze()
        self.logger.set_run(run, self.stat)
        self._left = None
        self._follow()

    def _follow(self):
        run, moment = self._source.run, self._source.moment
        if run is None or moment is None:
            self.stat.show(None, 0, 0, self._source.programFile)
            self.logger.show(None, 0.0)
            return
        line = run.program.steps[moment.step].where.program_line if run.program.steps else 0
        self.logger.show(moment.step, run.fraction(moment.step, moment.time))
        self.stat.show(self.logger.last(), moment.tool, line, self._source.programFile, moment.origin)
        # a new one only when the material is: the static layer it is drawn
        # in is drawn again for it, and a rapid or a stop cuts nothing
        if self._left is None or self._left.material is not moment.material:
            self._left = _Left(moment.material, moment.time)

    def observe(self):
        pass

    def material_left(self, ctx, host):
        return self._left


class _Left:
    """The material at a moment of the run, as a MaterialLeft reads: what
    is left, and something that changes when it does."""

    def __init__(self, material, version):
        self.material = material
        self.version = version


class SimulatedStatus:
    """``linuxcnc.stat`` as the machine running a simulation would answer it:
    the machine's own status, but where the run is - the tool's position, the
    current loaded tool and its offset, the line, the program running - and
    the work offset the run started from (freeze), moved as the program moves
    its origin (a Facing's new Z0). The tool offset is the loaded tool's, from
    the machine's tool table, as the M6 that loads it sets it: what the limits
    box is drawn back from, the tool tip's reach."""

    def __init__(self, machine):
        self._machine = machine
        self._shown = {}
        self._frozen = {}

    def poll(self):
        try:
            self._machine.poll()
        except Exception:
            pass

    def freeze(self):
        """The offsets now, kept for the run: as it was worked out from them."""
        self._shown = {}
        self.poll()
        m = self._machine
        self._frozen = {
            "g5x_offset": tuple(m.g5x_offset), "g92_offset": tuple(m.g92_offset),
            "g5x_index": m.g5x_index, "rotation_xy": m.rotation_xy,
            "tool_offset": tuple(m.tool_offset),
        }

    def show(self, tip, tool, line, program_file, origin=None):
        """The machine at ``tip`` - the logger's point, the tool offset out -
        with tool ``tool`` in, on ``line`` of ``program_file``, the program's
        work origin at ``origin`` (mm (z, r) from the one the run started
        from; None, there)."""
        import linuxcnc

        offset = self._tool_offset(int(tool))
        if tip is None:
            position = tuple(self._machine.position)
        else:
            position = tuple(t + o for t, o in zip(tuple(tip[:3]) + (0.0,) * 6, offset))
        self._shown = {
            "position": position, "actual_position": position,
            "tool_in_spindle": int(tool), "tool_offset": offset,
            "motion_line": int(line), "current_line": int(line),
            "file": program_file or "", "call_level": 0,
            "task_mode": linuxcnc.MODE_AUTO, "interp_state": linuxcnc.INTERP_READING,
        }
        g5x = self._frozen.get("g5x_offset")
        if origin is not None and g5x is not None and (origin.z or origin.r):
            per_mm = float(self._machine.linear_units or 1.0)
            moved = list(g5x)
            moved[0] += origin.r * per_mm
            moved[2] += origin.z * per_mm
            self._shown["g5x_offset"] = tuple(moved)

    def _tool_offset(self, tool):
        """Tool ``tool``'s offset in the machine's tool table, as
        ``stat.tool_offset`` has one; none for no tool, and the one the run
        started with for a tool the table does not have."""
        frozen = self._frozen.get("tool_offset") or tuple(self._machine.tool_offset)
        if tool <= 0:
            return (0.0,) * len(frozen)
        for entry in getattr(self._machine, "tool_table", ()) or ():
            if int(getattr(entry, "id", -1)) == tool:
                return tuple(float(getattr(entry, axis + "offset", 0.0)) for axis in "xyzabcuvw")
        return frozen

    def __getattr__(self, name):
        shown = self.__dict__.get("_shown", {})
        if name in shown:
            return shown[name]
        frozen = self.__dict__.get("_frozen", {})
        if name in frozen:
            return frozen[name]
        return getattr(self.__dict__["_machine"], name)


class SimulatedLogger:
    """``linuxcnc.positionlogger`` as a simulation's trail: the points the
    tool's tip goes through, from the run's moves up to the moment shown,
    each in its motion's colour - and, as the machine's logger does not know,
    the tool and the program line that made each (blade_shifts)."""

    def __init__(self, colors):
        self._colors = [tuple(int(v) for v in color) for color in colors]
        self._master = None         # every point of the run, LOGGER_DTYPE
        self._ends = []             # how many points there are once each step is done
        self._step_colors = {}      # each move's colour, by its step
        self._run = None
        self._frame = (0.0, 0.0, 1.0)   # the work origin's X, Z in machine units; machine units per mm
        self._shown = np.zeros(0, dtype=LOGGER_DTYPE) if np is not None else None
        self._skip = 0
        # the tool and the program line of each point of the run, and of each
        # shown; a blade's offsets by tool
        self._made_by = (np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)) if np is not None else None
        self._shown_made_by = self._made_by
        self._blades = {}

    def set_run(self, run, stat):
        """The trail of ``run``, in the frame the machine's ``stat`` has:
        the work offset it started with, its units."""
        from teachinlathe.simulation.logic.program_run import move_points
        from teachinlathe.simulation.model.moves import Move, MoveKind

        self._run, self._skip = run, 0
        self._blades = {}
        if run is None or np is None:
            self._master, self._ends = None, []
            return
        g5x, g92 = stat.g5x_offset, stat.g92_offset
        units = float(stat.linear_units or 1.0)
        self._frame = (g5x[0] + g92[0], g5x[2] + g92[2], units)
        colours = {MoveKind.RAPID: TRAVERSE, MoveKind.FEED: FEED, MoveKind.ARC: ARC,
                   MoveKind.TOOL_CHANGE: TOOL_CHANGE}
        points, colors, ends, self._step_colors = [], [], [], {}
        tools, lines = [], []
        start = run.program.start
        if start is not None:
            points.append(tuple(start))
            colors.append(TRAVERSE)
            tools.append(run.program.start_tool)
            lines.append(0)
        for step in run.program.steps:
            if isinstance(step, Move):
                self._step_colors[len(ends)] = colours[step.kind]
                drawn = move_points(step)
                if not points:
                    points.append(drawn[0])
                    colors.append(colours[step.kind])
                    tools.append(step.tool)
                    lines.append(step.where.program_line)
                points.extend(drawn[1:])
                colors.extend([colours[step.kind]] * (len(drawn) - 1))
                tools.extend([step.tool] * (len(drawn) - 1))
                lines.extend([step.where.program_line] * (len(drawn) - 1))
            ends.append(len(points))
        self._master = self._points(points, colors)
        self._made_by = (np.asarray(tools, dtype=np.int64), np.asarray(lines, dtype=np.int64))
        self._ends = ends

    def _points(self, points, colors):
        """(z, r) points in mm, with their colours, as logger points."""
        out = np.zeros(len(points), dtype=LOGGER_DTYPE)
        if not points:
            return out
        x0, z0, units = self._frame
        zr = np.asarray(points, dtype=float)
        out["pos"][:, 0] = zr[:, 1] * units + x0
        out["pos"][:, 2] = zr[:, 0] * units + z0
        out["c"] = np.asarray([self._colors[c] for c in colors], dtype=np.uint8)
        out["pos2"] = out["pos"]
        out["c2"] = out["c"]
        return out

    def show(self, step, fraction):
        """The trail at step ``step`` of the run, ``fraction`` of it done."""
        from teachinlathe.simulation.logic.program_run import move_points
        from teachinlathe.simulation.model.moves import Move

        if self._master is None or step is None:
            self._shown = np.zeros(0, dtype=LOGGER_DTYPE) if np is not None else None
            self._shown_made_by = (np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)) if np is not None else None
            return
        done = self._ends[step - 1] if step > 0 else (1 if self._run.program.start is not None else 0)
        trail = self._master[:done]
        tools, lines = self._made_by[0][:done], self._made_by[1][:done]
        current = self._run.program.steps[step] if step < len(self._run.program.steps) else None
        if isinstance(current, Move) and 0.0 < fraction < 1.0:
            partial = move_points(current, fraction)[1:]
            extra = self._points(partial, [self._step_colors.get(step, FEED)] * len(partial))
            trail = np.concatenate([trail, extra])
            tools = np.concatenate([tools, np.full(len(partial), current.tool)])
            lines = np.concatenate([lines, np.full(len(partial), current.where.program_line)])
        self._shown = trail
        self._shown_made_by = (tools, lines)

    def blade_shifts(self, corners, units):
        """How far along Z each point shown is moved to be drawn as the
        program is for a blade (actors.trail): by the blade that made it and
        the line it was cutting - not, as the machine's trail is, by the tool
        in and the line being cut when the point is first seen, which a seek
        or a fast play would give hundreds of points at once. In the logger's
        unit; None with no points."""
        from teachinlathe.ui.tabs.programs.backplot import blade_middle, tool_source

        if self._shown is None or self._shown_made_by is None:
            return None
        tools, lines = (column[self._skip:] for column in self._shown_made_by)
        shifts = np.zeros(len(tools))
        for tool in np.unique(tools):
            tool = int(tool)
            if not tool:
                continue
            if tool not in self._blades:
                self._blades[tool] = blade_middle.blade_offsets(tool_source.describe(tool))
            shift, half = self._blades[tool]
            if not (shift or half):
                continue
            rows = tools == tool
            corner = np.array([corners.get(int(line), 0) for line in lines[rows]], dtype=float)
            shifts[rows] = (shift + corner * half) * units
        return shifts

    # ── what the backplot asks of a position logger ──────────────────────

    def points(self):
        shown = self._shown[self._skip:] if self._shown is not None else None
        if shown is None:
            return b"", 0, False
        return shown.tobytes(), len(shown), False

    @property
    def npts(self):
        return max(0, len(self._shown) - self._skip) if self._shown is not None else 0

    def last(self, _flag=True):
        if self._shown is None or not len(self._shown):
            return None
        x, y, z = (float(v) for v in self._shown["pos"][-1])
        return (x, y, z, 0.0, 0.0, 0.0)

    def get_colors(self):
        return list(self._colors)

    def clear(self):
        """The trail so far wiped, as the clear button wipes the machine's."""
        self._skip = len(self._shown) if self._shown is not None else 0

    def set_depth(self, *_args):
        pass

    def set_colors(self, *_args):
        pass

    def start(self, *_args):
        pass

    def stop(self):
        pass

    def call(self):
        pass
