"""
GremlinWidget — LinuxCNC Gremlin-based G-code backplot widget for TeachInLathe.

Drop-in replacement for QtPyVCP's VTKBackPlot. Wraps LinuxCNC's Lcnc_3dGraphics
(qt5_graphics.py) which is a QOpenGLWidget that renders G-code tool paths using
OpenGL, with live back-plotting during program execution.

Dependencies (all system-installed by LinuxCNC):
    - qt5_graphics    (Lcnc_3dGraphics — the core OpenGL widget)
    - glnav           (3D navigation: pan, rotate, zoom)
    - rs274.glcanon   (G-code geometry storage and drawing)
    - rs274.interpret (G-code state machine mixin)
    - linuxcnc        (machine status C extension)
    - gcode           (G-code parser C extension)
    - OpenGL          (python3-opengl)
"""

from qtpyvcp.utilities import logger
LOG = logger.getLogger('qtpyvcp.' + __name__)

try:
    from qt5_graphics import Lcnc_3dGraphics
    _LIB_GOOD = True
except ImportError as e:
    LOG.error('GremlinWidget: could not import qt5_graphics: %s', e)
    _LIB_GOOD = False

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class GremlinWidget(Lcnc_3dGraphics if _LIB_GOOD else QWidget):
    """
    LinuxCNC Gremlin backplot widget configured for lathe use.

    Subclasses Lcnc_3dGraphics (QOpenGLWidget) directly, adding:
      - Lathe mode enabled by default (XZ plane view, diameter display)
      - VTKBackPlot-compatible API: setViewXZ2(), enable_panning(), clearLivePlot()
      - Gradient background disabled (matches TeachInLathe dark theme)

    Usage in mainwindow.py (same as VTKBackPlot):
        self.vtk.setViewXZ2()
        self.vtk.enable_panning(True)
        self.vtk.clearLivePlot()

    The widget name in the .ui file should remain 'vtk' so that no changes
    are required in mainwindow.py, only the widget class needs to be swapped.
    """

    def __init__(self, runtime_store=None, parent=None):
        if parent is None and runtime_store is not None and not hasattr(runtime_store, 'poll'):
            parent = runtime_store
            runtime_store = None

        self._runtime_store = runtime_store
        if not _LIB_GOOD:
            QWidget.__init__(self, parent)
            layout = QVBoxLayout(self)
            label = QLabel("Gremlin unavailable\n(qt5_graphics not found)", self)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            return

        super().__init__(parent)

        # Force lathe mode — this project is always a lathe.
        # Must be set before realize() is called so set_view_y() picks it up.
        self.lathe_option = True

        # Show diameter (not radius) on DRO, standard for lathes
        self.show_lathe_radius = False

        # 'y' + is_lathe()=True → orthographic XZ plane view (same as AXIS lathe):
        # CNC Z goes right (spindle axis), CNC X goes down (diameter, larger at bottom).
        # perspective=False is set by set_view_y() automatically.
        self.current_view = 'y'
        self._pending_default_view = False
        self._last_preview_tool_signature = None

        # ------------------------------------------------------------------
        # Color overrides — all values are (R, G, B) tuples in 0.0–1.0 range.
        # Alpha variants use a separate key with '_alpha' suffix (0.0–1.0).
        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # Cone (tool position marker) shape
        # base_radius / height = tan(half-angle): smaller ratio = sharper cone.
        # cone_basesize (inherited) scales the whole cone relative to program extents.
        # ------------------------------------------------------------------
        self.cone_tip_radius   = 0.0    # 0 = perfect point
        self.cone_base_radius  = 0.06   # default 0.10 — decrease for sharper
        self.cone_height       = 0.35   # default 0.25 — increase for longer/slimmer
        self.cone_basesize     = 0.4    # overall scale factor (default 0.5)

        # Enable coordinate overlay (DRO) drawn over the plot
        self.enable_dro   = True
        self.show_overlay = True

        # Font for the DRO overlay — Pango font string, number at end is point size.
        self._font = 'monospace bold 14'

        # 'back': (0.92, 0.92, 0.92),  # light grey background
        self.colors.update({
            # Background
            'back':               (0.10, 0.10, 0.10),   # dark grey background

            # G-code preview lines (program not yet run)
            'straight_feed':      (0.00, 0.60, 1.00),   # blue — linear feed moves
            'arc_feed':           (0.00, 0.80, 0.80),   # cyan — arc feed moves
            'traverse':           (0.40, 0.40, 0.40),   # grey — rapid moves

            # Live back-plot (lines drawn while program runs)
            'backplotfeed':       (0.20, 0.80, 0.20),   # green — executed feed
            'backplotarc':        (0.00, 0.90, 0.60),   # teal  — executed arc
            'backplottraverse':   (0.50, 0.50, 0.50),   # grey  — executed rapid
            'backplotjog':        (1.00, 0.80, 0.00),   # yellow — jog moves
            'backplottoolchange': (1.00, 0.50, 0.00),   # orange — tool change

            # Tool cone at current position
            'cone':               (1.00, 1.00, 1.00),   # white

            # Lathe tool shape
            'lathetool':          (0.70, 0.70, 0.70),

            # Coordinate axis arrows
            'axis_x':             (0.20, 1.00, 0.20),   # green
            'axis_y':             (1.00, 0.20, 0.20),   # red
            'axis_z':             (0.40, 0.40, 1.00),   # blue

            # Machine limits bounding box
            'grid':               (0.20, 0.20, 0.20),
        })

    # ------------------------------------------------------------------
    # Overrides to fix file loading and view fitting
    # ------------------------------------------------------------------

    def cache_tool(self, current_tool):
        """
        Override to always draw the lathe tool shape when orientation is set,
        even when diameter == 0. The parent only calls lathetool() when both
        diameter != 0 and orientation != 0 — which means tools without a
        diameter set never show orientation-dependent shapes.
        """
        from OpenGL.GL import glNewList, glEndList, glBlendColor, GL_COMPILE
        self.cached_tool = current_tool

        orientation = current_tool.orientation if hasattr(current_tool, 'orientation') else current_tool[-1]
        diameter    = current_tool.diameter    if hasattr(current_tool, 'diameter')    else current_tool[-4]

        if self.is_lathe() and orientation != 0:
            # Build a synthetic tool entry with a fallback diameter so that
            # lathetool() always produces a visible shape.
            MIN_DIAMETER = 10.0  # mm — used only when tool diameter is 0
            if diameter == 0:
                # Replace diameter field; tool table entries are namedtuples
                try:
                    current_tool = current_tool._replace(diameter=MIN_DIAMETER)
                except AttributeError:
                    # plain tuple fallback
                    t = list(current_tool)
                    t[-4] = MIN_DIAMETER
                    current_tool = tuple(t)

            glNewList(self.dlist('tool'), GL_COMPILE)
            glBlendColor(0, 0, 0, self.colors['lathetool_alpha'])
            self.lathetool(current_tool)
            glEndList()
        else:
            super().cache_tool(current_tool)

    def make_cone(self, n):
        """Override to use configurable cone dimensions."""
        from OpenGL.GLU import gluNewQuadric, gluCylinder, gluDisk, gluDeleteQuadric
        from OpenGL.GL import (glNewList, glEndList, glPushMatrix, glPopMatrix,
                               glTranslatef, glEnable, glDisable, glBlendColor,
                               GL_COMPILE, GL_LIGHTING)
        q = gluNewQuadric()
        glNewList(n, GL_COMPILE)
        glBlendColor(0, 0, 0, self.colors['tool_alpha'])
        glEnable(GL_LIGHTING)
        gluCylinder(q, self.cone_tip_radius, self.cone_base_radius,
                    self.cone_height, 32, 1)
        glPushMatrix()
        glTranslatef(0, 0, self.cone_height)
        gluDisk(q, 0, self.cone_base_radius, 32, 1)
        glPopMatrix()
        glDisable(GL_LIGHTING)
        glEndList()
        gluDeleteQuadric(q)

    def realize(self):
        super().realize()
        if self._current_file:
            self._pending_default_view = True
            self.update()

    def _build_preview_initcodes(self, stat):
        initcodes = []

        tool_offset = "G43.1"
        has_offset = False
        for i in range(9):
            if stat.axis_mask & (1 << i):
                value = stat.tool_offset[i]
                tool_offset += " %s%.8f" % ("XYZABCUVW"[i], value)
                has_offset = has_offset or abs(value) > 1e-12

        if has_offset:
            initcodes.append(tool_offset)

        return initcodes

    def report_gcode_error(self, result, seq, filename):
        message = f"Gremlin preview error {result} at line {seq} while loading {filename}"
        try:
            LOG.error(message)
        except Exception:
            print(message)
        try:
            self.output_notify_message(message)
        except Exception:
            pass

    def _reload_preview(self, filename=None, *, sync_task=True):
        import os
        import shutil
        import tempfile

        import gcode
        from qt5_graphics import DummyProgress, Progress, StatCanon

        linuxcnc = __import__("linuxcnc")

        if sync_task:
            linuxcnc.command().task_plan_synch()

        snapshot = self._runtime_store.poll() if self._runtime_store else None
        stat = self._runtime_store.stat if self._runtime_store else self.stat
        if not self._runtime_store:
            stat.poll()

        runtime_file = snapshot.machine_file if snapshot else getattr(stat, 'file', '')
        if not filename and runtime_file:
            filename = runtime_file
        elif not filename and not runtime_file:
            return

        with open(filename, 'r', encoding='utf-8', errors='replace') as handle:
            lines = handle.readlines()
        progress = Progress(2, len(lines))
        progress.emit_percent = self.emit_percent

        code = []
        i = 0
        for i, line in enumerate(lines):
            line = line.expandtabs().replace("\r", "")
            code.extend(["%6d: " % (i + 1), "lineno", line, ""])
            if i % 1000 == 0:
                del code[:]
                progress.update(i)
        progress.nextphase(len(lines))

        td = tempfile.mkdtemp()
        self._current_file = filename
        canon = None
        try:
            self._last_preview_tool_signature = (
                snapshot.preview_tool_signature if snapshot else (
                    stat.tool_in_spindle,
                    tuple(stat.tool_offset),
                )
            )
            random = int(self.inifile.find("EMCIO", "RANDOM_TOOLCHANGER") or 0)
            arcdivision = int(self.inifile.find("DISPLAY", "ARCDIVISION") or 64)
            text = ""
            canon = StatCanon(
                self.colors,
                self.get_geometry(),
                self.foam_option,
                self.lathe_option,
                stat,
                text,
                random,
                i,
                progress,
                arcdivision,
            )
            canon.output_notify_message = self.output_notify_message
            parameter = self.inifile.find("RS274NGC", "PARAMETER_FILE")
            temp_parameter = os.path.join(td, os.path.basename(parameter or "linuxcnc.var"))
            if parameter:
                shutil.copy(parameter, temp_parameter)
            canon.parameter_file = temp_parameter

            initcodes = self._build_preview_initcodes(stat)
            initcode = self.inifile.find("RS274NGC", "RS274NGC_STARTUP_CODE") or ""
            linear_units = snapshot.linear_units if snapshot else stat.linear_units
            unitcode = "G%d" % (20 + (linear_units == 1))
            if initcodes:
                if initcode:
                    initcodes.insert(0, initcode)
                initcodes.insert(0, unitcode)
                result, seq = self.load_preview(filename, canon, initcodes)
            else:
                result, seq = self.load_preview(filename, canon, unitcode, initcode)
            if result > gcode.MIN_ERROR:
                self.report_gcode_error(result, seq, filename)
            self.logger.set_depth(
                self.from_internal_linear_unit(self.get_foam_z()),
                self.from_internal_linear_unit(self.get_foam_w()),
            )
            self.calculate_gcode_properties(canon)
        except Exception as e:
            print(e)
            self.gcode_properties = None
        finally:
            shutil.rmtree(td)
            if canon:
                canon.progress = DummyProgress()
            try:
                progress.done()
            except UnboundLocalError:
                pass
        self._redraw()

    def load(self, filename=None):
        self._reload_preview(filename, sync_task=True)

    def poll(self):
        linuxcnc = __import__("linuxcnc")

        if self._runtime_store:
            snapshot = self._runtime_store.poll()
            s = self._runtime_store.stat
        else:
            s = self.stat
            try:
                s.poll()
            except Exception:
                return
            preview_tool_signature = (
                s.tool_in_spindle,
                tuple(s.tool_offset),
            )
            machine_file = s.file
            task_mode = s.task_mode
            fingerprint = (
                self.logger.npts,
                self.soft_limits(),
                s.actual_position,
                s.joint_actual_position,
                s.homed,
                s.g5x_offset,
                s.g92_offset,
                s.limit,
                s.tool_in_spindle,
                s.motion_mode,
                s.current_vel,
            )
            if machine_file and machine_file != self._current_file:
                self._reload_preview(machine_file, sync_task=False)
                self._pending_default_view = True
                return True
            if (
                self._current_file
                and task_mode != linuxcnc.MODE_AUTO
                and preview_tool_signature != self._last_preview_tool_signature
            ):
                self._reload_preview(self._current_file, sync_task=False)
                self._pending_default_view = True
                return True
            if fingerprint != self.fingerprint:
                self.fingerprint = fingerprint
                self.update()
            return True

        machine_file = snapshot.machine_file
        if machine_file and machine_file != self._current_file:
            self._reload_preview(machine_file, sync_task=False)
            self._pending_default_view = True
            return True

        if (
            self._current_file
            and snapshot.task_mode != linuxcnc.MODE_AUTO
            and snapshot.preview_tool_signature != self._last_preview_tool_signature
        ):
            self._reload_preview(self._current_file, sync_task=False)
            self._pending_default_view = True
            return True

        fingerprint = (
            self.logger.npts,
            self.soft_limits(),
            snapshot.actual_position,
            snapshot.joint_actual_position,
            snapshot.homed,
            snapshot.g5x_offset,
            snapshot.g92_offset,
            snapshot.limit,
            snapshot.tool_in_spindle,
            snapshot.motion_mode,
            snapshot.current_vel,
        )

        if fingerprint != self.fingerprint:
            self.fingerprint = fingerprint
            self.update()
        return True

    def paintGL(self):
        # Apply the default lathe view on the first paint after a file is loaded.
        # Done here rather than outside paintGL because Qt guarantees the GL
        # context is current inside this method — modifications to the MODELVIEW
        # matrix are guaranteed to take effect for this frame.
        if self._pending_default_view:
            self._pending_default_view = False
            self.current_view = 'y'
            self.set_view_y()   # modifies MODELVIEW matrix + sets self.distance
        super().paintGL()

    # ------------------------------------------------------------------
    # Custom DRO overlay — lathe-specific: Tool / Z / Dia
    # ------------------------------------------------------------------

    def dro_format(self, s, spd, dtg, limit, homed,
                   positions, axisdtg, g5x_offset, g92_offset, tlo_offset):
        fmt  = self.dro_mm if self.get_show_metric() else self.dro_in
        line = "% 6s:" + fmt

        posstrs = [
            "   T%-2d" % s.tool_in_spindle,
            line % ("Z",   positions[2]),
            line % ("Dia", positions[0] * 2.0),
        ]
        return limit, homed, posstrs, posstrs

    # ------------------------------------------------------------------
    # VTKBackPlot-compatible API
    # ------------------------------------------------------------------

    def setViewXZ2(self):
        """Set view to XZ plane (standard lathe view). Matches VTKBackPlot.setViewXZ2()."""
        self.current_view = 'y'
        if self.display_loaded:
            self.set_view_y()
            self.update()

    def enable_panning(self, enabled):
        """
        Enable or disable panning via left mouse button.
        In Gremlin, mouse_btn_mode=0 uses button list (L=pan, R=rotate, M=zoom).
        This is a no-op because panning is always available; provided for API
        compatibility with VTKBackPlot.
        """
        pass

    def clearLivePlot(self):
        """Clear the live back-plot trace. Matches VTKBackPlot.clearLivePlot()."""
        self.clear_live_plotter()

    def zoomIn(self):
        """Zoom in slot — connected from zoomInView button in mainwindow.ui."""
        self.zoomin()
        self.current_view = 'y'
        self.set_view_y()
        self.update()

    def zoomOut(self):
        """Zoom out slot — connected from zoomOutView button in mainwindow.ui."""
        self.zoomout()
        self.current_view = 'y'
        self.set_view_y()
        self.update()
