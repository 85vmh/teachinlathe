"""The view model behind each operation's editor in the Conversational tab.

One per operation type that has an editor, made by ConversationalViewModel
for the operation selected in the program (``editor_for``). It holds what the
editor shows - the operation, as ``operation`` - and what the editor asks:
the program's stock, the tool in by then, a preview of the cut. ``save``
sends an edit to the tab, which applies it and saves the program.

An editor is made for one operation at one place in the program. Selecting
another operation, or coming back to this one, makes a new one.
"""

import dataclasses
from enum import Enum

from PyQt6.QtCore import QObject, pyqtEnum, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.conversational.logic.program_tools import Scope as ProgramToolScope
from teachinlathe.conversational.logic.program_tools import ToolStatus
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


class OperationEditorViewModel(QObject):
    #: The operation type its edits are applied as (ConversationalUseCase._updaters).
    update_type = ""

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(parent)
        self._tab = tab
        self._use_case = tab.use_case
        self._program = program
        self._index = index
        self._operation = operation

    @pyqtProperty(str, constant=True)
    def operationType(self):
        return str(self._operation.get("type", "")) if self._index >= 0 else "header"

    @pyqtProperty(int, constant=True)
    def opIndex(self):
        return self._index

    @pyqtProperty("QVariant", constant=True)
    def operation(self):
        """The operation as the editor shows it."""
        return PauseToInspect.for_qml(self._operation)

    @pyqtProperty(QObject, constant=True)
    def touchedOffTools(self):
        """Every holder with a tool and both offsets set: the ones a program
        can change to, for the tool pickers."""
        return self._tab.touched_off_tools

    @pyqtSlot("QVariant")
    def save(self, payload):
        """The whole operation, with the editor's changes: applied and saved."""
        self._tab.update_operation(self.update_type, self._index, PauseToInspect.from_qml(to_py(payload)))


class HeaderEditorViewModel(OperationEditorViewModel):
    @pyqtSlot("QVariant")
    def save(self, payload):
        self._tab.update_header(payload)


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

    #: The holders whose tool the operation can cut with may have changed:
    #: the Tool Library did, or the operation (an OD profile become ID).
    suitableToolNosChanged = pyqtSignal()

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        self._tool_card = None
        from teachinlathe.core.tool_library_repository import tool_library_repository
        tool_library_repository().toolsChanged.connect(self.suitableToolNosChanged)

    @pyqtProperty("QVariantList", notify=suitableToolNosChanged)
    def suitableToolNos(self):
        """The T numbers whose tool the operation can cut with: the only
        ones its tool picker shows."""
        return self._use_case.suitable_tool_nos(self._program, self._index)

    @pyqtSlot("QVariant")
    def save(self, payload):
        super().save(payload)
        self.suitableToolNosChanged.emit()

    @pyqtProperty("QVariant", constant=True)
    def workpiece(self):
        """The program header's stock, as its dict, or {}."""
        return self._use_case.workpiece(self._program)

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

    @pyqtSlot("QVariant", result="QVariant")
    def preview(self, op_data):
        """What facing would cut with ``op_data``."""
        return self._tab.preview(lambda op: qml_preview(self._use_case.facing_preview(op)), op_data)

    # Shared by every Facing of the program: kept by the tab.
    def _get_canvas_mirror(self):
        return self._tab.facingMirror

    def _set_canvas_mirror(self, on):
        self._tab.facingMirror = on

    canvasMirror = pyqtProperty(bool, _get_canvas_mirror, _set_canvas_mirror)


class ProfileFollowingEditorViewModel(ToolOperationEditorViewModel):
    """Profile Roughing and Profile Contour: they cut the last profile above."""

    @pyqtProperty("QVariant", constant=True)
    def lastProfile(self):
        """The last Define Profile above, as its details payload, or {}."""
        return self._use_case.last_profile_before(self._program, self._index)


class ProfileRoughingEditorViewModel(ProfileFollowingEditorViewModel):
    update_type = "profileRoughing"

    #: A preview asked for with requestPreview, once worked out.
    previewReady = pyqtSignal("QVariant")

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        #: what the last request went in with: an answer for an older one is
        #: not passed on
        self.wanted_preview = None

    @pyqtSlot("QVariant")
    def requestPreview(self, op_data):
        """What roughing would cut with ``op_data``, to ``previewReady``: the
        plan takes up to a second, so it is worked out in the planning worker
        and the screen goes on meanwhile."""
        self._tab.request_roughing_preview(self, self._index, op_data)

    @pyqtSlot()
    def addRestRoughing(self):
        """For what this roughing leaves: a copy of this roughing on rest
        material, with no tool yet - opened."""
        self._tab.add_rest_roughing(self._index)


class ProfileContourEditorViewModel(ProfileFollowingEditorViewModel):
    update_type = "profileContour"

    @pyqtSlot("QVariant", result="QVariant")
    def preview(self, op_data):
        return self._tab.preview(
            lambda op: qml_preview(self._use_case.profile_contour_preview(self._program, self._index, op)), op_data)


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

    @pyqtSlot("QVariant", result="QVariant")
    def preview(self, op_data):
        """What drilling would cut with ``op_data``: a feed each peck."""
        return self._tab.preview(lambda op: qml_preview(self._use_case.drilling_preview(op)), op_data)

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

    @pyqtSlot("QVariant", result="QVariant")
    def preview(self, op_data):
        """What parting would cut with ``op_data``: its edge break and feeds."""
        return self._tab.preview(lambda op: qml_preview(self._use_case.parting_preview(op)), op_data)


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


class ThreadingEditorViewModel(OperationEditorViewModel):
    update_type = "threading"

    @pyqtSlot(str, "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def calculateThreadDiameter(self, location, pitch, major_diameter, minor_diameter):
        return calculate_thread_diameter(location, pitch, major_diameter, minor_diameter)


class G33ThreadingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "g33Threading"

    @pyqtSlot(str, result=float)
    def threadAngle(self, form):
        return thread_angle(form)

    @pyqtSlot(str, "QVariant", "QVariant", "QVariant", result="QVariantMap")
    def calculateThreadDiameter(self, location, pitch, major_diameter, minor_diameter):
        return calculate_thread_diameter(location, pitch, major_diameter, minor_diameter)


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
    """Groove Roughing and Groove Finishing: they cut a radial profile above,
    and show what they would cut (``_preview``: the use case's preview)."""

    def _preview(self, op):
        raise NotImplementedError

    @pyqtSlot(int, result="QVariant")
    def radialProfile(self, profile_id):
        """The Define Radial Profile ``profile_id`` above - the last one with
        none - as its details payload, or {}."""
        return self._use_case.radial_profile_before(self._program, self._index, profile_id)

    @pyqtSlot("QVariant", result="QVariant")
    def preview(self, op_data):
        """What it would cut with ``op_data``."""
        return self._tab.preview(lambda op: qml_preview(self._preview(op)), op_data)


class GrooveRoughingEditorViewModel(GrooveEditorViewModel):
    update_type = "grooveRoughing"

    def _preview(self, op):
        return self._use_case.groove_roughing_preview(self._program, self._index, op)


class GrooveFinishingEditorViewModel(GrooveEditorViewModel):
    update_type = "grooveFinishing"

    def _preview(self, op):
        return self._use_case.groove_finishing_preview(self._program, self._index, op)


class DefineProfileEditorViewModel(OperationEditorViewModel):
    """A profile drawn by hand or read from a drawing: its summary in the
    details pane, the full screen editor, and the DXF import screen."""
    update_type = "defineProfile"

    @pyqtProperty("QVariant", constant=True)
    def workpiece(self):
        return self._use_case.workpiece(self._program)

    @pyqtSlot()
    def openEditor(self):
        self._tab.open_profile_editor(self._index)

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


# The editor for each operation type.
EDITORS = {
    "positionAt": PositionAtEditorViewModel,
    "facing": FacingEditorViewModel,
    "knurling": KnurlingEditorViewModel,
    "profiling": ProfilingEditorViewModel,
    "profileRoughing": ProfileRoughingEditorViewModel,
    "profileContour": ProfileContourEditorViewModel,
    "grooveRoughing": GrooveRoughingEditorViewModel,
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
