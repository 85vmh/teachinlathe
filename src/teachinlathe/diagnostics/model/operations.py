"""The names of the timed operations (``timed``, ``Profiler.record``) and of
the marks (``Profiler.mark``), and how a timed operation's series are named
in the store."""

from __future__ import annotations

# ── the event loop, the garbage collector, the Qt Quick frame ───────────────

EVENT_LOOP_STALL = "event_loop.stall"
#: a collection of generation N: ``PYTHON_GC_GEN % N``
PYTHON_GC_GEN = "python.gc.gen%d"
#: a stage of the Qt Quick frame: ``QSG_PREFIX + stage`` (quick_frames)
QSG_PREFIX = "qsg."

# ── the application's shell ─────────────────────────────────────────────────

#: a tab shown: ``UI_TAB_SWITCH_PREFIX + tab_id``
UI_TAB_SWITCH_PREFIX = "ui.tab_switch."
UI_FULLSCREEN_ENTER = "ui.fullscreen.enter"
UI_FULLSCREEN_EXIT = "ui.fullscreen.exit"

# ── the machine ─────────────────────────────────────────────────────────────

HAL_POLL = "hal.poll"
STATUS_POLL = "status.poll"
MACHINE_MESSAGES_POLL = "machine_messages.poll"
DRO_UPDATE = "dro.update"
PROGRAM_RUNTIME_POLL = "program_runtime.poll"

# ── the planner's results ───────────────────────────────────────────────────

PLANNER_RESULT_CONVERSATIONAL = "planner.result.conversational"
PLANNER_RESULT_FINAL_PROFILE = "planner.result.final_profile"
PLANNER_RESULT_SIMULATE = "planner.result.simulate"
PLANNER_RESULT_TOOL_CHANGES = "planner.result.tool_changes"

# ── the screens ─────────────────────────────────────────────────────────────

PROGRAMS_SCREEN_CHANGE = "programs.screen_change"
TOOLS_LIBRARY_REFRESH = "tools.library.refresh"
TOOLS_MANUAL_LIST_REFRESH = "tools.manual_list.refresh"

# ── the backplot ────────────────────────────────────────────────────────────

BACKPLOT_POLL = "backplot.poll"
BACKPLOT_PREVIEW_RELOAD = "backplot.preview_reload"
BACKPLOT_MATERIAL = "backplot.material"
BACKPLOT_TRAIL_READ = "backplot.trail_read"
BACKPLOT_TRAIL_DRAW = "backplot.trail_draw"
BACKPLOT_RENDER = "backplot.render"
BACKPLOT_RENDER_REDRAW = "backplot.render.redraw"
BACKPLOT_RENDER_CONTEXT = "backplot.render.context"
BACKPLOT_RENDER_STATIC_REBUILD = "backplot.render.static_rebuild"
BACKPLOT_RENDER_STATIC_BLIT = "backplot.render.static_blit"
#: a part of the scene drawn: the prefix and the part's class name
BACKPLOT_RENDER_PART_PREFIX = "backplot.render.part."
BACKPLOT_RENDER_STATIC_PART_PREFIX = "backplot.render.static_part."

# ── picking a tool on the Manual tab ────────────────────────────────────────

#: The stages of picking a tool, marked as each is reached (``Profiler.mark``):
#: the tap, M61 sent, the status' current loaded tool changed, the list's
#: model told; the times between them are recorded as the TOOL_*_TO_* below.
TOOL_CLICK = "tool.click"
TOOL_M61_SENT = "tool.m61_sent"
TOOL_IN_SPINDLE = "tool.in_spindle"
TOOL_MODEL_NOTIFIED = "tool.model_notified"

TOOL_CLICK_TO_M61 = "tool.click_to_m61"
TOOL_M61_TO_IN_SPINDLE = "tool.m61_to_in_spindle"
TOOL_IN_SPINDLE_TO_MODEL = "tool.in_spindle_to_model"
TOOL_MODEL_TO_QML = "tool.model_to_qml"
TOOL_CLICK_TO_QML = "tool.click_to_qml"

# ── a timed operation's series in the store ─────────────────────────────────

#: ``OP_SERIES_PREFIX + name + one of the suffixes``
OP_SERIES_PREFIX = "op."
OP_COUNT_SUFFIX = ".count"
OP_MEAN_SUFFIX = ".mean_ms"
OP_P50_SUFFIX = ".p50_ms"
OP_P95_SUFFIX = ".p95_ms"
OP_P99_SUFFIX = ".p99_ms"
OP_MAX_SUFFIX = ".max_ms"
#: what every series in milliseconds ends with
MS_SUFFIX = "_ms"
