// GrooveDetailsView.qml — what the groove operations' details views share
// (Groove Roughing, BiDirectional Grooving, Groove Finishing): the operation's
// header - speeds and feeds, and the inspection stop - over the groove's canvas
// (GrooveCanvas), the radial profile it cuts drawn on the header's stock with
// what the operation cuts. It keeps nothing of its own: all it shows is its
// editor's operation, and every change is the editor's edit, which the
// operation then shows.
//
// A view binds ``profileId`` - the Define Radial Profile its operation names -
// and its values to ``op``, and lays its boxes and marks over the canvas (its
// children go onto it), setting what the canvas draws of it through
// ``canvas`` (startPosition, clearance, boxWidth, extraMarkers).
import QtQuick
import QtQuick.Layouts
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py):
    // the one place what the view shows comes from, and every edit goes to
    required property var editor
    readonly property var op: editor.operation

    // the header's stock, and the tool it cuts with: editor.toolCard, a ToolCard
    readonly property var workpiece: editor.workpiece || ({})
    readonly property var toolCard: editor.toolCard

    // the Define Radial Profile it cuts: bound by the view to its operation's
    property int profileId: 1
    // the radial profile it cuts
    readonly property var _profileOp: editor.radialProfile(profileId) || ({})
    readonly property var primitives: _profileOp.profile_primitives || []
    readonly property string profileType: _profileOp.profile_type !== undefined ? String(_profileOp.profile_type) : "od"

    // the stock to leave its Stock to Leave box edits - none while it is off
    readonly property bool _stockOn: !!op.stock_to_leave_enabled
    readonly property real stockRadial: _stockOn ? numberIn(op.stock_to_leave, "radial", 0) : 0
    readonly property real stockAxial: _stockOn ? numberIn(op.stock_to_leave, "axial", 0) : 0
    // whether its header has the inspection stop
    property bool hasM1: true

    readonly property alias canvas: profileCanvas
    // the view's boxes and marks, laid over the canvas
    default property alias canvasContent: profileCanvas.data

    readonly property bool hasGroove: profileCanvas.hasGroove
    // what it cuts, as its view model's preview has it
    readonly property var groovePreview: hasGroove ? editor.preview : null

    signal openNumPadRequested(var field)

    // ``values[key]`` as a number, ``fallback`` when it has none
    function numberIn(values, key, fallback) {
        return values && values[key] !== undefined ? Number(values[key]) : fallback
    }

    // the profile id in ``values`` - an op's parameters - or ``fallback``
    function profileIdIn(values, fallback) {
        var id = numberIn(values, "profile_id", 0)
        return id > 0 ? Math.round(id) : fallback
    }

    // a change to the stock to leave: on when there is any
    function editStock(changes) {
        var radial = changes.radial !== undefined ? changes.radial : stockRadial
        var axial = changes.axial !== undefined ? changes.axial : stockAxial
        editor.edit({ stock_to_leave: { radial: radial, axial: axial },
                      stock_to_leave_enabled: radial > 0 || axial > 0 })
    }
    function editCutting(changes) { editor.edit({ cutting_parameters: changes }) }

    // another operation: the drawing fitted to it
    onEditorChanged: profileCanvas.resetView()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        OperationHeader {
            id: header
            editor: root.editor
            hasM1: root.hasM1
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
        }

        GrooveCanvas {
            id: profileCanvas
            Layout.fillWidth: true
            Layout.fillHeight: true
            editor: root.editor
            toolCard: root.toolCard
            profileId: root.profileId
            primitives: root.primitives
            profileType: root.profileType
            workpiece: root.workpiece
            preview: root.groovePreview
            startDiameter: root.groovePreview && root.groovePreview.startDiameter != null
                           ? root.groovePreview.startDiameter : 0
        }
    }
}
