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

from PyQt6.QtCore import QObject, QSize, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtOpenGL import (QOpenGLFramebufferObject,
                            QOpenGLFramebufferObjectFormat)
from PyQt6.QtQml import qmlRegisterType
from PyQt6.QtQuick import QQuickFramebufferObject

from teachinlathe.widgets.backplot import actors, workpiece
from teachinlathe.widgets.backplot.actors import base as actor_base
from teachinlathe.widgets.backplot.actors import palette, screen, text

LOG = logging.getLogger(__name__)

#: How often the preview looks at the machine, in milliseconds.
#:
#: The tool marker and the live trail only move when this fires, so it is what
#: sets how smooth they look. Each tick costs one linuxcnc status poll (a
#: shared-memory read, negligible); each tick that finds the machine has moved
#: costs a redraw of the preview - about 4 ms of CPU at full screen with a
#: program loaded - and one repaint of the window.
#:
#: 40 ms is 25 updates a second. That was roughly a tenth of one core when
#: this was written; it is nearer a quarter now, because the plot has since
#: grown a grid, a scale, stock, hatching, dashed rapids and an insert, and a
#: frame costs about 10 ms rather than the 4 it used to.
#:
#: **This is the largest single lever on that**, and the cheapest: the cost is
#: linear in the rate, and a tool marker is perfectly readable at half of it.
#: 80 ms is twelve updates a second and half the processor;
#: ``TEACHINLATHE_POLL_MS`` sets it without editing anything, so the trade can
#: be heard on the machine rather than argued about here.
PREVIEW_POLL_INTERVAL_MS = int(
    os.environ.get("TEACHINLATHE_POLL_MS", 40) or 40)

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
    from OpenGL.GL import (GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
                           GL_DRAW_FRAMEBUFFER, GL_DRAW_FRAMEBUFFER_BINDING,
                           GL_FALSE, GL_FRAMEBUFFER, GL_MULTISAMPLE,
                           GL_NEAREST, GL_READ_FRAMEBUFFER, GL_TRUE, glBindFramebuffer,
                           glBlitFramebuffer, glClear, glClearColor,
                           glColorMask, glDisable, glGetIntegerv, glViewport)
    from rs274 import glcanon
    from qt5_graphics import Lcnc_3dGraphics
    LIB_GOOD = True
except ImportError as exc:  # pragma: no cover - depends on the LinuxCNC install
    LOG.error("backplot: LinuxCNC preview modules unavailable: %s", exc)
    LIB_GOOD = False


#: Attributes ``Lcnc_3dGraphics.__init__`` sets that this host must set too.
#:
#: The graft takes that class's *methods* and leaves its ``__init__`` behind,
#: because running it would construct the QOpenGLWidget the graft exists to
#: avoid. Anything those methods read as a bare attribute therefore has to be
#: set here instead, and upstream adding one is invisible until the frame that
#: reads it raises - which is every frame, with nothing rendered.
#:
#: ``show_workpiece`` is the one that has already happened, on a LinuxCNC
#: update. ``GlCanonDraw`` reads it through a defensive
#: ``getattr(self, 'show_workpiece', True)``, but qt5_graphics overrides the
#: getter with a bare ``self.show_workpiece``, and that is the one the graft
#: takes.
#:
#: ``tests/test_backplot_graft.py`` checks this against upstream, so the next
#: addition fails a test rather than the render loop.
_GRAFT_REQUIRES = frozenset({
    "show_workpiece",
})

#: Set by ``Lcnc_3dGraphics.__init__`` and deliberately not set here, because
#: only its widget-only methods read it - ``_buttonList`` is the mouse button
#: mapping, read by the event handlers in ``_WIDGET_ONLY``.
_GRAFT_IGNORES = frozenset({
    "_buttonList",
})


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
        self.rebuilds = 0
        self.rebuild_s = 0.0
        self.rebuild_worst_s = 0.0
        self.updates = 0
        self.renders = 0
        self.render_s = 0.0
        self.render_worst_s = 0.0
        self.reloads = 0
        self.reload_s = 0.0

    def layer_rebuilt(self, seconds):
        """One frame that had to draw the static layer again.

        Counted apart from the rest because it is the one frame in the loop
        that is not cheap, and a mean nine times under the worst frame says
        nothing about which frames those are.
        """
        self.rebuilds += 1
        self.rebuild_s += seconds
        self.rebuild_worst_s = max(self.rebuild_worst_s, seconds)

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
            "%d reloads (%.0f ms); %d layer rebuilds (%.1f ms mean, "
            "%.1f ms worst); msaa %s",
            self.polls / elapsed,
            self.updates / elapsed,
            self.renders / elapsed,
            mean_ms,
            1000.0 * self.render_worst_s,
            100.0 * self.render_s / elapsed,
            self.reloads,
            1000.0 * self.reload_s,
            self.rebuilds,
            1000.0 * self.rebuild_s / self.rebuilds if self.rebuilds else 0.0,
            1000.0 * self.rebuild_worst_s,
            # Said out loud, so a run can never be compared against another
            # without knowing which of the two had it on.
            ("%dx" % SAMPLES) if SAMPLES else "off",
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
        # Whether this framebuffer's alpha channel has been made opaque. Reset
        # whenever a new one is made - see _seal_alpha.
        self._alpha_sealed = False

        # The static layer: everything up to the live trace, drawn once and
        # copied back each frame. See redraw().
        self._static_fbo = None
        self._static_key = None
        self._static_at = 0.0

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

        # The stock dimensions for the loaded program, read from the
        # conversational header beside it. Empty until a program is loaded,
        # and empty for a file that has no header - see backplot.workpiece.
        #
        # Named "stock" and not "workpiece" deliberately: upstream's canon has
        # a "workpieces" of its own, one letter away, holding the outlines
        # declared by (WORKPIECE,...) comments. Two different things on one
        # object, distinguished by a plural, is a trap to walk into later.
        self.stock = {}

        # A per-tool insert choice, once the tool list can set one. The insert
        # actor falls back to its own default while this is empty.
        self.insert = {}

        # Upstream's own stock outlines, left on. It draws what
        # (WORKPIECE,...) comments in the G-code declare, and the stock actor
        # draws the conversational header - two sources that in practice never
        # both have something to say: this lathe's generated programs carry
        # the header and no comments, and a hand-written file brought in from
        # elsewhere is the other way round. On, that file still gets its
        # stock; off, it would get none.
        #
        # Set here rather than left to its default because the getter that
        # reads it is qt5_graphics', which is a bare attribute read - see
        # _GRAFT_REQUIRES.
        self.show_workpiece = True

        # Rapids come out of upstream's baked buffer, so that RapidsActor can
        # draw them dashed - which that buffer cannot, having neither a width
        # nor a dash to give. What stays on its fast path is the cutting
        # moves, which are the bulk of a program. See actors/rapids.py.
        self.show_rapids = False

        # GlCanonDraw.colors is a class attribute: updating it in place would
        # repaint every other preview in the process too.
        #
        # The palette is the QML 2D renderer's, so this plot and that one read
        # as the same drawing - see actors/palette.py, which holds the hex each
        # value came from. Upstream's own defaults assume a black background
        # and are unusable here whatever else changes: the tool marker is
        # white and the jog trace yellow.
        #
        # Note the axis pair: **Z is green and X is blue**, which is the QML
        # renderer's choice and the reverse of what this plot used before.
        self.colors = dict(self.colors)
        self.colors.update({
            'back':               palette.BACK,

            # Program preview. One colour for straight and arc feeds alike:
            # the QML renderer drew both in a single 'feed' style, and the
            # distinction is not one an operator reads off the plot.
            #
            # Rapids draw solid. The QML renderer dashed them, but the
            # program's geometry is baked and drawn by upstream's ProgramPart,
            # which has no dash path - see palette.DASH_TRAVERSE.
            'straight_feed':      palette.FEED,
            'arc_feed':           palette.FEED,
            'traverse':           palette.TRAVERSE,

            # Live trace.
            'backplotfeed':       (0.00, 0.55, 0.10),
            'backplotarc':        (0.00, 0.50, 0.40),
            'backplottraverse':   (0.62, 0.62, 0.62),
            'backplotjog':        (0.80, 0.55, 0.00),
            'backplottoolchange': (0.85, 0.35, 0.00),

            # The tool marker. Unused while the insert actor stands in for
            # upstream's ToolPart, which is what drew the cone and the
            # lathetool wedge; kept so turning that replacement off in
            # actors/scene.py gives back something legible rather than white
            # on white.
            'cone':               (0.15, 0.15, 0.15),
            'lathetool':          (0.35, 0.35, 0.35),

            # Axes. The actors read these, so the arrows, letters and ticks
            # all follow the palette.
            'axis_x':             palette.AXIS_X,
            'axis_y':             (0.75, 0.00, 0.00),
            'axis_z':             palette.AXIS_Z,

            # Dimension lines, labels and the machine-limit box.
            'label_ok':           (0.55, 0.15, 0.15),
            'label_limit':        (0.85, 0.00, 0.05),
            'small_origin':       (0.00, 0.50, 0.55),
            'dwell':              (0.80, 0.25, 0.25),
            'grid':               palette.GRID,
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
        self._set_multisample_baseline()
        self._seal_alpha()
        started = time.perf_counter() if self._perf is not None else 0.0
        try:
            # Alpha masked off for the whole frame, so upstream's clear and
            # every draw in it leave the sealed channel alone.
            _set_alpha_writes(False)
            if self.perspective:
                self.redraw_perspective()
            else:
                self.redraw_ortho()
        except Exception as exc:
            LOG.error("backplot render failed: %s", exc)
        finally:
            _set_alpha_writes(True)
        if self._perf is not None:
            self._perf.render_done(time.perf_counter() - started)

    # ── the two layers ──────────────────────────────────────────────────────

    def redraw(self):
        """The frame, in two layers.

        Upstream draws every part on every frame, which it must: the
        framebuffer is cleared first, so there is no such thing as redrawing
        only what moved - the tool marker leaves its old position behind and
        erasing it means drawing back whatever was under it.

        So what does not move is drawn once into a framebuffer of its own and
        copied back at the start of each frame. The split is by position in
        the scene's own parts list, at the live backplot trace: everything
        before it - the grid, the stock and its hatching, the rapids, the
        toolpath, the extents, the limits box - is static until the operator
        moves the view or a new program loads. Everything from the trace on is
        drawn as before, because it moves: the trace, the workpiece, the tool
        marker, and the annotation that has to sit over the tool.

        The body above the split is ``GlCanonDraw.redraw``'s, unchanged - bar
        the import. Upstream has ``linuxcnc`` at module scope; this module
        imports it inside each function that needs it, and a body copied from
        there without the import raises on every frame.
        """
        import linuxcnc

        s = self.stat
        s.poll()
        linuxcnc.gui_rot_offsets(s.g5x_offset[0] + s.g92_offset[0],
                                 s.g5x_offset[1] + s.g92_offset[1],
                                 s.g5x_offset[2] + s.g92_offset[2])

        ctx = self.frame_context()
        scene = self.scene
        try:
            split = scene.index_of(scene.backplot)
        except (AttributeError, ValueError) as exc:
            LOG.debug("backplot: no split point, drawing whole: %s", exc)
            scene.draw(ctx)
            return

        if not STATIC_LAYER or not self._replay_static(ctx, scene, split):
            # Could not cache it - draw the whole scene as upstream does, so a
            # failure here costs speed and nothing else.
            scene.draw(ctx)
            return
        # The baseline again: on a cached frame nothing else has set it, and
        # upstream guarantees every part is entered from it.
        scene.apply_baseline()
        self._draw_parts(ctx, scene.parts[split:])

    @staticmethod
    def _draw_parts(ctx, parts):
        """``Scene.draw``'s loop over a slice of it, gates and scopes intact."""
        for part, gate in parts:
            if gate(ctx):
                with part.scope(ctx):
                    part.draw(ctx)

    def _replay_static(self, ctx, scene, split):
        """Put the static layer on the frame, rebuilding it first if it is
        stale. False if it could not be done at all."""
        target = self._prepare_static(ctx)
        if target is None:
            return False
        key = self._static_signature(ctx)
        now = time.perf_counter()
        if key != self._static_key or now - self._static_at > STATIC_MAX_AGE_S:
            started = time.perf_counter() if self._perf is not None else 0.0
            if not self._render_static(ctx, scene, split, target):
                return False
            if self._perf is not None:
                self._perf.layer_rebuilt(time.perf_counter() - started)
            self._static_key = key
            self._static_at = now
        return self._blit_static(target)

    def _prepare_static(self, ctx):
        """The layer's own framebuffer, made or remade to match the frame.

        Same samples and depth attachment as the one being drawn into: a blit
        between buffers of different sample counts is not allowed, and the
        depth has to come across with the colour or the parts drawn afterwards
        would depth-test against nothing.
        """
        size = QSize(max(1, int(ctx.width)), max(1, int(ctx.height)))
        if self._static_fbo is not None and self._static_fbo.size() == size:
            return self._static_fbo
        try:
            fmt = QOpenGLFramebufferObjectFormat()
            fmt.setAttachment(
                QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
            if SAMPLES:
                fmt.setSamples(SAMPLES)
            self._static_fbo = QOpenGLFramebufferObject(size, fmt)
            self._static_key = None
        except Exception as exc:       # pragma: no cover - driver dependent
            LOG.debug("backplot: no static layer: %s", exc)
            self._static_fbo = None
        return self._static_fbo

    def _render_static(self, ctx, scene, split, target):
        """Draw the parts before the trace into ``target``."""
        try:
            previous = int(glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING))
            glBindFramebuffer(GL_FRAMEBUFFER, target.handle())
            glViewport(0, 0, ctx.width, ctx.height)
            # Alpha written for the clear, so this buffer starts opaque, then
            # masked off again for the drawing.
            #
            # The frame masks alpha for its whole length - see _seal_alpha -
            # and this buffer is not the one that was sealed. Cleared under
            # that mask it keeps whatever alpha it was made with, which is
            # nothing, and the blit carries that into the frame: the plot
            # composites premultiplied against the page and disappears
            # completely, with every frame drawn and no error anywhere.
            _set_alpha_writes(True)
            glClearColor(*(self.colors['back'] + (1.0,)))
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            _set_alpha_writes(False)
            scene.apply_baseline()
            self._draw_parts(ctx, scene.parts[:split])
        except Exception as exc:       # pragma: no cover - driver dependent
            LOG.error("backplot: static layer failed: %s", exc)
            self._static_fbo = None
            return False
        finally:
            try:
                glBindFramebuffer(GL_FRAMEBUFFER, previous)
                glViewport(0, 0, ctx.width, ctx.height)
            except Exception:
                pass
        return True

    def _blit_static(self, target):
        """Copy the layer onto the frame, colour and depth together."""
        try:
            previous = int(glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING))
            width, height = target.size().width(), target.size().height()
            glBindFramebuffer(GL_READ_FRAMEBUFFER, target.handle())
            glBindFramebuffer(GL_DRAW_FRAMEBUFFER, previous)
            glBlitFramebuffer(0, 0, width, height, 0, 0, width, height,
                              GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT,
                              GL_NEAREST)
            glBindFramebuffer(GL_FRAMEBUFFER, previous)
        except Exception as exc:       # pragma: no cover - driver dependent
            LOG.error("backplot: static blit failed: %s", exc)
            self._static_fbo = None
            return False
        return True

    def invalidate_static(self):
        """Drop the cached layer. Cheap, and safe to call at any time."""
        self._static_key = None

    def _static_signature(self, ctx):
        """Everything the static layer is drawn from.

        Compared, not hashed - some of these are lists. Anything left out of
        here leaves a stale picture on screen, which is why ``STATIC_MAX_AGE_S``
        exists as well.
        """
        stat = ctx.stat
        return (
            ctx.width, ctx.height,
            self._preview_mvp().tobytes(),
            getattr(ctx.canon, "program_geometry", None),
            ctx.highlight_line,
            tuple(stat.g5x_offset), tuple(stat.g92_offset),
            stat.rotation_xy, tuple(stat.tool_offset), stat.g5x_index,
            ctx.limits, ctx.grid_size, ctx.program_alpha,
            ctx.show_program, ctx.show_rapids, ctx.show_extents,
            ctx.show_limits, ctx.show_relative, ctx.show_workpiece,
            dict(self.stock) if isinstance(self.stock, dict) else self.stock,
            dict(self.insert) if isinstance(self.insert, dict) else self.insert,
        )

    def _pixel_quantum(self):
        """How far the tool must move to move one pixel, in model units.

        Zero when the frame cannot be measured, which means "do not quantise"
        - a redraw too many is always better than a plot that has stopped
        following the machine.
        """
        try:
            scale = screen.pixels_per_unit(
                _Viewport(self._vp_width, self._vp_height), self._preview_mvp())
        except Exception as exc:       # pragma: no cover - depends on glnav
            LOG.debug("backplot: no scale to quantise against: %s", exc)
            return 0.0
        if scale is None:
            return 0.0
        # The finer of the two axes, so a move visible on either one counts.
        finest = max(scale)
        return 1.0 / finest if finest > 0 else 0.0

    @staticmethod
    def _set_multisample_baseline():
        """Multisampling **off** for the frame, on a multisampled buffer.

        The framebuffer asks for samples (see ``SAMPLES``) because some of
        what is drawn needs them: the insert is a filled outline with a radius
        on it, the origin symbol is a 16-pixel circle, and the tick labels are
        glyph strokes. None of those have whole pixels to land on, and without
        multisampling they staircase.

        The grid, the tick marks and the centreline are the opposite case.
        They are axis-aligned straight lines that do land on whole pixels, and
        multisampling one spreads its coverage over two at partial alpha - so
        it reads thinner and paler than the crisp line it replaced, and
        because the spread depends on where it falls between samples, its
        weight changes as the operator zooms. That is "the lines got thinner
        and the thickness follows the zoom".

        So the frame's baseline is off, and the parts whose geometry is curved
        or diagonal turn it on over their own draw - see ``Actor.MULTISAMPLE``
        and ``base.multisample``. Toggling it is defined on a multisample
        buffer: with MULTISAMPLE disabled, fragments are produced as though
        there were one sample, which is the crisp line back.
        """
        if not LIB_GOOD:
            return
        try:
            glDisable(GL_MULTISAMPLE)
        except Exception as exc:       # pragma: no cover - driver dependent
            LOG.debug("backplot: could not disable multisampling: %s", exc)

    def invalidate_alpha_seal(self):
        """Told by the renderer when a new framebuffer is made."""
        self._alpha_sealed = False

    def _seal_alpha(self):
        """Make the framebuffer opaque, once per framebuffer.

        **This is what made everything transparent disappear.** Upstream's
        redraw clears with ``self.colors['back'] + (0,)`` - alpha zero - and
        every draw then blends source-alpha, so a pixel's alpha ends up at
        whatever was drawn onto it. Opaque geometry leaves 1 and is fine.
        Anything else does not: a line at 0.7 leaves 0.49, and a glyph's
        antialiased edge leaves its coverage.

        Qt composites this framebuffer's texture as **premultiplied**, so an
        alpha below one is read as "this pixel is partly not there" and the
        page behind shows through in proportion. On a white page the
        arithmetic comes out at white exactly: the centreline at 0.7 and the
        grid at 0.5 both vanish, and text keeps only the fully covered core of
        each stroke - which is the whole of why the tick labels read as thin
        however they were drawn.

        A masked clear fixes all three in one call: ``glClear`` honours the
        colour mask, so this writes the alpha channel and nothing else.

        **Once per framebuffer, not once per frame.** A colour-masked clear
        cannot take the driver's fast-clear path, and on a multisampled buffer
        it writes every sample of every pixel - here two and a half million of
        them, which is not something to do twenty-five times a second on a
        panel's integrated graphics. So the channel is sealed when the
        framebuffer is new and then masked off for the rest of the frame,
        which leaves it sealed: see ``_set_alpha_writes``.
        """
        if not LIB_GOOD or self._alpha_sealed:
            return
        try:
            glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_TRUE)
            glClearColor(0.0, 0.0, 0.0, 1.0)
            glClear(GL_COLOR_BUFFER_BIT)
            self._alpha_sealed = True
        except Exception as exc:       # pragma: no cover - driver dependent
            LOG.debug("backplot: could not seal the alpha channel: %s", exc)
        finally:
            try:
                glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
            except Exception:
                pass

    @staticmethod
    def _report_line_weights():
        """What the lines on this plot actually come out at, once per context.

        Written down because there is no way to read it off the screen and
        three separate things decide it - the driver's own ceiling on
        glLineWidth, whether upstream is therefore expanding lines into quads,
        and the display scaling the weights are multiplied by. When a line
        looks wrong, this is the line of log that says which of the three to
        go and look at.
        """
        if not LIB_GOOD:
            return
        try:
            from rs274 import glcanon_gl

            # A probe, not a setting: asking for 3 tells set_line_width to
            # work out what the driver grants, and pending_line_expansion then
            # reports whether it had to fall back to the quad path. Put back
            # to 1 straight after, which is the frame's baseline.
            glcanon_gl.set_line_width(3.0)
            expanded = glcanon_gl.pending_line_expansion()
            glcanon_gl.set_line_width(1.0)
        except Exception as exc:       # pragma: no cover - driver dependent
            LOG.debug("backplot: could not probe the line width: %s", exc)
            return

        LOG.info("%s", line_weight_report(expanded))

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
        self._report_line_weights()

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
        # Read before the parse rather than after it: a program that fails to
        # parse still has a bar, and the operator is better off seeing the
        # stock than an empty plot.
        self.stock = workpiece.for_program(filename)
        self.invalidate_static()
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

        # What the picture is made of, so a poll that changes none of it does
        # not redraw. Two things are deliberately not in here:
        #
        # ``current_vel`` was, and nothing draws it - the DRO overlay that
        # would is off (see enable_dro). It changes on every poll while the
        # machine moves, so it alone forced a full redraw twenty-five times a
        # second for a picture that had not changed.
        #
        # The positions are rounded to the pixel grid rather than taken raw.
        # They are floats off a servo: during a finishing pass at 50 mm/min
        # they change every poll and move the marker by a fraction of a pixel,
        # and the frame that draws it costs the same as one where the tool
        # crossed the screen.
        quantum = self._pixel_quantum()
        fingerprint = (
            self.logger.npts,
            self.soft_limits(),
            _on_pixel_grid(source.actual_position, quantum),
            _on_pixel_grid(source.joint_actual_position, quantum),
            source.homed,
            source.g5x_offset,
            source.g92_offset,
            source.limit,
            source.tool_in_spindle,
            source.motion_mode,
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
        self.invalidate_static()
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
        self.invalidate_static()
        self.current_view = 'y'
        self.zoomin()
        self.update()

    def zoom_out(self):
        self.invalidate_static()
        self.current_view = 'y'
        self.zoomout()
        self.update()


class _Viewport:
    """The two fields ``screen.pixels_per_unit`` reads, outside a frame."""

    __slots__ = ("width", "height")

    def __init__(self, width, height):
        self.width = width
        self.height = height


def _on_pixel_grid(position, quantum):
    """``position`` rounded to whole screen pixels.

    Un-quantised at ``quantum`` zero, which is what an unmeasurable frame
    asks for.
    """
    if quantum <= 0:
        return tuple(position)
    return tuple(round(value / quantum) for value in position)


def _set_alpha_writes(enabled):
    """Let the frame write the alpha channel, or keep it off it.

    Off for the whole of a frame's drawing, so the sealed channel survives
    upstream's clear and every blend in it. Cheap - one piece of state - where
    re-sealing afterwards is a full-surface write.
    """
    if not LIB_GOOD:
        return
    try:
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE,
                    GL_TRUE if enabled else GL_FALSE)
    except Exception as exc:           # pragma: no cover - driver dependent
        LOG.debug("backplot: could not set the alpha mask: %s", exc)


def line_weight_report(expanded):
    """What the lines on this plot come out at, as one line of log.

    Apart from the drawing so it can be checked without a GL context. It is
    the only statement anywhere of what the weights actually are, and it has
    already broken once by quietly outliving a change to ``text.FONTS`` - a
    format string is code, and this one is exercised by nothing else.
    """
    scale = palette.WIDTH_SCALE * actor_base.device_pixel_ratio()
    fonts = ", ".join(sorted({text.description_of(name)
                              for name in text.FONTS}))
    # Nothing draws below a pixel: set_line_width floors the request there.
    drawn = lambda width: max(1.0, width * scale)        # noqa: E731
    return (
        "backplot line weights: pixel ratio %.2f x scale %.2f; wide lines "
        "drawn as %s. cutting %.1fpx%s, rapids %.1fpx, centreline %.1fpx, "
        "grid %.1fpx, hatch %.1fpx, ticks %.1fpx, stock %.1fpx, arrows "
        "%.1fpx, insert edge %.1fpx. Text is from the glyph atlas (%s)."
        % (actor_base.device_pixel_ratio(), palette.WIDTH_SCALE,
           "quads (the driver caps glLineWidth at 1)" if expanded
           else "native GL lines",
           drawn(palette.WIDTH_FEED),
           " asked for, 1.0px given - the trajectory is never expanded"
           if expanded else "",
           drawn(palette.WIDTH_TRAVERSE), drawn(palette.WIDTH_CENTERLINE),
           drawn(palette.WIDTH_GRID), drawn(palette.WIDTH_HATCH),
           drawn(palette.WIDTH_TICK), drawn(palette.WIDTH_STOCK),
           drawn(palette.WIDTH_ARROW), drawn(palette.WIDTH_INSERT_EDGE),
           fonts))


#: Whether the static layer is cached at all; ``TEACHINLATHE_LAYERS=0`` draws
#: every part on every frame, as upstream does.
#:
#: Here because the layer's failures are silent by nature - it either shows an
#: old picture or none - and one environment variable is a faster way back to
#: a working plot than an edit and a restart.
STATIC_LAYER = bool(int(os.environ.get("TEACHINLATHE_LAYERS", 1) or 0))

#: How long a cached static layer may go unrebuilt, in seconds.
#:
#: The layer is invalidated by a key that names everything known to change it
#: - the camera, the program, the offsets, the flags. This is the net under
#: that: something not in the key would otherwise leave the plot frozen on an
#: old picture, looking perfectly normal. Two seconds costs one extra full
#: draw in fifty and turns a silent freeze into a brief staleness.
STATIC_MAX_AGE_S = 2.0

#: Multisampling for the framebuffer; 0 turns it off.
#:
#: Four buys smooth edges on the two curved things drawn - the insert's nose
#: radius and the origin symbol - and costs a resolve of the whole viewport
#: every frame the plot redraws, which while a program runs is twenty-five
#: times a second on the panel's integrated graphics. Whether that is a fair
#: trade is a question about a particular machine, so
#: ``TEACHINLATHE_SAMPLES`` answers it without editing anything: set it to 0
#: and compare the "ms mean" in the perf line with it on.
SAMPLES = int(os.environ.get("TEACHINLATHE_SAMPLES", 4) or 0)


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
        self._canon.invalidate_alpha_seal()
        self._tell_actors_the_pixel_ratio(size)
        fmt = QOpenGLFramebufferObjectFormat()
        # The preview depth-tests; without an attachment here the tool cone
        # and the limits box draw in whatever order they happen to come in.
        fmt.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
        # Multisampled, unlike the QOpenGLWidget this replaced: its
        # preview_surface_format() never asked for samples, and for a plot
        # that was only straight toolpath segments nothing needed them. The
        # insert, the origin symbol and the tick labels changed that.
        #
        # The cost is the resolve, once per frame over the viewport, and it is
        # paid only when the plot redraws - which is when the machine has
        # moved. SAMPLES is here so a panel that cannot afford it can be set
        # back to 0 in one place.
        if SAMPLES:
            fmt.setSamples(SAMPLES)
        self._fbo = QOpenGLFramebufferObject(size, fmt)
        return self._fbo

    def _tell_actors_the_pixel_ratio(self, size):
        """How many framebuffer pixels there are to one of the item's.

        Qt sizes the framebuffer in device pixels while the item is measured
        in logical ones, so this is the display's scaling as it actually
        reaches the plot. The actors' line weights are written in the Canvas'
        logical pixels and would otherwise come out thinner by exactly this
        factor on a scaled panel.
        """
        item = getattr(self._canon, "_item", None)
        width = item.width() if item is not None else 0
        if width and width > 0:
            actor_base.set_device_pixel_ratio(size.width() / width)

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
