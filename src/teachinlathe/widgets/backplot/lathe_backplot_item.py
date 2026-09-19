"""The G-code backplot, as a Qt Quick item rather than a widget.

The preview used to be LinuxCNC's ``Lcnc_3dGraphics`` - a ``QOpenGLWidget`` -
held over a placeholder in the QML scene and moved by hand whenever anything
resized. That was the one thing keeping a QWidget tree in this application.

It is no longer needed. LinuxCNC split the preview renderer out of the widget:
``rs274.glcanon_gl`` draws through shaders against an explicit projection and
model-view, and what ``GlCanonDraw`` still wants from whatever hosts it is
small enough to list - a viewport size, a way to ask for a repaint, and three
no-ops left over from the GTK original. A ``QQuickFramebufferObject`` can
supply all of it, so the renderer draws straight into the scene graph.

``Lcnc_3dGraphics`` is not subclassed here, because subclassing it would drag
in the ``QOpenGLWidget`` it is. Its logic - view handling, preview loading,
the DRO overlay, the many ``get_*`` hooks ``GlCanonDraw`` calls back into - is
grafted onto a plain QObject instead, minus the dozen methods that are purely
the widget's (see ``_WIDGET_ONLY``). Everything else stays upstream's, so this
does not fork the renderer.
"""

import logging
import os
import shutil
import tempfile
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtOpenGL import (QOpenGLFramebufferObject,
                            QOpenGLFramebufferObjectFormat)
from PyQt6.QtQml import qmlRegisterType
from PyQt6.QtQuick import QQuickFramebufferObject

from teachinlathe.widgets.backplot import actors

LOG = logging.getLogger(__name__)

#: How often the preview looks at the machine, in milliseconds.
#:
#: The tool marker and the live trail only move when this fires, so it is what
#: sets how smooth they look. Each tick costs one linuxcnc status poll (a
#: shared-memory read, negligible); each tick that finds the machine has moved
#: costs a redraw of the preview - about 4 ms of CPU at full screen with a
#: program loaded - and one repaint of the window.
#:
#: 40 ms is 25 updates a second, roughly a tenth of one core while the machine
#: is moving. 25 ms looks smoother again and costs about a sixth; below the
#: display's own 60 Hz there is nothing left to gain.
PREVIEW_POLL_INTERVAL_MS = 40

#: Set TEACHINLATHE_PERF=1 in the environment to have the preview report what
#: it costs, every few seconds, to the usual log.
#:
#: This is here because the preview's share of the frame budget is the thing
#: most likely to creep: it is the only part of the UI that redraws on the
#: machine's clock rather than on the operator's. A profiler attached by hand
#: sees a moment; these counters cover a whole program, which is what shows
#: whether something grows as the program advances.
#:
#: Off by default, and when off it costs one attribute test per poll and per
#: frame.
PERF_LOGGING = bool(os.environ.get("TEACHINLATHE_PERF"))
PERF_REPORT_INTERVAL_MS = 5000

# Mirrors gremlin_widget.py: qt5_graphics reaches for Qt through qtpy, which
# picks PyQt5 unless told otherwise, and two bindings in one process do not
# survive each other. teachinlathe/__init__ pins this already; repeated here
# because this module is importable on its own.
os.environ.setdefault("QT_API", "pyqt6")

try:
    import glnav
    from rs274 import glcanon
    from qt5_graphics import Lcnc_3dGraphics
    LIB_GOOD = True
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot: LinuxCNC preview modules unavailable: %s", exc)
    LIB_GOOD = False


# Methods of Lcnc_3dGraphics that exist only because it is a QOpenGLWidget.
# Everything not named here is grafted onto the headless host below.
#
# The GL entry points (initializeGL/paintGL/resizeGL) become the renderer's
# job; the event handlers become QML's, forwarded through the slots on
# LatheBackplotItem; winfo_* answer from the FBO instead of the widget
# geometry; and activate/deactivate/swapbuffers/_redraw are the GTK-era
# context dance, which Qt Quick already does for us.
_WIDGET_ONLY = frozenset({
    "__init__",
    "showEvent",
    "initializeGL", "paintGL", "resizeGL",
    "wheelEvent", "mousePressEvent", "mouseReleaseEvent",
    "mouseDoubleClickEvent", "mouseMoveEvent",
    "winfo_width", "winfo_height",
    "minimumSizeHint", "sizeHint",
    "activate", "deactivate", "swapbuffers", "_redraw",
    "set_current_view", "update",
    # Re-declared on the host, because a Signal has to be a class attribute
    # at class-definition time to become a real signal.
    "percentLoaded", "xRotationChanged", "yRotationChanged", "zRotationChanged",
})


def _grafted_namespace():
    """Lcnc_3dGraphics' own attributes, minus the widget-only ones.

    Only the class's own ``__dict__`` is taken - the GlCanonDraw and GlNavBase
    halves of its bases are inherited normally by the host. The two ``super()``
    calls in the class are both in methods that are excluded, so nothing
    grafted here carries a ``__class__`` cell that would look for
    Lcnc_3dGraphics in the host's MRO and not find it.
    """
    return {
        name: value
        for name, value in vars(Lcnc_3dGraphics).items()
        if name not in _WIDGET_ONLY and not name.startswith("__")
    }


if LIB_GOOD:
    _HostBase = type(
        "_HostBase",
        (QObject, glcanon.GlCanonDraw, glnav.GlNavBase),
        _grafted_namespace(),
    )
else:  # pragma: no cover - keeps the module importable without LinuxCNC
    _HostBase = QObject


class _PreviewPerf:
    """Counters for what the preview costs, reported on a timer.

    Rates are per second over the reporting window, so they can be compared
    across windows of different lengths, and "share of one core" is the number
    to watch: it is what the preview takes away from the thread the rest of
    the UI draws on.
    """

    def __init__(self, parent):
        self._timer = QTimer(parent)
        self._timer.setInterval(PERF_REPORT_INTERVAL_MS)
        self._timer.timeout.connect(self.report)
        self._reset(time.perf_counter())
        self._timer.start()

    def _reset(self, now):
        self._since = now
        self.polls = 0
        self.updates = 0
        self.renders = 0
        self.render_s = 0.0
        self.render_worst_s = 0.0
        self.reloads = 0
        self.reload_s = 0.0

    def render_done(self, seconds):
        self.renders += 1
        self.render_s += seconds
        if seconds > self.render_worst_s:
            self.render_worst_s = seconds

    def report(self):
        now = time.perf_counter()
        elapsed = now - self._since
        if elapsed <= 0:
            return
        mean_ms = 1000.0 * self.render_s / self.renders if self.renders else 0.0
        LOG.info(
            "preview: %.1f polls/s, %.1f redraws asked/s, %.1f drawn/s, "
            "%.2f ms mean, %.2f ms worst, %.1f%% of one core; "
            "%d reloads (%.0f ms)",
            self.polls / elapsed,
            self.updates / elapsed,
            self.renders / elapsed,
            mean_ms,
            1000.0 * self.render_worst_s,
            100.0 * self.render_s / elapsed,
            self.reloads,
            1000.0 * self.reload_s,
        )
        self._reset(now)


class LatheBackplotCanon(_HostBase):
    """The preview state and renderer, with no widget under it.

    Holds what ``Lcnc_3dGraphics.__init__`` would have set up - the position
    logger, the INI-derived options, the view defaults - plus this lathe's
    own configuration, which used to live in ``GremlinWidget``.
    """

    percentLoaded = pyqtSignal(int)
    xRotationChanged = pyqtSignal(int)
    yRotationChanged = pyqtSignal(int)
    zRotationChanged = pyqtSignal(int)

    def __init__(self, item):
        QObject.__init__(self)
        self._item = item
        # Set for real at the end of this constructor; declared here because
        # the grafted set-up below can already ask for a redraw.
        self._perf = None
        # The viewport the renderer last built an FBO for. Answered by
        # winfo_width/winfo_height, which is the whole of GlCanonDraw's
        # remaining interest in its host.
        self._vp_width = 1
        self._vp_height = 1

        glnav.GlNavBase.__init__(self)

        def C(name):
            alpha = self.colors[name + "_alpha"]
            rgb = self.colors[name]
            return [int(x * 255) for x in rgb + (alpha,)]

        import _thread

        import linuxcnc

        inifile = os.environ.get("INI_FILE_NAME", "/dev/null")
        stat = linuxcnc.stat()
        try:
            stat.poll()
        except Exception:
            from qtvcp.widgets.fake_status import fakeStatus
            stat = fakeStatus()

        self.inifile = linuxcnc.ini(inifile)
        self.foam_option = self.inifile.getbool("DISPLAY", "FOAM", fallback=False)
        try:
            trajcoordinates = self.inifile.find(
                "TRAJ", "COORDINATES").lower().replace(" ", "")
        except Exception:
            trajcoordinates = "unknown"
        kinsmodule = self.inifile.find("KINS", "KINEMATICS")

        self.logger = linuxcnc.positionlogger(
            linuxcnc.stat(),
            C("backplotjog"), C("backplottraverse"), C("backplotfeed"),
            C("backplotarc"), C("backplottoolchange"), C("backplotprobing"),
            self.get_geometry(), self.foam_option,
        )
        _thread.start_new_thread(self.logger.start, (.01,))
        glcanon.GlCanonDraw.__init__(self, stat, self.logger)
        glcanon.GlCanonDraw.init_glcanondraw(
            self, trajcoordinates=trajcoordinates, kinsmodule=kinsmodule)

        self.display_loaded = False
        self.fingerprint = ()
        self.select_primed = None
        self.lat = 0
        self.minlat = -90
        self.maxlat = 90

        self._current_file = None
        self.highlight_line = None
        self.program_alpha = False
        self.use_joints_mode = True
        self.use_commanded = True
        self.show_limits = True
        self.show_extents_option = True
        self.gcode_properties = None
        self.show_live_plot = True
        self.show_velocity = True
        self.metric_units = True
        self.show_program = True
        self.show_rapids = True
        self.use_relative = True
        self.show_tool = True
        self.show_dtg = True
        self.grid_size = 0.0

        self.show_offsets = False
        self.use_default_controls = True
        self.mouse_btn_mode = 0
        self._mousemoved = False
        self.cancel_rotate = False
        self.use_gradient_background = False
        self.gradient_color1 = (0.0, 0.0, 1.0)
        self.gradient_color2 = (0.0, 0.0, 0.0)
        self.a_axis_wrapped = self.inifile.getbool("AXIS_A", "WRAPPED_ROTARY", fallback=False)
        self.b_axis_wrapped = self.inifile.getbool("AXIS_B", "WRAPPED_ROTARY", fallback=False)
        self.c_axis_wrapped = self.inifile.getbool("AXIS_C", "WRAPPED_ROTARY", fallback=False)

        self._tool_dia = 0
        self.spindle_speed = 0

        live_axis_count = 0
        for i, _name in enumerate("XYZABCUVW"):
            if self.stat.axis_mask & (1 << i) == 0:
                continue
            live_axis_count += 1
        self.num_joints = self.inifile.getint("KINS", "JOINTS", fallback=live_axis_count)

        self.presetViewSettings(v=None, z=0, x=0, y=0, lat=None, lon=None)
        self._presetFlag = False

        self.object = 0
        self.xRot = 0
        self.yRot = 0
        self.zRot = 0

        self.Green = QColor.fromCmykF(0.40, 0.0, 1.0, 0.0)
        self.inhibit_selection = True

        self.dro_in = "% 9.4f"
        self.dro_mm = "% 9.3f"
        self.dro_deg = "% 9.2f"
        self.dro_vel = "Vel:% 6.2f"
        self.dro_vel_mm = "Vel:% 9.2f"
        self.fpr_in = "FPR: %.3f"
        self.fpr_mm = "FPR: % 1.2f"
        self.sf_in = "SFM: %4d"
        self.sf_mm = "SMM: %4d"
        self._fontLarge = 'monospace bold 22'
        self._largeFontState = False
        self._scroll_mode = 0
        self._invertWheelZoom = False
        self.mach_units = 'Metric'

        self._configure_for_lathe()

        # The preview keeps its own clock and its own status handle.
        #
        # Following the runtime store's snapshotChanged instead tied the tool
        # marker to that store's 150 ms timer, which is a visible stagger at
        # constant feed. Upstream's addTimer() is not used either: it is fixed
        # at 100 ms, and the interval belongs to this preview, not to the
        # class it was grafted from.
        self._timer = QTimer(self)
        self._timer.setInterval(PREVIEW_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self.poll)
        self._timer.start()

        self._perf = _PreviewPerf(self) if PERF_LOGGING else None

        # The first look at the machine, from the event loop rather than from
        # whatever is running now: this constructor is reached through
        # createRenderer(), inside the render pass. It is also what loads the
        # preview when a program is already on the machine at start-up, since
        # realize() no longer does.
        QTimer.singleShot(0, self.poll)

    # ── this lathe's configuration (was GremlinWidget) ──────────────────────

    def _configure_for_lathe(self):
        # Always a lathe, whatever [DISPLAY]LATHE says; must be set before
        # realize() so set_view_y() picks the XZ plane up.
        self.lathe_option = True
        # Diameter, not radius - standard for a lathe DRO.
        self.show_lathe_radius = False
        # 'y' + is_lathe() -> orthographic XZ, the same view AXIS uses:
        # Z right (spindle axis), X down (diameter growing downwards).
        self.current_view = 'y'
        self._pending_default_view = False
        self._last_preview_tool_signature = None
        # The program the Programs screen loaded, which is not always the file
        # the interpreter is reading - see poll().
        self._program_file = ''

        # No DRO on the plot: the screen already has one, larger and beside
        # it. enable_dro is the gate on the whole overlay part in the scene,
        # so this removes the readout and its backdrop together, rather than
        # drawing them and hiding them.
        self.enable_dro = False
        self.show_overlay = False
        self._font = 'monospace bold 14'

        # GlCanonDraw.colors is a class attribute: updating it in place would
        # repaint every other preview in the process too.
        #
        # The whole palette is tuned for a light background, to match the
        # panels the rest of the screen uses. That is not a one-line change:
        # upstream's defaults assume black, so the tool cone is white and the
        # jog trace is yellow - both invisible here - and the bright axis and
        # feed colours wash out. Every entry below was darkened for white. If
        # 'back' ever goes dark again, these go back with it.
        self.colors = dict(self.colors)
        self.colors.update({
            'back':               (1.00, 1.00, 1.00),

            # Program preview.
            'straight_feed':      (0.00, 0.35, 0.75),
            'arc_feed':           (0.00, 0.45, 0.55),
            'traverse':           (0.62, 0.62, 0.62),

            # Live trace.
            'backplotfeed':       (0.00, 0.55, 0.10),
            'backplotarc':        (0.00, 0.50, 0.40),
            'backplottraverse':   (0.62, 0.62, 0.62),
            'backplotjog':        (0.80, 0.55, 0.00),
            'backplottoolchange': (0.85, 0.35, 0.00),

            # The tool marker. White on black upstream, which is nothing at
            # all on white.
            'cone':               (0.15, 0.15, 0.15),
            'lathetool':          (0.35, 0.35, 0.35),

            # Axes. The actors read these, so the arrows follow the palette.
            'axis_x':             (0.00, 0.60, 0.00),
            'axis_y':             (0.75, 0.00, 0.00),
            'axis_z':             (0.10, 0.10, 0.75),

            # Dimension lines, labels and the machine-limit box.
            'label_ok':           (0.55, 0.15, 0.15),
            'label_limit':        (0.85, 0.00, 0.05),
            'small_origin':       (0.00, 0.50, 0.55),
            'dwell':              (0.80, 0.25, 0.25),
            'grid':               (0.85, 0.85, 0.85),
        })

        # Still honoured by the current renderer; the cone_tip/base/height
        # overrides that went with it are not - the display-list make_cone()
        # they patched no longer exists in rs274.glcanon.
        self.cone_basesize = 0.4

        # The annotation actors - arrows, letters, origin - over the
        # toolpath and the trace. See actors/scene.py for the whole cast.
        actors.install(self)

    # ── the host contract GlCanonDraw still expects ─────────────────────────

    def set_viewport(self, width, height):
        self._vp_width = max(1, int(width))
        self._vp_height = max(1, int(height))

    def winfo_width(self):
        return self._vp_width

    def winfo_height(self):
        return self._vp_height

    # Qt Quick makes the context current around render() and owns the buffer
    # swap, so the GTK-era context dance is three no-ops.
    def activate(self):
        pass

    def deactivate(self):
        pass

    def swapbuffers(self):
        pass

    def makeCurrent(self):
        pass

    def doneCurrent(self):
        pass

    def _count_update(self):
        if self._perf is not None:
            self._perf.updates += 1

    def update(self, *_args, **_kwargs):
        """Ask for another frame.

        Named ``update`` because glcanon and the grafted Lcnc_3dGraphics
        methods call it expecting QWidget.update(); it schedules a Quick
        repaint instead.
        """
        self._count_update()
        item = self._item
        if item is not None:
            item.update()

    def _redraw(self):
        self.update()

    def set_current_view(self):
        # Upstream makes the widget's context current first; there is no
        # separate context to make current here.
        if self.current_view not in ('p', 'x', 'y', 'y2', 'z', 'z2'):
            return None
        return getattr(self, 'set_view_%s' % self.current_view)()

    # ── rendering ───────────────────────────────────────────────────────────

    def render_frame(self):
        """Draw one frame into whatever framebuffer is currently bound.

        The body is Lcnc_3dGraphics.paintGL plus the deferred default view
        that GremlinWidget applied there: the view has to be set with the
        context current, because set_view_y() writes the model-view the same
        frame draws from.
        """
        if self._pending_default_view:
            self._pending_default_view = False
            self.current_view = 'y'
            self.set_view_y()
        started = time.perf_counter() if self._perf is not None else 0.0
        try:
            if self.perspective:
                self.redraw_perspective()
            else:
                self.redraw_ortho()
        except Exception as exc:
            LOG.error("backplot render failed: %s", exc)
        if self._perf is not None:
            self._perf.render_done(time.perf_counter() - started)

    # ── preview loading ─────────────────────────────────────────────────────

    def realize(self):
        """GL set-up, and nothing else.

        This runs inside the scene graph's render pass. Upstream's realize()
        ends by loading the preview, and loading it issues
        ``task_plan_synch()`` - a command on LinuxCNC's command channel, which
        blocks until the interpreter answers. That was survivable when the
        preview was a QOpenGLWidget realising in its own initializeGL; here it
        would block the render pass, and with it every other item in the
        window. A stalled command channel would freeze the DRO, not just the
        plot.

        So the preview is not loaded here. poll() notices that the machine's
        file differs from the one on screen and loads it from the event loop,
        without the task synch.
        """
        self.set_current_view()
        if not self._presetFlag:
            self.recordCurrentViewSettings()

        try:
            self.stat.poll()
        except Exception:
            return
        self._current_file = None
        self.set_font(False)
        glcanon.GlCanonDraw.realize(self)

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
        message = "Backplot preview error %s at line %s while loading %s" % (
            result, seq, filename)
        LOG.error(message)
        try:
            self.output_notify_message(message)
        except Exception:
            pass

    def _reload_preview(self, filename=None, *, sync_task=False):
        """Re-parse the program and rebuild the preview.

        ``sync_task`` writes to LinuxCNC's command channel and waits for the
        interpreter. Nothing here asks for it: the two callers below both pass
        False, and it defaults to False so that a future caller has to opt in
        deliberately rather than block the UI by accident.
        """
        import gcode
        import linuxcnc
        from qt5_graphics import DummyProgress, Progress, StatCanon

        reload_started = time.perf_counter() if self._perf is not None else 0.0

        if sync_task:
            linuxcnc.command().task_plan_synch()

        # This preview's own status handle, freshly polled - the same one
        # poll() reads. It used to take the runtime store's snapshot, which
        # refreshes on a timer of its own and so could be a sixth of a second
        # out of date at the moment the program is parsed.
        stat = self.stat
        try:
            stat.poll()
        except Exception:
            pass

        runtime_file = getattr(stat, 'file', '')
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
                stat.tool_in_spindle, tuple(stat.tool_offset))
            random = int(self.inifile.find("EMCIO", "RANDOM_TOOLCHANGER") or 0)
            arcdivision = int(self.inifile.find("DISPLAY", "ARCDIVISION") or 64)
            canon = StatCanon(
                self.colors, self.get_geometry(), self.foam_option,
                self.lathe_option, stat, "", random, i, progress, arcdivision,
            )
            canon.output_notify_message = self.output_notify_message
            parameter = self.inifile.find("RS274NGC", "PARAMETER_FILE")
            temp_parameter = os.path.join(td, os.path.basename(parameter or "linuxcnc.var"))
            if parameter:
                shutil.copy(parameter, temp_parameter)
            canon.parameter_file = temp_parameter

            initcodes = self._build_preview_initcodes(stat)
            initcode = self.inifile.find("RS274NGC", "RS274NGC_STARTUP_CODE") or ""
            linear_units = stat.linear_units
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
        except Exception as exc:
            LOG.error("backplot preview failed: %s", exc)
            self.gcode_properties = None
        finally:
            shutil.rmtree(td, ignore_errors=True)
            if canon:
                canon.progress = DummyProgress()
            try:
                progress.done()
            except UnboundLocalError:
                pass
            if self._perf is not None:
                self._perf.reloads += 1
                self._perf.reload_s += time.perf_counter() - reload_started
        self._redraw()

    def poll(self):
        import linuxcnc

        # Read from this preview's own linuxcnc.stat, not from the runtime
        # store's snapshot: the store refreshes on a timer of its own, so
        # taking the position from it would cap the marker at that rate however
        # often this runs. A status poll is a shared-memory read.
        if self._perf is not None:
            self._perf.polls += 1

        stat = self.stat
        try:
            stat.poll()
        except Exception:
            return None
        machine_file = os.path.abspath(stat.file) if stat.file else ''
        call_level = int(getattr(stat, 'call_level', 0) or 0)
        task_mode = stat.task_mode
        tool_signature = (stat.tool_in_spindle, tuple(stat.tool_offset))
        source = stat

        # The interpreter's current file is not necessarily the program. While
        # a subroutine runs, stat.file names the subroutine, and call_level
        # does not always rise in the same status update - so the guard below
        # lets one through. Parsing a subroutine on its own fails, because it
        # is a sub/endsub with no main body, and the failure would replace a
        # good preview with a broken one and then reload the program again
        # when the interpreter came back. The Programs screen says which file
        # is the program; when it has, anything else is ignored.
        wanted_file = self._program_file or machine_file
        if wanted_file and wanted_file != self._current_file and call_level == 0:
            self._reload_preview(wanted_file, sync_task=False)
            self._pending_default_view = True
            return True

        if (self._current_file
                and task_mode != linuxcnc.MODE_AUTO
                and tool_signature != self._last_preview_tool_signature):
            self._reload_preview(self._current_file, sync_task=False)
            self._pending_default_view = True
            return True

        fingerprint = (
            self.logger.npts,
            self.soft_limits(),
            source.actual_position,
            source.joint_actual_position,
            source.homed,
            source.g5x_offset,
            source.g92_offset,
            source.limit,
            source.tool_in_spindle,
            source.motion_mode,
            source.current_vel,
        )
        if fingerprint != self.fingerprint:
            self.fingerprint = fingerprint
            self.update()
        return True

    # ── the lathe DRO overlay: Tool / Z / Dia ───────────────────────────────

    # Only reached if enable_dro is turned back on in _configure_for_lathe;
    # kept because it is what makes the readout read as a lathe's - tool, Z
    # and diameter - rather than the default three-axis one.
    def dro_format(self, s, spd, dtg, limit, homed,
                   positions, axisdtg, g5x_offset, g92_offset, tlo_offset):
        fmt = self.dro_mm if self.get_show_metric() else self.dro_in
        line = "% 6s:" + fmt

        posstrs = [
            "   T%-2d" % s.tool_in_spindle,
            line % ("Z", positions[2]),
            line % ("Dia", positions[0] * 2.0),
        ]
        return limit, homed, posstrs, posstrs

    # ── view control ────────────────────────────────────────────────────────

    def set_program_file(self, path):
        """The program to preview, as opposed to whatever the interpreter has
        open. Empty falls back to following the machine's file."""
        self._program_file = os.path.abspath(path) if path else ''

    def set_lathe_view(self):
        """The standard XZ lathe view, fitted to the window."""
        self.current_view = 'y'
        self._pending_default_view = False
        try:
            self.set_view_y()
        except Exception as exc:
            LOG.debug("set_view_y failed: %s", exc)
        self.update()

    def clear_live_plot(self):
        self.clear_live_plotter()

    def zoom_in(self):
        self.current_view = 'y'
        self.zoomin()
        self.update()

    def zoom_out(self):
        self.current_view = 'y'
        self.zoomout()
        self.update()


class _BackplotRenderer(QQuickFramebufferObject.Renderer):
    """Draws the preview into the item's framebuffer.

    ``realize()`` needs a current GL context - it compiles the shaders and
    builds the buffers - so it is deferred to the first render() rather than
    done when the canon is constructed.
    """

    def __init__(self, canon):
        super().__init__()
        self._canon = canon
        self._realized = False
        # Qt takes ownership of the framebuffer, but sip does not know that,
        # so without a reference on this side Python frees it the moment
        # createFramebufferObject returns and the next frame draws into
        # released memory.
        self._fbo = None

    def createFramebufferObject(self, size):
        self._canon.set_viewport(size.width(), size.height())
        fmt = QOpenGLFramebufferObjectFormat()
        # The preview depth-tests; without an attachment here the tool cone
        # and the limits box draw in whatever order they happen to come in.
        fmt.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
        # No multisampling, which is what the QOpenGLWidget had:
        # preview_surface_format() never asks for samples. 4x MSAA over the
        # whole viewport plus a resolve every frame is not free on the panel's
        # integrated GPU, and nothing asked for smoother lines.
        self._fbo = QOpenGLFramebufferObject(size, fmt)
        return self._fbo

    def render(self):
        if not self._realized:
            try:
                self._canon.realize()
            except Exception as exc:
                LOG.error("backplot realize failed: %s", exc)
            # Set regardless: a realize that raised will raise again every
            # frame, and the log would be the only thing rendered.
            self._realized = True
        self._canon.render_frame()


class LatheBackplotItem(QQuickFramebufferObject):
    """The QML-facing item. Instantiated from QML as ``LatheBackplot``.

    The runtime store is injected from Python after construction, because QML
    creates the item: ``ProgramsController`` hands over the same store the
    rest of the Programs screen reads.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._canon = None
        # The preview draws bottom-up, as OpenGL does; Quick composes
        # top-down.
        self.setMirrorVertically(True)

    # ── wiring ──────────────────────────────────────────────────────────────

    def canon(self):
        if self._canon is None and LIB_GOOD:
            self._canon = LatheBackplotCanon(self)
        return self._canon

    def createRenderer(self):
        return _BackplotRenderer(self.canon())

    # ── slots QML and the controller call ───────────────────────────────────

    @pyqtSlot()
    def zoomIn(self):
        canon = self.canon()
        if canon is not None:
            canon.zoom_in()

    @pyqtSlot()
    def zoomOut(self):
        canon = self.canon()
        if canon is not None:
            canon.zoom_out()

    @pyqtSlot()
    def fitToWindow(self):
        canon = self.canon()
        if canon is not None:
            canon.set_lathe_view()

    @pyqtSlot()
    def clearPlot(self):
        canon = self.canon()
        if canon is not None:
            canon.clear_live_plot()

    @pyqtSlot()
    def poll(self):
        canon = self.canon()
        if canon is not None:
            canon.poll()

    @pyqtSlot(str)
    def setProgramFile(self, path):
        """Tell the preview which file is the program.

        Without this it follows the interpreter's current file, which dips
        into subroutines while the program runs.
        """
        canon = self.canon()
        if canon is not None:
            canon.set_program_file(path)

    @pyqtSlot(str)
    def invalidatePreview(self, path):
        """Drop the cached preview so the next poll reloads it.

        The Programs screen calls this when a new program is about to be
        loaded: the file name on disk can stay the same while its contents
        change, and the preview is keyed on the name.
        """
        canon = self.canon()
        if canon is not None:
            canon.clear_live_plot()
            canon._current_file = ''

    # ── pointer interaction, forwarded from QML ─────────────────────────────

    @pyqtSlot(float, float)
    def pressed(self, x, y):
        canon = self.canon()
        if canon is None:
            return
        canon.recordMouse(int(x), int(y))
        canon.startZoom(int(y))

    @pyqtSlot(float, float)
    def panned(self, x, y):
        canon = self.canon()
        if canon is None:
            return
        canon.translateOrRotate(int(x), int(y))
        self.update()

    @pyqtSlot(float)
    def zoomDragged(self, y):
        canon = self.canon()
        if canon is None:
            return
        canon.continueZoom(int(y))
        self.update()

    @pyqtSlot(float)
    def wheelZoom(self, angle_delta):
        canon = self.canon()
        if canon is None:
            return
        if angle_delta < 0:
            canon.zoom_out()
        else:
            canon.zoom_in()


def register_qml_types():
    """Make the item available to QML as ``TeachInLathe.Backplot 1.0``."""
    qmlRegisterType(LatheBackplotItem, "TeachInLathe.Backplot", 1, 0,
                    "LatheBackplot")
