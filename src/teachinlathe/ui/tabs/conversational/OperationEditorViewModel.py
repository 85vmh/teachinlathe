"""The view model behind each operation's editor in the Conversational tab.

One per operation type that has an editor, made by ConversationalViewModel
for the operation selected in the program (``editor_for``). It holds what the
editor shows - the operation, as ``operation`` - and what the editor asks:
the program's stock, the tool in by then, a preview of the cut. ``edit``
sends a change to the tab, which applies it and saves the program.

An editor is made for one operation of the program. Selecting another
operation, or coming back to this one, makes a new one.

The operation in the program - what its JSON file holds - is the editor's one
source of truth: ``operation`` is read from it again each time the program
changes, and ``edit`` applies a change to it, which the tab saves. A view
shows only what ``operation`` says and keeps nothing of its own.
"""

import dataclasses
from enum import Enum

from PyQt6.QtCore import QObject, QTimer, pyqtEnum, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.conversational.logic.program_tools import Scope as ProgramToolScope
from teachinlathe.conversational.logic.program_tools import ToolStatus
from teachinlathe.conversational.model import profile_editing
from teachinlathe.conversational.model.data_types import InspectPosition, PredefinedPosition, ThreadForm

# Thread depth over pitch, per side, for a 60° thread.
EXTERNAL_THREAD_HEIGHT_FACTOR = 0.61344
INTERNAL_THREAD_HEIGHT_FACTOR = 0.54127

EMPTY_PREVIEW = {"profile": [], "offset": [], "feeds": [], "rapids": []}


#: The preview fields whose name in QML is not their own in camelCase.
_QML_NAMES = {"pass_no": "pass", "from_x": "from", "to_x": "to"}


def _qml_name(name):
    if name in _QML_NAMES:
        return _QML_NAMES[name]
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


def _qml_value(value):
    """A preview's value as QML takes it: a dataclass an object of its fields
    by their QML names - those None left out, but at the top - a tuple a
    list, an Enum its value."""
    if dataclasses.is_dataclass(value):
        return {_qml_name(f.name): _qml_value(getattr(value, f.name)) for f in dataclasses.fields(value)
                if getattr(value, f.name) is not None}
    if isinstance(value, (tuple, list)):
        return [_qml_value(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def qml_preview(preview):
    """An operation's preview (OperationPreview, or one of the kinds of it
    an operation has: ProfileRoughingPreview, GrooveRoughingPreview, ...) as
    the canvases take it: an object of its fields by their QML names -
    profile, offset, feeds, rapids, warnings, error, and the kind's own
    (restOffered, startDiameter, ...). The one place a preview is made into
    what QML reads."""
    return {_qml_name(f.name): _qml_value(getattr(preview, f.name)) for f in dataclasses.fields(preview)}


def to_py(obj):
    """Convert QJSValue / nested JS structures to Python dict/list."""
    try:
        if hasattr(obj, "toVariant"):
            obj = obj.toVariant()
    except Exception:
        pass
    if isinstance(obj, dict):
        return {k: to_py(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_py(x) for x in obj]
    return obj


class PauseToInspect(QObject):
    """Where Pause to Inspect stops, as M1Parameters.qml has it
    (``PauseToInspect.G28``, ``PauseToInspect.InPlace``): the operation an
    editor shows has its m1_parameters' inspect_position one of these
    (for_qml), and what the editor saves has it the domain's
    InspectPosition again (from_qml)."""

    @pyqtEnum
    class Position(Enum):
        G28 = 0
        G30 = 1
        InPlace = 2

    _POSITIONS = {InspectPosition.G28: Position.G28, InspectPosition.G30: Position.G30,
                  InspectPosition.IN_PLACE: Position.InPlace}
    _INSPECT = {position.value: inspect for inspect, position in _POSITIONS.items()}

    @classmethod
    def _with_position(cls, operation, position_of):
        m1 = operation.get("m1_parameters") if isinstance(operation, dict) else None
        if not isinstance(m1, dict) or m1.get("inspect_position") is None:
            return operation
        return {**operation, "m1_parameters": {**m1, "inspect_position": position_of(m1["inspect_position"])}}

    @classmethod
    def for_qml(cls, operation):
        """``operation``, as its dict, with its inspect position QML's."""
        return cls._with_position(operation, lambda raw: cls._POSITIONS[InspectPosition(raw)].value)

    @classmethod
    def from_qml(cls, payload):
        """What an editor saves, with its inspect position the domain's."""
        return cls._with_position(payload, lambda value: cls._INSPECT[int(value)])


#: ``preview`` not made since the operation last changed.
_NOT_MADE = object()


class OperationEditorViewModel(QObject):
    #: The operation type its edits are applied as (ConversationalUseCase._updaters).
    update_type = ""

    #: The operation in the program changed: ``operation`` (and ``opIndex``) say what it is now.
    operationChanged = pyqtSignal()

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(parent)
        self._tab = tab
        self._use_case = tab.use_case
        self._program = program
        self._index = index
        self._operation = operation
        # the operation itself, which stays this editor's wherever it moves to
        self._op = self._use_case.operation(program, index) if index >= 0 else None
        self._preview = _NOT_MADE
        tab.programChanged.connect(self._follow_program)

    def _current_index(self):
        """Where the operation is in the program now; -1 for the header, None
        once it is gone."""
        if self._op is None:
            return self._index
        return next((i for i, op in enumerate(self._program.operations) if op is self._op), None)

    def _follow_program(self):
        """The program changed: the operation read again from it."""
        index = self._current_index()
        if index is None:
            return
        operation = self._use_case.details_payload(self._program, index)
        if not operation:
            return
        self._index, self._operation = index, operation
        self._preview = _NOT_MADE
        self.operationChanged.emit()

    @pyqtProperty(str, constant=True)
    def operationType(self):
        return str(self._operation.get("type", "")) if self._index >= 0 else "header"

    @pyqtProperty(int, notify=operationChanged)
    def opIndex(self):
        return self._index

    @pyqtProperty("QVariant", notify=operationChanged)
    def operation(self):
        """The operation, as the program has it now: all a view shows of it."""
        return PauseToInspect.for_qml(self._operation)

    @pyqtSlot("QVariant")
    def edit(self, patch):
        """Change the operation by ``patch``: only the fields it names, in the
        operation's own shape (``{"drilling_parameters": {"z_end": -15}}``).
        The program is saved, and ``operation`` follows."""
        index = self._current_index()
        if index is None or index < 0:
            return
        self._tab.update_operation(self.update_type, index, PauseToInspect.from_qml(to_py(patch)))

    @pyqtProperty(QObject, constant=True)
    def touchedOffTools(self):
        """Every holder with a tool and both offsets set: the ones a program
        can change to, for the tool pickers."""
        return self._tab.touched_off_tools

    @pyqtProperty("QVariant", notify=operationChanged)
    def preview(self):
        """What the operation cuts, as its canvas draws it (``_make_preview``),
        made once each time it changes; None for one with no preview."""
        if self._preview is _NOT_MADE:
            self._preview = self._make_preview()
        return self._preview

    def _make_preview(self):
        return None

    def _preview_of(self, build):
        """The preview ``build`` makes of the operation, or an empty one with
        the error (the tab's preview)."""
        return self._tab.preview(build, dict(self._operation))


class HeaderEditorViewModel(OperationEditorViewModel):
    """The program's header: ``operation`` is the program, as its dict."""

    @pyqtSlot("QVariant")
    def edit(self, patch):
        """Change the header by ``patch``: only the fields it names, in the
        header's own shape (``{"header": {"workpiece": {"stock_length": 80}}}``)."""
        self._tab.update_header(to_py(patch))


class ToolCard(QObject):
    """An operation's tool as its editor shows it: the holder ``toolNo`` (0
    with none chosen), the cutting tool as the Tool Library's card draws it -
    ``card`` its kind ("turning", ..., as ToolTitles.js has them), ``view`` its
    view (a TurningToolView, ...) - where the tool change to it goes, and
    whether the Tool Library still has it as it was chosen (``status``): but
    when Ok, ``card`` and ``view`` are the tool as it was chosen.
    ``suggestedToolNo``: the holder the tool picker starts on - where the tool
    is now - 0 for none; ``users``: how many operations cut with this tool
    from this one down, it included.

    Its enums are QML's (``ToolCard.Moved``, ``ToolCard.ThisAndBelow``,
    ``ToolCard.G30``); position_of and scope_of make them the domain's."""

    @pyqtEnum
    class Status(Enum):
        NoTool = 0
        Ok = 1
        Moved = 2
        Changed = 3
        Missing = 4
        Unfit = 5

    @pyqtEnum
    class Scope(Enum):
        """Which operations a tool chosen for one is for: that one, it and
        those below cutting with its tool, or every one cutting with it."""
        ThisOperation = 0
        ThisAndBelow = 1
        AllOperations = 2

    @pyqtEnum
    class ChangePosition(Enum):
        """Where the machine goes to change the tool."""
        G28 = 0
        G30 = 1

    _STATUS = {ToolStatus.NONE: Status.NoTool, ToolStatus.OK: Status.Ok, ToolStatus.MOVED: Status.Moved,
               ToolStatus.CHANGED: Status.Changed, ToolStatus.MISSING: Status.Missing,
               ToolStatus.UNFIT: Status.Unfit}
    _POSITIONS = {PredefinedPosition.G28: ChangePosition.G28, PredefinedPosition.G30: ChangePosition.G30}
    _SCOPES = {Scope.ThisOperation: ProgramToolScope.THIS, Scope.ThisAndBelow: ProgramToolScope.BELOW,
               Scope.AllOperations: ProgramToolScope.ALL}

    def __init__(self, tool_no=0, card="", view=None, toolchange_position=PredefinedPosition.G28,
                 status=ToolStatus.NONE, suggested_tool_no=0, users=0, parent=None):
        super().__init__(parent)
        self._tool_no = tool_no
        self._card = card
        self._view = view
        self._position = self._POSITIONS[toolchange_position]
        self._status = self._STATUS[status]
        self._suggested_tool_no = suggested_tool_no
        self._users = users

    @classmethod
    def position_of(cls, value: int) -> PredefinedPosition:
        """The domain's PredefinedPosition of a ChangePosition from QML."""
        wanted = cls.ChangePosition(value)
        return next(p for p, q in cls._POSITIONS.items() if q is wanted)

    @classmethod
    def scope_of(cls, value: int) -> ProgramToolScope:
        """program_tools' Scope of a Scope from QML."""
        return cls._SCOPES[cls.Scope(value)]

    @pyqtProperty(bool, constant=True)
    def hasTool(self):
        return self._tool_no > 0

    @pyqtProperty(int, constant=True)
    def toolNo(self):
        return self._tool_no

    @pyqtProperty(str, constant=True)
    def card(self):
        return self._card

    @pyqtProperty(QObject, constant=True)
    def view(self):
        return self._view

    @pyqtProperty(int, constant=True)
    def toolchangePosition(self):
        """A ChangePosition."""
        return self._position.value

    @pyqtProperty(int, constant=True)
    def status(self):
        """A Status."""
        return self._status.value

    @pyqtProperty(int, constant=True)
    def suggestedToolNo(self):
        return self._suggested_tool_no

    @pyqtProperty(int, constant=True)
    def users(self):
        return self._users


class ToolOperationEditorViewModel(OperationEditorViewModel):
    """An operation drawn on the stock with the tool that cuts it, which the
    editor can change."""

    #: What it shows from the program changed: the operation, or what is around it.
    toolOperationChanged = pyqtSignal()
    #: The holders whose tool the operation can cut with may have changed:
    #: the Tool Library did, or the operation (an OD profile become ID).
    suitableToolNosChanged = pyqtSignal()

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        self.operationChanged.connect(self.toolOperationChanged)
        # the operation changed - say from OD to ID - and with it what can cut it
        self.operationChanged.connect(self.suitableToolNosChanged)
        self._tool_card = None
        from teachinlathe.core.tool_library_repository import tool_library_repository
        tool_library_repository().toolsChanged.connect(self.suitableToolNosChanged)
        if self.planned_preview:
            self._start_planned_preview()

    # ── a preview the planning worker works out ─────────────────────────────
    #: Set by the editors whose preview takes the planning worker (Turning,
    #: Profile Roughing): ``plannedPreview`` is then asked for as the editor is
    #: made and each time the operation changes, and follows the answer.
    planned_preview = False

    #: A preview asked of the tab (request_roughing_preview), once worked out.
    previewReady = pyqtSignal("QVariant")
    plannedPreviewChanged = pyqtSignal()

    #: How long the operation stays unchanged before its preview is asked for:
    #: a quick run of edits - or an operation only passed over in the list -
    #: asks once, or not at all.
    PLANNED_PREVIEW_DELAY_MS = 150

    def _start_planned_preview(self):
        #: what the last request went in with: an answer for an older one is
        #: not passed on
        self.wanted_preview = None
        self._planned_preview = None
        self.previewReady.connect(self._take_planned_preview)
        # the editor's own: gone with it, so an editor left asks nothing
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(self.PLANNED_PREVIEW_DELAY_MS)
        self._preview_timer.timeout.connect(self._ask_planned_preview)
        self.operationChanged.connect(self._preview_timer.start)
        self._preview_timer.start()

    def stop_planned_preview(self):
        """No preview asked for any more: the editor is no longer shown."""
        if self.planned_preview:
            self._preview_timer.stop()

    def _ask_planned_preview(self):
        index = self._current_index()
        if index is not None and index >= 0:
            self._tab.request_roughing_preview(self, index, self._operation)

    def _take_planned_preview(self, preview):
        self._planned_preview = preview
        self.plannedPreviewChanged.emit()

    @pyqtProperty("QVariant", notify=plannedPreviewChanged)
    def plannedPreview(self):
        """What the operation cuts, as the planning worker worked it out:
        None until the first answer."""
        return self._planned_preview if self.planned_preview else None

    @pyqtProperty("QVariantList", notify=suitableToolNosChanged)
    def suitableToolNos(self):
        """The T numbers whose tool the operation can cut with: the only
        ones its tool picker shows."""
        return self._use_case.suitable_tool_nos(self._program, self._index)

    @pyqtProperty("QVariant", notify=toolOperationChanged)
    def workpiece(self):
        """The program header's stock, as its dict, or {}."""
        return self._use_case.workpiece(self._program)

    @pyqtProperty(str, notify=toolOperationChanged)
    def toolChangePositionText(self):
        """Where M6 takes the tool, for the tool picker to show: "Default
        Position [X: 75.000 Z: 200.000]" - the INI's - or "Custom Position
        [...]" - the one set on the Manual Turning tab."""
        x, z, custom = self._use_case.tool_change_position()
        where = "Custom Position" if custom else "Default Position"
        if x is None or z is None:
            return f"{where} [not set]"
        return f"{where} [X: {x:.3f} Z: {z:.3f}]"

    @pyqtProperty(QObject, constant=True)
    def toolCard(self):
        """The operation's tool, as its ToolCard."""
        if self._tool_card is None:
            self._tool_card = self._make_tool_card()
        return self._tool_card

    def _make_tool_card(self):
        from teachinlathe.tooling.model.data_types import CuttingTool
        from teachinlathe.ui.tabs.programs.backplot import tool_source
        from teachinlathe.ui.tabs.tool_library.tool_library_models import card_and_view
        entry = self._use_case.tool_entry(self._program, self._index)
        if entry is None:
            return ToolCard(parent=self)
        result = self._use_case.tool_check(self._program, self._index)
        if result.status is ToolStatus.OK:
            tool = tool_source.tool_in(int(entry.tool_holder_id))
        else:
            try:
                tool = CuttingTool.from_json(entry.snapshot.get("cutting_tool") or {})
            except Exception:
                tool = None
        # The view lives as long as this editor: QML holds only a reference.
        card, view = card_and_view(tool, self)
        return ToolCard(tool_no=int(entry.tool_holder_id), card=card, view=view,
                        toolchange_position=entry.toolchange_position, status=result.status,
                        # not one it cannot cut with
                        suggested_tool_no=0 if result.status is ToolStatus.UNFIT else int(result.tool_holder_id),
                        users=self._use_case.tool_users_below(self._program, self._index), parent=self)

    @pyqtSlot(int, int, int)
    def useTool(self, tool_no, toolchange_position, scope):
        """Cut with the tool in holder ``tool_no``, changed to at
        ``toolchange_position`` (a ToolCard.ChangePosition), for ``scope``'s
        operations (a ToolCard.Scope). The editor is made again, with it."""
        self._tab.use_tool(self._index, tool_no, ToolCard.position_of(toolchange_position),
                           ToolCard.scope_of(scope))


class FacingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "facing"

    def _make_preview(self):
        """What facing cuts."""
        return self._preview_of(lambda op: qml_preview(self._use_case.facing_preview(op)))

    # Shared by every Facing of the program: kept by the tab.
    def _get_canvas_mirror(self):
        return self._tab.facingMirror

    def _set_canvas_mirror(self, on):
        self._tab.facingMirror = on

    canvasMirror = pyqtProperty(bool, _get_canvas_mirror, _set_canvas_mirror)


class TurningEditorViewModel(ToolOperationEditorViewModel):
    update_type = "turning"
    planned_preview = True

    #: What it shows from the program changed: the operation, or what is around it.
    turningChanged = pyqtSignal()

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        self.operationChanged.connect(self.turningChanged)

    @pyqtProperty(bool, notify=turningChanged)
    def hasFinishingOperation(self):
        parent_order = int(self._operation.get("order", 0))
        return any(getattr(op, "type", "") == "turningFinish"
                   and int(getattr(op, "parentOrder", 0)) == parent_order
                   for op in getattr(self._program, "operations", []))

    @pyqtSlot()
    def addTurningFinish(self):
        self._tab.add_turning_finish(self._index)

    @pyqtProperty("QVariant", notify=turningChanged)
    def inlineProfile(self):
        """The OD profile the turning cuts, for the canvas and the stock cut out."""
        from teachinlathe.conversational.gcode.operations.profiling.operation_input import inline_turning_profile
        from teachinlathe.conversational.model.data_types import Operation
        if self._operation.get("type") != "turning":
            return {}
        profile = inline_turning_profile(Operation.from_dict(dict(self._operation)))
        return {
            "profile_type": profile.profile_type.value,
            "profile_primitives": [primitive.to_dict() for primitive in profile.profile_primitives],
        }


class TurningFinishEditorViewModel(ToolOperationEditorViewModel):
    update_type = "turningFinish"

    #: What it shows from the program changed: the operation, or what is around it.
    turningFinishChanged = pyqtSignal()

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        self.operationChanged.connect(self.turningFinishChanged)

    def _parent_turning(self):
        from teachinlathe.conversational.model.data_types import Turning
        parent_order = int(self._operation.get("parent_order", 0))
        operations = getattr(self._program, "operations", [])
        parent = next((op for op in operations
                       if isinstance(op, Turning) and op.order == parent_order), None)
        return parent or next((op for op in reversed(operations[:self._index])
                               if isinstance(op, Turning)), None)

    @pyqtProperty("QVariant", notify=turningFinishChanged)
    def parentProfile(self):
        """The embedded OD profile this finish operation follows, for its canvas."""
        parent = self._parent_turning()
        if parent is None:
            return {}
        from teachinlathe.conversational.gcode.operations.profiling.operation_input import inline_turning_profile
        profile = inline_turning_profile(parent)
        return {
            "profile_type": profile.profile_type.value,
            "profile_primitives": [primitive.to_dict() for primitive in profile.profile_primitives],
        }

    @pyqtProperty("QVariant", notify=turningFinishChanged)
    def workpiece(self):
        workpiece = self._use_case.workpiece(self._program)
        parent = self._parent_turning()
        if parent is None:
            return workpiece
        geometry = parent.geometryParameters
        has_header_stock = float(workpiece.get("external_diameter", 0) or 0) > 0 and \
            float(workpiece.get("stock_length", 0) or 0) > 0
        if not has_header_stock and geometry.xStart > 0 and geometry.zStart > geometry.zEnd:
            workpiece["external_diameter"] = geometry.xStart
            workpiece["stock_length"] = max(10.0, max(0.0, -geometry.zEnd) + 10.0)
        if geometry.xStart > 0 and geometry.zStart > geometry.zEnd:
            workpiece["face_z"] = max(0.0, float(workpiece.get("face_z", 0) or 0), geometry.zStart)
            workpiece["break_after_profile"] = True
            workpiece.pop("break_after_z", None)
            workpiece.pop("break_after_setback", None)
        return workpiece

    @pyqtProperty(bool, notify=turningFinishChanged)
    def undercutAvailable(self):
        from teachinlathe.conversational.model.data_types import BlendType
        parent = self._parent_turning()
        return bool(parent and parent.geometryParameters.shoulderBlend.blend_type is BlendType.NONE)

    def _make_preview(self):
        return self._preview_of(
            lambda op: qml_preview(self._use_case.profile_contour_preview(self._program, self._index, op)))


class ProfileFollowingEditorViewModel(ToolOperationEditorViewModel):
    """Profile Roughing and Profile Contour: they cut the last profile above."""

    #: What it shows from the program changed: the operation, or what is around it.
    profileFollowingChanged = pyqtSignal()

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        self.operationChanged.connect(self.profileFollowingChanged)

    @pyqtProperty("QVariant", notify=profileFollowingChanged)
    def lastProfile(self):
        """The last Define Profile above, as its details payload, or {}."""
        return self._use_case.last_profile_before(self._program, self._index)


class ProfileRoughingEditorViewModel(ProfileFollowingEditorViewModel):
    update_type = "profileRoughing"
    # the plan takes up to a second: worked out in the planning worker, and
    # the screen goes on meanwhile
    planned_preview = True

    @pyqtSlot()
    def addRestRoughing(self):
        """For what this roughing leaves: a copy of this roughing on rest
        material, with no tool yet - opened."""
        self._tab.add_rest_roughing(self._index)


class ProfileContourEditorViewModel(ProfileFollowingEditorViewModel):
    update_type = "profileContour"

    def _make_preview(self):
        return self._preview_of(
            lambda op: qml_preview(self._use_case.profile_contour_preview(self._program, self._index, op)))


class DrillingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "drilling"

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        from teachinlathe.tooling.model.data_types import DrillingTool
        from teachinlathe.ui.tabs.tool_library.DrillingToolView import DrillingToolView
        tool = self._use_case.tool_of(program, index)
        # lives as long as this editor: QML holds only a reference
        self._drill = (DrillingToolView(tool, self)
                       if isinstance(tool, DrillingTool) and tool.diameter > 0 else None)

    def _make_preview(self):
        """What drilling cuts: a feed each peck."""
        return self._preview_of(lambda op: qml_preview(self._use_case.drilling_preview(op)))

    @pyqtProperty(QObject, constant=True)
    def drill(self):
        """The drill it cuts with, as the Tool Library shows it (a
        DrillingToolView); None with no drill - or one not as chosen, or of
        no diameter."""
        return self._drill


class TappingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "tapping"

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        from teachinlathe.tooling.model.data_types import TappingTool
        from teachinlathe.ui.tabs.tool_library.TappingToolView import TappingToolView
        tool = self._use_case.tool_of(program, index)
        # lives as long as this editor: QML holds only a reference
        self._tap = (TappingToolView(tool, self)
                     if isinstance(tool, TappingTool) and tool.diameter > 0 and tool.pitch > 0 else None)

    @pyqtProperty(QObject, constant=True)
    def tap(self):
        """The tap it cuts with, as the Tool Library shows it (a
        TappingToolView); None with no tap - or one not as chosen, or of no
        diameter or pitch."""
        return self._tap


class PartingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "parting"

    def _make_preview(self):
        """What parting cuts: its edge break and feeds."""
        return self._preview_of(lambda op: qml_preview(self._use_case.parting_preview(op)))


def thread_angle(form):
    """The included angle of a thread form's flanks, degrees - metric's 60
    when the form is unknown."""
    try:
        return ThreadForm(str(form or "").lower()).angle
    except ValueError:
        return ThreadForm.METRIC.angle


def calculate_thread_diameter(location, pitch, major_diameter, minor_diameter):
    """The diameter the thread's depth gives from its pitch: the minor from
    the major for an OD thread, the major from the minor for an ID one."""
    try:
        pitch_value = float(pitch)
    except (TypeError, ValueError):
        return {"valid": False}

    location_value = str(location or "OD").upper()
    try:
        major_value = float(major_diameter)
    except (TypeError, ValueError):
        major_value = 0.0
    try:
        minor_value = float(minor_diameter)
    except (TypeError, ValueError):
        minor_value = 0.0

    if location_value == "ID":
        major_value = minor_value + INTERNAL_THREAD_HEIGHT_FACTOR * pitch_value * 2.0
        calculated_diameter = major_value
    else:
        minor_value = major_value - EXTERNAL_THREAD_HEIGHT_FACTOR * pitch_value * 2.0
        calculated_diameter = minor_value

    return {
        "valid": True,
        "majorDiameter": round(major_value, 3),
        "minorDiameter": round(minor_value, 3),
        "calculatedDiameter": round(calculated_diameter, 3),
    }


def calculated_diameter_patch(operation, pitch=None):
    """The edit that sets a thread's calculated diameter from the one taught
    in - Minor Ø from Major Ø for an OD thread, Major Ø from Minor Ø for an
    ID one - with ``pitch``, or the thread's own: {} while the one taught in
    or the pitch is not set yet."""
    pitch = float(operation.get("pitch") or 0) if pitch is None else float(pitch)
    location = "ID" if operation.get("location") == "ID" else "OD"
    major = float(operation.get("major_diameter") or 0)
    minor = float(operation.get("minor_diameter") or 0)
    taught = minor if location == "ID" else major
    if pitch <= 0 or taught <= 0:
        return {}
    result = calculate_thread_diameter(location, pitch, major, minor)
    if not result.get("valid"):
        return {}
    key = "major_diameter" if location == "ID" else "minor_diameter"
    return {key: result["calculatedDiameter"]}


def edit_pitch(editor, pitch):
    """A threading editor's pitch, and the calculated diameter with it."""
    editor.edit({"pitch": pitch, **calculated_diameter_patch(editor._operation, pitch)})


def calculate_diameter(editor):
    """A threading editor's calculated diameter, from the one taught in and
    the pitch."""
    patch = calculated_diameter_patch(editor._operation)
    if patch:
        editor.edit(patch)


class ThreadingEditorViewModel(OperationEditorViewModel):
    update_type = "threading"

    @pyqtSlot(float)
    def editPitch(self, pitch):
        """The pitch, and the calculated diameter with it."""
        edit_pitch(self, pitch)

    @pyqtSlot()
    def calculateDiameter(self):
        """The calculated diameter, from the one taught in and the pitch."""
        calculate_diameter(self)


class G33ThreadingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "g33Threading"

    @pyqtSlot(float)
    def editPitch(self, pitch):
        """The pitch, and the calculated diameter with it."""
        edit_pitch(self, pitch)

    @pyqtSlot()
    def calculateDiameter(self):
        """The calculated diameter, from the one taught in and the pitch."""
        calculate_diameter(self)

    @pyqtSlot(str, result=float)
    def threadAngle(self, form):
        return thread_angle(form)


class PositionAtEditorViewModel(OperationEditorViewModel):
    update_type = "positionAt"


class KnurlingEditorViewModel(OperationEditorViewModel):
    update_type = "knurling"


class ProfilingEditorViewModel(OperationEditorViewModel):
    update_type = "profiling"

    @pyqtSlot()
    def addFinish(self):
        """A finishing pass right after this one."""
        self._tab.add_profiling_finish(self._index)


class GrooveEditorViewModel(ToolOperationEditorViewModel):
    """Groove Roughing, BiDirectional Grooving and Groove Finishing: they cut
    a radial profile above, and show what they would cut (the use case's
    groove_preview)."""

    @pyqtSlot(int, result="QVariant")
    def radialProfile(self, profile_id):
        """The Define Radial Profile ``profile_id`` above - the last one with
        none - as its details payload, or {}."""
        return self._use_case.radial_profile_before(self._program, self._index, profile_id)

    def _make_preview(self):
        """What it cuts."""
        return self._preview_of(
            lambda op: qml_preview(self._use_case.groove_preview(self._program, self._index, op)))


class GrooveRoughingEditorViewModel(GrooveEditorViewModel):
    update_type = "grooveRoughing"


class GrooveBidirectionalEditorViewModel(GrooveEditorViewModel):
    update_type = "grooveBidirectional"


class GrooveFinishingEditorViewModel(GrooveEditorViewModel):
    update_type = "grooveFinishing"


class DefineProfileEditorViewModel(OperationEditorViewModel):
    """A profile drawn by hand or read from a drawing: its summary in the
    details pane, the full screen editor, and the DXF import screen."""
    update_type = "defineProfile"

    #: What it shows from the program changed: the operation, or what is around it.
    defineProfileChanged = pyqtSignal()

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        self.operationChanged.connect(self.defineProfileChanged)

    @pyqtProperty("QVariant", notify=defineProfileChanged)
    def workpiece(self):
        return self._use_case.workpiece(self._program)

    @pyqtSlot()
    def openEditor(self):
        self._tab.open_profile_editor(self._index)

    # ── what the profile editor does to the primitives (profile_editing) ────

    def _primitives(self):
        return list(self._operation.get("profile_primitives") or [])

    def _edit_primitives(self, primitives):
        self.edit({"profile_primitives": primitives})

    @pyqtSlot(int, "QVariant")
    def updatePrimitive(self, index, primitive):
        """The primitive at ``index`` as its card edited it."""
        self._edit_primitives(profile_editing.with_primitive(self._primitives(), index, to_py(primitive)))

    @pyqtSlot(int, str)
    def addBlend(self, index, blend_type):
        """A ``blend_type`` blend at the end of the primitive at ``index``."""
        self._edit_primitives(profile_editing.with_blend(self._primitives(), index, blend_type))

    @pyqtSlot(int, str, result=int)
    def insertPrimitive(self, index, kind):
        """A new ``kind`` primitive at ``index``, starting where the one
        before it ends: where it went."""
        primitives, at = profile_editing.with_new_primitive(
            self._primitives(), index, kind, str(self._operation.get("profile_type") or "od"))
        self._edit_primitives(primitives)
        return at

    @pyqtSlot(int, result=int)
    def deletePrimitive(self, index):
        """The primitive at ``index`` gone: the one to select after, -1 for none."""
        primitives, selected = profile_editing.without_primitive(self._primitives(), index)
        self._edit_primitives(primitives)
        return selected

    @pyqtSlot("QVariant")
    def setPrimitives(self, primitives):
        """All the primitives, as the canvas changed them (a run's diameter)."""
        self._edit_primitives(profile_editing.renumbered(to_py(primitives) or []))

    @pyqtSlot(str, result="QVariant")
    def previewDxf(self, dxf_file_path):
        """The profile the drawing would give this one."""
        return self._use_case.preview_dxf_profile(self._program, self._index, dxf_file_path)

    @pyqtSlot(str)
    def importDxf(self, dxf_file_path):
        self._tab.import_dxf_profile(self._index, dxf_file_path)


class DefineRadialProfileEditorViewModel(OperationEditorViewModel):
    update_type = "defineRadialProfile"

    @pyqtSlot()
    def openEditor(self):
        self._tab.open_radial_profile_editor(self._index)

    # ── what the radial profile editor does to the primitives ───────────────

    def _primitives(self):
        return list(self._operation.get("profile_primitives") or [])

    def _edit_primitives(self, primitives):
        self.edit({"profile_primitives": primitives})

    @pyqtSlot(int, "QVariant")
    def updatePrimitive(self, index, primitive):
        """The primitive at ``index`` as its card edited it."""
        self._edit_primitives(profile_editing.with_radial_primitive(self._primitives(), index, to_py(primitive)))

    @pyqtSlot(str, result=int)
    def addPrimitive(self, kind):
        """A new ``kind`` primitive ("groove", "repeat") last: where it went."""
        primitives, at = profile_editing.with_new_radial_primitive(self._primitives(), kind)
        self._edit_primitives(primitives)
        return at

    @pyqtSlot(int, result=int)
    def deletePrimitive(self, index):
        """The primitive at ``index`` gone: the one to select after, -1 for none."""
        primitives, selected = profile_editing.without_radial_primitive(self._primitives(), index)
        self._edit_primitives(primitives)
        return selected


# The editor for each operation type.
EDITORS = {
    "positionAt": PositionAtEditorViewModel,
    "facing": FacingEditorViewModel,
    "turning": TurningEditorViewModel,
    "turningFinish": TurningFinishEditorViewModel,
    "knurling": KnurlingEditorViewModel,
    "profiling": ProfilingEditorViewModel,
    "profileRoughing": ProfileRoughingEditorViewModel,
    "profileContour": ProfileContourEditorViewModel,
    "grooveRoughing": GrooveRoughingEditorViewModel,
    "grooveBidirectional": GrooveBidirectionalEditorViewModel,
    "grooveFinishing": GrooveFinishingEditorViewModel,
    "defineProfile": DefineProfileEditorViewModel,
    "importDxfProfile": DefineProfileEditorViewModel,
    "defineRadialProfile": DefineRadialProfileEditorViewModel,
    "drilling": DrillingEditorViewModel,
    "threading": ThreadingEditorViewModel,
    "g33Threading": G33ThreadingEditorViewModel,
    "parting": PartingEditorViewModel,
    "tapping": TappingEditorViewModel,
}


def editor_for(tab, program, index, operation, parent=None):
    """The editor for the header (index -1) or the operation at ``index``,
    or None for a type without one."""
    if index < 0:
        return HeaderEditorViewModel(tab, program, index, operation, parent)
    editor_class = EDITORS.get(operation.get("type", ""))
    return editor_class(tab, program, index, operation, parent) if editor_class else None
