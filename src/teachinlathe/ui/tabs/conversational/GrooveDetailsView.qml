// GrooveDetailsView.qml — what the groove operations' details views share
// (Groove Roughing, BiDirectional Grooving, Groove Finishing): the operation's
// header - speeds and feeds, and the inspection stop - over the groove's canvas
// (GrooveCanvas), the radial profile it cuts drawn on the header's stock with
// what the operation would cut, and the saving of the whole op on every edit.
//
// A view sets ``draftOp`` - the op with the values in its boxes - and
// ``readData`` - those values read from the op - and lays its boxes and marks
// over the canvas (its children go onto it), setting what the canvas draws of
// it through ``canvas`` (startPosition, clearance, boxWidth, extraMarkers).
import QtQuick
import QtQuick.Layouts
import theme

Item {
    id: root
    anchors.fill: parent

    // The view model of the operation this edits (OperationEditorViewModel.py).
    property var editor: null
    property int opIndex: -1
    property var opData: null

    // the radial profile it cuts, and the header's stock
    property var    primitives:  []
    property string profileType: "od"
    property var    workpiece:   ({})
    // the tool it cuts with: editor.toolCard, a ToolCard; null with none
    property var    toolCard:    null

    // the Define Radial Profile it cuts, as readData reads it
    property int  profileId: 1
    // the stock to leave its Stock to Leave box edits; 0 for a view with none
    property real stockRadial: 0.0
    property real stockAxial: 0.0
    // whether its header has the inspection stop
    property bool hasM1: true

    // opData with the values edited in the view's boxes
    property var draftOp: function() { return copyOf(opData) }
    // the view's values read from ``data``, an op's dict
    property var readData: function(data) {}

    readonly property alias canvas: profileCanvas
    // the view's boxes and marks, laid over the canvas
    default property alias canvasContent: profileCanvas.data

    readonly property bool hasGroove: profileCanvas.hasGroove
    // what it will cut with the values in its boxes, as its view model's
    // preview has it
    readonly property var groovePreview: (opIndex >= 0 && hasGroove && editor) ? editor.preview(draftOp()) : null

    signal openNumPadRequested(var field)

    // ``data`` copied, for a draft of it to be changed
    function copyOf(data) {
        return JSON.parse(JSON.stringify(data || {}))
    }

    // ``values[key]`` as a number, ``fallback`` when it has none
    function numberIn(values, key, fallback) {
        return values && values[key] !== undefined ? Number(values[key]) : fallback
    }

    // the profile id in ``values`` - an op's parameters - or ``fallback``
    function profileIdIn(values, fallback) {
        var id = numberIn(values, "profile_id", 0)
        return id > 0 ? Math.round(id) : fallback
    }

    // ``op`` with the stock to leave in the boxes - on when there is any
    function withStock(op) {
        op.stock_to_leave = { radial: stockRadial, axial: stockAxial }
        op.stock_to_leave_enabled = stockRadial > 0 || stockAxial > 0
        return op
    }

    // the stock to leave of ``data`` into the boxes - none when it is off
    function readStock(data) {
        var on = !!data.stock_to_leave_enabled
        stockRadial = on ? numberIn(data.stock_to_leave, "radial", 0) : 0
        stockAxial  = on ? numberIn(data.stock_to_leave, "axial", 0) : 0
    }

    function _loadProfile() {
        var profileOp = editor ? (editor.radialProfile(profileId) || {}) : {}
        primitives  = copyOf(profileOp.profile_primitives || [])
        profileType = profileOp.profile_type !== undefined ? String(profileOp.profile_type) : "od"
    }

    // the whole op with every edited value, sent as one save; opData keeps it,
    // so the next edit builds on this one
    function save(op) {
        if (opIndex < 0 || !opData) return
        opData = op || draftOp()
        root.editor.save(opData)
    }

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}
        workpiece = editor ? (editor.workpiece || {}) : {}
        toolCard  = editor ? editor.toolCard : null
        readData(opData)
        _loadProfile()
        header.applyData(opData)
        profileCanvas.resetView()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: Theme.innerSpacings

        // each edit goes into the whole op with the canvas boxes' values
        OperationHeader {
            id: header
            hasM1: root.hasM1
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) {
                var op = root.draftOp()
                op.speeds_and_feeds = speeds
                root.save(op)
            }
            onM1Edited: function(m1) {
                var op = root.draftOp()
                op.m1_parameters = m1
                root.save(op)
            }
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
