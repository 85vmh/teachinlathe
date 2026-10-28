// GrooveFinishingVisualDetailsView.qml — Groove Finishing on the groove's
// canvas (GrooveCanvas), laid out as Groove Roughing: the stock the Groove
// Roughing above left on the profile - what this takes off - the contour its
// strategy goes along, the blade where it starts - over the groove's middle,
// between P1 and P4 - and the boxes down the right edge: the strategy
// (GroovingBox) and the clearance.
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

    // the radial profile it finishes, and the header's stock
    property var    primitives:  []
    property string profileType: "od"
    property var    workpiece:   ({})
    // the tool it cuts with: editor.toolCard, a ToolCard; null with none
    property var    toolCard:    null

    // what an operation saved without a value has: a new one's, as
    // conversational/model/factories.py makes it
    readonly property var defaults: ({ profileId: 1, strategy: "towards_center", retract: 1.0 })

    readonly property var strategies: [
        { label: "Towards Center", value: "towards_center" },
        { label: "Towards Left", value: "towards_left" },
        { label: "Towards Right", value: "towards_right" }
    ]

    // the values the boxes on the canvas show and edit
    property int    profileId: defaults.profileId
    property string strategy: defaults.strategy
    property real   retract: defaults.retract

    readonly property bool hasGroove: profileCanvas.hasGroove
    // where the blade starts: over the groove's middle, the clearance out
    // from the start diameter - the pulley's outside with the stock the
    // roughing left on it - as the G-code goes there (retract is the clearance)
    readonly property var startPosition: groovePreview && groovePreview.start ? groovePreview.start : null
    // what it will cut with the values above: the contour, and the stock the
    // roughing left
    readonly property var groovePreview: (opIndex >= 0 && hasGroove && editor)
                                         ? editor.preview(_draftOp()) : null

    signal openNumPadRequested(var field)

    function _loadProfile() {
        var profileOp = editor ? (editor.radialProfile(profileId) || {}) : {}
        primitives  = JSON.parse(JSON.stringify(profileOp.profile_primitives || []))
        profileType = profileOp.profile_type !== undefined ? String(profileOp.profile_type) : "od"
    }

    // opData with the values edited in the boxes
    function _draftOp() {
        var op = JSON.parse(JSON.stringify(opData || {}))
        op.finishing_parameters = { profile_id: profileId, strategy: strategy }
        op.cutting_parameters = op.cutting_parameters || {}
        op.cutting_parameters.retract = retract
        return op
    }

    // the whole op with every edited value, sent as one save; opData keeps it,
    // so the next edit builds on this one
    function save(op) {
        if (opIndex < 0 || !opData) return
        opData = op || _draftOp()
        root.editor.save(opData)
    }

    function applyData(index, data) {
        opIndex = index
        opData  = data || {}
        workpiece = editor ? (editor.workpiece || {}) : {}
        toolCard  = editor ? editor.toolCard : null

        var fp = opData.finishing_parameters || {}
        var cp = opData.cutting_parameters || {}
        profileId = fp.profile_id !== undefined && Number(fp.profile_id) > 0
                    ? Math.round(Number(fp.profile_id)) : defaults.profileId
        strategy  = fp.strategy !== undefined ? String(fp.strategy) : defaults.strategy
        retract   = cp.retract !== undefined ? Number(cp.retract) : defaults.retract

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
            hasM1: false
            onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            onSpeedsAndFeedsEdited: function(speeds) {
                var op = root._draftOp()
                op.speeds_and_feeds = speeds
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
            startPosition: root.startPosition
            startDiameter: root.groovePreview && root.groovePreview.startDiameter != null
                           ? root.groovePreview.startDiameter : 0
            clearance: root.retract
            clearanceBoxRect: clearanceBox.rect
            boxWidth: Math.max(groovingBox.implicitWidth, clearanceBox.implicitWidth)

            GroovingBox {
                id: groovingBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: profileCanvas.boxGap
                accent: profileCanvas.groovingColor
                strategies: root.strategies
                showOffsets: false
                strategy: root.strategy
                onStrategyEdited: function(value) { root.strategy = value; root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }

            // how far out from the start diameter the blade starts and backs
            // off to: the cutting_parameters' retract
            DimensionBox {
                id: clearanceBox
                x: profileCanvas.width - width - profileCanvas.boxGap
                y: groovingBox.y + groovingBox.height + profileCanvas.boxGap
                label: "Clearance"
                dimensionColor: profileCanvas.clearanceColor
                settingName: "groove_finishing.clearance"
                value: root.retract
                onValueEdited: function(value) { root.retract = Math.abs(value); root.save() }
                onOpenNumPadRequested: function(field) { root.openNumPadRequested(field) }
            }
        }
    }
}
