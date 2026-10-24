"""The view model behind each operation's editor in the Conversational tab.

One per operation type that has an editor, made by ConversationalViewModel
for the operation selected in the program (``editor_for``). It holds what the
editor shows - the operation, as ``operation`` - and what the editor asks:
the program's stock, the tool in by then, a preview of the cut. ``save``
sends an edit to the tab, which applies it and saves the program.

An editor is made for one operation at one place in the program. Selecting
another operation, or coming back to this one, makes a new one.
"""

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from teachinlathe.conversational.model.data_types import ThreadForm

# Thread depth over pitch, per side, for a 60° thread.
EXTERNAL_THREAD_HEIGHT_FACTOR = 0.61344
INTERNAL_THREAD_HEIGHT_FACTOR = 0.54127

EMPTY_PREVIEW = {"profile": [], "offset": [], "feeds": [], "rapids": []}


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
        return self._operation

    @pyqtProperty(QObject, constant=True)
    def touchedOffTools(self):
        """Every holder with a tool and both offsets set: the ones a program
        can change to, for the tool pickers."""
        return self._tab.touched_off_tools

    @pyqtSlot("QVariant")
    def save(self, payload):
        """The whole operation, with the editor's changes: applied and saved."""
        self._tab.update_operation(self.update_type, self._index, payload)


class HeaderEditorViewModel(OperationEditorViewModel):
    @pyqtSlot("QVariant")
    def save(self, payload):
        self._tab.update_header(payload)


class ToolOperationEditorViewModel(OperationEditorViewModel):
    """An operation drawn on the stock with the tool that cuts it, which the
    editor can change."""

    def __init__(self, tab, program, index, operation, parent=None):
        super().__init__(tab, program, index, operation, parent)
        self._tool_card = None

    @pyqtProperty("QVariant", constant=True)
    def workpiece(self):
        """The program header's stock, as its dict, or {}."""
        return self._use_case.workpiece(self._program)

    @pyqtProperty("QVariant", constant=True)
    def tool(self):
        """The tool the last Change Tool above puts in, as the backplot
        describes it, with its ``tool_no``; {} with none."""
        return self._use_case.tool_before(self._program, self._index)

    @pyqtProperty("QVariant", constant=True)
    def toolCard(self):
        """The same tool as the Tool Library's card shows it: {tool_no,
        card, view} - card the card's kind ("turning", ...), view its view
        (a TurningToolView, ...), for ToolTitles.js and the insert drawings.
        {} with no Change Tool; no card and no view when the holder is empty."""
        if self._tool_card is None:
            self._tool_card = self._make_tool_card()
        return self._tool_card

    def _make_tool_card(self):
        from teachinlathe.ui.tabs.programs.backplot import tool_source
        from teachinlathe.ui.tabs.tool_library.tool_library_models import card_and_view
        change = self._use_case.change_tool_before(self._program, self._index)
        if change is None:
            return {}
        # The view lives as long as this editor: QML holds only a reference.
        card, view = card_and_view(tool_source.tool_in(int(change.tool_no)), self)
        position = getattr(change, "toolchange_position", None)
        return {"tool_no": int(change.tool_no), "card": card, "view": view,
                "toolchange_position": getattr(position, "value", position) or "G28"}

    @pyqtSlot(int, str)
    def useTool(self, tool_no, toolchange_position):
        """Cut with tool ``tool_no``, changed to at ``toolchange_position``
        ("G28" or "G30"): the Change Tool right above changes to it, or one is
        put in. The editor is made again, with it."""
        self._tab.use_tool_before(self._index, tool_no, toolchange_position)


class FacingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "facing"

    @pyqtSlot("QVariant", result="QVariant")
    def preview(self, op_data):
        """What facing would cut with ``op_data``."""
        return self._tab.preview(lambda op: self._use_case.facing_preview(op), op_data)

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
        """For what this roughing leaves: a Change Tool with no tool yet and,
        after it, a copy of this roughing on rest material - opened."""
        self._tab.add_rest_roughing(self._index)


class ProfileContourEditorViewModel(ProfileFollowingEditorViewModel):
    update_type = "profileContour"

    @pyqtSlot("QVariant", result="QVariant")
    def preview(self, op_data):
        return self._tab.preview(
            lambda op: self._use_case.profile_contour_preview(self._program, self._index, op), op_data)


class DrillingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "drilling"


class TappingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "tapping"


class PartingEditorViewModel(ToolOperationEditorViewModel):
    update_type = "parting"


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


class ToolChangeEditorViewModel(OperationEditorViewModel):
    update_type = "changeTool"


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
        return self._tab.preview(self._preview, op_data)


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
    "changeTool": ToolChangeEditorViewModel,
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
